"""
Serverless runtime (Unit 4: serverless architectures), in Mission Control.

- Functions are registered by name with a trigger on the mission event bus (RabbitMQ events).
- Each function INSTANCE is a separate OS process. The first invocation pays a COLD START
  (spawn the process, import the code); later invocations reuse an idle WARM instance.
- Up to MAX_INSTANCES per function run concurrently; idle instances are terminated after
  IDLE_TIMEOUT seconds - the function scales to zero.
- Outputs are written to OrbitFS; every invocation is recorded with cold/warm, timings and PID.
"""

import asyncio
import base64
import logging
import multiprocessing as mp
import time
import uuid
from typing import Any, Awaitable, Callable, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException

from backend.fa2.bus import mission_bus
from backend.fa2.event_store import event_store
from backend.fa2.functions import worker_main
from backend.fa2_extensions.catalog import TASKS_BY_ID

logger = logging.getLogger("Serverless")
router = APIRouter(prefix="/api/serverless", tags=["Unit 4: serverless"])

MAX_INSTANCES = 3
IDLE_TIMEOUT = 20.0
_ctx = mp.get_context("spawn")


class Instance:
    def __init__(self, fn: str):
        self.fn = fn
        self.id = f"{fn}-{uuid.uuid4().hex[:4]}"
        self.parent, child = _ctx.Pipe()
        self.proc = _ctx.Process(target=worker_main, args=(fn, child), daemon=True)
        self.busy = True
        self.created = time.time()
        self.last_used = time.time()
        self.pid: Optional[int] = None
        self.invocations = 0

    def start_blocking(self) -> float:
        t = time.time()
        self.proc.start()
        if not self.parent.poll(30):
            raise RuntimeError("function instance did not start in 30 s")
        self.pid = self.parent.recv()["pid"]
        return (time.time() - t) * 1000

    def call_blocking(self, job: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        self.parent.send(job)
        if not self.parent.poll(timeout):
            raise TimeoutError("function timed out")
        return self.parent.recv()

    def stop(self) -> None:
        try:
            self.parent.send(None)
        except Exception:
            pass
        self.proc.join(timeout=2)
        if self.proc.is_alive():
            self.proc.terminate()


class Spec:
    def __init__(self, name: str, description: str, trigger: str,
                 matches: Callable[[Dict[str, Any]], bool],
                 prepare: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]],
                 output: Callable[[Dict[str, Any], Dict[str, Any]], str]):
        self.name, self.description, self.trigger = name, description, trigger
        self.matches, self.prepare, self.output = matches, prepare, output


class Runtime:
    def __init__(self):
        self.specs: Dict[str, Spec] = {}
        self.instances: Dict[str, List[Instance]] = {}
        self.invocations: List[Dict[str, Any]] = []
        self.scale_events: List[Dict[str, Any]] = []
        self._recent_triggers: Dict[str, float] = {}

    def register(self, spec: Spec) -> None:
        self.specs[spec.name] = spec
        self.instances.setdefault(spec.name, [])

    async def _acquire(self, fn: str) -> (Instance, bool, Optional[float]):
        while True:
            for inst in self.instances[fn]:
                if not inst.busy and inst.proc.is_alive():
                    inst.busy = True
                    return inst, False, None
            if len(self.instances[fn]) < MAX_INSTANCES:
                inst = Instance(fn)
                self.instances[fn].append(inst)
                try:
                    cold_ms = await asyncio.get_running_loop().run_in_executor(None, inst.start_blocking)
                except Exception:
                    self.instances[fn].remove(inst)
                    raise
                self.scale_events.append({"at": time.time(), "function": fn, "event": "SCALED_UP",
                                          "instances": len(self.instances[fn]), "pid": inst.pid})
                return inst, True, round(cold_ms, 1)
            await asyncio.sleep(0.05)   # all instances busy and at the limit: queue

    async def invoke(self, fn: str, event: Dict[str, Any], trigger: str = "manual") -> Dict[str, Any]:
        spec = self.specs.get(fn)
        if not spec:
            raise HTTPException(404, f"no function {fn}")
        t0 = time.time()
        record = {"invocation_id": f"inv-{uuid.uuid4().hex[:8]}", "function": fn, "trigger": trigger,
                  "event_type": event.get("type"), "started_at": t0}
        inst, cold, cold_ms = await self._acquire(fn)
        try:
            payload = {"event": event, "input": await spec.prepare(event)}
            res = await asyncio.get_running_loop().run_in_executor(None, inst.call_blocking, payload)
        except Exception as exc:
            res = {"ok": False, "error": f"{exc.__class__.__name__}: {exc}"}
        finally:
            inst.busy, inst.last_used = False, time.time()
            inst.invocations += 1
        record.update({"cold_start": cold, "cold_start_ms": cold_ms, "instance": inst.id, "pid": inst.pid,
                       "exec_ms": res.get("exec_ms"), "total_ms": round((time.time() - t0) * 1000, 1),
                       "status": "OK" if res.get("ok") else "ERROR", "error": res.get("error")})
        if res.get("ok"):
            try:
                from backend.fa2.orbitfs import archive_json
                record["output_path"] = await archive_json(spec.output(event, res["result"]), res["result"])
            except Exception as exc:
                record["output_error"] = str(exc)
            record["result"] = res["result"]
        self.invocations.append(record)
        del self.invocations[:-200]
        return record

    async def on_event(self, event: Dict[str, Any]) -> None:
        from backend.fa2.role import is_active
        if not is_active():
            return  # a passive standby replica sees the events but does not run functions
        for spec in self.specs.values():
            try:
                if spec.matches(event):
                    asyncio.ensure_future(self.invoke(spec.name, event, trigger=f"event:{event.get('type')}"))
            except Exception as exc:  # pragma: no cover
                logger.warning("trigger check failed: %s", exc)

    def once_per(self, key: str, seconds: float) -> bool:
        now = time.time()
        if now - self._recent_triggers.get(key, 0) < seconds:
            return False
        self._recent_triggers[key] = now
        return True

    async def reap(self) -> None:
        while True:
            await asyncio.sleep(3.0)
            try:
                for fn, insts in self.instances.items():
                    for inst in list(insts):
                        if not inst.busy and time.time() - inst.last_used > IDLE_TIMEOUT:
                            insts.remove(inst)
                            await asyncio.get_running_loop().run_in_executor(None, inst.stop)
                            self.scale_events.append({"at": time.time(), "function": fn, "pid": inst.pid,
                                                      "event": "SCALED_TO_ZERO" if not insts else "SCALED_DOWN",
                                                      "instances": len(insts)})
            except asyncio.CancelledError:
                break
            except Exception as exc:  # pragma: no cover
                logger.warning("reaper error: %s", exc)

    def shutdown(self) -> None:
        for insts in self.instances.values():
            for inst in insts:
                inst.stop()

    def status(self) -> Dict[str, Any]:
        return {"max_instances": MAX_INSTANCES, "idle_timeout_s": IDLE_TIMEOUT, "functions": [
            {"name": s.name, "description": s.description, "trigger": s.trigger,
             "warm_instances": sum(1 for i in self.instances[s.name] if i.proc.is_alive()),
             "busy": sum(1 for i in self.instances[s.name] if i.busy),
             "invocations": sum(1 for r in self.invocations if r["function"] == s.name),
             "cold_starts": sum(1 for r in self.invocations if r["function"] == s.name and r["cold_start"])}
            for s in self.specs.values()]}


runtime = Runtime()


# ------------------------------------------------------------------ the three functions
async def _incident_input(event: Dict[str, Any]) -> Dict[str, Any]:
    since = (event.get("at") or time.time()) - 60
    keep = {"PEER_SUSPECTED", "PEER_DEAD", "LEADER_LOST", "LEADER_ELECTED", "TASK_REASSIGNED", "ELECTION_START"}
    await asyncio.sleep(6.0)  # give the satellites time to finish electing / reassigning first
    return {"events": [e for e in event_store.query(since=since, limit=5000, include_background=True)
                       if e.get("label") in keep]}


async def _image_input(event: Dict[str, Any]) -> Dict[str, Any]:
    from backend.fa2.orbitfs import namenode
    data, _ = await namenode.read(event["path"])
    return {"data_b64": base64.b64encode(data).decode()}


async def _snapshot_input(event: Dict[str, Any]) -> Dict[str, Any]:
    return {"snapshot": event.get("snapshot"), "expected_tasks": sorted(TASKS_BY_ID)}


runtime.register(Spec(
    "incident_report", "Writes an incident report when satellites declare a peer dead", "PEER_DEAD (satellite event)",
    lambda e: e.get("type") == "PEER_DEAD" and runtime.once_per(f"inc-{(e.get('detail') or {}).get('peer')}", 30),
    _incident_input,
    lambda e, r: f"incidents/{r['incident']}.json"))
runtime.register(Spec(
    "image_stats", "Analyses images uploaded to OrbitFS under images/", "FILE_UPLOADED images/*",
    lambda e: e.get("type") == "FILE_UPLOADED" and str(e.get("path", "")).startswith("images/")
    and not str(e.get("path", "")).endswith(".stats.json"),
    _image_input,
    lambda e, r: f"{e['path']}.stats.json"))
runtime.register(Spec(
    "snapshot_audit", "Independently re-checks every Chandy-Lamport snapshot", "SNAPSHOT_COMPLETED",
    lambda e: e.get("type") == "SNAPSHOT_COMPLETED",
    _snapshot_input,
    lambda e, r: f"audits/{r['snapshot_id']}.json"))

mission_bus.subscribe(runtime.on_event)


# ------------------------------------------------------------------ API
@router.get("/functions")
async def functions():
    return runtime.status()


@router.post("/invoke")
async def invoke(body: Dict[str, Any] = Body(...)):
    fn = body.get("function")
    event = body.get("event") or {}
    if fn == "image_stats" and "path" not in event:
        raise HTTPException(422, "image_stats needs event.path of an image in OrbitFS")
    if fn == "incident_report" and not (event.get("detail") or {}).get("peer"):
        raise HTTPException(422, "incident_report needs event.detail.peer")
    return await runtime.invoke(fn, {"type": "MANUAL", "at": time.time(), **event}, trigger="manual")


@router.get("/invocations")
async def invocations(limit: int = 30):
    return {"invocations": runtime.invocations[-limit:][::-1], "scale_events": runtime.scale_events[-20:][::-1]}
