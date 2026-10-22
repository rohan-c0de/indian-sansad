/* The source-terms disclosure in the footer. Owner decision 2026-10-10.
 *
 * The dataset is published WITHOUT a determination of the terms under which
 * the Lok Sabha publishes the underlying records, with that gap disclosed and
 * a corrections path offered. `manifest.json` carries both statements --
 * `source_terms` and `corrections_url` -- and this module renders them.
 *
 * Both values are READ FROM THE MANIFEST AT RUNTIME. Neither is typed into the
 * page, for the same reason the licence is not: there would then be two
 * definitions, and the one on screen would be the one nobody re-measures.
 * `tests/unit/test_page_fetch_layer.py` asserts no page file contains either
 * published value as a literal.
 *
 * ## Why `corrections_url` gets a scheme check and `project_url` did not
 *
 * Both come from the same trusted module. The difference is what a wrong value
 * costs: `project_url` is a link to this project, while `corrections_url` is
 * the channel a RIGHTSHOLDER is told to use, so it is the one link on the page
 * a reader is being directed to act on. A published string reaching `href`
 * unchecked is also the one place on this page where a value from a file could
 * become executable -- `href="javascript:..."` runs on click, and no amount of
 * `textContent` discipline elsewhere prevents it. So the href is set only for
 * an `https://` value, and anything else is displayed as text with the reason.
 * It is a cheap invariant on the page rather than a theory about the writer.
 */

import { isMissing, stated } from "./format.js";

/** The headings. Exported so the test asserts the rendered text, not a guess. */
export const SOURCE_TERMS_HEAD = "Terms of the underlying records";
export const CORRECTIONS_HEAD = "Corrections and removal requests";

/** Shown instead of a link when the manifest states no channel at all. */
export const NO_CHANNEL_NOTE = " — the published manifest does not state one";

/** Shown instead of a link when the value is not an https URL. */
export const REFUSED_NOTE =
  " — not linked: the published value is not an https URL";

/**
 * The href to use for a URL read from a published file, or `null`.
 *
 * `https://` only, as an exact prefix. Not a parse: a scheme-relative `//host`
 * inherits the page's scheme, `http://` is a downgrade, and `javascript:`
 * executes -- all three are refused by the same rule, and a rule that reads
 * literally is one a reviewer can check without running it.
 */
export function safeHttpsHref(value) {
  if (typeof value !== "string") return null;
  return value.startsWith("https://") ? value : null;
}

/**
 * The disclosure, as a fragment to append to the footer's licence box.
 *
 * `doc` is passed in rather than read from the global, so this renders under
 * Node's test runner against a recording document and the assertions are about
 * the nodes actually produced.
 */
export function renderDisclosure(doc, manifest) {
  const node = (tag, className, text) => {
    const element = doc.createElement(tag);
    if (className) element.className = className;
    // textContent, never innerHTML. These strings are this project's own, but
    // the rule on this page is that no published value reaches markup.
    if (text !== undefined && text !== null) element.textContent = String(text);
    return element;
  };

  const frag = doc.createDocumentFragment();

  frag.append(node("p", "licence-head", SOURCE_TERMS_HEAD));
  frag.append(node("p", "licence-scope", stated(manifest.source_terms)));

  frag.append(node("p", "licence-head", CORRECTIONS_HEAD));
  const list = node("ul", "licence-links");
  const item = node("li");
  const url = manifest.corrections_url;
  const href = safeHttpsHref(url);

  if (href) {
    const link = node("a", null, href);
    link.href = href;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    item.append(link);
    item.append(node("span", "licence-links-note", " (opens in a new tab)"));
  } else {
    item.append(node("span", null, stated(url)));
    item.append(
      node("span", "licence-links-note", isMissing(url) ? NO_CHANNEL_NOTE : REFUSED_NOTE),
    );
  }

  list.append(item);
  frag.append(list);
  return frag;
}
