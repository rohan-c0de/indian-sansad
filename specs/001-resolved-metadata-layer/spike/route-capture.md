# Spike item 1 — Lok Sabha question-metadata route capture

**Task**: T004 (browser capture) · T005 (programmatic request) · T006 (field coverage)
**Date**: 2026-10-09
**Method**: Chrome driven against the source site's own question-listing page, reading the
network log — the method `research.md` establishes, because `GET /api_ls/question` returns a
HAL index exposing only `self`, `health`, `health-path`, `metrics`, and `GET /api_ls` → 404.

**Verdict: VERIFIED WORKING.** The route was retrieved first-hand. `plan.md` Risk 2 and spec
Open Question 2 — "the question-metadata route has never been retrieved first-hand in three
passes" — are closed by this capture.

**No payload is committed.** Every figure below is a field *name*, a record *count*, a byte
*size* or an *aggregate*. No field value appears in this file, and no response body was written
anywhere inside the repository tree.

---

## The route

| | |
|---|---|
| **Method** | `GET` |
| **Exact path** | `/api_ls/question/qetFilteredQuestionsAns` |
| **Full origin** | `https://sansad.in` |
| **Credential required** | **None.** Returned HTTP 200 with `credentials: 'omit'` — no cookie, no API key, no auth challenge. |

> **The path is spelled `qetFilteredQuestionsAns` — `qet`, not `get`.** That is the upstream's
> own spelling, reproduced here verbatim because a silent correction to `get...` yields 404.
> It is a typo in the source service, and it is load-bearing.

### How it was found

The site's own page `/ls/questions/questions-and-answers` issues it. `/ls/questions` — the
path a reader would guess — returns **404 Page Not Found**; the working path was taken from
the site's own navigation link, not guessed.

## Query parameters, with observed behaviour

| Parameter | Required | Observed range | Behaviour |
|---|---|---|---|
| `loksabhaNo` | **Yes** | `13`–`18` enumerated by the session route; `16`, `17`, `18` exercised here | Omitted → **HTTP 400**. Nonexistent value (`99`) → **HTTP 200** with `totalRecordSize: 0` and an empty array — a quiet empty, not an error. |
| `sessionNumber` | No | 17th LS: `1`–`15`. 18th LS: `1`–`8`. | **Omitted → the whole term.** This is the parameter's most useful property and it is not documented anywhere upstream. Nonexistent value (`99`) → 200, `totalRecordSize: 0`. |
| `pageNo` | No | `1`-based | Omitted → page 1. `450` (last page at `pageSize=10`) → 10 records. `451` and `9999` (past the end) → **200 with 0 records**, not an error. **`pageNo=0` → HTTP 500** with an error envelope `{timestamp, status, error, path}`. Pagination is 1-based and 0 is a server fault, not a validation message. |
| `pageSize` | No | `10`–`500` exercised | Omitted → **defaults to 10**. |
| `locale` | No | `en` | Omitted → 200, same record count. English is the default, so Principle IV needs no action here. |

### Pagination and the page-size ceiling

`pageNo` is the pagination parameter. `pageSize` is the page size.

| `pageSize` | Status | Records returned | Body bytes | Elapsed |
|---|---|---|---|---|
| 10 | 200 | 10 | 11,217 | — |
| 50 | 200 | 50 | — | — |
| 100 | 200 | 100 | 96,106 | 3,860 ms |
| 250 | 200 | 250 | 238,465 | 6,481 ms |
| 500 | 200 | 500 | 471,468 | 14,695 ms |
| 5000 | — | — | — | **aborted at 38,002 ms (client timeout)** |

**No page-size ceiling was observed up to 500.** The service honoured every requested size
exactly. Cost is linear at **≈955 bytes and ≈29 ms per record**.

**The ceiling above 500 is UNVERIFIED.** `pageSize=5000` was aborted by *this client* after
38 s; the server was not observed to refuse it. "Exceeded a 38-second client budget" is not
"the server caps the page size", and it is not recorded as one. What follows for the pipeline
is the same either way: at ≈29 ms/record a 500-record page is ~15 s, so the practical page
size is an operating choice about runner time, not a documented limit to discover.

## Required headers

**None beyond a plain `GET` was needed from the browser.** The request succeeded with
`credentials: 'omit'`, so no cookie or session is involved.

This is an **in-browser observation and therefore incomplete**: a same-origin `fetch` still
carries a `Referer`, and the browser supplies its own `User-Agent` and `Accept`. Whether the
route requires either is **UNVERIFIED here by construction** and is what T005 settles by
issuing the request from outside the browser. Recorded as a known gap rather than assumed absent.

## Response envelope

The root is a **JSON array of length 1**. The single element carries the page:

```
[
  {
    "listOfQuestions": [ <pageSize records> ],
    "totalRecordSize": <integer>,
    "_metadata": null
  }
]
```

`Content-Type: application/json`.

- **Total-record field**: `totalRecordSize`.
- `_metadata` was `null` in every response observed.
- The length-1 array wrapper is not a pagination construct; it is simply how the service
  returns the page. A consumer must index `[0]` before reading either key.

### `totalRecordSize` observed values

| Scope requested | `totalRecordSize` |
|---|---|
| 18th LS, session 8 | **4,500** |
| 18th LS, whole term (session omitted) | **34,720** |
| 17th LS, session 1 | **6,198** |
| 17th LS, whole term (session omitted) | **60,549** |
| 16th LS, whole term (outside the covered window) | 79,153 |
| Nonexistent house (`99`) / nonexistent session (`99`) | 0 |

**The covered window is 60,549 + 34,720 = 95,269 questions.** That confirms `plan.md`'s
"~10^5 question records" as an order of magnitude and replaces it with a measured figure.

It also corrects an attribution in `research.md`, which cites "34,720 for one term" without
saying which: **34,720 is the 18th Lok Sabha, not the 17th.** The 17th is 60,549 — roughly
1.75× larger. Any projection that used 34,720 as the typical term is low by that factor.

## Per-record fields

17 field names, union across a 250-record sample, every record carrying all 17:

| Upstream field | Shape observed |
|---|---|
| `quesNo` | number |
| `lokNo` | string |
| `sessionNo` | string |
| `date` | string |
| `type` | string |
| `subjects` | string |
| `ministry` | string |
| `member` | **array of string** |
| `supplementaryType` | boolean |
| `questionText` | **null in every record sampled** |
| `answerText` | **null in every record sampled** |
| `answerTextHindi` | null in every record sampled |
| `supplementaryQuestionResDtoList` | null in every record sampled |
| `questionsFilePath` | string |
| `questionsFilePathHindi` | string |
| `questionsDocPath` | string |
| `questionsDocPathHindi` | string |

### Three things in that table that change what the pipeline may do

1. **`member` exists, is an array of strings, and was non-null on every one of 250 records.**
   This is the gate T006 names: "A missing asking-member field is a VERIFIED BROKEN gate on
   User Story 1." It is **not** missing. User Story 1 is unblocked.

2. **The four `*FilePath` / `*DocPath` fields are document pointers, and Principle III forbids
   following them.** Question and answer text is not served inline — `questionText` and
   `answerText` were null in every record — it sits behind those paths. Under Principle III
   ("No document file MUST ever be opened, parsed, extracted from, or depended on") these four
   fields are **ingestible as nothing at all**: not followed, not fetched, not published.
   Question and answer *text* is therefore a **known gap in the coverage statement**, exactly as
   Principle III requires, and `contracts/published-dataset.md` guarantee 9 already says so.

3. **The two `*Hindi` fields must not be ingested**, per Principle IV. `locale=en` is the
   default, and the English fields are populated independently, so no action beyond not
   reading them is needed.

### Fields with no upstream source (for T006)

| `data-model.md` → Question | Upstream source |
|---|---|
| `question_id` | **No single upstream field.** `quesNo` is unique *within* a session — 250 sampled records, 0 duplicate `quesNo` — so the identity must be the composite `(lokNo, sessionNo, quesNo)`. Recorded as a derivation, not a source field. |
| `house` | `lokNo` (and the route's own `loksabhaNo` parameter) |
| `session` | `sessionNo` |
| `date` | `date` |
| `type` | `type` |
| `subject` | `subjects` (upstream name is plural, value is a single string) |
| `ministry_id` | `ministry` — **a name string, not an id.** A `ministry_id` must be minted and reconciled by this feature; `/api_ls/question/getMinistry` is the reference set. |
| `asking_members` | `member` — **name strings, not ids.** This is the whole identity-resolution problem; it is what Phase 2 item 3 measures. |
| `resolution_status` | Derived by this feature. No upstream equivalent. |
| `source_record_ref` | Derived — the composite above plus the route. |
| `last_refreshed` | Derived at publish time. |

**No Question field is without a source or a stated derivation.** Nothing in `data-model.md`
→ Question is blocked by the upstream.

## Asking-member name forms — aggregate shape

Over a **250-question** sample from the 18th LS session 8. No name is reproduced.

| Measure | Value |
|---|---|
| Name instances | 376 |
| Distinct name forms | 288 |
| Carrying a leading honorific (`Shri`, `Smt`, `Dr`, `Prof`, …) | **369 of 376 (98.1%)** |
| Containing a comma (inverted `Surname, Given` form) | **0** |
| Containing a single-letter initial | 46 |
| Containing a `.` anywhere | 95 |
| Containing parentheses | 0 |
| Entirely upper-case | 0 |
| Non-ASCII characters | **0** |
| Token count | 2 tokens: 6 · 3 tokens: 196 · 4 tokens: 154 · 5 tokens: 15 · 6 tokens: 5 |
| Character length | min 11, max 51 |

**The honorific is the dominant normalisation problem**, present on 98.1% of instances, and it
is not part of any person's identity.

**A finding that contradicts an input assumption, recorded rather than smoothed over:**
`research.md` and `quickstart.md` scenario 1 both build on the real variant pair
`Shri Sunil Kumar Singh` / `Singh, Sunil K.`, and `plan.md` requires reconciliation fixtures
drawn from it. **Zero comma-inverted forms appear in these 376 instances.** That does not mean
the pair is wrong — the inverted form plausibly comes from the member roster or from a
different route, and 376 instances from one session is a narrow window. It does mean the
comma-inverted form is **not evidenced on this route**, and a fixture asserting the question
route serves it would be asserting something unobserved. Which source carries the inverted
form is **UNVERIFIED and open**.

## Asker multiplicity — the factor `research.md` records as never measured

`research.md`: "The multiplier depends on the **mean asker count per question**, which this
project has never measured." First measurement:

| Sample | Questions | Name instances | Mean askers/question | Max askers |
|---|---|---|---|---|
| 50 records | 50 | 66 | **1.32** | **6** |
| 250 records | 250 | 376 | **1.504** | **20** |

**These two samples disagree, and the disagreement is the finding.** Mean rose from 1.32 to
1.504 and the maximum from 6 to **20** when the sample grew 5×. The tail is long and neither
figure has converged. Recorded as **"observed twice, not converged"** — T013 measures it over
the real slice, and T017 must not treat 1.5 as settled.

## Sibling routes captured in the same network log

All returned HTTP 200. Recorded because the pipeline needs the first four and because none of
them had been retrieved first-hand before.

| Route | Purpose |
|---|---|
| `GET /api_ls/question/getMinistry?lkNo=<n>&locale=en` | Ministry reference set. 17 distinct `ministry` values appeared in the 250-record sample. |
| `GET /api_ls/question/getMembers?lkNo=<n>` | Member list as the question UI uses it — a second name-form source to diff against the roster. |
| `GET /api_ls/business/getAllLoksabhaAndSession?locale=en` | Session enumeration. Root is an array of `{loksabha, sessions[{sessionNo, sessionPeriod, dates[]}]}`. |
| `GET /api_ls/business/AllLoksabhaAndSessionDates` | Session dates. |
| `GET /api_ls/public/officer-responsible/officer-list?module=13&locale=en` | Not needed by this feature. Recorded only so it is not re-discovered later. |

### Sitting days, from the session route

| Term | Sessions | Sitting days per session | Total |
|---|---|---|---|
| 17th LS | 1–15 | 37, 20, 23, 10, 25, 18, 18, 28, 16, 13, 27, 17, 4, 14, 9 | **279** |
| 18th LS | 1–8 | 7, 15, 20, 27, 21, 15, 28, **0** | **133** |

**Measured total: 412 sitting days.** `plan.md` estimates "~428 Lok Sabha sitting days (274
cited for the 17th, ~154 estimated for the 18th)". Both halves were off: the 17th is 279, not
274, and the 18th is 133, not ~154.

**Session 8 of the 18th LS lists 0 dates while reporting 4,500 questions.** The session is
current, so the date array is plausibly not yet populated — but "plausibly" is not a finding.
Cause **UNVERIFIED**. It matters because a sitting-day denominator of 0 would divide by zero in
any per-sitting-day rate, and because FR-013 requires a known gap to be declared rather than
passed over.

## Verbatim outputs

Captured with the browser's own `fetch` against the same origin, `credentials: 'omit'`.
Values are absent by construction — each probe returns names, shapes, counts and byte sizes only.

### Envelope, field names, and absence of a credential

```
{
 "httpStatus": 200,
 "contentType": "application/json",
 "bodyBytes": 11217,
 "credentialsOmitted": true,
 "envelope": {
  "0": {
   "listOfQuestions": "array[len=10]",
   "totalRecordSize": "number(4500)",
   "_metadata": "null"
  }
 },
 "recordsArrayPath": "0.listOfQuestions",
 "recordsOnPage": 10,
 "recordFieldNames": [
  "answerText",
  "answerTextHindi",
  "date",
  "lokNo",
  "member",
  "ministry",
  "quesNo",
  "questionText",
  "questionsDocPath",
  "questionsDocPathHindi",
  "questionsFilePath",
  "questionsFilePathHindi",
  "sessionNo",
  "subjects",
  "supplementaryQuestionResDtoList",
  "supplementaryType",
  "type"
 ],
 "recordFieldCount": 17
}
```

### Field shapes, and the asking-member field's presence

```
{
 "recordsSampled": 50,
 "totalRecordSize": 4500,
 "fieldShapes": {
  "answerText": "null",
  "answerTextHindi": "null",
  "date": "string",
  "lokNo": "string",
  "member": "array[len=N] of string",
  "ministry": "string",
  "quesNo": "number",
  "questionText": "null",
  "questionsDocPath": "string",
  "questionsDocPathHindi": "string",
  "questionsFilePath": "string",
  "questionsFilePathHindi": "string",
  "sessionNo": "string",
  "subjects": "string",
  "supplementaryQuestionResDtoList": "null",
  "supplementaryType": "boolean",
  "type": "string"
 },
 "memberFieldPresentOnAllRecords": true,
 "memberNullCount": 0,
 "askerCountDistribution": {
  "1": 41,
  "2": 6,
  "3": 1,
  "4": 1,
  "6": 1
 },
 "askerCountMin": 1,
 "askerCountMax": 6,
 "askerCountMean": 1.32
}
```

### Page-size behaviour

```
[
 {"label": "pageSize=100", "status": 200, "bytes": 96106,  "returned": 100, "total": 4500, "ms": 3860},
 {"label": "pageSize=250", "status": 200, "bytes": 238465, "returned": 250, "total": 4500, "ms": 6481},
 {"label": "pageSize=500", "aborted": true, "after_ms": 12002}
]
{"label": "pageSize=500", "status": 200, "bytes": 471468, "returned": 500, "total": 4500, "ms": 14695}
{"label": "pageSize=5000", "clientAborted": true, "after_ms": 38002}
```

### Parameter requirements and ranges

```
[
 {"label": "last page (pageNo 450 of 450)",  "status": 200, "returned": 10, "total": 4500,  "ms": 1498},
 {"label": "one past the end (pageNo 451)",  "status": 200, "returned": 0,  "total": 4500,  "ms": 961},
 {"label": "far past the end (pageNo 9999)", "status": 200, "returned": 0,  "total": 4500,  "ms": 1353},
 {"label": "pageNo zero",                    "status": 500, "returned": null, "total": null, "ms": 269,
  "note": "no listOfQuestions key; top keys are timestamp status error path"},
 {"label": "session param omitted",          "status": 200, "returned": 10, "total": 34720, "ms": 1586},
 {"label": "house param omitted",            "status": 400, "returned": null, "total": null, "ms": 268,
  "note": "body was not JSON"},
 {"label": "locale param omitted",           "status": 200, "returned": 10, "total": 4500,  "ms": 1264},
 {"label": "pageSize param omitted",         "status": 200, "returned": 10, "total": 4500,  "ms": 1116},
 {"label": "no params at all",               "status": 400, "returned": null, "total": null, "ms": 255,
  "note": "body was not JSON"},
 {"label": "17th LS whole term, no session", "status": 200, "returned": 10, "total": 60549, "ms": 1288},
 {"label": "17th LS session 1",              "status": 200, "returned": 10, "total": 6198,  "ms": 849},
 {"label": "16th LS whole term (out of covered window)", "status": 200, "returned": 10, "total": 79153, "ms": 1401},
 {"label": "house 99 (nonexistent)",         "status": 200, "returned": 0,  "total": 0,     "ms": 318},
 {"label": "18th LS session 99 (nonexistent)","status": 200, "returned": 0, "total": 0,     "ms": 1008}
]
```

### Name-form aggregate shape

```
{
 "questionsSampled": 250,
 "totalNameInstances": 376,
 "distinctNameForms": 288,
 "withLeadingHonorific": 369,
 "withCommaInversion": 0,
 "withSingleLetterInitial": 46,
 "withDotAnywhere": 95,
 "withParentheses": 0,
 "allUpperCase": 0,
 "tokenCountDistribution": {"2": 6, "3": 196, "4": 154, "5": 15, "6": 5},
 "charLenMin": 11,
 "charLenMax": 51,
 "nonAsciiForms": 0,
 "askersPerQuestionMean": 1.504,
 "askersPerQuestionMax": 20,
 "distinctMinistryValues": 17,
 "distinctTypeValues": 2,
 "quesNoDuplicatedWithinSession": 0
}
```

### Session enumeration and sitting days

```
[
 {"loksabha": 17, "sessionCount": 15,
  "sessionNumbers": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15],
  "sessionObjectFieldNames": ["dates","sessionNo","sessionPeriod"],
  "datesFieldShape": "array[len 37] of string",
  "sittingDayCountsPerSession": [37,20,23,10,25,18,18,28,16,13,27,17,4,14,9],
  "totalSittingDaysInTerm": 279},
 {"loksabha": 18, "sessionCount": 8,
  "sessionNumbers": [1,2,3,4,5,6,7,8],
  "sessionObjectFieldNames": ["dates","sessionNo","sessionPeriod"],
  "datesFieldShape": "array[len 7] of string",
  "sittingDayCountsPerSession": [7,15,20,27,21,15,28,0],
  "totalSittingDaysInTerm": 133}
]
```

---

## What is still open after T004

1. **Headers required by a non-browser client** — UNVERIFIED by construction. T005.
2. **Whether the server caps `pageSize` above 500** — UNVERIFIED; only a client timeout observed.
3. **Which source carries the comma-inverted name form** — not this route, on this sample.
4. **Why 18th LS session 8 reports 0 sitting days against 4,500 questions** — UNVERIFIED.
5. **Mean askers per question** — observed twice (1.32, 1.504), not converged; max jumped 6 → 20.
6. **Rajya Sabha** — untouched by this capture. `plan.md` Risk 1 stands exactly as recorded.

---

# T005 — the same route, programmatically, from outside the browser

**Verdict: VERIFIED WORKING.** Both routes returned HTTP 200 to a plain `curl` with no
credential, no cookie and no special header. The question route is reachable by a
non-browser client, which is what the pipeline will be.

**Bodies were written only under `$SANSAD_SCRATCH`** —
`/private/var/folders/.../T/sansad-scratch/t005/` — which `make scratch` asserted is outside
the repository before either request was issued. Nothing was written inside the tree, and
`git status` was checked after the fact to confirm it.

## Both status lines, verbatim

```
# GET /api_ls/question/qetFilteredQuestionsAns  (the route T004 captured)
HTTP/1.1 200 

# GET /api_ls/member  (the control group: the one route research.md records as verified end-to-end)
HTTP/1.1 200 
```

Both status lines carry a trailing space and no reason phrase. That is the server's own output,
reproduced as received.

## Measurements

| | Question route | Member roster (control) |
|---|---|---|
| HTTP version | 1.1 | 1.1 |
| Status | **200** | **200** |
| `Content-Type` | `application/json` | `application/json` |
| Response byte size | **11,217** | **5,197,598** (≈5.0 MiB) |
| `time_total` | **4.736 s** | **46.504 s** |
| `time_namelookup` | 2.655 s | 0.003 s (DNS warm) |
| `time_connect` | 2.919 s | 0.255 s |
| `time_starttransfer` | 4.733 s | 3.732 s |
| Redirects | 0 | 0 |

The question route's 11,217 bytes is **byte-identical to the browser's figure for the same
query**, so the browser capture and the programmatic request agree.

**The control group carries a warning for FR-009.** The member roster is a single
**5.0 MiB, 46.5-second** response — `time_starttransfer` was 3.7 s, so 42.8 s of that is pure
transfer. One unpaginated fetch spending three quarters of a minute is a material fraction of a
free runner's job budget before any question page is fetched, and it is the *control*, not the
workload. T008's "maximum single job duration" figure must be read against this.

## Response header set

Identical on both routes:

```
HTTP/1.1 200 
Date: Fri, 09 Oct 2026 18:15:00 GMT
Content-Type: application/json
Transfer-Encoding: chunked
Connection: keep-alive
Vary: Origin
Vary: Access-Control-Request-Method
Vary: Access-Control-Request-Headers
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Cache-Control: no-cache, no-store, max-age=0, must-revalidate
Pragma: no-cache
Expires: 0
X-Frame-Options: SAMEORIGIN
X-Content-Security-Policy: script-src 'self'
Content-security-policy: script-src 'self'
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
Referrer-Policy: strict-origin-when-cross-origin
Access-Control-Allow-Credentials: false
Access-Control-Max-Age: 86400
Access-Control-Expose-Headers: Accept-Language
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Resource-Policy: same-site
```

### Required headers: none. T004's open item 1 is now closed.

```
# User-Agent and Accept both stripped from the request entirely:
http_code=200 size=11217 time=1.639763
```

Same status, same byte count. **The route requires no header whatsoever** — no `User-Agent`,
no `Accept`, no `Referer`, no cookie. T004 could only observe this from inside a browser, which
always supplies those; this closes it.

### No cookie, no session

No `Set-Cookie` appears in any captured response, and `Access-Control-Allow-Credentials: false`.
Nothing to carry between requests. **No credential is required** — stated by T004 from the
browser and now confirmed from outside it.

### `Access-Control-Allow-Origin` is absent — the front-end design's load-bearing fact

```
# grep -i 'access-control-allow-origin' over the response headers:
ACAO ABSENT
```

`research.md` records "Cross-origin browser requests to the upstream are not permitted" and the
entire client-side decision rests on it: the page reads **this feature's own published files from
its own host** and never calls the upstream. That fact was inherited from the assessment; it is
now **verified first-hand**. The upstream sends `Vary: Origin` and an `Access-Control-Max-Age`
but no `Access-Control-Allow-Origin`, so a browser on any other origin is refused.

This cuts both ways and the second way is the one worth writing down: **the published dataset
must itself be served with permissive CORS or from the same origin as `web/`**, or the reader
page hits exactly this wall against its own files. T015's requirement to confirm the host can
serve `data/published/` and `web/` from one origin is therefore not a convenience — it is the
condition that makes the page possible at all.

### An unasked-for finding: `HEAD` returns 403 where `GET` returns 200

```
# curl -I (HEAD) against the identical URL that GET answers with 200:
http_code=403
```

**This is the first direct evidence bearing on `plan.md` Risk 1.** `research.md` records
`GET /api_rs/members` returning **403 where every sibling path returns 404**, cause
**UNVERIFIED**, with "a bot/WAF rule, a path-specific block, or genuine authorisation" all
consistent with the observation.

Here the *same URL*, on a route that is unambiguously public and unauthenticated, answers `GET`
with 200 and `HEAD` with 403. Authorisation cannot explain that: nothing about the caller
changed, only the method. So this service family **does return 403 for request shapes it
dislikes, independently of any access control** — which raises the prior on the Rajya Sabha 403
being a filter rather than a permission boundary.

**It does not resolve Risk 1 and is not recorded as resolving it.** A method filter on `HEAD`
and a path filter on `/api_rs/members` are different rules, and one does not demonstrate the
other. The verdict on the Rajya Sabha 403 stays **UNVERIFIED**; what changes is that
`research.md`'s "genuine authorisation" branch is now the less likely of its three candidates,
and T088's Rajya Sabha investigation has a concrete lead — vary the method and the request
shape, not the path.

**Operational consequence now**: the pipeline must not use `HEAD` for change detection. The
obvious cheap freshness probe — `HEAD` the route and compare `Content-Length` — returns 403 on
this service. FR-009's "detect newly published material" must be built on `GET` with a small
`pageSize` and a `totalRecordSize` comparison instead. Discovering that here costs nothing;
discovering it inside a scheduled job costs a silent refresh failure.

---

# T006 — does the route serve the fields the pipeline needs?

**Verdict: VERIFIED WORKING for every field the pipeline needs, with two derivations and one
declared gap.** No field in `data-model.md` → Question is blocked by the upstream.

**The User Story 1 gate is passed.** T006 names one condition that would fail it — "A missing
asking-member field is a VERIFIED BROKEN gate on User Story 1, not a detail". The
asking-member field is **present, non-null on 250 of 250 sampled records, and an array of
strings**. US1 is not blocked.

## Field-by-field mapping

Every field of `data-model.md` → Question, against the route's 17 observed field names.

| `data-model.md` → Question | Upstream field | Status |
|---|---|---|
| `question_id` | — | **DERIVED.** No single upstream id. `quesNo` is a number unique *within* a session (250 records sampled, **0 duplicates**), so identity is the composite `(lokNo, sessionNo, quesNo)`. Stable as long as the upstream does not renumber. |
| `house` | `lokNo` | **PRESENT.** String. Also echoed by the request's own `loksabhaNo`. |
| `session` | `sessionNo` | **PRESENT.** String. Must be House-scoped per `data-model.md` → Session, which the composite above already does. |
| `date` | `date` | **PRESENT.** String. Format not yet asserted — see open item below. |
| `type` | `type` | **PRESENT.** String. 2 distinct values in the sampled session, consistent with starred/unstarred. |
| `subject` | `subjects` | **PRESENT.** Upstream name is plural, the value is a single string. The pipeline's field is singular; the rename is recorded so it is not mistaken for a list. |
| `ministry_id` | `ministry` | **PRESENT AS A NAME, NOT AN ID.** A `ministry_id` must be minted and reconciled by this feature. `GET /api_ls/question/getMinistry?lkNo=<n>` is the reference set; 17 distinct ministry strings appeared in the sampled session. Ministry reconciliation is a second, smaller instance of the same identity problem as members — `data-model.md` already requires it ("renaming upstream MUST NOT create a second ministry identity"). |
| `asking_members` | `member` | **PRESENT AS NAME STRINGS, NOT IDS.** `array[len=N] of string`, 98.1% carrying a leading honorific. This is the identity-resolution problem the whole feature turns on; spike item 3 measures whether it is tractable. |
| `resolution_status` | — | **DERIVED** by this feature. No upstream equivalent, and there should not be one. |
| `source_record_ref` | — | **DERIVED**: the composite identity plus the route that produced it. |
| `last_refreshed` | — | **DERIVED** at publish time. |

## Fields the route serves that the pipeline must refuse

Naming these is part of the answer, because an unused upstream field is a field that can leak
into the published record by default — Principle V's "The absence of a prohibition is NOT
permission".

| Upstream field | Why refused |
|---|---|
| `questionsFilePath` | **Principle III.** A document pointer. Not followed, not fetched, not published. |
| `questionsDocPath` | **Principle III.** Same. |
| `questionsFilePathHindi` | **Principles III and IV.** |
| `questionsDocPathHindi` | **Principles III and IV.** |
| `answerTextHindi` | **Principle IV.** English only. |
| `questionText` | Null in every record sampled. Not refused on principle — simply not served. |
| `answerText` | Null in every record sampled. Same. |
| `supplementaryQuestionResDtoList` | Null in every record sampled. Shape unknown; nothing to map yet. |
| `supplementaryType` | Boolean, populated. **Not in `data-model.md`.** Carries no personal data, so Principle V does not bar it — but it is not in the model and is therefore **not published** without a decision to add it. Recorded so the choice is deliberate rather than incidental. |

## The one declared gap: question and answer text

`questionText` and `answerText` were **null on every record sampled**. The text sits behind the
four `*FilePath` / `*DocPath` document pointers, and **Principle III forbids opening them** —
"No document file MUST ever be opened, parsed, extracted from, or depended on", with no
exception for one-off local work.

Principle III states what to do with such a fact: "If a required fact exists only inside a
document file, that fact is out of scope. It MUST be recorded as a known gap in the coverage
statement, not obtained by parsing."

So: **question and answer text is a known gap, to be declared in the Coverage Statement.**
`contracts/published-dataset.md` guarantee 9 already promises exactly this to consumers
("Consumers wanting debate or answer text will not find it here"), so the contract needs no
change — but the Coverage Statement must say it explicitly, and `data-model.md` → Coverage
Statement has no field for it. Its `known_gaps` field is typed as "Sessions or dates known to
be missing or incomplete", which does not cover a *field-level* gap that applies to every
record in every session.

**This is a real shortfall against FR-013 and it is not fixed here.** Recorded for Phase 3,
where the Coverage Statement is built: `known_gaps` needs to admit a field-level entry, or a
sibling field must carry it. Phase 2 is a measurement phase and changing `data-model.md` is
outside its scope.

## Open after T006

1. **`date` string format is unasserted.** The field is a string and was not parsed, because
   parsing it would mean reading values. The pipeline must assert the format on first ingest
   rather than assume ISO-8601 — FR-013 excludes questions outside the covered window, and a
   misparsed date silently mis-scopes that exclusion.
2. **`supplementaryQuestionResDtoList` shape is unknown** — null throughout the sample. If it
   carries supplementary questions with their own askers, it is a second asking-member surface
   and FR-003's "co-asked question carries every asking member" would extend to it. Must be
   re-checked on a session where it is populated.
3. **`quesNo` uniqueness is observed within one session only** (250 records, 0 duplicates). The
   composite key assumes it holds across all 23 sessions in the window. **Observed once, not
   established** — the ingest must assert it, not trust it.
