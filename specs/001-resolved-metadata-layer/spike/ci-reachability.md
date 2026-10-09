# Spike item 2 — can a free CI runner reach the route?

**Task**: T010
**Date**: 2026-10-09
**Provider**: GitHub Actions (chosen in T007), standard GitHub-hosted runner
**Workflow**: `.github/workflows/spike-reachability.yml` (throwaway; deleted — see bottom)
**Run**: `37973110849`, repository `rohan-c0de/indian-sansad`, branch `001-resolved-metadata-layer`
**Conclusion**: **success**

## Verdict: VERIFIED WORKING

Both routes returned **HTTP 200** from a free GitHub-hosted runner. **FR-009's unattended
refresh is not blocked.** T010 names the failure condition — "A 403 or 429 from the runner where
the laptop got 200 is a VERIFIED BROKEN gate on FR-009's unattended refresh" — and it did not
occur on either route.

| Route | From the laptop (T005) | From the runner (T010) |
|---|---|---|
| `GET /api_ls/question/qetFilteredQuestionsAns` | 200 | **200** |
| `GET /api_ls/member` (control) | 200 | **200** |

## Runner context

```
Current runner version: '2.337.0'
Runner Image Provisioner / Hosted Compute Agent
Region: westus3
Cloud: Azure
Operating System: Ubuntu 24.04.5 LTS
Image: ubuntu-24.04 / Version: 20261004.327.1
GITHUB_TOKEN Permissions -- Contents: read, Metadata: read
runner_os=Linux  arch=X64
curl 8.5.0 (x86_64-pc-linux-gnu) libcurl/8.5.0 OpenSSL/3.0.13 ...
date_utc=2026-10-09T18:25:04Z
```

**The runner is in Azure `westus3` — a United States datacentre, not India.** No geographic
block, no datacentre-IP block, no bot challenge was encountered on either route. That matters
below.

## Runner log, verbatim

The output lines are reproduced exactly as the runner emitted them. The collapsed `##[group]`
blocks that merely echo the step's own shell source are omitted; that source is in git history
at the T009 commit. No response body appears because none was ever written — every request used
`-o /dev/null`.

### Step: question metadata route (T004)

```
GET /api_ls/question/qetFilteredQuestionsAns (query params omitted from this log line)
HTTP/1.1 200 
Date: Fri, 09 Oct 2026 18:25:06 GMT
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

CURL_HTTP_CODE=200
CURL_TIME_TOTAL=2.353357
CURL_TIME_CONNECT=0.755896
CURL_TIME_STARTTRANSFER=2.109698
CURL_SIZE_DOWNLOAD=11217
CURL_HTTP_VERSION=1.1
----
PASS: question route returned 200 from the runner.
```

### Step: member roster control (`GET /api_ls/member`)

```
GET /api_ls/member  (control group; ~5.0 MiB, measured 46.5s from the laptop)
HTTP/1.1 200 
Date: Fri, 09 Oct 2026 18:25:07 GMT
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

CURL_HTTP_CODE=200
CURL_TIME_TOTAL=4.133470
CURL_TIME_CONNECT=0.744203
CURL_TIME_STARTTRANSFER=1.271671
CURL_SIZE_DOWNLOAD=5197598
CURL_HTTP_VERSION=1.1
----
PASS: member roster returned 200 from the runner.
```

### Step: confirm no response body was written to disk

```
Files in the workspace (expect only the checked-out tree, which is not checked out here):
total 8
drwxr-xr-x 2 runner runner 4096 Oct  9 18:25 .
drwxr-xr-x 3 runner runner 4096 Oct  9 18:25 ..
No actions/checkout step runs in this workflow and every request used -o /dev/null,
so no upstream body exists on this runner to leak into an artefact.
```

The workspace is empty but for `.` and `..`. **Nothing fetched was persisted**, on the runner or
anywhere else.

## The runner is far faster than the laptop, and it changes a T008 projection

| Measure | Laptop (T005) | Runner (T010) | Ratio |
|---|---|---|---|
| Question route, `time_total` | 4.736 s | **2.353 s** | 2.0× faster |
| Question route, `time_starttransfer` | 4.733 s | **2.110 s** | 2.2× faster |
| Member roster, `time_total` | **46.504 s** | **4.133 s** | **11.3× faster** |
| Member roster, `time_starttransfer` | 3.732 s | 1.272 s | 2.9× faster |
| Member roster bytes | 5,197,598 | 5,197,598 | identical |

**The 46.5-second roster fetch was the laptop's bandwidth, not the upstream's speed.** The runner
pulled the identical 5,197,598 bytes in 4.13 s, of which 1.27 s was time-to-first-byte — so
~2.9 s of transfer for 5 MiB.

**This weakens, and partly invalidates, T008's full-ingest projection.** T008 projected ~46
minutes for 95,269 questions from the laptop's measured ≈29 ms/record. That figure was derived
on the wrong machine. Two separate costs are now visible and they do not scale together:

- **Transfer cost** scales with the 11.3× improvement.
- **Server-side processing cost does not.** The question route's `time_starttransfer` was 2.110 s
  for a 10-record page from the runner — the server spends ~2 s thinking before sending anything,
  largely independently of page size (the laptop saw 6.5 s for 250 records and 14.7 s for 500).

So the full-ingest time is dominated by **per-request server latency × number of pages**, not by
bytes. At `pageSize=500` the window needs ⌈95,269/500⌉ = **191 requests**; at the laptop-observed
~14.7 s per 500-record page that is ~47 minutes, and the runner's advantage on the
*processing* portion is nearer 2× than 11×, so **somewhere between 20 and 50 minutes** is the
honest range.

**Recorded as UNVERIFIED, because no multi-page ingest has been run on a runner.** The range
above is arithmetic over two measurements taken on different machines with different page sizes,
which is exactly the kind of composite that should not be stated as a figure. What is
*established* is the thing that matters for T008's gate: a full refresh is tens of minutes, not
hours, against a **6-hour** per-job ceiling. T020 records it that way.

## What this says about `plan.md` Risk 1 — narrowing, not resolving

`research.md` records `GET /api_rs/members` returning **403 where every sibling path returns
404**, cause **UNVERIFIED**, with three candidate causes: "a bot/WAF rule, a path-specific block,
or genuine authorisation".

Two pieces of evidence now bear on it, neither of which existed before this spike:

1. **From `route-capture.md` T005**: `HEAD` returns **403** where `GET` returns **200** on the
   *same* public, unauthenticated URL. Authorisation cannot explain that — only the method changed.
2. **From this run**: both Lok Sabha routes return **200 from an Azure `westus3` datacentre IP**.

Evidence 2 **weakens the "datacentre IP" candidate specifically.** `plan.md` Risk 1 names a
datacentre IP as a candidate cause of the Rajya Sabha 403; this run shows a datacentre IP
reaching the Lok Sabha routes unimpeded, with no challenge and no rate limit. An IP-reputation
rule that blocks `/api_rs/members` while serving `/api_ls/member` from the same address is
possible but needs the rule to be path-scoped — at which point "path-specific" is the simpler
explanation and the IP is doing no work.

**Combining 1 and 2, the surviving explanation is a request-shape or path-specific filter, not
authorisation and not IP reputation.** That is a narrowing of three candidates to one, on
evidence.

**It is not a resolution and is not recorded as one.** Nothing here was tested against
`/api_rs/members` at all. The Rajya Sabha verdict stays **UNVERIFIED**; what changes is that
T088's investigation has a direction — vary the method and request shape against the Rajya Sabha
path, from any IP — rather than more path guessing. Delivery remains Lok Sabha-only, exactly as
`contracts/published-dataset.md` already declares.

## One thing this run did NOT establish

**A single successful run is not a property of the provider.** This is one request pair, from one
runner, in one region, at one moment. It is recorded as **"observed once"**, per the Phase 2 gate
rule. It does not establish that:

- the upstream will not rate-limit a *sustained* ingest of 191 sequential requests — this run
  made **two**;
- other runner regions are treated the same — only `westus3` was observed;
- the behaviour is stable over time — the upstream carries no contract, versioning or deprecation
  notice (`research.md`), and three hosts in this family have already stopped resolving.

The rate-limit question is the live one, because the real refresh makes ~191 requests and this
test made 2. It is not answered here and should not be assumed from here.

## Workflow deleted, per T010

T010 requires the workflow to be deleted or disabled once the result is recorded. It has been
**deleted** rather than disabled, because a disabled workflow in `.github/workflows/` is a file
that can be re-enabled by accident and will be read as pipeline code by the next person. Its
source remains in git history at the T009 commit if it is ever needed again.
