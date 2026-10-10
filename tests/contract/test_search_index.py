"""T073 — the subject-search index, checked against the published files.

> the index resolves a known subject to its **real prior occurrences** with
> dates, ministries and askers

So the assertion is not "the index contains the term". It is that a reader who
searches a subject reaches the actual questions, and that each one carries the
three things the result is useless without: when it was asked, which ministry it
was put to, and who asked it. The index stores document **ids**, so "resolves"
means those ids are resolvable against the published question records — and the
test resolves them, rather than trusting that they would.

**No grade is asserted, because none is published.** Owner decision 2026-10-10:
the index carries no similarity score, weight or tier. T018's prototype stores
none, so a grade would be unmeasured. The tests below check that the index
publishes no such field, which is the only way that decision stays true.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def members():
    from sansad.ingest.members import load_members

    return load_members(
        json.loads(
            (Path(__file__).resolve().parents[1] / "fixtures" / "roster.json").read_text(
                encoding="utf-8"
            )
        )["members"],
        last_refreshed="2026-10-10",
    )


@pytest.fixture
def published(tmp_path, members, question_records):
    from sansad.publish.partitions import write_partitions
    from sansad.publish.search_index import write_search_index
    from sansad.resolve import resolve_questions

    records = []
    for name in ("co_asked.json", "unresolvable.json", "ambiguous.json", "shared_ques_no.json"):
        records.extend(question_records(name))
    resolved = resolve_questions(records, members)
    write_partitions(tmp_path, resolved.questions)
    write_search_index(tmp_path, resolved.questions)
    return tmp_path, resolved.questions


def _load_index(root: Path) -> dict:
    from sansad.publish.search_index import SEARCH_DIR_NAME, SEARCH_INDEX_NAME

    return json.loads((root / SEARCH_DIR_NAME / SEARCH_INDEX_NAME).read_text(encoding="utf-8"))


def _published_questions(root: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for path in sorted((root / "by-session").glob("*.jsonl")):
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    row = json.loads(line)
                    out[row["question_id"]] = row
    return out


def test_the_index_has_the_shape_t018_measured(published):
    """Postings delta-encoded, tokens lowercased, minimum length 3.

    The document list is prefix-encoded rather than a plain id list -- T072's
    gate, see the module docstring: as plain ids it was 65.5% of the file and
    40.5% over T018's projection. The encoding is checked here and the
    reconstruction is checked below.
    """
    from sansad.publish.search_index import document_count

    root, _ = published
    index = _load_index(root)
    assert set(index) >= {"prefixes", "doc_prefix", "doc_number", "terms", "postings"}
    # Terms are in VALUE position, sorted, with postings in a parallel array --
    # see the module docstring: in key position six ordinary English words look
    # like prohibited field names to the guard, and `make guard` failed on all
    # six before this shape.
    assert isinstance(index["terms"], list) and index["terms"]
    assert isinstance(index["postings"], list)
    assert len(index["terms"]) == len(index["postings"]), "parallel arrays must align"
    assert index["terms"] == sorted(index["terms"]), (
        "terms must be sorted -- the browser binary-searches them"
    )
    assert len(set(index["terms"])) == len(index["terms"]), "a term appears twice"
    assert len(index["doc_prefix"]) == len(index["doc_number"]) == document_count(index)
    assert index["prefixes"], "no prefix table"
    assert max(index["doc_prefix"]) < len(index["prefixes"]), "a doc points past the table"
    for term, deltas in zip(index["terms"], index["postings"], strict=True):
        assert term == term.lower(), "tokens must be lowercased"
        assert len(term) >= 3, "minimum token length is 3"
        assert all(isinstance(d, int) for d in deltas)
        assert deltas[0] >= 0 and all(d >= 1 for d in deltas[1:]), (
            "postings must be delta-encoded ascending doc ids"
        )


def test_every_document_id_reconstructs_exactly(published):
    """The encoding must be lossless, and that is the whole risk it carries.

    Checked against the published question records, not against the objects the
    index was built from -- a reconstruction that agreed with the builder but
    not with the files would pass a weaker test.
    """
    from sansad.publish.search_index import document_count, question_id_at

    root, questions = published
    index = _load_index(root)
    by_id = _published_questions(root)

    rebuilt = [question_id_at(index, i) for i in range(document_count(index))]
    assert rebuilt == [q.question_id for q in questions], "an id did not round-trip"
    assert set(rebuilt) <= set(by_id), "a rebuilt id is not in the published records"


def test_a_known_subject_resolves_to_its_real_prior_occurrences(published):
    """The requirement, end to end: term -> doc ids -> real questions.

    Resolved against the published question records, with the date, the ministry
    and the askers read off each one.
    """
    from sansad.publish.search_index import lookup

    root, questions = published
    index = _load_index(root)
    by_id = _published_questions(root)

    # A subject word the fixtures really use.
    hits = lookup(index, "placeholder")
    assert hits, "a term present in the fixtures resolved to nothing"

    expected = {q.question_id for q in questions if "placeholder" in q.subject.lower()}
    assert set(hits) == expected, (
        f"the index resolved {len(hits)} questions, the records hold {len(expected)}"
    )

    for question_id in hits:
        row = by_id[question_id]
        assert row["date"], f"{question_id}: no date to show"
        assert row["ministry_id"], f"{question_id}: no ministry to show"
        assert "asking_members" in row, f"{question_id}: no asker field at all"
        assert row["resolution_status"], f"{question_id}: no status to flag with"


def test_a_subject_with_no_identified_asker_is_still_indexed(published):
    """FR-004 reaching search: a question whose asker is unknown must still be
    findable, flagged rather than filtered out."""
    from sansad.publish.search_index import lookup

    root, questions = published
    index = _load_index(root)
    by_id = _published_questions(root)

    unlinked = {
        q.question_id
        for q in questions
        if q.resolution_status.value != "resolved" and not q.asking_members
    }
    assert unlinked, "the fixtures carry no unlinked question"

    reachable = set()
    for term in index["terms"]:
        reachable |= set(lookup(index, term))
    assert unlinked <= reachable, "an unlinked question is not reachable by search"
    for question_id in unlinked:
        assert by_id[question_id]["asking_members"] == []


def test_the_index_publishes_no_similarity_grade(published):
    """Owner decision 2026-10-10. The only way the decision stays true."""
    root, _ = published
    index = _load_index(root)
    forbidden = ("score", "grade", "weight", "similarity", "rank", "tier", "idf", "tfidf")
    flat = json.dumps(index).lower()
    present = [name for name in forbidden if f'"{name}"' in flat]
    assert not present, f"the index publishes a grading field: {present}"
    allowed = {"prefixes", "doc_prefix", "doc_number", "terms", "postings", "built"}
    assert set(index) == allowed, f"unexpected top-level keys: {sorted(set(index) - allowed)}"


def test_stopwords_and_short_tokens_are_absent(published):
    from sansad.publish.search_index import MIN_TOKEN_LENGTH, STOPWORDS

    root, _ = published
    index = _load_index(root)
    for term in index["terms"]:
        assert term not in STOPWORDS, f"{term!r} is a stopword and should not be indexed"
        assert len(term) >= MIN_TOKEN_LENGTH


def test_the_scope_is_subjects_only(published):
    """T018 measured two scopes and chose the narrower one.

    The wider scope indexed ministry and member names too, at +58.6% bytes for
    search over fields the page already holds. A ministry name appearing as a
    term would mean the wider scope had been adopted without measurement.
    """
    from sansad.publish.search_index import tokenise

    root, questions = published
    index = _load_index(root)

    del index
    index = _load_index(root)
    subject_terms: set[str] = set()
    for question in questions:
        subject_terms |= tokenise(question.subject)
    assert set(index["terms"]) == subject_terms, (
        f"indexed terms are not exactly the subject terms: "
        f"extra={sorted(set(index['terms']) - subject_terms)[:8]}"
    )
