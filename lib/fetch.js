/* The fetch layer. T076.
 *
 * EVERY request this page makes goes through `requestUrl` below. That is not
 * tidiness -- it is the only place the same-origin rule can be enforced, and
 * the rule is load-bearing rather than cautious:
 *
 *   `spike/route-capture.md` T005 verified first-hand that the upstream sends
 *   NO `Access-Control-Allow-Origin` header. A browser is therefore refused
 *   cross-origin reads of it. The page's entire viability rests on reading
 *   this project's OWN published files from its own host, and a request that
 *   wandered off-origin would not degrade -- it would fail, silently, in a
 *   visitor's browser where nobody is watching.
 *
 * So `requestUrl` REFUSES rather than attempts: it throws `CrossOriginRefused`
 * before calling fetch at all. `tests/page/fetch-layer.test.mjs` proves both
 * halves -- that it throws, and that the injected fetch was never reached.
 *
 * Paths are RELATIVE (`./data/published/...`, owner decision 2026-10-10).
 * Root-relative paths are refused too: GitHub Pages serves a project site
 * under `/<repo>/`, so `/data/published/x` resolves to the user site root and
 * 404s. A relative path works both there and under `make serve-local`.
 *
 * Nothing here is imported from anywhere but this repository: no CDN, no web
 * font, no analytics, no module specifier that is not a relative path.
 */

import { digestFileName } from "./format.js";

/** Published dataset root, relative to the page. Owner decision 2026-10-10. */
export const PUBLISHED_BASE = "./data/published/";

/** Raised instead of making a request that would leave this origin. */
export class CrossOriginRefused extends Error {
  constructor(message) {
    super(message);
    this.name = "CrossOriginRefused";
  }
}

/** Raised when a published file is missing or unreadable. */
export class PublishedFileUnavailable extends Error {
  constructor(message, { status } = {}) {
    super(message);
    this.name = "PublishedFileUnavailable";
    this.status = status ?? null;
  }
}

function pageHref(options) {
  if (options.pageUrl) return options.pageUrl;
  if (typeof location !== "undefined" && location.href) return location.href;
  throw new TypeError("no page URL: pass `pageUrl` when there is no `location`");
}

function pageOrigin(options) {
  if (options.origin) return options.origin;
  return new URL(pageHref(options)).origin;
}

function fetchFn(options) {
  if (options.fetchImpl) return options.fetchImpl;
  if (typeof fetch === "function") return fetch;
  throw new TypeError("no fetch available: pass `fetchImpl`");
}

/**
 * Resolve `target` against the page and refuse it if it leaves this origin.
 *
 * Exported separately from the request so a test can assert the refusal
 * without a network stack at all.
 */
export function assertSameOrigin(target, options = {}) {
  const origin = pageOrigin(options);
  let url;
  try {
    url = new URL(target, pageHref(options));
  } catch (cause) {
    throw new CrossOriginRefused(`refused: not a resolvable URL: ${String(target)}`, {
      cause,
    });
  }
  if (url.origin !== origin) {
    // The message names the two origins and nothing else. A thrown message can
    // end up in a console a visitor pastes somewhere.
    throw new CrossOriginRefused(
      `refused: ${url.origin} is not this page's origin (${origin}). ` +
        "This page reads only its own published files.",
    );
  }
  if (url.protocol !== "http:" && url.protocol !== "https:" && url.protocol !== "file:") {
    throw new CrossOriginRefused(`refused: unsupported scheme ${url.protocol}`);
  }
  return url;
}

/**
 * THE one function every request goes through.
 *
 * Returns the `Response`. Callers above parse it; nothing else calls fetch.
 */
export async function requestUrl(target, options = {}) {
  const url = assertSameOrigin(target, options);
  const impl = fetchFn(options);
  const response = await impl(url.href, {
    // No credentials, no cookies: the dataset is public static files and the
    // page has no session of any kind.
    credentials: "omit",
    // `same-origin` makes the browser itself refuse a cross-origin redirect
    // rather than following one past the check above.
    mode: "same-origin",
    redirect: "error",
    headers: { Accept: "text/plain, application/json" },
  });
  if (!response || !response.ok) {
    throw new PublishedFileUnavailable(
      `could not read ${url.pathname}: HTTP ${response ? response.status : "no response"}`,
      { status: response ? response.status : null },
    );
  }
  return response;
}

/** Build a published-file URL, refusing anything that escapes the base. */
export function publishedPath(relativePath) {
  if (typeof relativePath !== "string" || relativePath.length === 0) {
    throw new TypeError("publishedPath needs a non-empty string");
  }
  if (relativePath.startsWith("/")) {
    throw new CrossOriginRefused(
      "refused: root-relative paths break a GitHub Pages project site; " +
        "published paths are relative",
    );
  }
  if (relativePath.includes("..")) {
    throw new CrossOriginRefused("refused: a published path may not contain `..`");
  }
  if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(relativePath)) {
    throw new CrossOriginRefused(`refused: ${relativePath} is not a relative path`);
  }
  return PUBLISHED_BASE + relativePath;
}

/** Fetch one published file as text. */
export async function fetchText(relativePath, options = {}) {
  const response = await requestUrl(publishedPath(relativePath), options);
  return response.text();
}

/** Fetch one published `.json` file. */
export async function fetchJson(relativePath, options = {}) {
  return JSON.parse(await fetchText(relativePath, options));
}

/** Fetch one published `.jsonl` file as an array of records. */
export async function fetchNdjson(relativePath, options = {}) {
  const text = await fetchText(relativePath, options);
  const rows = [];
  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (trimmed.length > 0) rows.push(JSON.parse(trimmed));
  }
  return rows;
}

/* ------------------------------------------------------------------------ */
/* The named published files. Spelled once, here.                           */
/* ------------------------------------------------------------------------ */

/* Exactly what this page can request -- nothing dead, nothing speculative. An
 * unused entry here would overstate the page's request surface, and that
 * surface is the thing T082 asserts against a real network log. */
export const PUBLISHED_FILES = Object.freeze({
  manifest: "manifest.json",
  coverage: "coverage.jsonl",
  countingBasis: "aggregates/counting-basis.jsonl",
  sessions: "reference/sessions.jsonl",
  // T078/T080. Precomputed, because research.md records that fetching ~10^5
  // question records into a page is not viable: 284,685 B of aggregate
  // replaces the 842,496 B one-by-ministry file T019 budgeted for.
  ministryProfile: "aggregates/ministry-profile.jsonl",
  ministries: "reference/ministries.jsonl",
  // T079, both fetched on the FIRST SEARCH only -- see below.
  searchIndex: "search/subject-index.json",
  askerNames: "search/asker-names.jsonl",
  // T088, both fetched on FIRST USE OF THE STATE VIEW only -- see below.
  // 252,226 B and 181,347 B; neither is touched by a visitor who never opens
  // the view, which `boot()` asserts.
  constituencies: "reference/constituencies.jsonl",
  stateSubjects: "aggregates/state-subjects.jsonl",
});

/* `reference/members.jsonl` is NOT in the object above, and its absence is the
 * decision rather than an omission. It is 3,447,794 B -- 1.4x the search index
 * -- and T086 put each member's name, party and sitting status onto the
 * constituency set's representations so this page would never need it. An
 * entry here would overstate the page's request surface, which is the thing
 * T082 checks against a real network log. */

/* The 21 per-session search digests are NOT in the object above, because they
 * are not a fixed list of files: which ones a search fetches depends on which
 * sessions contain a match, and most searches fetch one. They are a PATTERN,
 * declared here and printed as one by `tools/list_page_urls.py`. */
export const DIGEST_BASE = "search/digest/";

/** The published path of one session's digest. `lok-sabha/17/4` ->
 * `./data/published/search/digest/lok-sabha-17-4.jsonl`. */
export function digestRelativePath(sessionId) {
  return DIGEST_BASE + digestFileName(sessionId);
}

/* The 1,592 per-member question files are a PATTERN too, for the same reason:
 * which one the state view fetches depends on which member the visitor opens,
 * and it opens one at a time. */
export const MEMBER_BASE = "by-member/";

/** A `member_id` is `ls-<digits>` (`src/sansad/resolve/identity.py`). Anything
 * else is refused HERE rather than at `publishedPath`, so the message names the
 * member id instead of the path it would have built -- and so a value taken
 * from a published record can never compose a path at all. */
const MEMBER_ID = /^[a-z]{2}-\d+$/;

export function memberRelativePath(memberId) {
  const id = String(memberId ?? "");
  if (!MEMBER_ID.test(id)) {
    throw new CrossOriginRefused(`refused: ${id || "(empty)"} is not a member id`);
  }
  return `${MEMBER_BASE}${id}.jsonl`;
}

/** Every URL this page can request, as it would be resolved. For the record,
 * and for `tools/list_page_urls.py` to print without running a browser. The
 * digest pattern is appended as a pattern, not as 21 entries: listing them
 * all would read as 21 requests a page load makes, and a search makes one. */
export function requestableUrls() {
  return [
    ...Object.values(PUBLISHED_FILES).map(publishedPath),
    publishedPath(DIGEST_BASE) + "<house>-<term>-<session>.jsonl",
    publishedPath(MEMBER_BASE) + "<member-id>.jsonl",
  ];
}

export const fetchManifest = (o) => fetchJson(PUBLISHED_FILES.manifest, o);
export const fetchCoverage = (o) => fetchNdjson(PUBLISHED_FILES.coverage, o);
export const fetchCountingBasis = (o) => fetchNdjson(PUBLISHED_FILES.countingBasis, o);
export const fetchSessions = (o) => fetchNdjson(PUBLISHED_FILES.sessions, o);
export const fetchMinistryProfile = (o) => fetchNdjson(PUBLISHED_FILES.ministryProfile, o);
export const fetchMinistries = (o) => fetchNdjson(PUBLISHED_FILES.ministries, o);

/* ------------------------------------------------------------------------ */
/* The search index, fetched LAZILY -- on the first search only.            */
/* ------------------------------------------------------------------------ */

/* T072 measured the index at 2,484,758 B (2.37 MiB) -- 1.0% of the dataset,
 * but about 73% of the bytes a first page load would cost if it were fetched
 * eagerly. A visitor who never searches must not pay for it, so it is not
 * requested until `loadSearchIndex` is called, and `app.js` calls it from the
 * search handler and from nowhere else.
 *
 * The promise is memoised rather than the value: two searches started before
 * the first resolves must share ONE request, not race two.
 */
let searchIndexPromise = null;
let askerNamesPromise = null;
/** One memoised promise per session id. A session fetched for page 1 is not
 * refetched for page 2, and two concurrent searches over the same session
 * share one request. */
const digestPromises = new Map();

export function loadSearchIndex(options = {}) {
  if (searchIndexPromise === null) {
    searchIndexPromise = fetchJson(PUBLISHED_FILES.searchIndex, options).catch((error) => {
      // A failed load must not poison every later attempt.
      searchIndexPromise = null;
      throw error;
    });
  }
  return searchIndexPromise;
}

/** `search/asker-names.jsonl`, fetched with the index on the first search.
 * 92,713 B against the index's 2,484,758 B: it rides along rather than being
 * a second round trip, because no result can be shown without it. */
export function loadAskerNames(options = {}) {
  if (askerNamesPromise === null) {
    askerNamesPromise = fetchNdjson(PUBLISHED_FILES.askerNames, options).catch((error) => {
      askerNamesPromise = null;
      throw error;
    });
  }
  return askerNamesPromise;
}

/**
 * One session's search digest.
 *
 * Called ONLY for a session the index says contains a match, and only when a
 * page of results actually needs it -- `web/lib/search.js` ->
 * `createResultSet` decides, and this just fetches. That is the whole of
 * T079's measured saving: `spike/size-budget.md` records 1,016,286 B for one
 * digest against 1,863,771 B for the median partition it replaces.
 */
export function loadSearchDigest(sessionId, options = {}) {
  const key = String(sessionId);
  if (!digestPromises.has(key)) {
    const promise = fetchNdjson(digestRelativePath(key), options).catch((error) => {
      digestPromises.delete(key);
      throw error;
    });
    digestPromises.set(key, promise);
  }
  return digestPromises.get(key);
}

/** Whether the index has been requested yet. For tests and for the page's own
 * "not loaded" state; never used to decide whether to fetch. */
export function searchIndexRequested() {
  return searchIndexPromise !== null;
}

/** Whether ANY search file has been requested -- the index, the name lookup
 * or a digest. `boot()` asserts this is false, which is the assertion that
 * keeps a visitor who never searches from paying for search. The narrower
 * `searchIndexRequested` would pass while a digest was already in flight. */
export function searchAssetsRequested() {
  return searchIndexPromise !== null || askerNamesPromise !== null || digestPromises.size > 0;
}

/** Which session digests have been requested. For tests, and for the page to
 * report what a search actually cost. */
export function requestedDigests() {
  return [...digestPromises.keys()];
}

/** Test seam only: forget every search request. */
export function resetSearchIndex() {
  searchIndexPromise = null;
  askerNamesPromise = null;
  digestPromises.clear();
}

/* ------------------------------------------------------------------------ */
/* T088 -- the state and constituency view, fetched LAZILY.                 */
/* ------------------------------------------------------------------------ */

/* Owner decision 2026-10-10: "Nothing for this view loads on page load. The
 * reference set is fetched when the visitor first opens the view, like search."
 *
 * Two files on first use -- the seat set (252,226 B) and the state subject
 * summary (181,347 B) -- then ONE member file per member the visitor opens.
 * The member files are the reason the state summary is a published aggregate
 * rather than something this page derives: a state's own members' files come
 * to 10,489,198 B for Maharashtra, and the summary is 181,347 B for all 36
 * states (`spike/size-budget.md` -> T086).
 *
 * Promises are memoised, not values: two interactions before the first
 * resolves must share ONE request rather than race two.
 */
let seatsPromise = null;
let stateSubjectsPromise = null;
/** One memoised promise per member id. Re-opening a member costs nothing. */
const memberPromises = new Map();

export function loadSeats(options = {}) {
  if (seatsPromise === null) {
    seatsPromise = fetchNdjson(PUBLISHED_FILES.constituencies, options).catch((error) => {
      seatsPromise = null; // a failed load must not poison every later attempt
      throw error;
    });
  }
  return seatsPromise;
}

export function loadStateSubjects(options = {}) {
  if (stateSubjectsPromise === null) {
    stateSubjectsPromise = fetchNdjson(PUBLISHED_FILES.stateSubjects, options).catch((error) => {
      stateSubjectsPromise = null;
      throw error;
    });
  }
  return stateSubjectsPromise;
}

/** One member's published questions. Called when the visitor OPENS that
 * member, and from nowhere else -- a view that fetched every member of a state
 * up front would cost 10,489,198 B in Maharashtra. */
export function loadMemberQuestions(memberId, options = {}) {
  const key = String(memberId);
  if (!memberPromises.has(key)) {
    const promise = fetchNdjson(memberRelativePath(key), options).catch((error) => {
      memberPromises.delete(key);
      throw error;
    });
    memberPromises.set(key, promise);
  }
  return memberPromises.get(key);
}

/** Whether ANY file this view needs has been requested. `boot()` asserts this
 * is false, the same assertion that keeps search lazy. */
export function seatAssetsRequested() {
  return seatsPromise !== null || stateSubjectsPromise !== null || memberPromises.size > 0;
}

/** Which member files have been requested. For tests, and for the page to
 * report what opening a member actually cost. */
export function requestedMembers() {
  return [...memberPromises.keys()];
}

/** Test seam only: forget every state-view request. */
export function resetSeatData() {
  seatsPromise = null;
  stateSubjectsPromise = null;
  memberPromises.clear();
}
