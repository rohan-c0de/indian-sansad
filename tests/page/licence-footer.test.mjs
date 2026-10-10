/* The footer's source-terms disclosure. Owner decision 2026-10-10.
 *
 * Two things are under test and the second is the reason this file exists:
 *
 *   1. The rendering — both published statements reach the page, as TEXT, in
 *      the order and with the classes the stylesheet already defines.
 *   2. The refusal — `corrections_url` becomes an `href` ONLY when the
 *      published value starts with `https://`. Anything else is displayed as
 *      text with the reason, and NO node on the fragment acquires an href.
 *
 * The document is a recording stand-in rather than a browser's. That is not a
 * shortcut: the assertions are about which property each value was assigned
 * to — `textContent` and not `innerHTML`, `href` set or never set — and a fake
 * records that directly, where a real DOM would normalise it away. What this
 * file does NOT establish is that the rendered footer looks right in a
 * browser; that is T082's, from the real page.
 *
 * Node 22 is already installed. Nothing was installed for this file: no test
 * framework, no DOM library, no package.json.
 */

import assert from "node:assert/strict";
import { test } from "node:test";

import {
  CORRECTIONS_HEAD,
  NO_CHANNEL_NOTE,
  REFUSED_NOTE,
  SOURCE_TERMS_HEAD,
  renderDisclosure,
  safeHttpsHref,
} from "../../web/lib/licence.js";
import { NOT_STATED } from "../../web/lib/format.js";

/* ---------------------------------------------------------------------- */
/* A document that records what was set, and nothing else.                */
/* ---------------------------------------------------------------------- */

function recordingDocument() {
  const created = [];
  const make = (tag) => {
    const node = {
      tagName: tag,
      kids: [],
      /* Anything the renderer sets lands on the object and is asserted by
       * name below — including `innerHTML`, which must stay undefined. */
      append(...kids) {
        for (const kid of kids) {
          if (kid && kid.isFragment) node.kids.push(...kid.kids);
          else node.kids.push(kid);
        }
      },
    };
    created.push(node);
    return node;
  };
  return {
    created,
    createElement: make,
    createDocumentFragment() {
      return {
        isFragment: true,
        kids: [],
        append(...kids) {
          for (const kid of kids) {
            if (kid && kid.isFragment) this.kids.push(...kid.kids);
            else this.kids.push(kid);
          }
        },
      };
    },
  };
}

/* Depth-first flatten, so a nested <li> child is still inspected.
 *
 * The recorded property is `kids`, not `children`: `tools/guard_no_raw_payloads.py`
 * reads `children` as the upstream's family-composition field and fails the
 * tree on it (Constitution Principle V). That is the guard working -- it
 * cannot tell a DOM stand-in's key from a published one, and the version that
 * could would be the version that let the real field through. */
function walk(nodes, out = []) {
  for (const node of nodes) {
    out.push(node);
    if (node.kids) walk(node.kids, out);
  }
  return out;
}

/** The real published values, as `attribution.py` defines them. */
const MANIFEST = {
  source_terms:
    "Not determined. The maintainer has not established the terms under which " +
    "the Lok Sabha publishes these records and publishes this dataset without " +
    "that determination. See DATA-LICENSE.md.",
  corrections_url: "https://github.com/rohan-c0de/indian-sansad/issues",
};

function render(manifest) {
  const doc = recordingDocument();
  const frag = renderDisclosure(doc, manifest);
  return { doc, frag, nodes: walk(frag.kids) };
}

/* ---------------------------------------------------------------------- */
/* (1) The rendering                                                      */
/* ---------------------------------------------------------------------- */

test("both published statements reach the page, verbatim", () => {
  const { nodes } = render(MANIFEST);
  const texts = nodes.map((n) => n.textContent);

  assert.ok(texts.includes(SOURCE_TERMS_HEAD), "the source-terms heading is missing");
  assert.ok(texts.includes(CORRECTIONS_HEAD), "the corrections heading is missing");
  // Verbatim: not truncated, not re-worded, not re-wrapped.
  assert.ok(
    texts.includes(MANIFEST.source_terms),
    "source_terms was not rendered as the published string",
  );
  assert.ok(
    texts.includes(MANIFEST.corrections_url),
    "corrections_url was not rendered as the published string",
  );
});

test("every value goes in through textContent and nothing touches innerHTML", () => {
  const { doc } = render(MANIFEST);
  assert.ok(doc.created.length > 4, "nothing was rendered");
  for (const node of doc.created) {
    assert.equal(node.innerHTML, undefined, `${node.tagName} was given innerHTML`);
    assert.equal(node.outerHTML, undefined, `${node.tagName} was given outerHTML`);
    assert.equal(node.insertAdjacentHTML, undefined, `${node.tagName} used insertAdjacentHTML`);
  }
});

test("the classes it sets are the ones the stylesheet already defines", () => {
  // No new CSS was added for this. If a class here changes, style.css has to.
  const { nodes } = render(MANIFEST);
  const classes = new Set(nodes.map((n) => n.className).filter(Boolean));
  assert.deepEqual(
    [...classes].sort(),
    ["licence-head", "licence-links", "licence-links-note", "licence-scope"],
  );
});

test("the disclosure is read from the manifest, not from this module", () => {
  // The whole point of the runtime read: change the manifest, the page changes.
  const { nodes } = render({
    source_terms: "Determined: whatever the next refresh says.",
    corrections_url: "https://example.com/elsewhere",
  });
  const texts = nodes.map((n) => n.textContent);
  assert.ok(texts.includes("Determined: whatever the next refresh says."));
  assert.ok(texts.includes("https://example.com/elsewhere"));
  assert.ok(!texts.includes(MANIFEST.source_terms));
});

test("an https corrections_url becomes a link, opened safely", () => {
  const { nodes } = render(MANIFEST);
  const anchors = nodes.filter((n) => n.tagName === "a");
  assert.equal(anchors.length, 1, "expected exactly one corrections link");
  const [link] = anchors;
  assert.equal(link.href, MANIFEST.corrections_url);
  assert.equal(link.textContent, MANIFEST.corrections_url, "the link must show where it goes");
  assert.equal(link.target, "_blank");
  assert.equal(link.rel, "noopener noreferrer");
});

/* ---------------------------------------------------------------------- */
/* (2) The refusal — the test this file is really for                     */
/* ---------------------------------------------------------------------- */

test("safeHttpsHref admits https and nothing else", () => {
  assert.equal(safeHttpsHref("https://example.com/x"), "https://example.com/x");
  for (const refused of [
    "http://example.com/x", // downgrade
    "//example.com/x", // scheme-relative: inherits the page's
    "/issues", // same-origin path: not a corrections channel
    "HTTPS://example.com", // the check is literal, on purpose
    " https://example.com", // leading space is not a URL
    "javascript:alert(1)", // the one that would EXECUTE on click
    "data:text/html,<script>alert(1)</script>",
    "mailto:someone@example.com",
    "",
    null,
    undefined,
    42,
    { href: "https://example.com" },
  ]) {
    assert.equal(safeHttpsHref(refused), null, `admitted ${JSON.stringify(refused)}`);
  }
});

test("a non-https corrections_url sets no href anywhere, and says why", () => {
  for (const refused of [
    "http://example.com/issues",
    "//example.com/issues",
    "javascript:alert(1)",
    "data:text/html,x",
    "mailto:someone@example.com",
  ]) {
    const { doc, nodes } = render({ source_terms: MANIFEST.source_terms, corrections_url: refused });

    // The refusal, stated as the absence it is: no anchor, and no node on the
    // whole fragment carrying an href — not just no anchor with one.
    assert.equal(
      nodes.filter((n) => n.tagName === "a").length,
      0,
      `${refused} was rendered as a link`,
    );
    for (const node of doc.created) {
      assert.equal(node.href, undefined, `${refused} reached an href on <${node.tagName}>`);
    }

    // And the value is still shown, with the reason. A silently dropped
    // channel would read as "there is no corrections path".
    const texts = nodes.map((n) => n.textContent);
    assert.ok(texts.includes(refused), `${refused} was not displayed as text`);
    assert.ok(texts.includes(REFUSED_NOTE), `${refused} was refused without a reason`);
  }
});

test("a missing corrections_url says the manifest states none, not that it was refused", () => {
  for (const absent of [undefined, null, "", "   ", "not stated"]) {
    const { nodes } = render({ source_terms: MANIFEST.source_terms, corrections_url: absent });
    const texts = nodes.map((n) => n.textContent);
    assert.equal(nodes.filter((n) => n.tagName === "a").length, 0);
    assert.ok(texts.includes(NOT_STATED), `${JSON.stringify(absent)} did not render "not stated"`);
    assert.ok(texts.includes(NO_CHANNEL_NOTE), "absent and refused must read differently");
    assert.ok(!texts.includes(REFUSED_NOTE), "an absent value is not a refused one");
  }
});

test("a missing source_terms renders not stated rather than nothing", () => {
  // Silence is the thing the disclosure exists to prevent, so a manifest that
  // lost the field must still produce a visible gap rather than an empty box.
  const { nodes } = render({ corrections_url: MANIFEST.corrections_url });
  const texts = nodes.map((n) => n.textContent);
  assert.ok(texts.includes(SOURCE_TERMS_HEAD));
  assert.ok(texts.includes(NOT_STATED));
});
