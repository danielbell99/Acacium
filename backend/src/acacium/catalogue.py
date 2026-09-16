from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from acacium.schemas import DocumentList, SourceDocument


@lru_cache
def load_manifest(path: Path) -> DocumentList:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return DocumentList.model_validate(raw)


def find_document(manifest: DocumentList, document_id: str) -> SourceDocument:
    for document in manifest.documents:
        if document.id == document_id:
            return document
    raise KeyError(document_id)
