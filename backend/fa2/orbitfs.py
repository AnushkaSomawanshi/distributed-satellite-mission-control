"""
OrbitFS NameNode (Unit 4: distributed file system), running in Mission Control.

The NameNode holds only METADATA: which files exist, their chunks, and which satellites hold each
chunk. File data lives on the satellites (DataNodes, satellites/dsync/datanode.py).

- write: split into chunks (text files split on line boundaries so MapReduce can read whole records),
  choose 3 satellites per chunk (least used first), send the chunk down a replication pipeline.
- read: fetch each chunk from a live replica, verify its SHA-256, fall back to the next replica.
- monitor loop: block reports from every DataNode; under-replicated chunks (a satellite died) are
  copied satellite-to-satellite to a new holder; over-replicated ones (it came back) are trimmed.
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import Response

from backend.fa2.bus import mission_bus
from backend.registry.service_registry import global_registry

logger = logging.getLogger("OrbitFS")
router = APIRouter(prefix="/api/orbitfs", tags=["Unit 4: OrbitFS"])

CHUNK_SIZE = 64 * 1024
REPLICATION = 3
META_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "storage_artifacts", "orbitfs_namenode.json")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class NameNode:
    def __init__(self):
        self.files: Dict[str, Dict[str, Any]] = {}
        self.chunks: Dict[str, Dict[str, Any]] = {}
        self.datanodes: Dict[str, Dict[str, Any]] = {}  # last block report per satellite
        self.log: List[Dict[str, Any]] = []
        self._client: Optional[httpx.AsyncClient] = None
        self._loaded_mtime = 0.0
        self._load()

    # ------------------------------------------------------------ persistence of metadata
    def _load(self) -> None:
        try:
            self._loaded_mtime = os.path.getmtime(META_PATH)
            with open(META_PATH, "r", encoding="utf-8") as f:
                meta = json.load(f)
            self.files = meta.get("files", {})
            self.chunks = {k: {**v, "replicas": set(v.get("replicas", []))} for k, v in meta.get("chunks", {}).items()}
        except FileNotFoundError:
            pass
        except Exception as exc:  # pragma: no cover
            logger.warning("could not load NameNode metadata: %s", exc)

    def maybe_reload(self) -> None:
        """A standby that takes over picks up metadata the primary saved on the shared volume."""
        try:
            if os.path.getmtime(META_PATH) > self._loaded_mtime + 0.001:
                self._load()
        except FileNotFoundError:
            pass

    def _save(self) -> None:
        os.makedirs(os.path.dirname(META_PATH), exist_ok=True)
        meta = {"files": self.files, "chunks": {k: {**v, "replicas": sorted(v["replicas"])} for k, v in self.chunks.items()}}
        with open(META_PATH, "w", encoding="utf-8") as f:
            json.dump(meta, f)
        self._loaded_mtime = os.path.getmtime(META_PATH)

    def _note(self, action: str, **detail: Any) -> None:
        self.log.append({"at": time.time(), "action": action, **detail})
        del self.log[:-200]

    # ------------------------------------------------------------ datanodes
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client

    def endpoint(self, sid: str) -> Optional[Dict[str, Any]]:
        reg = global_registry.lookup(sid)
        return {"id": sid, "address": reg.address, "port": reg.p2p_port} if reg else None

    def live(self) -> List[str]:
        return sorted(s for s, d in self.datanodes.items() if d.get("alive"))

    async def refresh_block_reports(self) -> None:
        self.maybe_reload()
        async def one(sid: str) -> Tuple[str, Optional[Dict[str, Any]]]:
            ep = self.endpoint(sid)
            try:
                r = await self.client().get(f"http://{ep['address']}:{ep['port']}/orbitfs/blocks", timeout=2.0)
                return sid, r.json() if r.status_code == 200 else None
            except Exception:
                return sid, None
        reports = await asyncio.gather(*(one(r.satellite_id) for r in global_registry.list_all()))
        for sid, rep in reports:
            if rep is None:
                self.datanodes[sid] = {**self.datanodes.get(sid, {}), "alive": False}
                continue
            self.datanodes[sid] = {"alive": True, "chunks": set(rep["chunks"]), "used_bytes": rep["used_bytes"],
                                   "stats": rep.get("stats", {}), "at": time.time()}
            held = set(rep["chunks"])
            for cid, c in self.chunks.items():   # reconcile metadata with what the DataNode really holds
                if cid in held:
                    c["replicas"].add(sid)
                elif time.time() - c.get("created", 0) > 10:   # ignore reports older than a fresh write
                    c["replicas"].discard(sid)

    def _pick_targets(self, n: int, exclude: set = frozenset()) -> List[str]:
        live = [s for s in self.live() if s not in exclude]
        return sorted(live, key=lambda s: (self.datanodes[s].get("used_bytes", 0), s))[:n]

    # ------------------------------------------------------------ files
    @staticmethod
    def split(data: bytes, line_aligned: bool, chunk_size: int = CHUNK_SIZE) -> List[bytes]:
        out, i = [], 0
        while i < len(data):
            end = min(i + chunk_size, len(data))
            if line_aligned and end < len(data):
                nl = data.rfind(b"\n", i, end)
                if nl > i:
                    end = nl + 1
            out.append(data[i:end])
            i = end
        return out or [b""]

    async def write(self, path: str, data: bytes, content_type: str = "application/octet-stream",
                    chunk_size: int = CHUNK_SIZE) -> Dict[str, Any]:
        await self.refresh_block_reports()
        if not self.live():
            raise HTTPException(503, "no DataNode (satellite) is reachable")
        if path in self.files:
            await self.delete(path)
        line_aligned = content_type.startswith("text/") or path.endswith((".csv", ".json", ".txt", ".log"))
        pieces = self.split(data, line_aligned, chunk_size)
        chunk_ids, placement = [], []
        for idx, piece in enumerate(pieces):
            cid = f"blk-{uuid.uuid4().hex[:12]}"
            targets = self._pick_targets(REPLICATION)
            pipeline = [self.endpoint(t) for t in targets]
            body = {"chunk_id": cid, "data_b64": base64.b64encode(piece).decode(), "checksum": sha256(piece),
                    "pipeline": pipeline[1:]}
            first = pipeline[0]
            try:
                r = await self.client().post(f"http://{first['address']}:{first['port']}/orbitfs/chunk", json=body, timeout=15.0)
                r.raise_for_status()
                acks = r.json()["acks"]
            except Exception as exc:
                raise HTTPException(502, f"pipeline write of chunk {idx} failed at {first['id']}: {exc}")
            self.chunks[cid] = {"size": len(piece), "checksum": sha256(piece), "replicas": set(acks), "file": path,
                                "index": idx, "created": time.time()}
            for a in acks:
                self.datanodes.get(a, {}).setdefault("chunks", set()).add(cid)
                self.datanodes[a]["used_bytes"] = self.datanodes[a].get("used_bytes", 0) + len(piece)
            chunk_ids.append(cid)
            placement.append({"chunk_id": cid, "pipeline": [p["id"] for p in pipeline], "acks": acks})
        self.files[path] = {"path": path, "size": len(data), "sha256": sha256(data), "chunks": chunk_ids,
                            "chunk_size": chunk_size,
                            "content_type": content_type, "created_at": time.time(), "line_aligned": line_aligned}
        self._save()
        self._note("WRITE", path=path, chunks=len(chunk_ids))
        await mission_bus.publish("FILE_UPLOADED", path=path, size=len(data), content_type=content_type)
        return {**self.info(path), "placement": placement}

    async def read(self, path: str) -> Tuple[bytes, List[Dict[str, Any]]]:
        meta = self.files.get(path)
        if not meta:
            raise HTTPException(404, f"{path} not found")
        out, served = b"", []
        for cid in meta["chunks"]:
            c = self.chunks[cid]
            order = sorted(c["replicas"], key=lambda s: (not self.datanodes.get(s, {}).get("alive"), s))
            got = None
            for sid in order:
                ep = self.endpoint(sid)
                try:
                    r = await self.client().get(f"http://{ep['address']}:{ep['port']}/orbitfs/chunk/{cid}", timeout=5.0)
                    if r.status_code != 200:
                        continue
                    data = base64.b64decode(r.json()["data_b64"])
                    if sha256(data) != c["checksum"]:
                        self._note("CHECKSUM_MISMATCH", chunk_id=cid, at=sid)
                        continue
                    got = data
                    served.append({"chunk_id": cid, "served_by": sid, "tried": order[:order.index(sid) + 1]})
                    break
                except Exception:
                    continue
            if got is None:
                raise HTTPException(503, f"chunk {cid} of {path} has no reachable healthy replica")
            out += got
        if sha256(out) != meta["sha256"]:
            raise HTTPException(500, "file checksum mismatch after reassembly")
        return out, served

    async def delete(self, path: str) -> Dict[str, Any]:
        meta = self.files.pop(path, None)
        if not meta:
            raise HTTPException(404, f"{path} not found")
        for cid in meta["chunks"]:
            c = self.chunks.pop(cid, None) or {"replicas": set()}
            for sid in c["replicas"]:
                ep = self.endpoint(sid)
                try:
                    await self.client().delete(f"http://{ep['address']}:{ep['port']}/orbitfs/chunk/{cid}", timeout=3.0)
                except Exception:
                    pass
        self._save()
        self._note("DELETE", path=path)
        return {"deleted": path}

    def info(self, path: str) -> Dict[str, Any]:
        meta = self.files[path]
        live = set(self.live())
        chunks = [{"chunk_id": cid, "index": self.chunks[cid]["index"], "size": self.chunks[cid]["size"],
                   "replicas": sorted(self.chunks[cid]["replicas"]),
                   "live_replicas": sorted(self.chunks[cid]["replicas"] & live)} for cid in meta["chunks"]]
        return {**{k: v for k, v in meta.items() if k != "chunks"}, "chunks": chunks,
                "under_replicated": sum(1 for c in chunks if len(c["live_replicas"]) < REPLICATION)}

    # ------------------------------------------------------------ self-healing
    async def heal_once(self) -> Dict[str, int]:
        await self.refresh_block_reports()
        live = set(self.live())
        copied = trimmed = lost = 0
        for cid, c in list(self.chunks.items()):
            have = c["replicas"] & live
            if not have:
                lost += 1
                continue
            while len(have) < min(REPLICATION, len(live)):
                targets = self._pick_targets(1, exclude=c["replicas"] | have)
                if not targets:
                    break
                src, dst = sorted(have)[0], targets[0]
                ep = self.endpoint(src)
                try:
                    r = await self.client().post(f"http://{ep['address']}:{ep['port']}/orbitfs/replicate",
                                                 json={"chunk_id": cid, "to": self.endpoint(dst)}, timeout=10.0)
                    r.raise_for_status()
                except Exception as exc:
                    logger.warning("re-replication of %s from %s to %s failed: %s", cid, src, dst, exc)
                    break
                c["replicas"].add(dst)
                have.add(dst)
                self.datanodes[dst]["used_bytes"] = self.datanodes[dst].get("used_bytes", 0) + c["size"]
                copied += 1
                self._note("RE_REPLICATED", chunk_id=cid, file=c["file"], source=src, target=dst)
            if len(have) > REPLICATION:     # a dead holder came back: drop the extra copy
                extra = sorted(have, key=lambda s: -self.datanodes[s].get("used_bytes", 0))[0]
                ep = self.endpoint(extra)
                try:
                    await self.client().delete(f"http://{ep['address']}:{ep['port']}/orbitfs/chunk/{cid}", timeout=3.0)
                    c["replicas"].discard(extra)
                    trimmed += 1
                    self._note("TRIMMED_EXTRA_REPLICA", chunk_id=cid, at=extra)
                except Exception:
                    pass
        if copied or trimmed:
            self._save()
        return {"copied": copied, "trimmed": trimmed, "lost": lost}

    async def run(self) -> None:
        while True:
            await asyncio.sleep(4.0)
            try:
                from backend.fa2.role import is_active
                if not is_active():
                    continue  # passive standby: do not repair (the primary does)
                if self.chunks:
                    await self.heal_once()
                else:
                    await self.refresh_block_reports()
            except asyncio.CancelledError:
                break
            except Exception as exc:  # pragma: no cover
                logger.warning("NameNode monitor error: %s", exc)

    def status(self) -> Dict[str, Any]:
        live = set(self.live())
        under = sum(1 for c in self.chunks.values() if len(c["replicas"] & live) < min(REPLICATION, max(1, len(live))))
        return {"replication_factor": REPLICATION, "chunk_size": CHUNK_SIZE, "files": len(self.files),
                "chunks": len(self.chunks), "under_replicated_chunks": under,
                "datanodes": {s: {"alive": d.get("alive", False), "chunks": len(d.get("chunks", [])),
                                  "used_bytes": d.get("used_bytes", 0)} for s, d in sorted(self.datanodes.items())},
                "recent_actions": self.log[-15:]}


namenode = NameNode()


async def archive_json(path: str, obj: Any) -> str:
    data = json.dumps(obj, default=str, indent=1).encode()
    await namenode.write(path, data, "application/json")
    return path


# ------------------------------------------------------------------ API
@router.get("/status")
async def status():
    return namenode.status()


@router.get("/files")
async def list_files(prefix: str = ""):
    return {"files": [namenode.info(p) for p in sorted(namenode.files) if p.startswith(prefix)]}


@router.post("/files")
async def upload(body: Dict[str, Any] = Body(...)):
    path = (body.get("path") or "").strip().lstrip("/")
    if not path or ".." in path:
        raise HTTPException(422, "a relative path is required")
    if "content_b64" in body:
        data = base64.b64decode(body["content_b64"])
    elif "text" in body:
        data = body["text"].encode()
    else:
        raise HTTPException(422, "send content_b64 or text")
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(413, "max 8 MB per file in this demo")
    return await namenode.write(path, data, body.get("content_type") or "application/octet-stream")


@router.get("/files/info")
async def file_info(path: str = Query(...)):
    if path not in namenode.files:
        raise HTTPException(404, f"{path} not found")
    return namenode.info(path)


@router.get("/files/download")
async def download(path: str = Query(...)):
    data, served = await namenode.read(path)
    meta = namenode.files[path]
    return Response(content=data, media_type=meta["content_type"], headers={
        "X-OrbitFS-Served-By": ",".join(f"{s['chunk_id']}@{s['served_by']}" for s in served),
        "Content-Disposition": f'attachment; filename="{os.path.basename(path)}"'})


@router.get("/files/verify")
async def verify(path: str = Query(...)):
    data, served = await namenode.read(path)
    return {"path": path, "bytes": len(data), "sha256": sha256(data), "matches_original": True, "served": served}


@router.delete("/files")
async def remove(path: str = Query(...)):
    return await namenode.delete(path)


@router.post("/heal")
async def heal():
    return await namenode.heal_once()
