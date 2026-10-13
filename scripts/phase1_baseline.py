#!/usr/bin/env python3
"""Read-only/simulation-oriented Phase 1 runtime smoke checks.

This deliberately does not stop containers or claim exactly-once task execution.
Those require a controlled, destructive failure-injection scenario and task IDs
whose lifecycle can be observed end to end.
"""
import argparse
import asyncio
import json
import sys
import time
import urllib.error
import urllib.request


def request_json(url, method="GET", payload=None, timeout=10):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return response.status, json.loads(body) if body else {}


def check(name, fn, results):
    try:
        detail = fn()
        results.append((name, True, str(detail)))
        print(f"PASS  {name}: {detail}")
    except Exception as exc:
        results.append((name, False, str(exc)))
        print(f"FAIL  {name}: {exc}")


async def websocket_probe(url):
    import websockets
    async with websockets.connect(url, open_timeout=8, close_timeout=3):
        return "WebSocket handshake accepted"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--frontend-url", default="http://localhost:3000")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    results = []

    def api_health():
        status, body = request_json(base + "/api/health")
        return f"HTTP {status}; keys={sorted(body)[:8]}"

    def registry():
        deadline = time.time() + 90
        latest = {}
        while time.time() < deadline:
            _, latest = request_json(base + "/api/satellites")
            sats = latest.get("satellites", [])
            ids = {s.get("satellite_id") for s in sats}
            expected = {f"SAT-0{i}" for i in range(1, 6)}
            if expected.issubset(ids):
                return f"registered {sorted(expected)}; registry count={latest.get('count', len(sats))}"
            time.sleep(3)
        raise AssertionError(f"Expected SAT-01..SAT-05; observed {[s.get('satellite_id') for s in latest.get('satellites', [])]}")

    def observatory():
        status, body = request_json(base + "/api/observatory/stats")
        return f"HTTP {status}; satellites_count={body.get('satellites_count')}"

    def tasks():
        status, body = request_json(base + "/api/tasks")
        return f"HTTP {status}; task_count={len(body.get('tasks', []))}"

    def election():
        status, body = request_json(base + "/api/election/ring?initiator_id=SAT-01", method="POST", payload={})
        return f"HTTP {status}; response_keys={sorted(body)[:10]}"

    def scenario():
        status, body = request_json(
            base + "/api/simulation/execute",
            method="POST",
            payload={"target_node": "SAT-05", "scenario_type": "COORDINATOR_FAILURE"},
            timeout=30,
        )
        return f"HTTP {status}; response_keys={sorted(body)[:10]} (simulation API result; not a container-kill test)"

    def frontend():
        with urllib.request.urlopen(args.frontend_url, timeout=10) as response:
            return f"HTTP {response.status}; content-type={response.headers.get('Content-Type')}"

    check("API /api/health", api_health, results)
    check("Five satellite registrations", registry, results)
    check("Observatory stats", observatory, results)
    check("Task API", tasks, results)
    check("Ring election API", election, results)
    check("Coordinator-failure simulation endpoint", scenario, results)
    check("Frontend HTTP response", frontend, results)

    ws_url = base.replace("http://", "ws://", 1).replace("https://", "wss://", 1) + "/ws"
    check("WebSocket handshake", lambda: asyncio.run(websocket_probe(ws_url)), results)

    print("\nNOT RUN (requires dedicated controlled scenario):")
    print("- Actual coordinator container termination and subsequent live election/recovery")
    print("- Task interruption, durable task-state recovery, and duplicate-execution assertion")
    print("- Database restart/persistence verification")
    print("- Browser interaction/console smoke test")
    print("\nSummary: %d passed, %d failed" % (sum(ok for _, ok, _ in results), sum(not ok for _, ok, _ in results)))
    sys.exit(1 if any(not ok for _, ok, _ in results) else 0)


if __name__ == "__main__":
    main()
