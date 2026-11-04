"""Every generator builds from samples/exercise_pack_sample.json with no network or model access."""

import copy
import re

import pytest
from docx import Document
from openpyxl import load_workbook
from pptx import Presentation

from ttx.build import build_all
from ttx.build.aar import build_aar, check_narrative
from ttx.common import read_json


def _docx_text(path):
    doc = Document(str(path))
    parts = [p.text for p in doc.paragraphs]
    for t in doc.tables:
        for row in t.rows:
            parts.extend(c.text for c in row.cells)
    return "\n".join(parts)


@pytest.fixture
def built(sample_pack, tmp_path_factory):
    out = tmp_path_factory.mktemp("built")
    return out, build_all(sample_pack, out)


def test_every_generator_builds(built):
    out, paths = built
    assert set(paths) == {"deck", "facilitator_guide", "participant_handout", "decision_tracker", "attendance", "signoff"}
    for p in paths.values():
        assert (out / p.split("\\")[-1].split("/")[-1]).exists()


def test_deck_slides_align_with_injects(sample_pack, built):
    out, _ = built
    prs = Presentation(str(out / "deck.pptx"))
    slides = list(prs.slides)
    assert len(slides) == 5 + len(sample_pack["injects"]) + 2
    for inj in sample_pack["injects"]:
        slide = slides[inj["slide_number"] - 1]
        text = " ".join(sh.text_frame.text for sh in slide.shapes if sh.has_text_frame)
        assert inj["title"] in text
        assert inj["decision_forced"] in text
        assert inj["host_lines"][0] in slide.notes_slide.notes_text_frame.text


def test_deck_has_no_spoilers(sample_pack, built):
    out, _ = built
    prs = Presentation(str(out / "deck.pptx"))
    text = " ".join(sh.text_frame.text for s in prs.slides for sh in s.shapes if sh.has_text_frame)
    for inj in sample_pack["injects"]:
        assert inj["what_good_looks_like"] not in text
        assert inj["where_teams_fail"] not in text
        for a in inj["expected_actions"]:
            assert a["id"] not in text


def test_handout_has_no_spoilers(sample_pack, built):
    out, _ = built
    text = _docx_text(out / "participant_handout.docx")
    seed = sample_pack["seed"]
    for part in ("entry", "pivot", "target"):
        assert seed[part]["asset"] not in text
        if seed[part].get("finding_id"):
            assert seed[part]["finding_id"] not in text
    for inj in sample_pack["injects"]:
        assert inj["title"] not in text


def test_guide_carries_plan_quotes_sources_and_banner(sample_pack, built):
    out, _ = built
    text = _docx_text(out / "facilitator_guide.docx")
    for inj in sample_pack["injects"]:
        assert inj["host_lines"][0] in text
        if inj["procedure_tested"]["type"] == "org_plan":
            assert inj["procedure_tested"]["quote"] in text
        if inj["source"]["type"] == "finding":
            assert f"Finding {inj['source']['ref']}" in text
    if sample_pack["banner"]["show"]:
        assert "Verify before exercise" in text
    for c in sample_pack["clocks"]:
        assert c["source_url"] in text


def test_tracker_has_a_row_for_every_question(sample_pack, built):
    out, _ = built
    wb = load_workbook(out / "decision_tracker.xlsx")
    assert wb.sheetnames[:2] == ["Host tracker", "Notification clocks"]
    assert wb["Lists"].sheet_state == "hidden"
    keys = {str(r[0].value) for r in wb["Host tracker"].iter_rows() if r[0].value}
    for inj in sample_pack["injects"]:
        for field in ("header", "decided_by", "speed", "discussion", "plan_step", "documented", "decision", "notes"):
            assert f"{inj['id']}|{field}" in keys
        for a in inj["expected_actions"]:
            assert f"{inj['id']}|action|{a['id']}" in keys
        for n in inj["expected_notifications"]:
            assert f"{inj['id']}|notify|{n}" in keys
    clock_ids = {r[0].value for r in wb["Notification clocks"].iter_rows(min_row=5) if r[0].value}
    assert clock_ids == {c["id"] for c in sample_pack["clocks"]}
    role_names = [c.value for c in wb["Lists"]["A"][1:] if c.value]
    assert role_names == [r["name"] for r in sample_pack["roles"]]
    # the host never has to type an id: every dropdown is a plain-language list
    assert all(len(dv.sqref.ranges) >= 1 for dv in wb["Host tracker"].data_validations.dataValidation)


def test_signoff_lists_documents_and_clocks(sample_pack, built):
    out, _ = built
    text = _docx_text(out / "signoff_sheet.docx")
    assert "sample_ir_plan.md" in text
    assert "Executive sponsor" in text
    for c in sample_pack["clocks"]:
        assert c["id"] in text


def test_unapproved_pack_is_refused_and_draft_is_watermarked(sample_pack, tmp_path):
    pack = copy.deepcopy(sample_pack)
    pack["approval"] = {"approved": False, "approved_by": None, "approved_at": None, "outline_hash": None}
    with pytest.raises(ValueError, match="not approved"):
        build_all(pack, tmp_path / "x")
    paths = build_all(pack, tmp_path / "draft", only=["guide"], allow_draft=True)
    assert "DRAFT" in _docx_text(paths["facilitator_guide"])


def test_aar_builds_with_coverage_map_and_evidence(sample_pack, tmp_path):
    score = read_json("samples/outputs/score.json")
    path = build_aar(sample_pack, score, tmp_path / "aar.docx")
    text = _docx_text(path)
    assert score["headline"] in text
    assert "Plan coverage map" in text
    assert "Evidence page" in text
    assert sample_pack["approval"]["outline_hash"] in text
    for g in score["gaps"]:
        assert g["id"] in text
    for fid in sample_pack["seed"]["findings_cited"]:
        assert fid in text


def test_aar_narrative_cannot_invent_numbers(sample_pack):
    score = read_json("samples/outputs/score.json")
    ok = {"headline": f"The team scored {score['summary']['percent']}% and missed one clock.", "summary": []}
    assert check_narrative(ok, score, sample_pack) == []
    bad = {"headline": "The team would have paid a 4,750,000 ransom within 17 minutes.", "summary": []}
    assert check_narrative(bad, score, sample_pack)
    with pytest.raises(ValueError):
        build_aar(sample_pack, score, "unused.docx", narrative=bad)


def test_outputs_contain_no_em_dashes(built, tmp_path):
    out, paths = built
    for name in ("facilitator_guide.docx", "participant_handout.docx", "signoff_sheet.docx"):
        assert "\u2014" not in _docx_text(out / name)
