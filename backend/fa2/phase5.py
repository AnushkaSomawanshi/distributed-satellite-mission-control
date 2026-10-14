"""
FA-2 Phase 5 Mission Control API: the CAP demo.
- /api/fa2/ledger : CP command ledger (signed hash chain on the satellites, majority quorum)
- /api/fa2/board  : AP status board (vector-clock replicated key-value store on the satellites)
Mission Control forwards requests and verifies chains; the satellites hold the data and decide.
"""

import hashlib
import json
import time
from collections import Counter
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException

from backend.fa2.router import _responsive, call, call_all, get_status, states

router = APIRouter(prefix="/api/fa2", tags=["FA-2 phase 5: CAP"])


def _leader_of(sid: str, st: Dict[str, Dict[str, Any]]) -> Optional[str]:
    return ((st.get(sid) or {}).get("election") or {}).get("leader")


# satellites/dsync/ledger.py is not shipped in the backend image, so Mission Control has its own
# independent verifier (same rules: hash links, content hash, >= 3 valid Ed25519 signatures).


def _block_hash(block: Dict[str, Any]) -> str:
    body = {k: block[k] for k in ("index", "prev_hash", "commands", "term", "proposer", "timestamp")}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _verify_sig(pub_hex: str, sig_hex: str, digest: str) -> bool:
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex)).verify(bytes.fromhex(sig_hex), digest.encode())
        return True
    except Exception:
        return False


def verify_chain(chain, pubkeys, quorum: int = 3) -> Dict[str, Any]:
    prev = "GENESIS"
    for i, b in enumerate(chain):
        if b.get("index") != i or b.get("prev_hash") != prev:
            return {"valid": False, "bad_index": i, "reason": "broken link"}
        digest = _block_hash(b)
        if digest != b.get("hash"):
            return {"valid": False, "bad_index": i, "reason": "content does not match hash (tampered)"}
        good = sum(1 for s, sig in (b.get("signatures") or {}).items() if s in pubkeys and _verify_sig(pubkeys[s], sig, digest))
        if good < quorum:
            return {"valid": False, "bad_index": i, "reason": f"{good} valid signatures < {quorum}"}
        prev = digest
    return {"valid": True, "height": len(chain), "tip": prev}


@router.get("/ledger")
async def ledger_view():
    """Each satellite's copy, verified independently by Mission Control, plus the majority view."""
    res = await call_all("GET", "/dsync/ledger", timeout=3.0)
    pubkeys: Dict[str, str] = {}
    for ok, data in res.values():
        if ok:
            pubkeys.update(data.get("pubkeys") or {})
    copies = {}
    for sid, (ok, data) in res.items():
        if not ok:
            copies[sid] = {"reachable": False}
            continue
        v = verify_chain(data["chain"], pubkeys)
        copies[sid] = {"reachable": True, "height": len(data["chain"]), "tip": data["chain"][-1]["hash"] if data["chain"] else "GENESIS",
                       "verification": v}
    tips = Counter(c["tip"] for c in copies.values() if c.get("reachable") and c["verification"]["valid"])
    majority_tip = tips.most_common(1)[0][0] if tips else None
    reference = next((data["chain"] for sid, (ok, data) in res.items() if ok and copies[sid]["tip"] == majority_tip), [])
    for c in copies.values():
        if c.get("reachable"):
            c["agrees_with_majority"] = c["tip"] == majority_tip
    return {"quorum": 3, "copies": copies, "majority_tip": majority_tip,
            "blocks": [{"index": b["index"], "hash": b["hash"], "prev_hash": b["prev_hash"], "proposer": b["proposer"],
                        "term": b["term"], "timestamp": b["timestamp"], "signers": sorted(b["signatures"]),
                        "commands": b["commands"]} for b in reference][::-1]}


@router.post("/ledger/submit")
async def ledger_submit(body: Dict[str, Any] = Body(...)):
    st = await states()
    via = body.get("via")
    if not via:
        via = (await get_status())["agreed_leader"]
        if not via:
            raise HTTPException(409, "no agreed leader; pass 'via' = the leader of one partition side")
    leader = _leader_of(via, st)
    if leader != via:
        raise HTTPException(409, f"{via} is not a leader (it follows {leader}); submit through {leader}")
    ok, data = await call(via, "POST", "/dsync/control/ledger",
                          {"action": "submit", "command": {k: body.get(k) for k in ("action", "target", "params")}}, timeout=20.0)
    if not ok:
        raise HTTPException(409, data)
    return {"submitted_via": via, **data}


@router.post("/ledger/tamper")
async def ledger_tamper(body: Dict[str, Any] = Body(...)):
    ok, data = await call(body.get("target", ""), "POST", "/dsync/control/ledger", {"action": "tamper", "index": int(body.get("index", 0))})
    if not ok:
        raise HTTPException(409, data)
    return data


@router.post("/ledger/repair")
async def ledger_repair(body: Dict[str, Any] = Body(...)):
    ok, data = await call(body.get("target", ""), "POST", "/dsync/control/ledger", {"action": "repair"}, timeout=15.0)
    if not ok:
        raise HTTPException(409, data)
    return data


@router.get("/board")
async def board_view():
    st = await states()
    return {"satellites": {sid: {"reachable": not s.get("unreachable"), "silent": s.get("silent"),
                                 "partition": s.get("partition_groups"), **(s.get("board") or {})}
                           for sid, s in st.items()}}


@router.post("/board/put")
async def board_put(body: Dict[str, Any] = Body(...)):
    via, key = body.get("via"), body.get("key")
    if not via or not key:
        raise HTTPException(422, "via and key are required")
    ok, data = await call(via, "POST", "/dsync/control/board", {"action": "put", "key": key, "value": body.get("value")})
    if not ok:
        raise HTTPException(409, data)
    return data


@router.post("/board/resolve")
async def board_resolve(body: Dict[str, Any] = Body(...)):
    ok, data = await call(body.get("via", ""), "POST", "/dsync/control/board",
                          {"action": "resolve", "key": body.get("key"), "strategy": body.get("strategy", "lww")})
    if not ok:
        raise HTTPException(409, data)
    return data


@router.get("/cap/status")
async def cap_status():
    st = await states()
    return {"partition": next((s.get("partition_groups") for s in st.values() if s.get("partition_groups")), None),
            "leaders": {sid: _leader_of(sid, st) for sid in st if not st[sid].get("unreachable")},
            "ledger_heights": {sid: (s.get("ledger") or {}).get("height") for sid, s in st.items()},
            "board_conflicts": {sid: sum(1 for v in ((s.get("board") or {}).get("keys") or {}).values() if len(v) > 1)
                                for sid, s in st.items()},
            "at": time.time()}
