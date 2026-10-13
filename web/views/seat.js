/* The state and constituency entry point, and what a state's members ask
 * about. T135.
 *
 * MOVED here from `app.js` unchanged -- see the note in `ministries.js`.
 *
 * Loaded by `import()` on the reader's first visit (FR-128). Its two files are
 * read on first USE and one `by-member` file when a member is opened, which is
 * the discipline `boot()` has asserted since T088.
 */

import { horizontalBars, legend, stackedColumns } from "../lib/chart.js";
import {
  STATE_BASIS_UNIT,
  memberQuestions,
  nameKey,
  representativesOf,
  seatById,
  seatHistory,
  seatsInState,
  seatsMatching,
  seatsNamed,
  stateSubjects,
  statesIn,
  statesWithSubjects,
  subjectTally,
  termsPhrase,
} from "../lib/constituency.js";
import { loadMemberQuestions, loadSeats, loadStateSubjects } from "../lib/fetch.js";
import { NOT_STATED, count, isMissing, isoDate, stated } from "../lib/format.js";
import { figure, figureText, starMark, typeWord } from "../lib/marks.js";
import { questionBucket, statusField } from "../lib/profile.js";
import { parseQuestionId } from "../lib/search.js";
import {
  describe,
  el,
  fact,
  list,
  renderUnavailable,
  replaceChildren,
} from "../lib/shared.js";
import {
  basisBlock,
  basisBlockForUnit,
  labelledSelect,
  ministryNameFor,
  questionTypeOf,
} from "../lib/viewkit.js";

/* ====================================================================== */
/* T088 — the state and constituency entry point. User Story 3.           */
/* ====================================================================== */

/* SC-008: "A person who knows only their constituency or state can reach
 * their members' questions without knowing a member's name."
 *
 * The walk, and nothing else (owner decision 2026-10-10):
 *
 *   first use of the view -> reference/constituencies.jsonl   252,226 B
 *                         -> aggregates/state-subjects.jsonl  181,347 B
 *   opening one member    -> by-member/<id>.jsonl             <= 442,053 B
 *
 * NOT `reference/members.jsonl` (3,447,794 B): T086 put the member's name,
 * party and sitting status onto the representation so this view would not need
 * it. NOT every member of a state up front: Maharashtra's 85 members come to
 * 10,489,198 B, which is why the state subject summary is a published
 * aggregate instead. NOT a per-state question partition, which the dataset
 * deliberately does not publish.
 *
 * STATE FIRST, THEN CONSTITUENCY. Three names in this window name a different
 * seat in each of two states, so a typed name always shows its state and this
 * view never resolves one to a single seat on its own.
 */

/** Everything the view holds between interactions. */
const seatView = {
  seats: null,
  stateRows: null,
  loaded: false,
  busy: false,
  state: "",
  seat: null,
  openMemberId: null,
};

function seatStatusLine(text) {
  return el("p", "search-status", text);
}

/** A member's sitting status, with the "as of" the record actually supports.
 *
 * `sitting_status` is a MEMBER-level fact as of the last refresh, not a fact
 * about the term — a former member's 17th-term representation still reads
 * `former`. Saying so is the difference between a date the record has and one
 * the page implied.
 */
function sittingStatusText(value) {
  if (isMissing(value)) return NOT_STATED;
  return `${String(value)} (as of the last refresh)`;
}

/* ---------------------------------------------------------------------- */
/* One seat                                                               */
/* ---------------------------------------------------------------------- */

function representativeCard(entry, { onOpen }) {
  const li = el("li", "rep");

  const head = el("div", "rep-top");
  const name = el("h4", "rep-name");
  if (entry.nameMissing) {
    // The record names the member but not who they are. The id is shown with a
    // flag rather than an empty row -- dropping them would make a seat look
    // as though it had fewer representatives than it had.
    name.textContent = entry.memberId;
    name.classList.add("rep-name-missing");
  } else {
    name.textContent = entry.name;
  }
  head.append(name);
  if (entry.nameMissing) {
    head.append(el("span", "flag-word", "flagged"));
    head.append(
      el("span", "result-flag-why", "this member's name is not in the published seat record"),
    );
  }
  li.append(head);

  const meta = el("dl", "rep-meta");
  const pair = (label, value, className) => {
    meta.append(el("dt", null, label));
    meta.append(el("dd", className, value));
  };
  pair("Party", stated(entry.party));
  pair("Represented", termsPhrase(entry.terms));
  pair("Sitting status", sittingStatusText(entry.sittingStatus));
  pair("Member id", entry.memberId, "rep-id");
  li.append(meta);

  const open = el("button", "rep-open", "Show their questions");
  open.type = "button";
  open.addEventListener("click", () => onOpen(entry));
  li.append(open);

  const host = el("div", "rep-questions");
  host.id = `rep-questions-${entry.memberId}`;
  host.dataset.state = "empty";
  li.append(host);

  return li;
}

function renderSeat(container, seat, { onOpen }) {
  const history = seatHistory(seat);
  const frag = document.createDocumentFragment();

  const head = el("div", "seat-head");
  head.append(el("h3", "seat-name", stated(seat.name)));
  /* The state is ALWAYS beside the name. Three names in this window are
   * ambiguous without it, and a reader cannot tell which three.
   *
   * No House is named here. A constituency only ever belongs to one of them,
   * but which Houses this RECORD covers is the coverage statement's claim and
   * it derives it from the published rows -- a second copy here would be the
   * typed claim that `housesClaim` exists to have removed. */
  head.append(el("p", "seat-state", stated(seat.state)));
  head.append(el("p", "seat-id", `Seat id: ${stated(seat.constituency_id)}`));
  frag.append(head);

  /* Whether the seat changed hands, in words. US3 scenario 3's whole point is
   * that two holders are not merged, so the page says which case this is
   * rather than leaving the reader to count the rows. */
  const note = el("p", "seat-history");
  if (history.people.length === 0) {
    note.textContent = "The published record lists no representation for this seat in the covered window.";
  } else if (history.changedHands) {
    note.textContent =
      `${count(history.people.length)} different members represented this seat across the ` +
      `covered window (${termsPhrase(history.terms)}). They are listed separately, with ` +
      "their own terms — not merged into one entry.";
  } else {
    note.textContent =
      `One member represented this seat across the covered window ` +
      `(${termsPhrase(history.terms)}).`;
  }
  frag.append(note);

  if (history.people.length > 0) {
    const ul = el("ul", "rep-list");
    for (const entry of history.people) ul.append(representativeCard(entry, { onOpen }));
    frag.append(ul);
  }

  frag.append(
    el(
      "p",
      "picker-note",
      "Dates are not shown because the published record does not carry them: every " +
        "representation's start and end date is “not stated”, so the term is the " +
        "period this record has. Only the member's name, party, state, constituency, " +
        "House, term and sitting status are published.",
    ),
  );

  replaceChildren(container, frag);
  container.dataset.state = "ready";
}

/* ---------------------------------------------------------------------- */
/* One member's questions                                                 */
/* ---------------------------------------------------------------------- */

function renderMemberQuestions(host, entry, records) {
  const summary = memberQuestions(records);
  const frag = document.createDocumentFragment();

  const totals = el("div", "member-totals");
  totals.append(
    fact(
      "Questions published",
      count(summary.total),
      "Counted once each. A question this member asked jointly with others is " +
        "one question here, and appears in every asker's file.",
    ),
  );
  frag.append(totals);

  /* Link status, in the SAME WORDS as the ministry profile and the search
   * results: the labels come from `statusField`, which reads that view's own
   * list. Flagged rows carry the WORD "flagged", never colour alone. */
  const status = el("div", "status-strip");
  status.append(el("p", "strip-head", "How these questions are linked to this member"));
  const statusList = el("ul", "status-list");
  for (const row of summary.statusRows) {
    const li = el("li", row.flagged ? "status-item flagged" : "status-item");
    if (row.flagged) {
      // A WORD, never colour alone, and in the same position the ministry
      // profile puts it.
      li.append(el("span", "flag-word", "flagged"));
    }
    li.append(el("span", "status-label", row.label));
    li.append(el("span", "status-value", count(row.questions)));
    statusList.append(li);
  }
  status.append(statusList);
  if (summary.unknownStatus > 0) {
    status.append(
      el(
        "p",
        "strip-note",
        `${count(summary.unknownStatus)} question(s) carry no link status at all and are ` +
          "counted in the total above but in none of the rows.",
      ),
    );
  }
  status.append(
    el(
      "p",
      "strip-note",
      "Unresolved and ambiguous questions are included in the total, not filtered out. " +
        "A partly linked question is in this member's file and is still counted as " +
        "unresolved in the published record.",
    ),
  );
  frag.append(status);

  // The member's own subject lines. From data already loaded -- this file.
  const tally = subjectTally(records, { limit: 10 });
  if (tally.rows.length > 0) {
    const box = el("div", "subject-tally");
    box.append(
      el(
        "p",
        "strip-head",
        `Their most-asked subject lines (${count(tally.shown)} of ` +
          `${count(tally.distinct)} distinct lines)`,
      ),
    );
    box.append(
      list("subject-list", tally.rows, (li, row) => {
        li.append(el("span", "subject-text", row.subject));
        li.append(el("span", "subject-count", count(row.questions)));
      }),
    );
    box.append(
      el(
        "p",
        "strip-note",
        "Exact subject lines as the source records them, not topics: two lines " +
          "differing by a word or by capitalisation are counted separately.",
      ),
    );
    frag.append(box);
  }

  // The questions themselves -- "individual questions are reachable".
  const shown = summary.questions.slice(0, SEAT_QUESTION_PAGE);
  const listBox = el("div", "member-questions");
  listBox.append(
    el(
      "p",
      "strip-head",
      `Questions, newest first (${count(shown.length)} of ${count(summary.total)} shown)`,
    ),
  );
  listBox.append(
    /* The SAME denser shape as a search result (T144).
     *
     * This was the second five-pair `<dl>` in the codebase, with the same
     * five labels on the same five lines of their own. Leaving it as it was
     * would have given the page two vocabularies for one thing: a question
     * rendered one way under a search and another way under a member, which
     * is the kind of difference a reader reads as a bug.
     *
     * Shared with the search view at the level that matters -- `starMark`,
     * `typeWord`, `figure` and `statusField` are the same functions, so the
     * asterisk, the wording of a type, the figure pairing and the status
     * vocabulary cannot drift apart. The markup is written twice because the
     * two rows carry different fields: a search result names its askers,
     * where this one is already inside one member's list and says instead how
     * many OTHERS asked with them. */
    list("question-list", shown, (li, question) => {
      li.dataset.questionId = String(question.question_id ?? "");

      const subject = el("p", "question-subject");
      const parsed = parseQuestionId(question.question_id);
      const type = questionTypeOf(parsed);
      const star = starMark(type, document);
      if (star) subject.append(star);
      if (isMissing(question.subject)) {
        subject.append(document.createTextNode(NOT_STATED));
        subject.classList.add("result-subject-missing");
      } else {
        subject.append(document.createTextNode(question.subject));
      }
      li.append(subject);

      const meta = el("p", "result-meta");
      meta.append(el("span", "result-date", isoDate(question.date)));

      const ministry = ministryNameFor(question.ministry_id);
      const ministrySpan = el(
        "span",
        ministry.flagged ? "result-ministry flagged" : "result-ministry",
      );
      ministrySpan.append(document.createTextNode(ministry.text));
      if (ministry.flagged) ministrySpan.append(el("span", "flag-word", "flagged"));
      meta.append(ministrySpan);

      meta.append(el("span", "result-type", typeWord(type)));

      const field = statusField(questionBucket(question));
      const statusSpan = el(
        "span",
        field && field.flagged ? "result-status flagged" : "result-status",
      );
      statusSpan.append(document.createTextNode(field ? field.label : NOT_STATED));
      if (field && field.flagged) statusSpan.append(el("span", "flag-word", "flagged"));
      meta.append(statusSpan);
      li.append(meta);

      /* Joint asking, as a figure against its denominator.
       *
       * The published `question` counting basis is the reason this says
       * "counted once": 23,385 questions in this window are asked jointly,
       * the by-member files republish each one per asker, and adding those
       * files up gives a larger number than there are questions. The row
       * states that where a reader can see it rather than leaving it to the
       * basis block below. */
      const askers = (question.asking_members ?? []).length;
      if (askers > 1) {
        const joint = el("p", "result-askers");
        joint.append(document.createTextNode("asked jointly — "));
        joint.append(
          figure(askers, askers, { unit: "question", label: "members, counted once" }),
        );
        li.append(joint);
      }
    }),
  );
  if (summary.total > shown.length) {
    listBox.append(
      el(
        "p",
        "strip-note",
        `The remaining ${count(summary.total - shown.length)} are in the published file ` +
          `by-member/${entry.memberId}.jsonl, which this page has already downloaded in ` +
          "full — they are not shown here to keep the page readable, not withheld.",
      ),
    );
  }
  frag.append(listBox);

  frag.append(basisBlockForUnit("question", { head: "How these figures were counted" }));

  replaceChildren(host, frag);
  host.dataset.state = "ready";
}

/** How many of a member's questions the page lists. The whole file is already
 * downloaded; this is a readability bound, and the page says so. */
const SEAT_QUESTION_PAGE = 25;

async function openMemberQuestions(entry) {
  const host = document.getElementById(`rep-questions-${entry.memberId}`);
  if (!host) return;
  if (seatView.openMemberId === entry.memberId && host.dataset.state === "ready") {
    // A second click closes it, so one member's questions are not left open
    // underneath another's.
    replaceChildren(host);
    host.dataset.state = "empty";
    seatView.openMemberId = null;
    return;
  }
  seatView.openMemberId = entry.memberId;
  host.dataset.state = "loading";
  replaceChildren(
    host,
    seatStatusLine(
      "Reading this member's published questions — one file, fetched only because you " +
        "opened them.",
    ),
  );
  try {
    const records = await loadMemberQuestions(entry.memberId);
    renderMemberQuestions(host, entry, records);
  } catch (error) {
    renderUnavailable(
      host,
      `This member's published question file could not be read, so none of their ` +
        "questions could be listed. This is a failed download, not a member with no " +
        "questions.",
      describe(error),
    );
  }
}

/* ---------------------------------------------------------------------- */
/* One state                                                              */
/* ---------------------------------------------------------------------- */

function renderStateSummary(container, state) {
  const summary = stateSubjects(seatView.stateRows, state);
  const frag = document.createDocumentFragment();
  frag.append(el("h3", "seat-name", `${stated(state)} — what its members have raised`));

  if (!summary) {
    frag.append(
      el(
        "p",
        "seat-history",
        "The published state subject summary carries no row for this state. That means no " +
          "question in the covered window could be attributed to a member holding a seat " +
          "here — not that its members asked none.",
      ),
    );
    frag.append(basisBlockForUnit(STATE_BASIS_UNIT, { head: "How this would have been counted" }));
    replaceChildren(container, frag);
    container.dataset.state = "ready";
    return;
  }

  const totals = el("div", "member-totals");
  totals.append(
    fact(
      "Questions attributed to this state",
      count(summary.stateQuestions),
      "A question counts once here if at least one of its identified asking members " +
        "holds a seat in this state.",
    ),
  );
  totals.append(
    fact(
      "Distinct subject lines",
      count(summary.stateSubjects),
      `The ${count(summary.subjectsShown)} most-asked are listed below; the rest are in ` +
        "the published question records.",
    ),
  );
  frag.append(totals);

  /* ---- what the state asks about, as a shape (T167-T170) --------------
   *
   * FR-119. The published rows for this state, drawn as bars rather than read
   * as a 25-row list. ZERO NEW BYTES: `aggregates/state-subjects.jsonl` is
   * already in hand -- the seat view fetches it on its own first use -- so
   * this is a second form of data the page had already paid for.
   *
   * THE DENOMINATOR is `state_questions`, this state's own question total, and
   * it is the figure that makes a count mean something: "2 of 639" is a
   * different statement from "2". FR-120.
   *
   * THE UNIT IS NOT THE SAME as the question counts elsewhere on this page.
   * `state-question` counts a question once if at least one of its identified
   * asking members holds a seat here, so the same question can be counted for
   * two states. The basis block below says so, read from the published file
   * rather than retyped. */
  const box = el("div", "subject-tally chart-block");
  box.append(
    el(
      "p",
      "strip-head",
      `Most-asked subject lines (${count(summary.rows.length)} of ` +
        `${count(summary.stateSubjects)} distinct lines)`,
    ),
  );

  /* THE ORDERING, stated rather than left to be inferred.
   *
   * Several of a state's subject lines share a count -- for Andaman and
   * Nicobar Islands every one of the 25 published rows has the same figure --
   * so "most-asked" does not determine the order on its own. The published
   * order is kept and the tie-break is named, which is the same discipline the
   * search view applies to its own result order. */
  box.append(
    el(
      "p",
      "order-text",
      "Ordered as the published aggregate orders them: by question count, " +
        "descending. Several lines in a state commonly share a count, and " +
        "those keep the order the published file gives them rather than being " +
        "re-sorted here.",
    ),
  );

  const seriesName = "Questions";
  box.append(legend([seriesName]));
  box.append(
    horizontalBars(
      summary.rows.map((row) => ({
        label: row.subject,
        parts: { [seriesName]: row.questions },
        totals: { [seriesName]: summary.stateQuestions },
      })),
      [seriesName],
      {
        title: `Most-asked subject lines in ${stated(state)}`,
        description:
          "One row per published subject line, each against this state's own " +
          "question total. The table below carries the same figures.",
      },
    ),
  );

  /* The table, which is the authoritative form (FR-121). The bars above are a
   * shape; this is the thing a keyboard and a screen reader reach. */
  const wrap = el("div", "table-wrap");
  wrap.setAttribute("role", "region");
  wrap.setAttribute("aria-label", "Most-asked subject lines, scrollable");
  wrap.tabIndex = 0;
  const table = el("table");
  const caption = el("caption", "table-caption");
  caption.textContent =
    `The ${count(summary.rows.length)} most-asked published subject lines in ` +
    `${stated(state)}, each against this state's own question total.`;
  table.append(caption);
  const thead = el("thead");
  const hrow = el("tr");
  for (const text of ["Subject line", "Questions"]) {
    const th = el("th", null, text);
    th.scope = "col";
    hrow.append(th);
  }
  thead.append(hrow);
  table.append(thead);
  const tbody = el("tbody");
  for (const row of summary.rows) {
    const tr = el("tr");
    const th = el("th", null, row.subject);
    th.scope = "row";
    tr.append(th);
    tr.append(el("td", "num-col", figureText(row.questions, summary.stateQuestions)));
    tbody.append(tr);
  }
  table.append(tbody);
  wrap.append(table);
  box.append(wrap);
  frag.append(box);

  // The published basis, read from the file. It carries the attribution rule.
  frag.append(basisBlockForUnit(summary.basisUnit, { head: "How these figures were counted" }));
  frag.append(
    el(
      "p",
      "picker-note",
      "These figures are read from the published aggregate, not recomputed by this page. " +
        "They can be reproduced by hand from the published by-member files — take every " +
        "member holding a seat in this state, de-duplicate their questions on question_id, " +
        "and count the subject lines.",
    ),
  );

  replaceChildren(container, frag);
  container.dataset.state = "ready";
}

/* ---------------------------------------------------------------------- */
/* The pickers                                                            */
/* ---------------------------------------------------------------------- */

function seatOptionsFor(state) {
  const seats = seatsInState(seatView.seats, state);
  return [["", `Choose one of ${seats.length} constituencies…`], ...seats.map((s) => [s.constituency_id, s.name])];
}

function showSeat(seatResult, seat) {
  seatView.seat = seat;
  seatView.openMemberId = null;
  renderSeat(seatResult, seat, { onOpen: (entry) => void openMemberQuestions(entry) });
}

function renderNameMatches(host, seatResult, text) {
  const exact = seatsNamed(seatView.seats, text);
  const near = exact.length > 0 ? exact : seatsMatching(seatView.seats, text);
  replaceChildren(host);
  if (near.length === 0) {
    host.append(
      seatStatusLine(
        text.trim().length < 2
          ? "Type at least two letters of a constituency name."
          : "No constituency in the published record has that name. Try picking a state above.",
      ),
    );
    return;
  }
  host.append(
    el(
      "p",
      "strip-head",
      exact.length > 1
        ? `${count(exact.length)} constituencies are named “${text.trim()}” — in different states. ` +
            "Pick the one you mean."
        : `${count(near.length)} match(es)`,
    ),
  );
  const ul = el("ul", "match-list");
  for (const seat of near) {
    const li = el("li");
    const button = el("button", "match-button");
    button.type = "button";
    // The STATE is always in the label. A name on its own is ambiguous for
    // three seats in this window and the reader cannot know which.
    button.append(el("span", "match-name", stated(seat.name)));
    button.append(el("span", "match-state", stated(seat.state)));
    button.addEventListener("click", () => {
      const states = statesIn(seatView.seats).map((s) => s.state);
      const stateSelect = document.getElementById("seat-state");
      if (stateSelect && states.includes(seat.state)) {
        stateSelect.value = seat.state;
        seatView.state = seat.state;
        refreshSeatSelect();
        renderStateSummary(document.getElementById("state-summary"), seat.state);
      }
      const seatSelect = document.getElementById("seat-constituency");
      if (seatSelect) seatSelect.value = seat.constituency_id;
      showSeat(seatResult, seat);
    });
    li.append(button);
    ul.append(li);
  }
  host.append(ul);
}

function refreshSeatSelect() {
  const wrap = document.getElementById("seat-constituency-host");
  if (!wrap) return;
  const seatResult = document.getElementById("seat-result");
  replaceChildren(wrap);
  if (!seatView.state) return;
  const { wrap: field, select } = labelledSelect(
    "seat-constituency",
    "Then pick your constituency",
    seatOptionsFor(seatView.state),
    "",
  );
  select.addEventListener("change", () => {
    const seat = seatById(seatView.seats, select.value);
    if (seat) showSeat(seatResult, seat);
    else {
      replaceChildren(seatResult, seatStatusLine("Pick a constituency to see its members."));
      seatResult.dataset.state = "empty";
    }
  });
  wrap.append(field);
}

function renderSeatPickers(host) {
  const seatResult = document.getElementById("seat-result");
  const stateSummary = document.getElementById("state-summary");
  const frag = document.createDocumentFragment();

  const states = statesIn(seatView.seats);
  const withSubjects = statesWithSubjects(seatView.stateRows);
  const { wrap, select } = labelledSelect(
    "seat-state",
    "Pick your state or union territory",
    [
      ["", `Choose one of ${states.length}…`],
      ...states.map((s) => [s.state, `${s.state} — ${s.seats} seat(s), ${s.members} member(s)`]),
    ],
    "",
  );
  select.addEventListener("change", () => {
    seatView.state = select.value;
    refreshSeatSelect();
    replaceChildren(seatResult, seatStatusLine("Pick a constituency to see its members."));
    seatResult.dataset.state = "empty";
    if (seatView.state) {
      renderStateSummary(stateSummary, seatView.state);
      if (!withSubjects.has(nameKey(seatView.state))) stateSummary.dataset.state = "ready";
    } else {
      replaceChildren(stateSummary);
      stateSummary.dataset.state = "empty";
    }
  });
  frag.append(wrap);

  const seatHost = el("div");
  seatHost.id = "seat-constituency-host";
  frag.append(seatHost);

  // The by-name box, which ALWAYS shows the state of every match.
  const form = el("form", "search-form");
  form.setAttribute("role", "search");
  const label = el("label", "field");
  label.htmlFor = "seat-name";
  label.append(el("span", "field-label", "Or type a constituency name"));
  const input = el("input");
  input.type = "search";
  input.id = "seat-name";
  input.name = "seat-name";
  input.autocomplete = "off";
  input.spellcheck = false;
  input.setAttribute("aria-describedby", "seat-name-help");
  label.append(input);
  const submit = el("button", "search-submit", "Find");
  submit.type = "submit";
  form.append(label, submit);
  const matches = el("div", "match-host");
  matches.id = "seat-matches";
  matches.setAttribute("role", "status");
  matches.setAttribute("aria-live", "polite");
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    renderNameMatches(matches, seatResult, input.value);
  });
  frag.append(form);
  const help = el("p", "picker-note");
  help.id = "seat-name-help";
  help.textContent =
    "Every match is listed with its state, always. Three constituency names in the " +
    "covered window name a different seat in each of two states, so a name on its own " +
    "does not identify a seat and this page never picks one for you.";
  frag.append(help);
  frag.append(matches);

  replaceChildren(host, frag);
}

/** Load the two files this view needs. FIRST USE ONLY. */
async function ensureSeatData() {
  if (seatView.seats && seatView.stateRows) return;
  const [seats, stateRows] = await Promise.all([loadSeats(), loadStateSubjects()]);
  seatView.seats = seats;
  seatView.stateRows = stateRows;
  seatView.loaded = true;
}

async function openSeatView(host) {
  if (seatView.busy) return;
  seatView.busy = true;
  replaceChildren(
    host,
    seatStatusLine(
      "Reading the published seat list and the state subject summary — the two files " +
        "this view fetches only when you open it.",
    ),
  );
  try {
    await ensureSeatData();
  } catch (error) {
    renderUnavailable(
      host,
      "The published seat list could not be read, so no state or constituency could be " +
        "listed. This is a failed download, not a record with no constituencies.",
      describe(error),
    );
    seatView.busy = false;
    return;
  }
  try {
    renderSeatPickers(host);
  } catch (error) {
    renderUnavailable(host, "The seat list was read but could not be displayed.", describe(error));
  }
  seatView.busy = false;
}

function buildConstituencyView(doc) {
  const host = doc.getElementById("seat-picker");
  const seatResult = doc.getElementById("seat-result");
  const stateSummary = doc.getElementById("state-summary");
  if (!host || !seatResult || !stateSummary) return;

  seatResult.setAttribute("role", "status");
  seatResult.setAttribute("aria-live", "polite");
  seatResult.setAttribute("aria-atomic", "false");

  const open = el("button", "search-submit", "Show states and constituencies");
  open.type = "button";
  open.id = "seat-open";
  open.addEventListener("click", () => void openSeatView(host));
  const note = el("p", "picker-note");
  note.textContent =
    "This view fetches nothing until you open it: the seat list and the state subject " +
    "summary are read on your first use and not before, so a visitor who never looks " +
    "one up never downloads them.";
  replaceChildren(host, open, note);

  replaceChildren(seatResult, seatStatusLine("Pick a state, then a constituency."));
  seatResult.dataset.state = "empty";
  replaceChildren(stateSummary);
  stateSummary.dataset.state = "empty";
}

/* ---------------------------------------------------------------------- */
/* The view's entry point, called by the router in app.js                 */
/* ---------------------------------------------------------------------- */

/** Build the state and constituency pickers. Fetches NOTHING on arrival. */
export async function mount(doc = document) {
  buildConstituencyView(doc);
}
