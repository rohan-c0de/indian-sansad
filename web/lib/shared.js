/* Everything more than one view needs. T136.
 *
 * This module exists because of a cycle that the obvious split would have
 * created. `app.js` loads each view with `import()` on first use (FR-128), so
 * if the views imported their shared helpers back out of `app.js` the graph
 * would be `app -> view -> app`. ES modules tolerate a cycle, but a cycle
 * through a DYNAMIC import is the fragile kind: the view's static import of
 * `app.js` would re-enter a module that is still evaluating, and which of its
 * bindings are initialised depends on evaluation order rather than on
 * anything written down.
 *
 * So the shared layer moved DOWN into `lib/` instead of staying in the shell,
 * and the dependency graph is acyclic by construction:
 *
 *     app.js  -> lib/shared.js -> lib/{format,profile,chart}.js
 *     views/* -> lib/shared.js -> ...
 *
 * Nothing here renders a view. Each function is either a DOM primitive, a
 * control, a figure/table treatment, or the one piece of cross-view state
 * (`views`), which holds reference data two views both read so it is fetched
 * once between them.
 */

import { CrossOriginRefused } from "./fetch.js";
import { NOT_STATED, count, isMissing, percent, stated } from "./format.js";


export function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

export function replaceChildren(node, ...children) {
  node.replaceChildren(...children);
}

/** A labelled figure with the sentence that says how it was counted. */
export function fact(label, value, note) {
  const wrap = el("div", "fact");
  wrap.append(el("p", "fact-label", label), el("p", "fact-value", value));
  if (note) wrap.append(el("p", "fact-note", note));
  return wrap;
}

export function list(className, items, render) {
  const ul = el("ul", className);
  for (const item of items) {
    const li = el("li");
    render(li, item);
    ul.append(li);
  }
  return ul;
}








export function renderUnavailable(container, message, detail) {
  const box = el("div", "unavailable");
  box.append(el("p", "unavailable-head", "This could not be read"));
  box.append(el("p", null, message));
  if (detail) box.append(el("p", "unavailable-detail", detail));
  box.append(
    el(
      "p",
      "unavailable-note",
      "Nothing above is estimated or filled in. The published files are still " +
        "downloadable directly.",
    ),
  );
  replaceChildren(container, box);
  container.dataset.state = "error";
}

export function describe(error) {
  if (!error) return "";
  if (error instanceof CrossOriginRefused) {
    return `${error.name}: ${error.message}`;
  }
  return `${error.name || "Error"}: ${error.message || String(error)}`;
}

/** Everything the two views read. Fetched once, shared. */
export const views = {
  rows: [],
  ministries: [],
  /** The FULL ministry reference, by id. T079 resolves a result's
   * `ministry_id` through this: a question can be put to a ministry that has
   * no row in the profile aggregate for the selected span. */
  ministryNames: new Map(),
  sessions: [],
  basis: [],
  ready: false,
};


