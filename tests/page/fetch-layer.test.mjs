/* T076's fetch layer, under Node's own test runner.
 *
 * Why Node and not a browser: the rule being tested is pure logic over a URL
 * and an origin, and it is enforced BEFORE fetch is called. Proving it needs
 * an injected fetch that can record whether it was reached -- which a real
 * browser makes harder, not easier. T082 drives the actual page in a browser
 * and asserts the real network log; this file asserts the refusal itself.
 *
 * Node 22 is already installed (v22.22.3, checked 2026-10-10). Nothing was
 * installed for this: no test framework, no browser driver, no package.json.
 * `tests/unit/test_page_fetch_layer.py` runs this file from pytest so there is
 * one suite to run.
 */

import assert from "node:assert/strict";
import { test } from "node:test";

import {
  CrossOriginRefused,
  PUBLISHED_BASE,
  PUBLISHED_FILES,
  PublishedFileUnavailable,
  assertSameOrigin,
  fetchNdjson,
  digestRelativePath,
  loadAskerNames,
  loadMemberQuestions,
  loadSearchDigest,
  loadSearchIndex,
  loadSeats,
  loadStateSubjects,
  memberRelativePath,
  publishedPath,
  requestUrl,
  requestableUrls,
  requestedDigests,
  requestedMembers,
  resetSearchIndex,
  resetSeatData,
  searchAssetsRequested,
  searchIndexRequested,
  seatAssetsRequested,
} from "../../web/lib/fetch.js";

const PAGE = "https://rohan-c0de.github.io/indian-sansad/index.html";
const ORIGIN = "https://rohan-c0de.github.io";

/** A fetch that records every call and never touches a network. */
function recordingFetch(body = "{}", { status = 200 } = {}) {
  const calls = [];
  const impl = async (url, init) => {
    calls.push({ url, init });
    return {
      ok: status >= 200 && status < 300,
      status,
      async text() {
        return body;
      },
    };
  };
  impl.calls = calls;
  return impl;
}

const opts = (impl) => ({ pageUrl: PAGE, origin: ORIGIN, fetchImpl: impl });

/* ---------------------------------------------------------------------- */
/* The refusal. This is the test the task asks for.                       */
/* ---------------------------------------------------------------------- */

test("refuses the upstream, and does not call fetch at all", async () => {
  const impl = recordingFetch();
  await assert.rejects(
    () => requestUrl("https://sansad.in/api_ls/question/qetFilteredQuestionsAns", opts(impl)),
    CrossOriginRefused,
  );
  // The important half: it refused BEFORE reaching the network. A check that
  // only asserted the throw would pass even if the request had been made and
  // the result discarded.
  assert.equal(impl.calls.length, 0, "fetch was called for a cross-origin URL");
});

test("refuses every off-origin shape, never calling fetch", async () => {
  const offOrigin = [
    "https://sansad.in/api_ls/member",
    "http://sansad.in/api_ls/member",
    // Same host, different scheme -- a different origin.
    "http://rohan-c0de.github.io/indian-sansad/data/published/manifest.json",
    // Same host, explicit non-default port -- a different origin.
    "https://rohan-c0de.github.io:8443/indian-sansad/manifest.json",
    // A different host that merely starts with ours.
    "https://rohan-c0de.github.io.example.com/manifest.json",
    // Protocol-relative: inherits the scheme, not the host.
    "//sansad.in/api_ls/member",
    // Schemes that are not http(s).
    "data:text/plain,hello",
    "javascript:void 0",
  ];
  for (const target of offOrigin) {
    const impl = recordingFetch();
    await assert.rejects(
      () => requestUrl(target, opts(impl)),
      CrossOriginRefused,
      `expected refusal for ${target}`,
    );
    assert.equal(impl.calls.length, 0, `fetch was called for ${target}`);
  }
});

test("allows this origin, and fetches exactly once", async () => {
  const impl = recordingFetch('{"license":"CC-BY-4.0"}');
  const response = await requestUrl("./data/published/manifest.json", opts(impl));
  assert.equal(impl.calls.length, 1);
  assert.equal(
    impl.calls[0].url,
    "https://rohan-c0de.github.io/indian-sansad/data/published/manifest.json",
  );
  assert.equal(impl.calls[0].init.credentials, "omit");
  assert.equal(impl.calls[0].init.mode, "same-origin");
  assert.equal(impl.calls[0].init.redirect, "error");
  assert.equal(await response.text(), '{"license":"CC-BY-4.0"}');
});

test("assertSameOrigin can be used on its own and returns the URL", () => {
  const url = assertSameOrigin("./data/published/coverage.jsonl", {
    pageUrl: PAGE,
    origin: ORIGIN,
  });
  assert.equal(url.origin, ORIGIN);
  assert.equal(url.pathname, "/indian-sansad/data/published/coverage.jsonl");
  assert.throws(
    () => assertSameOrigin("https://example.com/x", { pageUrl: PAGE, origin: ORIGIN }),
    CrossOriginRefused,
  );
});

/* ---------------------------------------------------------------------- */
/* Published paths are RELATIVE (owner decision 2026-10-10)               */
/* ---------------------------------------------------------------------- */

test("published paths are relative, and root-relative is refused", () => {
  assert.equal(publishedPath("manifest.json"), "./data/published/manifest.json");
  assert.equal(PUBLISHED_BASE, "./data/published/");
  // Root-relative would resolve to the USER site root on a GitHub Pages
  // project site, not to this project, and 404 in production while working
  // locally -- the worst failure shape available.
  assert.throws(() => publishedPath("/data/published/manifest.json"), CrossOriginRefused);
  assert.throws(() => publishedPath("../../etc/hosts"), CrossOriginRefused);
  assert.throws(() => publishedPath("https://sansad.in/x"), CrossOriginRefused);
  assert.throws(() => publishedPath(""), TypeError);
});

test("every requestable URL is relative and under the published base", () => {
  const urls = requestableUrls();
  assert.ok(urls.length > 0);
  for (const url of urls) {
    assert.ok(url.startsWith("./data/published/"), `${url} is not published-relative`);
    assert.ok(!/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(url), `${url} looks absolute`);
    assert.ok(!url.startsWith("//"), `${url} is protocol-relative`);
  }
  // Exactly what the page can reach, and no more. An entry here that nothing
  // calls would overstate the request surface, which is the thing T082 will
  // assert against a real network log.
  assert.deepEqual(new Set(Object.keys(PUBLISHED_FILES)), new Set([
    "manifest", "coverage", "countingBasis", "sessions",
    "ministryProfile", "ministries",       // T078 / T080
    "searchIndex", "askerNames",           // T079, both lazy
    "constituencies", "stateSubjects",     // T088, both lazy
  ]));
  // `reference/members.jsonl` is NOT here, and that is the decision: it is
  // 3,447,794 B, and T086 put each member's name, party and sitting status
  // onto the constituency set's representations so this page never needs it.
  assert.ok(
    !Object.values(PUBLISHED_FILES).includes("reference/members.jsonl"),
    "the 3.4 MB member set is not a file this page requests",
  );
  // The 21 per-session digests are a PATTERN, not 21 entries: which ones a
  // search fetches depends on which sessions contain a match, and most
  // searches fetch one. The pattern still has to be published-relative, which
  // the loop above asserts over it along with everything else.
  const pattern = urls.filter((url) => url.includes("<session>"));
  assert.equal(pattern.length, 1, "the digest pattern is listed exactly once");
  assert.equal(pattern[0], "./data/published/search/digest/<house>-<term>-<session>.jsonl");
  // And the 1,592 by-member files, for the same reason: T088 fetches ONE, for
  // the member the visitor opened.
  const members = urls.filter((url) => url.includes("<member-id>"));
  assert.equal(members.length, 1, "the by-member pattern is listed exactly once");
  assert.equal(members[0], "./data/published/by-member/<member-id>.jsonl");
});

test("a member id that is not one cannot compose a path", () => {
  // The id reaches `memberRelativePath` from a PUBLISHED RECORD, so it is
  // upstream-derived text and is checked before it can build a URL -- not left
  // to `publishedPath`, whose message would name the path instead of the id.
  for (const bad of ["", "../../etc/hosts", "ls-129/../..", "LS-129", "ls-", "x".repeat(40)]) {
    assert.throws(() => memberRelativePath(bad), CrossOriginRefused, `accepted ${bad}`);
  }
  assert.equal(memberRelativePath("ls-129"), "by-member/ls-129.jsonl");
  assert.equal(publishedPath(memberRelativePath("ls-5199")),
    "./data/published/by-member/ls-5199.jsonl");
});

/* ---------------------------------------------------------------------- */
/* Failure is explicit, not silent                                        */
/* ---------------------------------------------------------------------- */

test("a missing published file raises rather than returning empty", async () => {
  const impl = recordingFetch("", { status: 404 });
  await assert.rejects(
    () => requestUrl("./data/published/manifest.json", opts(impl)),
    PublishedFileUnavailable,
  );
});

test("ndjson parsing drops blank lines and keeps every record", async () => {
  const impl = recordingFetch('{"a":1}\n\n{"a":2}\n');
  const rows = await fetchNdjson("coverage.jsonl", opts(impl));
  assert.deepEqual(rows, [{ a: 1 }, { a: 2 }]);
});

/* ---------------------------------------------------------------------- */
/* The index is lazy                                                      */
/* ---------------------------------------------------------------------- */

test("the search index is not requested until asked for, then once", async () => {
  resetSearchIndex();
  assert.equal(searchIndexRequested(), false, "the index was requested on import");

  const impl = recordingFetch('{"terms":[],"postings":[]}');
  const first = loadSearchIndex(opts(impl));
  const second = loadSearchIndex(opts(impl));
  assert.equal(searchIndexRequested(), true);
  await Promise.all([first, second]);
  // Two concurrent searches must share ONE request, not race two: the index is
  // 2.37 MiB and fetching it twice would double the largest cost on the page.
  assert.equal(impl.calls.length, 1, "the index was fetched more than once");
  assert.equal(
    impl.calls[0].url,
    "https://rohan-c0de.github.io/indian-sansad/data/published/search/subject-index.json",
  );
  resetSearchIndex();
});

test("a failed index load does not poison later attempts", async () => {
  resetSearchIndex();
  const failing = recordingFetch("", { status: 500 });
  await assert.rejects(() => loadSearchIndex(opts(failing)), PublishedFileUnavailable);
  assert.equal(searchIndexRequested(), false, "the failure was memoised");

  const working = recordingFetch('{"terms":["x"],"postings":[[0]]}');
  const index = await loadSearchIndex(opts(working));
  assert.deepEqual(index.terms, ["x"]);
  resetSearchIndex();
});

test("the asker-name lookup is lazy too, and fetched once", async () => {
  resetSearchIndex();
  const impl = recordingFetch('{"member_id":"ls-1","canonical_name":"A"}\n');
  const rows = await loadAskerNames(opts(impl));
  await loadAskerNames(opts(impl));
  assert.equal(impl.calls.length, 1);
  assert.deepEqual(rows, [{ member_id: "ls-1", canonical_name: "A" }]);
  assert.equal(
    impl.calls[0].url,
    "https://rohan-c0de.github.io/indian-sansad/data/published/search/asker-names.jsonl",
  );
  resetSearchIndex();
});

test("a session digest resolves to its published path and is fetched ONCE", async () => {
  resetSearchIndex();
  assert.equal(digestRelativePath("lok-sabha/17/4"), "search/digest/lok-sabha-17-4.jsonl");

  const impl = recordingFetch('{"question_id":"lok-sabha/17/4/starred/1"}\n');
  await loadSearchDigest("lok-sabha/17/4", opts(impl));
  // Page 2 of the same search must not refetch a session page 1 already read.
  await loadSearchDigest("lok-sabha/17/4", opts(impl));
  assert.equal(impl.calls.length, 1, "the digest was fetched more than once");
  assert.equal(
    impl.calls[0].url,
    "https://rohan-c0de.github.io/indian-sansad/data/published/search/digest/lok-sabha-17-4.jsonl",
  );
  // A DIFFERENT session is a different file, and is fetched.
  await loadSearchDigest("lok-sabha/18/8", opts(impl));
  assert.equal(impl.calls.length, 2);
  assert.deepEqual(requestedDigests(), ["lok-sabha/17/4", "lok-sabha/18/8"]);
  resetSearchIndex();
});

test("a failed digest load does not poison that session for a retry", async () => {
  resetSearchIndex();
  const failing = recordingFetch("", { status: 503 });
  await assert.rejects(
    () => loadSearchDigest("lok-sabha/18/8", opts(failing)),
    PublishedFileUnavailable,
  );
  assert.deepEqual(requestedDigests(), [], "the failure was memoised");
  const working = recordingFetch('{"question_id":"lok-sabha/18/8/starred/1"}\n');
  const rows = await loadSearchDigest("lok-sabha/18/8", opts(working));
  assert.equal(rows.length, 1);
  resetSearchIndex();
});

test("NO search file is requested until a search happens — the boot assertion", async () => {
  // `boot()` throws if this is true at load time, which is what keeps a
  // visitor who never searches from paying for 2.37 MiB plus a digest. The
  // narrower searchIndexRequested() would pass while a digest was in flight.
  resetSearchIndex();
  assert.equal(searchAssetsRequested(), false);

  const impl = recordingFetch('{"question_id":"x"}\n');
  await loadSearchDigest("lok-sabha/18/8", opts(impl));
  assert.equal(searchIndexRequested(), false, "the index itself was still not fetched");
  assert.equal(searchAssetsRequested(), true, "but a search file was");

  resetSearchIndex();
  assert.equal(searchAssetsRequested(), false);
  await loadAskerNames(opts(impl));
  assert.equal(searchAssetsRequested(), true);
  resetSearchIndex();
});


/* ---------------------------------------------------------------------- */
/* T088 — the state view's three files are lazy, and memoised             */
/* ---------------------------------------------------------------------- */

function counting(body) {
  const calls = [];
  const impl = async (url) => {
    calls.push(url);
    return { ok: true, status: 200, text: async () => body };
  };
  return { impl, calls };
}

test("nothing the state view needs is requested until it is asked for", () => {
  resetSeatData();
  assert.equal(seatAssetsRequested(), false);
  assert.deepEqual(requestedMembers(), []);
});

test("the seat set and the state summary are each requested once", async () => {
  resetSeatData();
  const seats = counting('{"constituency_id":"bihar-aurangabad","representations":[]}\n');
  await Promise.all([loadSeats(opts(seats.impl)), loadSeats(opts(seats.impl))]);
  assert.equal(seats.calls.length, 1, "two callers must share one request");
  assert.equal(seatAssetsRequested(), true);
  assert.ok(seats.calls[0].endsWith("/data/published/reference/constituencies.jsonl"));

  const subjects = counting('{"state":"Bihar","subject":"Water","questions":2}\n');
  await Promise.all([
    loadStateSubjects(opts(subjects.impl)),
    loadStateSubjects(opts(subjects.impl)),
  ]);
  assert.equal(subjects.calls.length, 1);
  assert.ok(subjects.calls[0].endsWith("/data/published/aggregates/state-subjects.jsonl"));
  resetSeatData();
});

test("one member file per member, memoised, and the id is in the path", async () => {
  resetSeatData();
  const member = counting('{"question_id":"lok-sabha/18/1/unstarred/1","subject":"Water"}\n');
  await loadMemberQuestions("ls-129", opts(member.impl));
  await loadMemberQuestions("ls-129", opts(member.impl));
  assert.equal(member.calls.length, 1, "re-opening a member must cost nothing");
  assert.ok(member.calls[0].endsWith("/data/published/by-member/ls-129.jsonl"));

  await loadMemberQuestions("ls-5199", opts(member.impl));
  assert.equal(member.calls.length, 2);
  assert.deepEqual(requestedMembers().sort(), ["ls-129", "ls-5199"]);
  resetSeatData();
  assert.deepEqual(requestedMembers(), []);
});

test("a failed load does not poison every later attempt", async () => {
  resetSeatData();
  let attempt = 0;
  const impl = async () => {
    attempt += 1;
    if (attempt === 1) return { ok: false, status: 503, text: async () => "" };
    return { ok: true, status: 200, text: async () => '{"constituency_id":"x"}\n' };
  };
  await assert.rejects(() => loadSeats(opts(impl)), PublishedFileUnavailable);
  assert.equal(seatAssetsRequested(), false, "a failed load must not look requested");
  const rows = await loadSeats(opts(impl));
  assert.equal(rows.length, 1);
  resetSeatData();
});
