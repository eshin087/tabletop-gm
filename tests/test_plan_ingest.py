import pytest

from ttx.plan_ingest import extract, find_quote, ingest, normalize_text


def test_markdown_sections_carry_numbers():
    doc = extract("samples/sample_ir_plan.md")
    numbers = {s["number"] for s in doc["sections"]}
    assert {"2.1", "2.3", "4.1", "5.1", "7.1", "8"} <= numbers
    assert doc["format"] == "md"
    assert doc["sha256"]


def test_find_quote_locates_section():
    doc = extract("samples/sample_ir_plan.md")
    hit = find_quote(doc, "within 15 minutes of identifying a suspected SEV1 or SEV2 incident")
    assert hit["found"] and hit["number"] == "4.1"
    miss = find_quote(doc, "the team may pay the ransom without approval")
    assert not miss["found"]
    assert not find_quote(doc, "short")["found"]


def test_normalize_text():
    assert normalize_text("  Hello’s   “World”\n") == "hello's \"world\""


def test_docx_extraction(tmp_path):
    from docx import Document

    d = Document()
    d.add_heading("Incident Response Plan", level=0)
    d.add_heading("3.1 Declaration", level=1)
    d.add_paragraph("The Security Director declares an incident within 20 minutes of confirmation.")
    d.add_heading("3.2 Containment", level=1)
    d.add_paragraph("Isolate first, preserve evidence second.")
    table = d.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "System"
    table.rows[0].cells[1].text = "RTO 6 hours"
    path = tmp_path / "plan.docx"
    d.save(path)
    doc = extract(path)
    assert doc["format"] == "docx"
    numbers = [s["number"] for s in doc["sections"]]
    assert "3.1" in numbers and "3.2" in numbers
    hit = find_quote(doc, "declares an incident within 20 minutes")
    assert hit["found"] and hit["number"] == "3.1"
    assert find_quote(doc, "RTO 6 hours")["found"]


def test_ingest_assigns_document_ids():
    result = ingest(["samples/sample_ir_plan.md"])
    assert result["documents"][0]["id"] == "D1"


def test_unsupported_type_rejected(tmp_path):
    p = tmp_path / "plan.xyz"
    p.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        extract(p)
