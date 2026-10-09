# Fixture policy

**Fixtures in this directory are hand-written or redacted. Never a recorded
upstream response.** Not one, not "just this once for a regression test", not
under a `.example` suffix.

## Why

`quickstart.md` scenario 10 records the reason:

> A committed fixture of a raw upstream response is the likeliest route by
> which the full personal-data payload enters the repository.

Constitution Principle V (NON-NEGOTIABLE) defines the scope that makes this a
publication rather than a convenience:

> "Published" covers everything a third party can reach: the published dataset
> files, any extract, any interactive page, any derived statistic, and **any
> fixture, sample, or test file in the repository.**

The member endpoint returns personal contact, address, date of birth, marital
status and family composition fields for **5,426 named people without
authentication**, and the owner declined to adopt a guardrail against
republishing it. A committed response body is therefore not a test artefact. It
is a publication of that payload, whether or not anyone reads the file.

## What this means in practice

- **Every value in every fixture here is invented or a placeholder.** Where a
  fixture needs to exercise a real-world name form, the *form* is reproduced
  and the identity is fictional — see the note on name variants below.
- **Need a real response to debug?** Fetch it to `$SANSAD_SCRATCH`, which lives
  outside the repository tree and which `make scratch` and
  `sansad.ingest.transport` both refuse to place inside it. Read it there.
  Delete it. Do not copy a fragment of it into this directory.
- **Field names are permitted; field values are not.** `spike/route-capture.md`
  records the upstream's field names and record counts deliberately and holds no
  values. Fixtures follow the same line.
- **`make audit-fields` scans this directory** as one of its three scopes, with
  the 64 KB payload ceiling applied. If a fixture here trips it, the fixture is
  wrong — not the check.

## The name-variant pair

`variants.json` carries the pair `tasks.md` requires: `Shri Sunil Kumar Singh`
and `Singh, Sunil K.`. These are **name forms**, which Principle V permits, and
the member identity they attach to in the fixture is fictional (`fx-`
prefixed). The pair is kept because the honorific-plus-reordering-plus-initial
shape is the one the spike measured as the hard residual class — the 17th Lok
Sabha's unresolved forms are "initials, parenthetical aliases and divergent
orderings", and all four owner-confirmed assertions are of that kind.

## Every fixture here, and what it is for

| File | Exercises |
|---|---|
| `variants.json` | The required variant pair, plus honorific/ordering/initial forms |
| `co_asked.json` | One question with several askers, carried as one record |
| `unresolvable.json` | An asking name with no possible match — must be retained, never guessed |
| `ambiguous.json` | A form matching several members equally — must list candidates |
| `near_identical_members.json` | Two genuinely distinct members with near-identical names — must never merge |
| `roster.json` | A small member roster the above resolve against |
