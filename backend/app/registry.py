# backend/app/registry.py
import json
import os
import time
from typing import Dict, Any, List, Optional

from .store import get_paths

REGISTRY_FILENAME = "docs_registry.json"

def _registry_path() -> str:
    paths = get_paths()
    data_dir = os.path.dirname(paths["docs_dir"])  # backend/data
    return os.path.join(data_dir, REGISTRY_FILENAME)

def _load() -> Dict[str, Any]:
    path = _registry_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}

def _save(data: Dict[str, Any]) -> None:
    path = _registry_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def upsert_doc(doc_id: str, doc_name: str, pdf_path: str) -> None:
    data = _load()
    data[doc_id] = {
        "doc_id": doc_id,
        "doc_name": doc_name,
        "pdf_path": pdf_path,
        "uploaded_at": int(time.time()),
    }
    _save(data)

def get_doc(doc_id: str) -> Optional[Dict[str, Any]]:
    data = _load()
    return data.get(doc_id)

def list_docs() -> List[Dict[str, Any]]:
    data = _load()
    # newest first
    docs = list(data.values())
    docs.sort(key=lambda x: x.get("uploaded_at", 0), reverse=True)
    return docs