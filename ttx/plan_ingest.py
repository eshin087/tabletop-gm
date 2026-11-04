"""Policy and procedure ingest.

Extracts text from an uploaded IR plan, BCP/DR plan, playbook, procedure, or
communication template (docx, pdf, md, txt) with section and page anchors so
the policy_ingest skill can fill org_plan.json with a verbatim quote and
locator for every item, and so the validator can confirm each quote exists.

Documents are processed locally and never written anywhere but the output the
caller names. Only the synthetic samples/sample_ir_plan.md ships in the repo.
"""

from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path
from typing import Any

from .common import now_iso, read_text, sha256_file

HEADING_RE = re.compile(r"^\s*(?:(\d+(?:\.\d+)*)[\.\)]?\s+)?([A-Z][^\n]{2,120})\s*$")
NUMBERED_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)[\.\)]?\s+(\S.*)$")
MAX_CHARS = 2_000_000


def _section(sid: int, heading: str, number: str | None, page: int | None) -> dict:
    return {"id": f"s{sid}", "heading": heading.strip(), "number": number, "page": page, "text": ""}


def extract_markdown(text: str) -> list[dict]:
    sections: list[dict] = []
    current = _section(0, "(preamble)", None, None)
    sid = 0
    for line in text.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            if current["text"].strip() or current["heading"] != "(preamble)":
                sections.append(current)
            sid += 1
            heading = m.group(2).strip()
            num = NUMBERED_RE.match(heading)
            number = num.group(1) if num else None
            current = _section(sid, heading, number, None)
        else:
            current["text"] += line + "\n"
    sections.append(current)
    return sections


def extract_docx(path: Path) -> list[dict]:
    from docx import Document  # python-docx

    doc = Document(str(path))
    sections: list[dict] = []
    current = _section(0, "(preamble)", None, None)
    sid = 0
    for para in doc.paragraphs:
        style = (para.style.name if para.style is not None else "") or ""
        text = para.text
        if style.lower().startswith("heading") or style.lower() == "title":
            if current["text"].strip() or current["heading"] != "(preamble)":
                sections.append(current)
            sid += 1
            num = NUMBERED_RE.match(text.strip())
            current = _section(sid, text.strip(), num.group(1) if num else None, None)
        else:
            current["text"] += text + "\n"
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            current["text"] += " | ".join(cells) + "\n"
    sections.append(current)
    return sections


def extract_pdf(path: Path) -> list[dict]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    sections: list[dict] = []
    current = _section(0, "(preamble)", None, 1)
    sid = 0
    empty_pages = 0
    for pno, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if not text.strip():
            empty_pages += 1
        for line in text.splitlines():
            stripped = line.strip()
            num = NUMBERED_RE.match(stripped)
            looks_heading = bool(num and len(stripped) <= 120 and not stripped.endswith(".")) or (
                stripped.isupper() and 3 < len(stripped) <= 80
            )
            if looks_heading:
                if current["text"].strip() or current["heading"] != "(preamble)":
                    sections.append(current)
                sid += 1
                current = _section(sid, stripped, num.group(1) if num else None, pno)
            else:
                current["text"] += line + "\n"
    sections.append(current)
    if empty_pages and empty_pages == len(reader.pages):
        raise ValueError("PDF has no extractable text (scanned PDF needing OCR is roadmap)")
    return sections


def extract(path: str | os.PathLike) -> dict:
    """Extract one document into sections with anchors."""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".docx":
        sections = extract_docx(p)
        fmt = "docx"
    elif suffix == ".pdf":
        sections = extract_pdf(p)
        fmt = "pdf"
    elif suffix in {".md", ".markdown", ".txt"}:
        sections = extract_markdown(read_text(p))
        fmt = "md" if suffix != ".txt" else "txt"
    else:
        raise ValueError(f"unsupported document type '{suffix}' (use .docx, .pdf, .md, or .txt)")
    full_text = "\n".join(s["text"] for s in sections)
    if len(full_text) > MAX_CHARS:
        raise ValueError(f"document too large ({len(full_text)} characters); split it or proceed with pack defaults")
    title = next((s["heading"] for s in sections if s["heading"] != "(preamble)"), p.stem)
    return {
        "filename": p.name,
        "path": str(p),
        "format": fmt,
        "sha256": sha256_file(p),
        "title": title,
        "ingested_at": now_iso(),
        "sections": sections,
        "full_text": full_text,
        "characters": len(full_text),
    }


def ingest(paths: list[str | os.PathLike]) -> dict:
    docs = []
    for i, path in enumerate(paths, start=1):
        d = extract(path)
        d["id"] = f"D{i}"
        docs.append(d)
    return {"schema_version": "1", "generated_at": now_iso(), "documents": docs}


# --------------------------------------------------------------------------- #
# Quote verification
# --------------------------------------------------------------------------- #

_QUOTE_MAP = {
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-",
    "\u00a0": " ", "\u2026": "...",
}


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    for k, v in _QUOTE_MAP.items():
        text = text.replace(k, v)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def find_quote(document: dict, quote: str) -> dict:
    """Locate a verbatim quote in an extracted document.

    Matching ignores case, whitespace runs, and typographic quotes and dashes;
    otherwise the words must appear in order, exactly. Returns
    {"found": bool, "section": id or None, "heading": ..., "number": ..., "page": ...}.
    """
    needle = normalize_text(quote)
    if len(needle) < 8:
        return {"found": False, "reason": "quote too short (minimum 8 characters)"}
    for s in document.get("sections", []):
        if needle in normalize_text(s.get("text", "")) or needle in normalize_text(s.get("heading", "")):
            return {"found": True, "section": s["id"], "heading": s["heading"], "number": s.get("number"), "page": s.get("page")}
    if needle in normalize_text(document.get("full_text", "")):
        return {"found": True, "section": None, "heading": None, "number": None, "page": None, "reason": "found across a section boundary"}
    return {"found": False, "reason": "quote not found in document"}


def verify_org_plan(org_plan: dict, documents: dict[str, dict]) -> list[dict]:
    """Check every quoted item. documents maps org_plan document id (D1...) or filename to an extracted document."""
    results: list[dict] = []
    for item in org_plan.get("items", []):
        doc_ref = item.get("document")
        doc = documents.get(doc_ref) if doc_ref else None
        if doc is None:
            for key, d in documents.items():
                if d.get("filename") == doc_ref or key == doc_ref:
                    doc = d
                    break
        if doc is None:
            results.append({"id": item.get("id"), "ok": False, "reason": f"document '{doc_ref}' not ingested"})
            continue
        quote = item.get("quote") or ""
        hit = find_quote(doc, quote)
        if not hit.get("found"):
            results.append({"id": item.get("id"), "ok": False, "reason": hit.get("reason", "quote not found")})
            continue
        res = {"id": item.get("id"), "ok": True, "section": hit.get("section"), "heading": hit.get("heading"), "page": hit.get("page")}
        claimed = item.get("section")
        if claimed and hit.get("number") and str(claimed) != str(hit["number"]) and str(claimed) != str(hit.get("section")):
            res["warning"] = f"item says section {claimed}; quote found in {hit.get('number') or hit.get('section')} ({hit.get('heading')})"
        results.append(res)
    return results


def documents_index(ingested: dict) -> dict[str, dict]:
    """{D1: doc, filename: doc} for verify_org_plan."""
    index: dict[str, dict] = {}
    for d in ingested.get("documents", []):
        index[d["id"]] = d
        index[d["filename"]] = d
    return index
