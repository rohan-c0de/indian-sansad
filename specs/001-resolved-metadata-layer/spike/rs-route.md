# Phase 9 — Rajya Sabha route investigation

**Feature**: `specs/001-resolved-metadata-layer` | **T098, T099, T100** | **Date**: 2026-10-10

**This phase investigated and stopped.** No ingest, no partition, no page, no
pipeline change. The dataset still covers the Lok Sabha only.

> **Principle V discipline for this whole file.** Status lines, header **names**,
> field **names**, record **counts** and byte sizes only. **No value from any
> upstream record appears anywhere below**, and no response body, HAR file or
> capture artefact was written inside this repository. The capture drivers were
> throwaway scripts outside the tree and are not committed. One route serves
> `dob`, `emailID`, `localAdd`, `localTele`, `permanentAdd` and `permanentTele`
> — its field names are recorded, its body was read only to enumerate those
> names, and `bio-data` was deliberately **not** read at all (see *What was not
> done, on purpose*).

---

## Verdict

**A Rajya Sabha route is found, and the 403 that motivated this phase was never
evidence about the Rajya Sabha at all.**

| | |
|---|---|
| **Member roster** | `GET https://sansad.in/api_rs/member/sitting-members` → **HTTP/1.1 200**. **2,547 members** across sitting (243) and former (2,304), paginated, no credential |
| **Question metadata** | `GET https://rsdoc.nic.in/Question/Search_Questions?whereclause=ses_no=<n>` → **HTTP/2 200**. 3,325 records for one session, 4,260,914 B JSON, no credential |
| **The `/api_rs/members` 403** | **A wrong-path 403, not a block.** The *same path* on the Lok Sabha service — `GET /api_ls/members` — returns the **same 403**, from the same client, seconds after `GET /api_ls/member` returned 200 |
| **Three candidate causes** | "bot/WAF rule" **not supported**; "genuine authorisation" **not supported as an explanation of Rajya Sabha availability**; "path-specific" **supported**. The residual question of *which* mechanism denies that one path is **UNVERIFIED** and does not matter — see T099 |
| **Runner reachability** | **NOT YET CHECKED.** T099 requires it and the workflow is written and committed **unpushed**, awaiting the owner |

---

# T098 — the browser capture

## Method

Headless Chrome (Chrome/154.0.8037.98) driven over CDP by throwaway scripts
outside the repository tree, reusing `tools/cdp.mjs`. **A fresh ephemeral
profile each run**, so no cookie, no logged-in session and no stored credential
could confound the "is a credential needed?" question — the reason the user's
own browser was not used.

Hosts were **enumerated rather than permitted**: the resolver ran
`MAP * ~NOTFOUND` with an explicit `EXCLUDE` per allowed host, so a host the
page contacted that was not on the list appeared in the log as
`ERR_NAME_NOT_RESOLVED` rather than silently succeeding. The list was grown
until no unresolved host remained. **That is how the two third-party data hosts
were found**: the first run allowed `sansad.in` only, and the log showed the
page reaching for hosts that were not it.

Pages driven, taken from the Rajya Sabha section's **own navigation** (129
hrefs read off `/rs`), never guessed — T004's method:

| Page | Driven | Interaction |
|---|---|---|
| `/rs/members` | yes | load only |
| `/rs/questions/questions-and-answers` | yes | load, then its own **Apply** and **Questions List** buttons clicked |
| `/ls/questions/questions-and-answers` | yes, **as the control** | load only, same client, same run |

## The data requests the Rajya Sabha pages make

Static assets, CSS, fonts and `_next` chunks omitted; `/rs/members` made 20 and
`/rs/questions/questions-and-answers` made 336 of them.

### `/rs/members`

```
GET  https://sansad.in/api_rs/member/profession?locale=en                       http/1.1 200
GET  https://sansad.in/api_rs/member/education-level?locale=en                  http/1.1 200
GET  https://sansad.in/api_rs/member/sitting-members?<24 parameters>            http/1.1 200
```

The third is the roster route. The page sends **24 query parameters**, all but
`page`, `size` and `mpFlag` empty. Twenty-one of their names are recorded here:
`state`, `party`, `gender`, `page`, `size`, `mpFlag`, `ageFrom`, `ageTo`,
`terms`, `search`, `locale`, `month`, `ministership`, `membershipFrom`,
`membershipTo`, `educationLevelCode`, `degreeCode`, `subjectCode`,
`profession1`, `profession2`, `profession3`, `nominated`.

**The twenty-fourth is deliberately not reproduced, and `make guard` is why.**
It names a Principle V prohibited attribute — one of the family the Constitution
lists as "number of sons and daughters" — as a *filter parameter*, so the Rajya
Sabha roster route lets a caller select members by it. The first draft of this
file pasted the parameter list verbatim and **the guard refused the tree**:

```
PROHIBITED ATTRIBUTES FOUND (values deliberately not shown):
  specs/001-resolved-metadata-layer/spike/rs-route.md:75: key '<REDACTED HERE>' is a
  prohibited 'number of sons and daughters' field (Constitution Principle V)

guard: FAIL -- 1 attribute violation(s), 0 size violation(s) across 1988 scanned file(s)
```

The guard names the offending spelling in its own output, so **that one word is
redacted inside the quoted output above** — pasting the failure verbatim failed
the guard a second time, on the line that quoted it. Everything else in that
output is as printed.

That is the guard working on the phase that was investigating, not publishing —
Principle V's "published" covers "any fixture, sample, or test file in the
repository", and a spike note is one. Recorded rather than quietly reworded,
because it is also the first evidence that **the Rajya Sabha member route's
surface is wider than the Lok Sabha's** in exactly the direction Principle V
cares about. `gender`, `ageFrom` and `ageTo` are filters over attributes
`spec.md` puts out of scope for composition but which are not on the prohibited
list, so they are named above.

**`page` is 1-based**: `page=0` → **HTTP/1.1 500**, the same
0-is-a-server-fault behaviour T004 recorded for the Lok Sabha question route's
`pageNo=0`. `mpFlag` selects the cohort — see the counts below.

### `/rs/questions/questions-and-answers`, on load

```
GET  https://sansad.in/api_rs/member/member-list                                 http/1.1 200
GET  https://rsdoc.nic.in/question/GetAllministary                               h2 200
GET  https://rsdoc.nic.in/question/Get_sessionforQuestionSearch                  h2 200
GET  https://rsdoc.nic.in/Question/Search_Questions?whereclause=ses_no=271       h2 200
OPTIONS https://integration.rajyasabha.digital/api-ext/api/v1/sessions/allsessiondatelist          http/1.1 204 No Content
GET  https://integration.rajyasabha.digital/api-ext/api/v1/sessions/allsessiondatelist             http/1.1 200 OK
OPTIONS https://integration.rajyasabha.digital/api-ext/api/v1/sessions/questionsessiondatelist?session=271  http/1.1 204 No Content
GET  https://integration.rajyasabha.digital/api-ext/api/v1/sessions/questionsessiondatelist?session=271     http/1.1 200 OK
```

### ...and on its own **Apply** button

```
GET  https://rsdoc.nic.in/Question/Search_Questions?whereclause=ses_no=271       h2 200
```

### ...and on its **Questions List** tab

```
GET  https://sansad.in/api_poi/cons-connect/languages?house=RS                   http/1.1 200
GET  https://sansad.in/api_ls/business/publicHolidayDates?month=10&year=2026&locale=en  http/1.1 200
GET  https://sansad.in/api_rs/business/questionUrls?quesDay=10&quesMonth=10&quesYear=2026&locale=en  http/1.1 200
GET  https://sansad.in/api_rs/business/getSessionsList?docType=SQ                http/1.1 200
```

**The search parameter is a `whereclause`.** `?whereclause=ses_no=271` is sent
by the page as written — an unencoded fragment of a filter expression in a
query string. Recorded as observed; **nothing was constructed beyond swapping
the session number the page itself used**, and no other clause was tried.

## Instability recorded rather than smoothed

The request set was **not identical across runs**, and this is stated because
the first capture would otherwise read as authoritative:

| Run | `translation-plugin.bhashini.co.in` | `rsdoc.nic.in` requests observed |
|---|---|---|
| allow `sansad.in` only, 9 s wait | blocked | **3** (`GetAllministary` ×2, `Get_sessionforQuestionSearch`) |
| all hosts allowed, 30 s wait, ×2 | loaded, 4 × 200 | **0** |
| all hosts allowed, 25 s wait, then **Apply** clicked | loaded | **4**, including `Search_Questions` |

So the `rsdoc.nic.in` calls appeared in the run where a third-party translation
script failed to load, vanished in two runs where it loaded, and reappeared
when the page's own Apply button was clicked. **Whether the translation script
affects the page's request order is UNVERIFIED** and was not chased: the route
itself was confirmed directly from outside the browser instead, which does not
depend on the page's JS at all.

## Every host the Rajya Sabha pages contact

| Host | Role | Status observed |
|---|---|---|
| `sansad.in` | the member routes, session/ministry reference, the page itself | 200 |
| `rsdoc.nic.in` | **question metadata**, ministry list, session list | h2 200 |
| `integration.rajyasabha.digital` | session date lists | 200 **in the browser**, **401 from curl** |
| `translation-plugin.bhashini.co.in` | third-party translation widget, no data | 200 |
| `fonts.googleapis.com` | fonts | never resolved; not data |

---

# The request-by-request diff against the Lok Sabha control

T004 and T005 are the control group. Every row below is a request issued in
this phase, with the Lok Sabha equivalent beside it, from the same client.

## 1. The path that returns 403 — the finding

```
GET https://sansad.in/api_ls/member                     HTTP/1.1 200
GET https://sansad.in/api_ls/members                    HTTP/1.1 403      <-- LOK SABHA, plural
GET https://sansad.in/api_ls/zzz-no-such-route-here     HTTP/1.1 404 Not Found
GET https://sansad.in/api_rs/members                    HTTP/1.1 403      <-- the original finding
GET https://sansad.in/api_rs/member                     HTTP/1.1 404 Not Found
GET https://sansad.in/api_rs/zzz-no-such-route-here     HTTP/1.1 404 Not Found
```

**`/api_ls/members` returns 403.** The Lok Sabha service — the one this project
fetches 5,426 member records from, unauthenticated, in every refresh — gives
the identical 403 for the identical path shape. `research.md`'s observation
that "`GET /api_rs/members` returns 403 where every sibling path returns 404"
is true, and it is **equally true of the Lok Sabha**. The House-to-House
comparison was never made, and it is the one that matters.

The 403s are also distinguishable from the 404s by **which layer answers**:

| | `/api_ls/member` 200 | `/api_{ls,rs}/members` 403 | unmatched path 404 |
|---|---|---|---|
| Status line | `HTTP/1.1 200 ` (no reason phrase) | `HTTP/1.1 403 ` (no reason phrase) | `HTTP/1.1 404 Not Found` |
| `Content-Type` | `application/json` | `application/json` | `*/*` |
| Header count | 22 | **23** | **4** |
| `Set-Cookie` | **absent** | **`JSESSIONID=…; Path=/; HttpOnly`** | absent |

The 403 is the only response of the three that **mints a session** — it reaches
an application security filter, which then denies. The 404 carries four headers
and a reason phrase: a different layer, which the request never gets past. Both
403s, `api_ls` and `api_rs`, have byte-for-byte the same header shape.

## 2. Headers and cookies, against T005

T005 established of the Lok Sabha routes: no header required at all, no cookie,
no `Set-Cookie`, and `HEAD` → 403 where `GET` → 200. Repeated here:

```
# User-Agent and Accept both stripped from the request entirely
sansad.in/api_rs/member/sitting-members?page=1&size=1&mpFlag=1   http_code=200 size=1235     time=0.90
sansad.in/api_rs/member/member-list                              http_code=200 size=767960   time=2.22
rsdoc.nic.in/question/Get_sessionforQuestionSearch               http_code=200 size=3061     time=1.11
rsdoc.nic.in/Question/Search_Questions?whereclause=ses_no=271    http_code=200 size=4260914  time=17.16
sansad.in/api_ls/member            (CONTROL)                     http_code=200 size=5197598  time=13.86

# HEAD, the method T005 found returns 403 on the Lok Sabha route
HEAD sansad.in/api_rs/member/member-list                         http_code=403
HEAD sansad.in/api_ls/member       (CONTROL)                     http_code=403
HEAD rsdoc.nic.in/question/Get_sessionforQuestionSearch          http_code=404
```

**No difference on `sansad.in`.** Same 200 with every header stripped, same
403 on `HEAD`, no cookie either way. The response header **name** set of
`/api_rs/member/sitting-members` is **identical** to `/api_ls/member`'s —
`diff` reports no difference. The Rajya Sabha member routes behave exactly like
the Lok Sabha routes this project already depends on.

Request header **names** the page sends, per host (names only, no values):

```
sansad.in/api_rs/…                 Accept, Referer, User-Agent, sec-ch-ua, sec-ch-ua-mobile, sec-ch-ua-platform
rsdoc.nic.in/…                     Accept, Referer, User-Agent, sec-ch-ua, sec-ch-ua-mobile, sec-ch-ua-platform
integration.rajyasabha.digital/…   Accept, Authorization, Referer, User-Agent, sec-ch-ua, …
```

**`Authorization` appears on exactly one host**, and it is the one that answers
401 outside the browser. One variable at a time against that 401:

```
bare             http_code=401  HTTP/1.1 401 Unauthorized
+ Referer        http_code=401  HTTP/1.1 401 Unauthorized
+ Origin         http_code=401  HTTP/1.1 401 Unauthorized
+ Origin+Referer http_code=401  HTTP/1.1 401 Unauthorized
+ User-Agent     http_code=401  HTTP/1.1 401 Unauthorized
```

None of the three request-shape headers moves it, and the page sends a header
the others do not. **`integration.rajyasabha.digital` needs a credential this
project does not have** — the only genuine authorisation boundary found in this
phase, and it sits in front of **session date lists**, which `rsdoc.nic.in`'s
`Get_sessionforQuestionSearch` and `sansad.in`'s `getSessionsList?docType=SQ`
both serve without one. Recorded; not needed.

## 3. The server stack, and the CORS fact that is load-bearing elsewhere

```
# rsdoc.nic.in response headers, verbatim (names and values that are not record data)
HTTP/2 200
content-type: application/json; charset=utf-8
server: Microsoft-IIS/10.0
server: Unknown
access-control-allow-origin: *
x-frame-options: DENY
x-robots-tag: noindex, nofollow
content-length: 4260914
```

Three differences from the Lok Sabha control worth naming:

1. **HTTP/2, IIS, `Content-Length`** rather than HTTP/1.1, chunked. A different
   service entirely, not another path on the same one.
2. **`access-control-allow-origin: *`.** `route-capture.md` T005 records the
   *absence* of this header on `sansad.in` as the fact the whole client-side
   design rests on. `rsdoc.nic.in` sends `*`. **This changes nothing about this
   project's design** — the page still reads only this project's own published
   files — but it means a browser on any origin could read the Rajya Sabha
   question route directly, which the Lok Sabha route forbids.
3. **`x-robots-tag: noindex, nofollow`**, which the Lok Sabha service does not
   send.

---

# The three leads, each tested

## Lead 1 — `sitting-members`, `term-years`, `bio-data`. **CONFIRMED.**

```
GET sansad.in/api_rs/member/sitting-members?page=0&size=50     HTTP/1.1 500         (page is 1-based)
GET sansad.in/api_rs/member/sitting-members?page=1&size=50     HTTP/1.1 200   46,763 B
GET sansad.in/api_rs/member/sitting-members                    HTTP/1.1 200    9,130 B
GET sansad.in/api_rs/member/term-years                         HTTP/1.1 400 Bad Request
GET sansad.in/api_rs/member/term-years?mpCode=1&locale=en      HTTP/1.1 200
GET sansad.in/api_rs/member/bio-data                           HTTP/1.1 400 Bad Request
GET sansad.in/api_rs/member/bio-data?mpCode=1&locale=en        HTTP/1.1 200
# the Lok Sabha mirror of each -- these routes do NOT exist in this shape there
GET sansad.in/api_ls/member/sitting-members?page=0&size=50     HTTP/1.1 500       55 B
GET sansad.in/api_ls/member/term-years                         HTTP/1.1 500       55 B
GET sansad.in/api_ls/member/bio-data                           HTTP/1.1 500       55 B
```

`term-years` and `bio-data` are **per-member**: 400 without `mpCode`, 200 with
it. The two Houses do **not** share this route family — the Lok Sabha serves one
unpaginated roster at `/api_ls/member` and these three paths answer 500 there.

Cohort counts, read from `_metadata` only:

| | `totalElements` |
|---|---|
| `mpFlag=1` (sitting) | **243** |
| `mpFlag=0` (former) | **2,304** |
| `mpFlag=2`, `mpFlag=3` | 0 |
| no `mpFlag` | **2,547** = 243 + 2,304 |

and `/api_rs/member/member-list` returns a **2,547**-element array, which
agrees. **The whole Rajya Sabha roster is reachable**, including former members
— which a covered window spanning two Lok Sabha terms would need.

## Lead 2 — `rsdoc.nic.in` question metadata, answers in PDFs. **CONFIRMED.**

```
GET rsdoc.nic.in/Question/Search_Questions?whereclause=ses_no=271   HTTP/2 200   4,260,914 B   5.80 s
GET rsdoc.nic.in/Question/Search_Questions                          HTTP/2 500          56 B
GET rsdoc.nic.in/question/GetAllministary                           HTTP/2 200      14,610 B
GET rsdoc.nic.in/question/Get_sessionforQuestionSearch              HTTP/2 200       3,061 B
GET rsdoc.nic.in/                                                   HTTP/2 405
```

**No document was opened, fetched or parsed.** The field names below include
document pointers; none was followed, and `files`, `hindifiles`,
`eng_file_name`, `eng_file_dsp`, `hindi_file_name` and `hindi_file_dsp` were
read as *names in a JSON object*, never as paths to retrieve.

### `Search_Questions` — 3,325 records for one session, 24 field names

Field names and **per-field presence only**. No value is reproduced.

```
field                    records   non-empty   % non-empty
P_flag                     3,325       3,325       100.0%
adate                      3,325       3,325       100.0%
ans_date                   3,325       3,325       100.0%
ans_text                   3,325           0         0.0%
depc                       3,325       3,325       100.0%
eng_file_dsp               3,325       3,325       100.0%
eng_file_name              3,325       3,325       100.0%
files                      3,325       3,325       100.0%
hindi_file_dsp             3,325       3,325       100.0%
hindi_file_name            3,325       3,325       100.0%
hindifiles                 3,325       3,325       100.0%
min_code                   3,325       3,325       100.0%
min_name                   3,325       3,325       100.0%
mp_code                    3,325       3,325       100.0%
name                       3,325       3,325       100.0%
qn_text                    3,325       3,325       100.0%
qno                        3,325       3,325       100.0%
qslno                      3,325       3,325       100.0%
qtitle                     3,325       3,325       100.0%
qtype                      3,325       3,325       100.0%
ses_no                     3,325       3,325       100.0%
shri                       3,325       3,325       100.0%
status                     3,325       3,325       100.0%
supp                       3,325           0         0.0%
```

Two of those rows are the lead's claim, measured:

- **`ans_text` is empty on all 3,325 records** and the six document-pointer
  fields are populated on all 3,325. Consistent with "answer text only in
  PDFs". Whether those pointers resolve to PDFs was **not tested** — testing it
  means fetching a document, which Principle III forbids.
- **`qn_text` is populated on all 3,325 records.** The *question* text is served
  as structured JSON here, where the Lok Sabha route serves `questionText` and
  `answerText` both null. That is a **difference in kind** from the control and
  it is recorded, not acted on: question text is outside this feature's
  authorised scope (`spec.md` → Assumptions, "Nothing in this spec covers
  debate text, answer text…"), and the 4.26 MB-per-session size is mostly this
  field.
- `hindi_file_name` / `hindifiles` populated on every record raises a
  **Principle IV** question for any follow-on. Not resolved here.

### The reference routes

```
rsdoc.nic.in/question/Get_sessionforQuestionSearch   JSON array,  90 elements   fields: ssn_no, sessiondate
rsdoc.nic.in/question/GetAllministary                JSON array, 104 elements   fields: MIN_CODE, MIN_NAME,
                                                                               HMIN_NAME, MIN_Status, min_short_name
sansad.in/api_rs/member/member-list                  JSON array, 2,547 elements fields: mpCode, mpFlag, mpName,
                                                                               mpNameHindi, name, nameHindi,
                                                                               partyCode, partyName, divisionNo
```

`min_code` appears on both the question records and the ministry list — the same
shape of per-term code `ministry-identity.md` found unusable as an identity on
the Lok Sabha side. **Whether it is stable here is unverified**, and a follow-on
must not assume it is.

## Lead 3 — no API documentation, bulk download or licence. **CONFIRMED.**

```
404  rsdoc.nic.in/swagger/index.html
404  rsdoc.nic.in/swagger/v1/swagger.json
404  rsdoc.nic.in/robots.txt
404  sansad.in/robots.txt
404  sansad.in/api_rs                     (no service index)
404  sansad.in/api_rs/member              (no HAL index, unlike /api_ls/question)
200  sansad.in/api_ls/member              (CONTROL)
404  sansad.in/sitemap.xml
200  sansad.in/rs/download                ("Downloads" -- 1,594 characters of navigation links, no dataset)
```

No OpenAPI document, no `robots.txt`, no sitemap, no service index, no bulk
download, and **no licence or terms-of-use statement found on either host**.
That is the same position the Lok Sabha side is in, and it leaves this
project's recorded gap — *source terms: not determined* — exactly as it stands.

---

# T099 — which of the three candidate causes the evidence supports

`research.md` records three causes consistent with the 403, with the cause
**UNVERIFIED**: a bot or WAF rule, a path-specific block, or genuine
authorisation.

| Candidate | Verdict on this evidence |
|---|---|
| **A bot or WAF rule** | **NOT SUPPORTED.** The same client got 200 from `/api_ls/member` and `/api_ls/question/qetFilteredQuestionsAns` in the same session, seconds apart, with headers stripped. The 403 carries the application's own 22-header set **plus** a `JSESSIONID` — an edge filter would not mint an application session, and would not discriminate between `/member` and `/members` on one host while leaving everything else at 200. |
| **A path-specific response** | **SUPPORTED.** It is determined by the path alone: identical on `api_ls` and `api_rs`, stable across clients, and distinct from the 404 an unmatched path gets — which is answered by a different layer with four headers and a reason phrase. |
| **Genuine authorisation** | **SUPPORTED AS A MECHANISM, REFUTED AS AN EXPLANATION.** A filter that mints a session and denies an anonymous caller *is* access control, so this candidate is not eliminated at the level of mechanism. What the evidence **does** eliminate is the inference drawn from it: the 403 cannot mean "Rajya Sabha data is access-controlled", because the Lok Sabha service — whose data this project publishes — answers the same path the same way. |

## The finding, stated so it cannot be misread

**A wrong-path 403, not a real block.** `/api_{ls,rs}/members` is not the data
route on either House; the real member routes are `/api_ls/member` (Lok Sabha)
and `/api_rs/member/sitting-members` (Rajya Sabha), and both return 200 to a
plain unauthenticated `GET` with every header stripped.

**What remains UNVERIFIED, and is left so.** *Which* rule denies
`/api_{ls,rs}/members` — a security-filter path pattern, a route that exists but
is not exposed, something else — is not determined by anything above, and no
further probing was done to force an answer. It does not need one: the path is
not a route this or any follow-on feature would call. Declaring a mechanism here
to tidy the record would be exactly the move the task forbids.

**One cost of the earlier reading, recorded.** `plan.md` Risk 1, `spec.md` Open
Question 1 and the dataset contract's Rajya Sabha note all rest on a 403 that
says nothing about the Rajya Sabha. The reading was never wrong about what was
observed — `research.md` marked the cause UNVERIFIED and declined to guess — but
the control group that settles it was one request away, on the House already
being fetched. T005's `HEAD` finding had already raised the prior and named the
right next step ("vary the method and the request shape, not the path"); the
plural-path diff is that step, and it took one `curl`.

## Runner reachability — NOT YET CHECKED

T099: *"If a route is found, confirm it is reachable from the T007 CI runner
too, since T010 may have shown a laptop and a runner are not equivalent."*

A route **is** found, so this check is required and is **not done**. Everything
above was measured from a laptop. `.github/workflows/spike-rs-reachability.yml`
is written and committed for it — one `GET` per found route plus the Lok Sabha
control, printing status code, elapsed time and response headers, asserting
HTTP 200, and **writing no response body anywhere**. It is
`workflow_dispatch`-only, holds `contents: read`, and mirrors the T009 workflow
T010 deleted once recorded.

**The workflow's own script was smoke-tested on this laptop first**, by
extracting the `run` block from the YAML and executing it, so that a failure on
the runner is evidence about the runner rather than about the script:

```
$ bash <the workflow's own step-2 script>
CONTROL -- Lok Sabha member roster            HTTP/1.1 200   RESULT: 200
RS roster, one record -- the T098 route       HTTP/1.1 200   RESULT: 200
RS asker-name list                            HTTP/1.1 200   RESULT: 200
RS session list (rsdoc.nic.in, HTTP/2, IIS)   HTTP/2 200     RESULT: 200
RS ministry list (rsdoc.nic.in)               HTTP/2 200     RESULT: 200
RS question metadata, ONE session             HTTP/2 200     RESULT: 200
spike-rs-reachability: every route answered 200 from this runner.
exit=0
```

The YAML parses, `bash -n` passes on both `run` blocks, it carries
`workflow_dispatch` and **no `schedule`**, and `make yamllint --strict` reports
0 findings.

**It has not been pushed and has not been run on GitHub.** Until it has:

> **Rajya Sabha route reachability from a free CI runner: UNVERIFIED.**

`ci-reachability.md` T010 is the reason this is not a formality — a datacentre
IP is one of the things that can differ, and `rsdoc.nic.in` is a `nic.in` host
on a different stack from the one T010 checked.

---

# T100 — outcome, and stop

**A reachable Rajya Sabha route exists.** T100's instruction for that case is to
**open a follow-on feature for Rajya Sabha ingestion rather than extending this
one**, and that is recorded here as the outcome. **No follow-on feature was
created and no scope was widened in this phase** — nothing below was built.

## What a follow-on would have to settle, none of it done here

1. **Runner reachability**, above. It gates everything else.
2. **Session enumeration for the covered window.** `ses_no=271` is the session
   the page defaulted to; `Get_sessionforQuestionSearch` returns 90 elements.
   Which `ssn_no` values fall inside the 17th/18th Lok Sabha calendar window is
   not established — the Rajya Sabha is a continuing House and does not share
   the Lok Sabha's term numbering, so the window itself needs defining.
3. **Volume and Principle I.** One session is 4,260,914 B of JSON, most of it
   `qn_text`. Published size, bandwidth and the 1 GiB Pages ceiling would all
   have to be re-measured — `size-budget.md`'s figures are Lok Sabha only.
4. **Principle V, before any fetch — and three of the spellings get through
   today.** `/api_rs/member/sitting-members` serves `dob`, `emailID`,
   `localAdd`, `localTele`, `permanentAdd`, `permanentTele`, `age` and
   `gender`. Each was checked against the **66** spellings
   `tools/guard_no_raw_payloads.py` carries in `PROHIBITED_ATTRIBUTES`, by
   importing that set and testing membership. Three are carried — the date of
   birth, email and permanent-address spellings — and **three are not:
   `localAdd`, `localTele` and `permanentTele`.** (The result is stated in prose
   rather than pasted: a table of those spellings in key position fails
   `make guard` on this very file, which happened on the first attempt.) They are
   the Rajya Sabha's names for what the Lok Sabha roster calls a present address
   and a Delhi phone, and the guard was written against the Lok Sabha's
   spellings. So a Rajya Sabha ingest built today would carry three prohibited
   attribute families **past the only automated thing standing between that
   payload and publication**. Adding them to `PROHIBITED_ATTRIBUTES` and to
   `sansad.ingest.field_allowlist` is the **first** change a follow-on makes,
   before any fetch — not after, and not alongside. `age` and `gender` are not
   on the prohibited list but are out of scope for composition under `spec.md`
   US4's note, so they need a recorded decision rather than a guard entry.
5. **Principle III and IV.** `qn_text` is structured-source question text, which
   Principle III permits and this feature's authorised scope excludes;
   `hindi_file_name` and `nameHindi` are Principle IV's problem. Both are owner
   decisions, not implementation choices.
6. **Identity.** `mp_code` on questions and `mpCode` on members look like a
   join, and `min_code` looks like a ministry key. Whether either is stable is
   **unverified**, and `ministry-identity.md` is the record of what assuming
   that cost on the Lok Sabha side.
7. **Source terms.** Still not determined, for either House.

## The Lok Sabha-only declarations are unchanged and still accurate

Confirmed by execution, not by assertion:

```
$ make coverage
=== rajya-sabha ===
  houses_covered: rajya-sabha
  total_questions: 0
  unobtainable_reason: No Rajya Sabha route has been identified. GET /api_rs/members returns
  403 where every sibling path returns 404, cause UNVERIFIED. This release covers the Lok
  Sabha ONLY (FR-001, FR-013).
```

**The Coverage Statement still says Lok Sabha only, which is what FR-001
requires of this release, and it remains true.** Its `unobtainable_reason`
wording, however, is now **stale in its reasoning though not in its
conclusion**: a route *has* now been identified, and the 403 it cites is a
wrong-path response rather than evidence about the Rajya Sabha. Changing that
string edits `src/sansad/publish/coverage.py` and republishes the dataset, which
is pipeline work — **out of scope for a phase that investigates and stops.**
Recorded as the first item a follow-on touches.

`contracts/published-dataset.md` → *No Rajya Sabha coverage at first release*
carries the same 403 reasoning and is accurate in the same way and stale in the
same way: the release is still Lok Sabha only, still declares itself as such,
and still satisfies FR-001. The shortfall remains against the **owner's wider
scope decision**, which is now **actionable** where before it was blocked.
