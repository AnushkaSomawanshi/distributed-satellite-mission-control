"""
UNIT 4: DISTRIBUTED STORAGE SERVICE

Provides distributed filesystem / storage adapter:
- Distinguishes transactional operational DB state from historical artifact storage.
- Stores telemetry archives, global snapshots, incident artifacts, and simulation reports.
"""

import os
import json
import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("DistributedStorage")

STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "storage_artifacts")

class DistributedStorageService:
    def __init__(self):
        os.makedirs(STORAGE_DIR, exist_ok=True)

    def store_artifact(self, category: str, artifact_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        cat_dir = os.path.join(STORAGE_DIR, category)
        os.makedirs(cat_dir, exist_ok=True)

        file_path = os.path.join(cat_dir, f"{artifact_id}.json")
        payload = {
            "artifact_id": artifact_id,
            "category": category,
            "size_bytes": 0,
            "data": data,
            "stored_at": time.time()
        }
        encoded = json.dumps(payload, indent=2)
        payload["size_bytes"] = len(encoded)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(payload, indent=2))

        logger.info(f"[DISTRIBUTED STORAGE] Saved artifact '{artifact_id}' under category '{category}' ({payload['size_bytes']} bytes)")
        return {
            "artifact_id": artifact_id,
            "category": category,
            "path": file_path,
            "size_bytes": payload["size_bytes"],
            "status": "STORED",
            "stored_at": payload["stored_at"]
        }

    def retrieve_artifact(self, category: str, artifact_id: str) -> Optional[Dict[str, Any]]:
        file_path = os.path.join(STORAGE_DIR, category, f"{artifact_id}.json")
        if not os.path.exists(file_path):
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_artifacts(self, category: str = None) -> List[Dict[str, Any]]:
        res = []
        if category:
            cat_dirs = [os.path.join(STORAGE_DIR, category)]
        else:
            cat_dirs = [os.path.join(STORAGE_DIR, d) for d in os.listdir(STORAGE_DIR) if os.path.isdir(os.path.join(STORAGE_DIR, d))]

        for d in cat_dirs:
            if os.path.exists(d):
                cat_name = os.path.basename(d)
                for fname in os.listdir(d):
                    if fname.endswith(".json"):
                        fpath = os.path.join(d, fname)
                        res.append({
                            "artifact_id": fname.replace(".json", ""),
                            "category": cat_name,
                            "path": fpath,
                            "size_bytes": os.path.getsize(fpath)
                        })
        return res

global_distributed_storage = DistributedStorageService()
