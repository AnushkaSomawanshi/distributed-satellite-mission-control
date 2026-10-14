"""
Tamper-evident command ledger (self-study: blockchain / distributed ledger) - the CP side of the CAP demo.

- Every satellite keeps a full copy of a hash-chained ledger of mission commands.
- Block = {index, prev_hash, commands, term, proposer, timestamp}; its hash covers all of that.
- Proof of authority: each satellite has an Ed25519 key (public keys travel in beacons). The leader
  proposes a block; each satellite checks it extends its own chain and signs the block hash.
  A block is committed only with signatures from a MAJORITY OF ALL 5 satellites (3). On the minority
  side of a partition no block can reach 3 signatures, so writes are refused: consistency over
  availability (CP).
- Satellites that fall behind fetch missing blocks from a peer with a longer chain and verify every
  hash link and signature before appending.
- Any edit to a stored block breaks its hash (and the next block's prev_hash), so verification
  pinpoints the tampered block.
"""

import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional

from .transport import PeerUnreachable

logger = logging.getLogger("dsync.ledger")

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    HAS_CRYPTO = True
except Exception:  # pragma: no cover
    HAS_CRYPTO = False

CONSTELLATION_SIZE = 5
QUORUM = CONSTELLATION_SIZE // 2 + 1
ACTIONS = {"SET_POWER_MODE", "POINT_PAYLOAD", "RESET_FAULTS", "SET_TASK_PRIORITY", "SCHEDULE_DOWNLINK"}


def block_hash(block: Dict[str, Any]) -> str:
    body = {k: block[k] for k in ("index", "prev_hash", "commands", "term", "proposer", "timestamp")}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def verify_signature(pub_hex: str, sig_hex: str, digest: str) -> bool:
    if not HAS_CRYPTO:
        return False
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex)).verify(bytes.fromhex(sig_hex), digest.encode())
        return True
    except Exception:
        return False


def verify_chain(chain: List[Dict[str, Any]], pubkeys: Dict[str, str]) -> Dict[str, Any]:
    """Check every hash, every prev link and that each block has a quorum of valid signatures."""
    prev = "GENESIS"
    for i, b in enumerate(chain):
        if b.get("index") != i:
            return {"valid": False, "bad_index": i, "reason": "index out of sequence"}
        if b.get("prev_hash") != prev:
            return {"valid": False, "bad_index": i, "reason": "prev_hash does not match the previous block"}
        digest = block_hash(b)
        if digest != b.get("hash"):
            return {"valid": False, "bad_index": i, "reason": "block content does not match its hash (tampered)"}
        good = [s for s, sig in (b.get("signatures") or {}).items() if s in pubkeys and verify_signature(pubkeys[s], sig, digest)]
        if len(good) < QUORUM:
            return {"valid": False, "bad_index": i, "reason": f"only {len(good)} valid signatures (< {QUORUM})"}
        prev = digest
    return {"valid": True, "height": len(chain), "tip": prev}


class LedgerService:
    def __init__(self, node: Any):
        self.node = node
        self.chain: List[Dict[str, Any]] = []
        self.applied: List[Dict[str, Any]] = []
        self.rejections: List[Dict[str, Any]] = []
        self.on_apply = []   # callbacks(command) for commands targeting this satellite
        if HAS_CRYPTO:
            self._key = Ed25519PrivateKey.generate()
            self.public_hex = self._key.public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
        else:  # pragma: no cover
            self._key, self.public_hex = None, ""
        t = node.transport
        t.on("LEDGER_PROPOSE", self._on_propose)
        t.on("LEDGER_COMMIT", self._on_commit)
        t.on("LEDGER_FETCH", self._on_fetch)

    # ------------------------------------------------------------ helpers
    def tip(self) -> str:
        return self.chain[-1]["hash"] if self.chain else "GENESIS"

    def pubkeys(self) -> Dict[str, str]:
        keys = {self.node.node_id: self.public_hex}
        for pid, e in self.node.directory.entries.items():
            if e.get("pubkey"):
                keys[pid] = e["pubkey"]
        return keys

    def sign(self, digest: str) -> str:
        return self._key.sign(digest.encode()).hex()

    def summary(self) -> Dict[str, Any]:
        return {"height": len(self.chain), "tip": self.tip()[:16], "pubkey": self.public_hex}

    def to_dict(self) -> Dict[str, Any]:
        return {"height": len(self.chain), "tip": self.tip(), "pubkey": self.public_hex,
                "applied_commands": self.applied[-10:], "recent_rejections": self.rejections[-5:]}

    def _ev(self, label: str, run_id: Optional[str] = None, **detail: Any) -> None:
        self.node.transport.local_event(label, algo="ledger", run_id=run_id, detail=detail or None)

    # ------------------------------------------------------------ append (shared by commit + catch-up)
    def _append_verified(self, block: Dict[str, Any]) -> bool:
        if block.get("index") != len(self.chain) or block.get("prev_hash") != self.tip():
            return False
        if verify_chain(self.chain + [block], self.pubkeys()).get("valid") is not True:
            # verify only the new block (earlier ones were verified when appended)
            digest = block_hash(block)
            keys = self.pubkeys()
            good = [s for s, sig in block.get("signatures", {}).items() if s in keys and verify_signature(keys[s], sig, digest)]
            if digest != block.get("hash") or len(good) < QUORUM:
                return False
        self.chain.append(block)
        for cmd in block["commands"]:
            if cmd.get("target") == self.node.node_id:
                self.applied.append({**cmd, "block": block["index"], "applied_at": time.time()})
                self._ev("COMMAND_APPLIED", command=cmd["action"], block=block["index"], params=cmd.get("params"))
                for cb in self.on_apply:
                    try:
                        cb(cmd)
                    except Exception as exc:  # pragma: no cover
                        logger.warning("command hook failed: %s", exc)
        return True

    # ------------------------------------------------------------ leader: propose + commit
    async def submit(self, command: Dict[str, Any], run_id: Optional[str] = None) -> Dict[str, Any]:
        if self.node.election.leader != self.node.node_id:
            raise RuntimeError(f"{self.node.node_id} is not the leader (leader is {self.node.election.leader})")
        if command.get("action") not in ACTIONS:
            raise ValueError(f"action must be one of {sorted(ACTIONS)}")
        cmd = {"command_id": f"CMD-{int(time.time() * 1000)}", "action": command["action"],
               "target": command.get("target"), "params": command.get("params") or {}, "submitted_at": time.time()}
        block = {"index": len(self.chain), "prev_hash": self.tip(), "commands": [cmd],
                 "term": self.node.election.term, "proposer": self.node.node_id, "timestamp": time.time()}
        block["hash"] = block_hash(block)
        sigs = {self.node.node_id: self.sign(block["hash"])}
        peers = [p for p in self.node.directory.live_ids() if p not in self.node.transport.blocked]
        votes: Dict[str, str] = {}
        for p in peers:
            try:
                reply = await self.node.transport.request(p, "LEDGER_PROPOSE", {"block": block}, algo="ledger",
                                                          run_id=run_id, timeout=3.0)
            except PeerUnreachable:
                votes[p] = "unreachable"
                continue
            if reply and reply.get("behind"):        # bring the peer up to date, then ask again
                await self.node.transport.send(p, "LEDGER_COMMIT", {"blocks": self.chain[reply["height"]:]},
                                               algo="ledger", run_id=run_id)
                reply = await self.node.transport.request(p, "LEDGER_PROPOSE", {"block": block}, algo="ledger",
                                                          run_id=run_id, timeout=3.0)
            if reply and reply.get("signature"):
                sigs[p] = reply["signature"]
                votes[p] = "signed"
            else:
                votes[p] = (reply or {}).get("reason", "refused")
        result = {"block_index": block["index"], "hash": block["hash"], "signatures": len(sigs), "quorum": QUORUM,
                  "votes": votes, "command": cmd}
        if len(sigs) < QUORUM:
            result["status"] = "REJECTED_NO_QUORUM"
            self.rejections.append({"at": time.time(), "command": cmd["action"], "signatures": len(sigs)})
            self._ev("LEDGER_REJECTED", run_id, block=block["index"], signatures=len(sigs), quorum=QUORUM,
                     reason="no majority of the constellation reachable (CP: refuse rather than diverge)")
            return result
        block["signatures"] = sigs
        self._append_verified(block)
        self._ev("LEDGER_COMMITTED", run_id, block=block["index"], signatures=len(sigs), command=cmd["action"])
        for p in peers:
            try:
                await self.node.transport.send(p, "LEDGER_COMMIT", {"blocks": [block]}, algo="ledger", run_id=run_id)
            except PeerUnreachable:
                pass
        result["status"] = "COMMITTED"
        return result

    async def _on_propose(self, env: Dict[str, Any]) -> Dict[str, Any]:
        block = env["payload"]["block"]
        if block["index"] > len(self.chain):
            return {"behind": True, "height": len(self.chain), "_reply_type": "LEDGER_VOTE"}
        if block["index"] != len(self.chain) or block["prev_hash"] != self.tip():
            return {"reason": "does not extend my chain", "_reply_type": "LEDGER_VOTE"}
        if block_hash(block) != block["hash"]:
            return {"reason": "hash mismatch", "_reply_type": "LEDGER_VOTE"}
        if any(c.get("action") not in ACTIONS for c in block["commands"]):
            return {"reason": "invalid command", "_reply_type": "LEDGER_VOTE"}
        return {"signature": self.sign(block["hash"]), "_reply_type": "LEDGER_VOTE"}

    async def _on_commit(self, env: Dict[str, Any]) -> None:
        for block in env["payload"].get("blocks", []):
            if block["index"] < len(self.chain):
                continue
            if not self._append_verified(block):
                self._ev("LEDGER_BLOCK_REFUSED", block=block.get("index"), reason="failed verification or gap")
                break
        return None

    async def _on_fetch(self, env: Dict[str, Any]) -> Dict[str, Any]:
        start = int(env["payload"].get("from", 0))
        return {"blocks": self.chain[start:], "_reply_type": "LEDGER_BLOCKS"}

    # ------------------------------------------------------------ catch-up after partitions / restarts
    async def catch_up(self, peer: str) -> int:
        try:
            reply = await self.node.transport.request(peer, "LEDGER_FETCH", {"from": len(self.chain)}, algo="ledger")
        except PeerUnreachable:
            return 0
        added = 0
        for block in (reply or {}).get("blocks", []):
            if not self._append_verified(block):
                break
            added += 1
        if added:
            self._ev("LEDGER_CAUGHT_UP", source=peer, blocks=added, height=len(self.chain))
        return added

    def observe_beacon(self, src: str, payload: Dict[str, Any]) -> None:
        info = payload.get("ledger") or {}
        if info.get("pubkey"):
            self.node.directory.upsert(src, pubkey=info["pubkey"])
        if int(info.get("height") or 0) > len(self.chain):
            import asyncio
            asyncio.ensure_future(self.catch_up(src))

    # ------------------------------------------------------------ demo controls
    def tamper(self, index: int) -> Dict[str, Any]:
        """Edit a stored block in place (without re-signing) - what an attacker with disk access might do."""
        block = self.chain[index]
        block["commands"][0]["params"] = {**block["commands"][0].get("params", {}), "tampered": True}
        self._ev("LEDGER_TAMPERED_LOCALLY", block=index)
        return {"tampered_block": index}

    async def repair(self) -> Dict[str, Any]:
        """Drop everything from the first invalid block and re-fetch verified blocks from peers."""
        check = verify_chain(self.chain, self.pubkeys())
        if check["valid"]:
            return {"repaired": False, "reason": "chain already valid"}
        bad = check["bad_index"]
        del self.chain[bad:]
        added = 0
        for p in self.node.directory.live_ids():
            added += await self.catch_up(p)
            if added:
                break
        self._ev("LEDGER_REPAIRED", from_block=bad, refetched=added)
        return {"repaired": True, "from_block": bad, "refetched": added, "height": len(self.chain)}
