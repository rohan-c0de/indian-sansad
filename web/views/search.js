/* The subject search view, its result list, and a searched subject's trend
 * across the covered sessions. T134.
 *
 * MOVED here from `app.js` unchanged -- see the note in `ministries.js`.
 *
 * Loaded by `import()` on the reader's first visit to the search view
 * (FR-128), and its three data files on the first SEARCH rather than on the
 * first visit, which is the discipline `boot()` has asserted since T079.
 */

import { legend, stackedColumns } from "../lib/chart.js";
import {
  loadAskerNames,
  loadSearchDigest,
  loadSearchIndex,
} from "../lib/fetch.js";
import { NOT_STATED, count, isMissing, isoDate, sessionLabel, stated } from "../lib/format.js";
import { figure, figureText, starMark, typeWord } from "../lib/marks.js";
import { questionBucket, statusField } from "../lib/profile.js";
import {
  ORDER_STATEMENT,
  PAGE_SIZE,
  askerIndex,
  askersFor,
  createResultSet,
  parseQuestionId,
  planSearch,
} from "../lib/search.js";
import {
  describe,
  el,
  list,
  renderUnavailable,
  replaceChildren,
  views,
} from "../lib/shared.js";
import {
  basisBlockForUnit,
  ensureMinistryNames,
  ministryNameFor,
  questionTypeOf,
} from "../lib/viewkit.js";

/* ====================================================================== */
/* T079 — subject search                                                  */
/* ====================================================================== */

/* THE ORDER, the AND rule and the no-ranking rule all live in
 * `lib/search.js`; this file renders what that returns and adds nothing of
 * its own. In particular:
 *
 *   - ORDER_STATEMENT is RENDERED, not retyped, so the sentence on screen
 *     cannot describe an order the code does not implement.
 *   - the status label comes from `statusField()`, which reads the ministry
 *     profile's own STATUS_FIELDS list -- one vocabulary, two views.
 *   - no result carries a position, a score or a grade, and neither of the
 *     two match labels the owner prohibited appears anywhere -- they are not
 *     spelled out here either, for the reason recorded in `lib/search.js`.
 *
 * Everything from a published file goes in through `textContent`. A subject
 * line is upstream text this project does not control.
 */

/** Everything the search view holds between queries. */
const search = {
  index: null,
  names: null,
  /** The in-flight or finished result set for the current query. */
  set: null,
  plan: null,
  busy: false,
};

/** A one-line politely-announced summary, and the node a screen reader reads. */
function searchStatusLine(text) {
  const node = el("p", "search-status", text);
  return node;
}

/** How many identified askers a row names before the rest are summarised.
 *
 * Three, because the row has to fit inside about 96 px at 390 px for SC-006 to
 * hold, and a name with its party is roughly a third of a line there. It is a
 * presentation limit and nothing else: the count is always exact, the number
 * not shown is always stated (FR-103), and no question is ever filtered out of
 * the list for having too many askers. 23,385 questions in this window are
 * asked jointly and one is asked by 47 members. */
const ASKERS_SHOWN = 3;

/* One result. T139-T142.
 *
 * WHAT THIS REPLACED, and the figure that forced it. Every result was a
 * five-pair `<dl>` -- Question, Date, Ministry, Link status, Asked by -- with
 * each asker on its own line underneath. Measured by `make test-page` against
 * the unmodified page: **388.8 px per result at 390 px, 9,720 px for 25**. The
 * spec estimated "about six thousand pixels"; 6,047 px turned out to be the
 * figure at 768 px and wider, and nobody had measured the narrow case the page
 * was designed for.
 *
 * SC-006 asks for 2,800 px, which is a 3.5x reduction and leaves about 96 px
 * per result. A label-and-value grid cannot reach that: five labels are five
 * lines of their own before any value is shown.
 *
 * So the labels go, and what carries their meaning instead is POSITION and
 * FORM, which is the same vocabulary FR-115 applies to the rest of the page:
 *
 *   * Drinking Water in Rural Areas          <- the subject, with the star
 *     2021-03-11 · Jal Shakti · linked        <- one meta line, middot-joined
 *     asked by 4 of 4 identified              <- a figure-and-denominator
 *
 * Every one of the five fields is still present and still reachable. The
 * question id moves to the row's `title` and a `data-question-id` attribute --
 * it is a provenance handle a reader needs rarely and a machine needs always,
 * and spending a line of every result on it is what made the list unreadable.
 *
 * The date is NOT dropped and NOT reformatted: question dates are real in this
 * record, unlike term and session dates, and `isoDate` keeps the published
 * spelling.
 */
function resultItem(record, position) {
  const li = el("li", "result");
  li.dataset.questionId = String(record.questionId ?? "");

  // tabindex -1 so "Show 25 more" can move focus here without adding a tab
  // stop for a reader who is not using that button.
  const subject = el("h4", "result-subject");
  subject.tabIndex = -1;
  subject.id = `result-${position}`;

  /* The starred mark (T123, FR-113). The type is NOT a field on the search
   * digest -- it is already in the question id, `lok-sabha/18/7/starred/1` --
   * so `parseQuestionId` yields it and nothing further is fetched and nothing
   * in data/published/ changes. An unstarred question gets no mark; the type
   * is also a word in the meta line, so the glyph is never the only carrier. */
  const parsed = parseQuestionId(record.questionId);
  const type = questionTypeOf(parsed);
  const star = starMark(type, document);
  if (star) subject.append(star);

  if (isMissing(record.subject)) {
    subject.append(document.createTextNode(NOT_STATED));
    subject.classList.add("result-subject-missing");
  } else {
    subject.append(document.createTextNode(record.subject));
  }
  li.append(subject);

  /* ---- the meta line: date, ministry, type, link status ----------------
   *
   * Separated by middots rendered in CSS rather than typed into the text, so
   * the separator never lands in `textContent` and a screen reader reads four
   * facts instead of four facts and three interpuncts. */
  const meta = el("p", "result-meta");

  meta.append(el("span", "result-date", isoDate(record.date)));

  const ministry = ministryNameFor(record.ministry_id);
  const ministrySpan = el("span", ministry.flagged ? "result-ministry flagged" : "result-ministry");
  ministrySpan.append(document.createTextNode(ministry.text));
  if (ministry.flagged) {
    // A WORD, never colour or position alone (FR-104). The reason is kept too,
    // because "flagged" without the why is a dead end.
    ministrySpan.append(el("span", "flag-word", "flagged"));
    ministrySpan.append(
      el(
        "span",
        "result-flag-why",
        "this ministry id is not in the published ministry reference set",
      ),
    );
  }
  meta.append(ministrySpan);

  // The question type as a WORD, beside the asterisk that is its glyph. Both,
  // so the mark is never the only carrier -- and "unstarred" is a word even
  // though its absence of a mark is the visual signal.
  meta.append(el("span", "result-type", typeWord(type)));

  /* Link status, in the SAME WORDS as the ministry profile's status strip:
   * `statusField` reads that view's own list, so the two views cannot drift
   * into two vocabularies for one fact. */
  const bucket = questionBucket(record);
  const field = statusField(bucket);
  const statusSpan = el(
    "span",
    field && field.flagged ? "result-status flagged" : "result-status",
  );
  statusSpan.append(document.createTextNode(field ? field.label : NOT_STATED));
  if (field && field.flagged) statusSpan.append(el("span", "flag-word", "flagged"));
  meta.append(statusSpan);

  li.append(meta);

  /* ---- the askers, INLINE (T140, T141, FR-102, FR-103) -----------------
   *
   * These were one list item per asker. The published record has a question
   * asked by 47 members, and 23,385 questions are asked jointly -- so the old
   * form spent up to 47 lines on one result, and the spec's complaint about
   * "twenty asking members listed vertically" was the mild case.
   *
   * Inline, comma-joined, with the count as a figure against its denominator.
   * Past ASKERS_SHOWN the rest are summarised rather than dropped: FR-103
   * requires the number not shown to be stated, and the full set stays
   * reachable through the `by-member` files the footer names. */
  const { identified, unknownIds } = askersFor(record, search.names);
  const total = identified.length + unknownIds.length;
  const askers = el("p", "result-askers");

  if (total === 0) {
    askers.append(el("span", "result-no-asker", "no asking member is identified"));
  } else {
    askers.append(document.createTextNode("asked by "));
    askers.append(
      figure(identified.length, total, { unit: "question", label: "identified" }),
    );

    const shown = identified.slice(0, ASKERS_SHOWN);
    if (shown.length > 0) {
      // The dash is inside `.asker-names` so it disappears with them below
      // 768 px -- a trailing em dash with nothing after it is worse than no
      // dash, and a text node could not be hidden by CSS.
      const names = el("span", "asker-names");
      names.append(document.createTextNode(" — "));
      shown.forEach((member, index) => {
        if (index > 0) names.append(document.createTextNode(", "));
        const one = el("span", "asker");
        one.append(el("span", "asker-name", stated(member.canonical_name)));
        one.append(el("span", "asker-party", stated(member.party)));
        names.append(one);
      });
      askers.append(names);
    }

    const hiddenCount = identified.length - shown.length;
    if (hiddenCount > 0) {
      // STATED, never silent. The figure is the count not shown, against the
      // identified total it came out of.
      askers.append(document.createTextNode(", and "));
      askers.append(
        figure(hiddenCount, identified.length, {
          unit: "question",
          label: "more not listed here",
        }),
      );
    }

    if (unknownIds.length > 0) {
      /* An id the name lookup does not carry is shown AS THE ID with a flag,
       * because dropping it would make a co-asked question look as though
       * fewer people asked it. */
      askers.append(document.createTextNode(" — "));
      const unknown = el("span", "asker-unknown");
      unknown.append(document.createTextNode(unknownIds.join(", ")));
      unknown.append(el("span", "flag-word", "flagged"));
      unknown.append(
        el("span", "result-flag-why", "this member id is not in the published asker names"),
      );
      askers.append(unknown);
    }
  }
  li.append(askers);

  /* The two flags that are about the RECORD rather than about one field. Both
   * keep their full wording: they are rare, and each explains a disagreement
   * between two published files that a reader would otherwise have to guess
   * at. Shortening these would save pixels on the results that least deserve
   * it. */
  if (field && field.key === "partly_linked") {
    li.append(
      el(
        "p",
        "result-flag",
        "Some of this question's asking members were not identified. The ones above " +
          "are those that were; the question is counted in full and is not filtered " +
          "out of this list.",
      ),
    );
  }
  if (record.notInDigest) {
    li.append(
      el(
        "p",
        "result-flag",
        "The search index matched this question but the published search digest for " +
          "its session does not carry it, so there is nothing here to show but the " +
          "id. Two published files disagree; it is listed rather than dropped so the " +
          "count above still accounts for it.",
      ),
    );
  }
  return li;
}

function ignoredBlock(plan) {
  if (plan.ignored.length === 0) return null;
  const box = el("div", "ignored");
  box.append(
    el(
      "p",
      "ignored-head",
      `Ignored: ${plan.ignored.map((i) => i.word).join(", ")}`,
    ),
  );
  box.append(
    el(
      "p",
      "ignored-note",
      "The index stores a subject's words the same way this box reads your query: " +
        "lowercased, split on anything that is not a letter or a digit, and with " +
        "words under three characters and 36 very common words left out. These were " +
        "left out of the search, not searched for and missed.",
    ),
  );
  box.append(
    list("ignored-list", plan.ignored, (li, entry) => {
      li.append(el("span", "ignored-word", entry.word));
      li.append(el("span", "ignored-why", entry.reason));
    }),
  );
  return box;
}

function searchOrderNote() {
  const box = el("div", "order-note");
  box.append(el("p", "order-head", "The order these are listed in"));
  // RENDERED from lib/search.js, never retyped here: the sentence on screen
  // and the comparator are then one thing.
  box.append(el("p", "order-text", ORDER_STATEMENT));
  return box;
}

function renderSearchEmpty(container, plan) {
  const frag = document.createDocumentFragment();
  if (plan.blank) {
    frag.append(searchStatusLine("Type a word or two above and press Search."));
  } else if (plan.noLetters) {
    frag.append(
      searchStatusLine(
        "That query has no letters or digits in it, so there is nothing to look up.",
      ),
    );
  } else if (plan.emptyQuery) {
    frag.append(
      searchStatusLine(
        "Every word in that query is one the index does not store, so there is " +
          "nothing left to look up.",
      ),
    );
    const ignored = ignoredBlock(plan);
    if (ignored) frag.append(ignored);
  } else if (plan.missingWords.length > 0) {
    // The NAMED reason for zero results. "No results" alone tells a visitor
    // nothing about what to do next.
    const words = plan.missingWords.map((w) => `"${w}"`).join(" and ");
    frag.append(
      searchStatusLine(
        `No questions match. ${words} ${plan.missingWords.length === 1 ? "does" : "do"} ` +
          "not appear in any published subject line, so no question could match " +
          "whatever else you searched for.",
      ),
    );
    const ignored = ignoredBlock(plan);
    if (ignored) frag.append(ignored);
  } else {
    frag.append(
      searchStatusLine(
        `No questions match. Every word you searched for appears in some subject, ` +
          `but no single subject carries all ${plan.words.length} of them — this ` +
          "search requires every word, not any.",
      ),
    );
    const ignored = ignoredBlock(plan);
    if (ignored) frag.append(ignored);
  }
  replaceChildren(container, frag);
  container.dataset.state = "empty";
}

/** The summary line. The total comes from the INDEX, before any digest. */
function searchSummary(page, plan) {
  const box = el("div", "search-summary");
  box.append(
    el(
      "p",
      "search-count",
      `${count(page.shown)} of ${count(page.total)} matching questions shown`,
    ),
  );
  box.append(
    el(
      "p",
      "search-count-note",
      `The total is counted in the published index itself, before any question ` +
        `record is fetched. Searched for: ${plan.words.join(" + ")} — every word ` +
        "must appear in the subject.",
    ),
  );
  return box;
}

function renderSearchResults(container, { page, plan, focusFrom }) {
  const frag = document.createDocumentFragment();
  frag.append(searchSummary(page, plan));
  const ignored = ignoredBlock(plan);
  if (ignored) frag.append(ignored);
  frag.append(searchOrderNote());

  const ul = el("ol", "result-list");
  page.results.forEach((record, position) => {
    ul.append(resultItem(record, position));
  });
  frag.append(ul);

  if (!page.done) {
    const more = el("button", "show-more");
    more.type = "button";
    const remaining = page.total - page.shown;
    more.textContent = `Show ${Math.min(PAGE_SIZE, remaining)} more`;
    more.addEventListener("click", () => {
      void showMore(container);
    });
    frag.append(more);
    frag.append(
      el(
        "p",
        "show-more-note",
        `${count(remaining)} more match. Each session's records are fetched only ` +
          "when a page of results needs them, and only for sessions that contain a " +
          "match — so this button may fetch one file, or none at all if the next " +
          "results are in a session already read.",
      ),
    );
  } else if (page.total > 0) {
    frag.append(el("p", "show-more-note", "That is every matching question."));
  }

  replaceChildren(container, frag);
  container.dataset.state = "ready";

  /* Focus after "Show 25 more": the first NEWLY added result, so a keyboard
   * or screen-reader user lands where the new content starts rather than at
   * the top of the page or on a button that has moved. On the first page
   * nothing is moved -- focus stays in the search box where the reader put
   * it. */
  if (typeof focusFrom === "number" && focusFrom > 0) {
    const target = container.querySelector(`#result-${focusFrom}`);
    if (target) target.focus();
  }
}

/** The error a failed digest produces, shown BESIDE results already on screen
 * rather than instead of them. */
function searchDigestError(container, error, { keepResults }) {
  const box = el("div", "unavailable");
  box.append(el("p", "unavailable-head", "Some of these results could not be read"));
  box.append(
    el(
      "p",
      null,
      "The published records for one session did not load, so the questions in it " +
        "are not listed below.",
    ),
  );
  box.append(el("p", "unavailable-detail", describe(error)));
  box.append(
    el(
      "p",
      "unavailable-note",
      "Nothing above is estimated or filled in, and the list is not silently short: " +
        "the count says how many questions match. Searching again will retry.",
    ),
  );
  if (keepResults) {
    container.prepend(box);
  } else {
    replaceChildren(container, box);
    container.dataset.state = "error";
  }
}

async function showMore(container) {
  if (search.busy || !search.set) return;
  search.busy = true;
  const before = search.set.shown;
  try {
    const page = await search.set.next();
    renderSearchResults(container, { page, plan: search.plan, focusFrom: before });
  } catch (error) {
    searchDigestError(container, error, { keepResults: true });
  } finally {
    search.busy = false;
  }
}

/** Load the index and the asker names. FIRST SEARCH ONLY. */
async function ensureSearchData() {
  if (search.index && search.names) return;
  /* The ministry names come with the search data, not before it: every result
   * row names a ministry, and without this map `ministryNameFor` flags all of
   * them as unknown ids. Fetched in parallel with the index -- it is 1,856 B
   * against the index's 794,402, so it adds nothing measurable to a first
   * search, and it is memoised so opening a ministry view later is free. */
  const [index, names] = await Promise.all([
    loadSearchIndex(),
    loadAskerNames(),
    ensureMinistryNames(),
  ]);
  search.index = index;
  search.names = askerIndex(names);
}

async function runSearch(container, query) {
  if (search.busy) return;
  search.busy = true;
  container.dataset.state = "loading";
  replaceChildren(
    container,
    searchStatusLine(
      search.index
        ? "Searching…"
        : "Reading the search index — this is the one file the page fetches only when " +
            "you search, so the first search takes longer than the next.",
    ),
  );

  try {
    await ensureSearchData();
  } catch (error) {
    // A failed index fetch shows a visible error and NEVER an empty list: an
    // empty list would read as "no such subject", which is a claim about the
    // record rather than about the network.
    renderUnavailable(
      container,
      "The search index could not be read from the published files, so no search " +
        "could run. This is a failed download, not an empty result.",
      describe(error),
    );
    search.busy = false;
    return;
  }

  let plan;
  try {
    plan = planSearch(search.index, query);
  } catch (error) {
    renderUnavailable(container, "The published search index could not be read.", describe(error));
    search.busy = false;
    return;
  }

  search.plan = plan;
  search.set = null;

  if (plan.total === 0) {
    renderSearchEmpty(container, plan);
    search.busy = false;
    return;
  }

  search.set = createResultSet(plan, { loadDigest: (sessionId) => loadSearchDigest(sessionId) });
  try {
    const page = await search.set.next();
    renderSearchResults(container, { page, plan });
  } catch (error) {
    searchDigestError(container, error, { keepResults: false });
  } finally {
    search.busy = false;
  }
}

function buildSearchView(doc) {
  const host = doc.getElementById("search-form-host");
  const result = doc.getElementById("search-result");
  if (!host || !result) return;

  const form = el("form", "search-form");
  // No action and no method: there is no server. Submit is handled here, and
  // prevented, so Enter in the field works exactly like the button.
  form.setAttribute("role", "search");
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    void runSearch(result, input.value);
  });

  const label = el("label", "field");
  label.htmlFor = "search-query";
  label.append(el("span", "field-label", "Search question subjects"));
  const input = el("input");
  input.type = "search";
  input.id = "search-query";
  input.name = "search-query";
  input.autocomplete = "off";
  input.spellcheck = false;
  input.setAttribute("aria-describedby", "search-help");
  label.append(input);

  const submit = el("button", "search-submit", "Search");
  submit.type = "submit";

  form.append(label, submit);
  replaceChildren(host, form);

  const help = el("p", "picker-note");
  help.id = "search-help";
  help.textContent =
    "Every word you type must appear in the question's subject line — this is not a " +
    "phrase search and not a ranked one. The index covers subject lines only, not " +
    "question or answer text, which this project never opens. It is fetched on your " +
    "first search and not before, so a visitor who never searches never downloads it.";
  host.append(help);

  // Politely announced: a reader who submits the form is told the result
  // without focus being moved out from under them.
  result.setAttribute("role", "status");
  result.setAttribute("aria-live", "polite");
  result.setAttribute("aria-atomic", "false");

  replaceChildren(result, searchStatusLine("Type a word or two above and press Search."));
  result.dataset.state = "empty";
}

/* ---------------------------------------------------------------------- */
/* The view's entry point, called by the router in app.js                 */
/* ---------------------------------------------------------------------- */

/** Build the search box. Fetches NOTHING -- the index, the asker names and
 * each session digest are read on the first search, not on arrival. */
export async function mount(doc = document) {
  buildSearchView(doc);
}
