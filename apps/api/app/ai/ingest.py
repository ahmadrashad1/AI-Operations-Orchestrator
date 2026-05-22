"""Document parsing and chunking helpers for ingestion."""
from __future__ import annotations

import json
import re
from pathlib import Path

DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 150

_TEXT_EXTENSIONS = {".txt", ".md", ".rst", ".csv", ".log", ".json", ".yml", ".yaml"}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def chunk_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []

    if len(normalized) <= chunk_size:
        return [normalized]

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + chunk_size)
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        start = max(0, end - overlap)
    return chunks


def extract_text_from_bytes(filename: str, data: bytes, content_type: str | None = None) -> str:
    suffix = Path(filename).suffix.lower()
    content_type = (content_type or "").lower()

    if suffix in _TEXT_EXTENSIONS or content_type.startswith("text/") or suffix in {".py", ".toml", ".ini"}:
        return data.decode("utf-8", errors="ignore")

    if suffix == ".json":
        try:
            return json.dumps(json.loads(data.decode("utf-8", errors="ignore")), indent=2)
        except Exception:
            return data.decode("utf-8", errors="ignore")

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise ValueError("PDF ingestion requires pypdf to be installed") from exc

        from io import BytesIO

        pdf_reader = PdfReader(BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in pdf_reader.pages)

    if suffix == ".docx":
        try:
            from docx import Document  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise ValueError("DOCX ingestion requires python-docx to be installed") from exc

        from io import BytesIO

        document = Document(BytesIO(data))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)

    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1", errors="ignore")
