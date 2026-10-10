"""The checkpoint and resume paths. Both were shipped with zero tests.

`eb85860` added per-term checkpointing while a live run was in progress, and
**the resume branch had never executed** -- not in a test, not live. Review then
found the defect that follows from that: a complete checkpoint was re-read with
no age check and nothing cleared it after a successful publish, so the next
`make refresh SOURCE=upstream` on the same machine would re-read an old window
and stamp it with today's date and `"source": "upstream"`. Stale data labelled
live.

These tests cover the five things that defect turned on, each driven through the
**real** transport and ingest code against a scripted upstream.

**No prohibited attribute name appears as a literal here.** The planted key is
read from the guard's own list, the way `tests/unit/test_guard_scopes.py` does
it -- this file is scanned by the guard like any other.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import httpx
import pytest

from sansad.ingest.questions import (
    CHECKPOINT_COMPLETE_SUFFIX,
    IngestionFailed,
    checkpoint_is_complete,
    checkpoint_written_at,
    fetch_question_records,
)
from sansad.ingest.transport import ScratchPathInsideRepoError

REPO_ROOT = Path(__file__).resolve().parents[2]
TOTAL = 40
PAGE = 10


def _excluded_key() -> str:
    """One prohibited spelling, taken from the guard's own list.

    `min(..., key=len)` is stable in meaning however the list is ordered, and
    writing the spelling as a literal would trip the guard on this file.
    """
    spec = importlib.util.spec_from_file_location(
        "sansad_guard_ckpt_resume", REPO_ROOT / "tools" / "guard_no_raw_payloads.py"
    )
    assert spec and spec.loader
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    return min(guard.PROHIBITED_ATTRIBUTES["date of birth"], key=len)


def _record(ques_no: int, *, with_excluded: bool = False) -> dict:
    record = {
        "quesNo": ques_no,
        "lokNo": "18",
        "sessionNo": "1",
        "date": "01.07.2024",
        "type": "UNSTARRED",
        "subjects": "Placeholder subject",
        "ministry": "Ministry of Placeholder Affairs",
        "member": ["Shri Placeholder Name"],
    }
    if with_excluded:
        record[_excluded_key()] = "MUST-NEVER-REACH-THE-CHECKPOINT"
    return record


def _upstream(*, die_on_last: bool = False, with_excluded: bool = False):
    """A scripted upstream serving TOTAL records in pages of PAGE."""
    pages = TOTAL // PAGE

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(httpx.URL(str(request.url)).params.get("pageNo", 1))
        if die_on_last and page == pages:
            raise httpx.ReadTimeout("simulated drop on the last page", request=request)
        rows = (
            [
                _record(n, with_excluded=with_excluded)
                for n in range(page * PAGE - PAGE + 1, page * PAGE + 1)
            ]
            if page <= pages
            else []
        )
        return httpx.Response(
            200, json=[{"listOfQuestions": rows, "totalRecordSize": TOTAL, "_metadata": None}]
        )

    return httpx.Client(transport=httpx.MockTransport(handler))


def _fetch(checkpoint: Path, **kwargs):
    return fetch_question_records(loksabha=18, page_size=PAGE, checkpoint=checkpoint, **kwargs)


# ---------------------------------------------------------------------------
# 1. the sidecar is written only after the truncation check passes
# ---------------------------------------------------------------------------
def test_the_sidecar_is_written_only_after_the_truncation_check(tmp_path):
    checkpoint = tmp_path / "questions_ls18.jsonl"
    records = _fetch(checkpoint, client=_upstream())

    assert len(records) == TOTAL
    sidecar = tmp_path / (checkpoint.name + CHECKPOINT_COMPLETE_SUFFIX)
    assert sidecar.is_file()
    marker = json.loads(sidecar.read_text(encoding="utf-8"))
    assert marker["records"] == TOTAL
    assert marker["expected"] == TOTAL
    assert marker["written_at"], "a resumed term must be able to say how old it is"
    assert checkpoint_is_complete(checkpoint) == TOTAL


def test_a_fetch_that_fails_on_its_last_page_leaves_no_sidecar(tmp_path):
    """The case that would otherwise certify a short term as whole."""
    checkpoint = tmp_path / "questions_ls18.jsonl"
    with pytest.raises(IngestionFailed):
        _fetch(checkpoint, client=_upstream(die_on_last=True))

    kept = [ln for ln in checkpoint.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(kept) == TOTAL - PAGE, "the pages that arrived should survive"
    assert not (tmp_path / (checkpoint.name + CHECKPOINT_COMPLETE_SUFFIX)).exists()
    assert checkpoint_is_complete(checkpoint) is None
    assert checkpoint_written_at(checkpoint) == "not stated"


# ---------------------------------------------------------------------------
# 2. a complete checkpoint is IGNORED by default and used only with the flag
# ---------------------------------------------------------------------------
def _run(tmp_path, monkeypatch, *, resume: bool, scratch: Path):
    """Drive `run_refresh` against the scripted upstream."""
    from sansad import cli

    monkeypatch.setenv("SANSAD_SCRATCH", str(scratch))
    monkeypatch.setattr(cli, "WINDOW_TERMS", (18,))

    def fake_members(**kwargs):
        from sansad.ingest.members import load_members

        return load_members(
            [
                {
                    "memberId": "ls-1",
                    "memberName": "Placeholder Name",
                    "party": "P",
                    "state": "S",
                    "constituency": "C",
                    "house": "Lok Sabha",
                    "term": 18,
                    "sittingStatus": "sitting",
                }
            ],
            last_refreshed=kwargs.get("last_refreshed") or "2026-10-10",
        )

    import sansad.ingest.members as members_mod
    import sansad.ingest.questions as questions_mod

    monkeypatch.setattr(members_mod, "fetch_members", fake_members)
    real = questions_mod.fetch_question_records

    def patched(**kwargs):
        kwargs.pop("timeout", None)
        return real(client=_upstream(), page_size=PAGE, **kwargs)

    monkeypatch.setattr(questions_mod, "fetch_question_records", patched)
    code = cli.run_refresh(source="upstream", published_dir=tmp_path / "published", resume=resume)
    assert code == 0
    return json.loads((tmp_path / "published" / "manifest.json").read_text(encoding="utf-8"))


def test_a_complete_checkpoint_is_ignored_by_default(tmp_path, monkeypatch):
    """The defect, as a test. Default must REFETCH, not reuse."""
    scratch = tmp_path / "scratch"
    checkpoint = scratch / "live-refresh" / "questions_ls18.jsonl"
    checkpoint.parent.mkdir(parents=True)
    # A stale checkpoint claiming a different record count than the upstream
    # will serve, so a reuse is detectable from the published figures.
    checkpoint.write_text(
        "".join(json.dumps(_record(n)) + "\n" for n in range(1, 4)),
        encoding="utf-8",
    )
    (scratch / "live-refresh" / (checkpoint.name + CHECKPOINT_COMPLETE_SUFFIX)).write_text(
        json.dumps({"records": 3, "expected": 3, "written_at": "2020-01-01T00:00:00+00:00"}),
        encoding="utf-8",
    )
    assert checkpoint_is_complete(checkpoint) == 3

    manifest = _run(tmp_path, monkeypatch, resume=False, scratch=scratch)

    assert manifest["window_questions"] == TOTAL, "the stale checkpoint was reused"
    assert manifest["resumed_terms"] == []
    assert [e["mode"] for e in manifest["question_source_by_term"]] == ["fetched"]


def test_a_complete_checkpoint_is_used_with_the_flag(tmp_path, monkeypatch):
    scratch = tmp_path / "scratch"
    checkpoint = scratch / "live-refresh" / "questions_ls18.jsonl"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_text(
        "".join(json.dumps(_record(n)) + "\n" for n in range(1, 4)), encoding="utf-8"
    )
    (scratch / "live-refresh" / (checkpoint.name + CHECKPOINT_COMPLETE_SUFFIX)).write_text(
        json.dumps({"records": 3, "expected": 3, "written_at": "2020-01-01T00:00:00+00:00"}),
        encoding="utf-8",
    )

    manifest = _run(tmp_path, monkeypatch, resume=True, scratch=scratch)

    assert manifest["window_questions"] == 3, "the checkpoint was not reused"
    assert manifest["resumed_terms"] == [18]


# ---------------------------------------------------------------------------
# 3. the manifest and the coverage statement name resumed terms and their date
# ---------------------------------------------------------------------------
def test_the_manifest_and_coverage_record_resumed_terms_and_their_date(tmp_path, monkeypatch):
    scratch = tmp_path / "scratch"
    checkpoint = scratch / "live-refresh" / "questions_ls18.jsonl"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_text(
        "".join(json.dumps(_record(n)) + "\n" for n in range(1, 4)), encoding="utf-8"
    )
    written = "2020-01-01T00:00:00+00:00"
    (scratch / "live-refresh" / (checkpoint.name + CHECKPOINT_COMPLETE_SUFFIX)).write_text(
        json.dumps({"records": 3, "expected": 3, "written_at": written}), encoding="utf-8"
    )

    manifest = _run(tmp_path, monkeypatch, resume=True, scratch=scratch)

    entry = next(e for e in manifest["question_source_by_term"] if e["term"] == 18)
    assert entry["mode"] == "resumed"
    assert entry["checkpoint_written_at"] == written

    from sansad.publish.formats import read_ndjson

    row = next(
        r
        for r in read_ndjson(tmp_path / "published" / "coverage.jsonl")
        if r["house"] == "lok-sabha"
    )
    assert row["resumed_terms"] == [18]
    assert any("resumed-term" in gap and written in gap for gap in row["known_gaps"]), (
        "a resumed term must be a declared known gap, with its date"
    )


def test_checkpoints_are_cleared_after_a_successful_publish(tmp_path, monkeypatch):
    """A checkpoint exists to survive a FAILED run.

    Leaving it after a successful one is what let the next run silently re-read
    a stale window.
    """
    scratch = tmp_path / "scratch"
    _run(tmp_path, monkeypatch, resume=False, scratch=scratch)

    checkpoint = scratch / "live-refresh" / "questions_ls18.jsonl"
    assert not checkpoint.exists(), "the checkpoint outlived a successful publish"
    assert not (scratch / "live-refresh" / (checkpoint.name + CHECKPOINT_COMPLETE_SUFFIX)).exists()


# ---------------------------------------------------------------------------
# 4. an excluded attribute never reaches the checkpoint
# ---------------------------------------------------------------------------
def test_a_prohibited_attribute_in_the_response_is_absent_from_the_checkpoint(tmp_path):
    """Principle V at the write boundary, against a mocked upstream that serves one."""
    checkpoint = tmp_path / "questions_ls18.jsonl"
    _fetch(checkpoint, client=_upstream(with_excluded=True))

    body = checkpoint.read_text(encoding="utf-8")
    assert _excluded_key() not in body
    assert "MUST-NEVER-REACH-THE-CHECKPOINT" not in body
    # ...and the permitted fields did land, or this would pass vacuously.
    assert "quesNo" in body and "member" in body


# ---------------------------------------------------------------------------
# 5. a checkpoint path inside the repository tree is refused
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "inside",
    ["data/published/x.jsonl", "tests/x.jsonl", "x.jsonl", "src/sansad/x.jsonl"],
)
def test_a_checkpoint_inside_the_repository_tree_is_refused(inside):
    """An argument that takes any Path can take an in-tree one.

    The upstream body is what lands in a checkpoint, so this must refuse rather
    than trust the caller -- and refuse BEFORE opening the file, or the refusal
    would leave the thing it refused to create.
    """
    target = REPO_ROOT / inside
    existed = target.exists()
    with pytest.raises(ScratchPathInsideRepoError, match="INSIDE the repository tree"):
        _fetch(target, client=_upstream())
    assert target.exists() is existed, "the refusal must not create the file"
