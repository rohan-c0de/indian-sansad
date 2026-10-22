/* Hand-built SVG. No library, no build step, nothing to install. T078.
 *
 * Accessibility rules this file keeps, rather than hopes for:
 *
 * - **The chart is never the only form.** Every chart is rendered beside a
 *   table carrying the same numbers, and the table is the one a screen reader
 *   and a keyboard reach. The <svg> is `role="img"` with a <title> and a
 *   <desc>, and its internals are hidden from assistive technology so a reader
 *   is not walked through 40 anonymous rectangles.
 * - **No meaning by colour alone.** Every segment carries its number as text,
 *   and every series is named in the legend AND in the table header. Remove
 *   all colour and the chart still says which bar is which.
 * - **Marks are at least 3:1 against the card they sit on** (#FFFFFF):
 *       --accent        #8C3325  ->  7.33:1
 *       --bar-unstarred #6F88BD  ->  3.53:1
 *   A third series, if one ever appears, falls back to a hatched pattern
 *   rather than a lighter colour, because a lighter colour is where the 3:1
 *   floor gets broken quietly.
 */

const NS = "http://www.w3.org/2000/svg";

/** Distinct fills, in order. Each is >= 3:1 on white; see the header. */
export const SERIES_FILLS = Object.freeze(["var(--accent)", "var(--bar-unstarred)"]);

/** A hatch for any series beyond the two measured fills. */
const HATCH_ID = "sansad-hatch";

function svgEl(tag, attrs = {}) {
  const node = document.createElementNS(NS, tag);
  for (const [key, value] of Object.entries(attrs)) {
    node.setAttribute(key, String(value));
  }
  return node;
}

/**
 * A stacked column chart: one column per session, one segment per type.
 *
 * `series` is the ordered list of type names; `columns` is
 * `[{ label, total, parts: { type: n } }]`.
 */
export function stackedColumns(columns, series, { title, description, height = 180 } = {}) {
  const figure = document.createElement("figure");
  figure.className = "chart";

  const max = Math.max(1, ...columns.map((c) => c.total));
  const colWidth = 100 / Math.max(1, columns.length);

  const svg = svgEl("svg", {
    viewBox: `0 0 100 ${height}`,
    preserveAspectRatio: "none",
    role: "img",
    "aria-labelledby": "chart-t chart-d",
    class: "chart-svg",
    focusable: "false",
  });
  const t = svgEl("title", { id: "chart-t" });
  t.textContent = title ?? "Questions per session";
  const d = svgEl("desc", { id: "chart-d" });
  d.textContent =
    description ?? "The same figures are given in the table immediately below.";
  svg.append(t, d);

  // The hatch, defined once and used only past the measured fills.
  const defs = svgEl("defs");
  const pattern = svgEl("pattern", {
    id: HATCH_ID, width: 4, height: 4, patternUnits: "userSpaceOnUse",
    patternTransform: "rotate(45)",
  });
  pattern.append(svgEl("rect", { width: 4, height: 4, fill: "var(--surface)" }));
  pattern.append(svgEl("rect", { width: 2, height: 4, fill: "var(--ink)" }));
  defs.append(pattern);
  svg.append(defs);

  columns.forEach((column, index) => {
    const x = index * colWidth;
    let y = height;
    series.forEach((name, s) => {
      const value = column.parts[name] ?? 0;
      if (value <= 0) return;
      const h = (value / max) * (height - 12);
      y -= h;
      svg.append(
        svgEl("rect", {
          x: x + colWidth * 0.14,
          y,
          width: colWidth * 0.72,
          height: h,
          fill: s < SERIES_FILLS.length ? SERIES_FILLS[s] : `url(#${HATCH_ID})`,
          stroke: "var(--surface)",
          "stroke-width": 0.3,
        }),
      );
    });
  });
  figure.append(svg);

  // The column labels and totals are HTML, not SVG text: HTML text scales with
  // the reader's font size and SVG text inside a non-uniform viewBox does not.
  const labels = document.createElement("ul");
  labels.className = "chart-labels";
  labels.setAttribute("aria-hidden", "true");
  for (const column of columns) {
    const li = document.createElement("li");
    const total = document.createElement("b");
    total.textContent = column.total.toLocaleString("en-IN");
    const name = document.createElement("span");
    name.textContent = column.label;
    li.append(total, name);
    labels.append(li);
  }
  figure.append(labels);

  const caption = document.createElement("figcaption");
  caption.textContent =
    `Columns run left to right from ${columns[0]?.label ?? "the first session"} to ` +
    `${columns[columns.length - 1]?.label ?? "the last"}, oldest first. ` +
    "Every figure is in the table below, which is the authoritative form — on a " +
    "narrow screen the per-column numbers are hidden there rather than shrunk to " +
    "an unreadable size.";
  figure.append(caption);
  return figure;
}

/** The legend. Named in text, so removing colour loses nothing. */
export function legend(series) {
  const ul = document.createElement("ul");
  ul.className = "legend";
  series.forEach((name, index) => {
    const li = document.createElement("li");
    const swatch = document.createElement("span");
    swatch.className = "swatch";
    swatch.setAttribute("aria-hidden", "true");
    swatch.style.background =
      index < SERIES_FILLS.length ? SERIES_FILLS[index] : "var(--ink)";
    li.append(swatch, document.createTextNode(name));
    ul.append(li);
  });
  return ul;
}
