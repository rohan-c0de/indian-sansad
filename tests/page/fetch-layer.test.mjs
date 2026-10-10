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
  loadSearchIndex,
  publishedPath,
  requestUrl,
  requestableUrls,
  resetSearchIndex,
  searchIndexRequested,
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
  // The five this part can reach, and no more.
  assert.deepEqual(new Set(Object.keys(PUBLISHED_FILES)), new Set([
    "manifest", "coverage", "countingBasis", "sessions", "searchIndex",
  ]));
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
