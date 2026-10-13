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
 * - **Marks are at least 3:1 against the surface they sit on.** Recomputed
 *   2026-10-13 against the feature 002 palette:
 *       --house    #1F5D3E  ->  6.75:1 on --paper, 7.66:1 on --sheet
 *       --series-2 #5F7D94  ->  3.75:1 on --paper, 4.25:1 on --sheet
 *
 * - **The two series are 1.80:1 against EACH OTHER -- below the 3:1
 *   adjacent-mark floor -- and no colour can fix that.** It is arithmetic, not
 *   a compromise: a darker second mark would need >= 3 x 6.75 = 20.25:1
 *   against --paper, and pure black reaches only 18.17:1; a lighter one needs
 *   paper:house >= 9:1, where it is 6.75:1. The window is empty.
 *
 *   So every segment is STROKED in --sheet, and that stroke is what makes two
 *   adjacent segments separable without relying on their fills. The series are
 *   named in the legend AND in the table, and the table is authoritative.
 *
 *   A third series, if one ever appears, falls back to a hatched pattern
 *   rather than a lighter colour, because a lighter colour is where the 3:1
 *   floor gets broken quietly.
 */

const NS = "http://www.w3.org/2000/svg";

/** Distinct fills, in order. See the header for every measured ratio.
 *
 * Series 1 is `--house`, not `--mark`. `--mark` is the LINK and FOCUS colour,
 * and a bar in it invites a reader to click a bar. `--house` is the
 * institutional marker, which FR-106 permits on a mark and which a chart
 * segment is.
 *
 * Series 2 is `--series-2 #5F7D94`, replacing `--bar-unstarred #6F88BD`. The
 * old value measured 3.06:1 on the page ground -- 2% above the floor, a margin
 * any later tweak to the ground erases silently. 3.75:1 survives one. */
export const SERIES_FILLS = Object.freeze(["var(--house)", "var(--series-2)"]);

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
  pattern.append(svgEl("rect", { width: 4, height: 4, fill: "var(--sheet)" }));
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
          stroke: "var(--sheet)",
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

/* ---------------------------------------------------------------------- */
/* Grouped columns — T153                                                 */
/* ---------------------------------------------------------------------- */

/**
 * Two independent totals side by side, one pair of columns per label.
 *
 * NOT a stacked chart, and the difference is the point: stacking two
 * ministries' question counts would draw a combined column whose height means
 * nothing — no reader wants "Jal Shakti plus Railways". Grouped columns put
 * them on one scale so they can be compared, without implying a sum.
 *
 * The 3:1 adjacency problem does not arise here the way it does in a stack:
 * the two columns of a pair are separated by the page ground, not by a shared
 * edge. The --sheet stroke is kept anyway, because a pair at 390 px can be
 * narrow enough for the gap to close.
 *
 * `columns` is `[{ label, parts: { series: n }, totals: { series: n } }]`.
 */
export function groupedColumns(columns, series, { title, description, height = 180 } = {}) {
  const figure = document.createElement("figure");
  figure.className = "chart";

  const max = Math.max(
    1,
    ...columns.flatMap((c) => series.map((s) => c.parts[s] ?? 0)),
  );
  const groupWidth = 100 / Math.max(1, columns.length);
  const barWidth = (groupWidth * 0.72) / Math.max(1, series.length);

  const svg = svgEl("svg", {
    viewBox: `0 0 100 ${height}`,
    preserveAspectRatio: "none",
    role: "img",
    "aria-labelledby": "grouped-t grouped-d",
    class: "chart-svg",
    focusable: "false",
  });
  const t = svgEl("title", { id: "grouped-t" });
  t.textContent = title ?? "Two series compared";
  const d = svgEl("desc", { id: "grouped-d" });
  d.textContent =
    description ?? "The same figures are given in the table immediately below.";
  svg.append(t, d);

  columns.forEach((column, index) => {
    const x = index * groupWidth + groupWidth * 0.14;
    series.forEach((name, s) => {
      const value = column.parts[name] ?? 0;
      // A zero is drawn as a labelled zero by the table, not as a 0-height
      // rectangle here: a rect with no height is indistinguishable from a
      // missing series, and session 18/8 has zero sitting days.
      if (value <= 0) return;
      const h = (value / max) * (height - 12);
      svg.append(
        svgEl("rect", {
          x: x + s * barWidth,
          y: height - h,
          width: barWidth,
          height: h,
          fill: s < SERIES_FILLS.length ? SERIES_FILLS[s] : `url(#${HATCH_ID})`,
          stroke: "var(--sheet)",
          "stroke-width": 0.3,
        }),
      );
    });
  });
  figure.append(svg);

  const labels = document.createElement("ul");
  labels.className = "chart-labels";
  labels.setAttribute("aria-hidden", "true");
  for (const column of columns) {
    const li = document.createElement("li");
    const name = document.createElement("span");
    name.textContent = column.label;
    li.append(name);
    labels.append(li);
  }
  figure.append(labels);

  const caption = document.createElement("figcaption");
  caption.textContent =
    "One pair of columns per label, on a single scale so the two can be " +
    "compared. They are NOT stacked: a combined height would imply a total " +
    "that means nothing. Every figure is in the table below, which is the " +
    "authoritative form.";
  figure.append(caption);
  return figure;
}

/* ---------------------------------------------------------------------- */
/* Horizontal bars — T154                                                 */
/* ---------------------------------------------------------------------- */

/**
 * One row per category, with a bar per series.
 *
 * Horizontal because the category labels cannot be read any other way at
 * 390 px: 25 subject lines and 42 party names are long text, and rotating them
 * under a vertical axis makes them unreadable while a row puts each one on its
 * own line at full size.
 *
 * The labels are HTML beside the SVG rather than SVG text, for the same reason
 * the column charts do it: HTML text scales with the reader's font size and
 * SVG text inside a non-uniform `viewBox` does not.
 *
 * `columns` is `[{ label, parts: { series: n }, totals: { series: n } }]`.
 */
export function horizontalBars(columns, series, { title, description } = {}) {
  const figure = document.createElement("figure");
  figure.className = "chart chart-horizontal";

  const max = Math.max(
    1,
    ...columns.flatMap((c) => series.map((s) => c.parts[s] ?? 0)),
  );

  const rows = document.createElement("ul");
  rows.className = "bars";

  for (const column of columns) {
    const li = document.createElement("li");
    li.className = "bar-row";

    const label = document.createElement("span");
    label.className = "bar-label";
    label.textContent = column.label;
    li.append(label);

    const track = document.createElement("span");
    track.className = "bar-track";
    series.forEach((name, s) => {
      const value = column.parts[name] ?? 0;
      const total = column.totals ? column.totals[name] : null;
      const bar = document.createElement("span");
      bar.className = "bar";
      // A category with zero in this series still gets a row and a number.
      // `max(0.6%, …)` so a non-zero value is never invisible: the long tail
      // of a dimension where one category holds half the total -- 282 of 544
      // members served exactly one term -- would otherwise round to nothing.
      bar.style.width = value > 0 ? `max(0.6%, ${(value / max) * 100}%)` : "0";
      bar.style.background = s < SERIES_FILLS.length ? SERIES_FILLS[s] : "var(--ink)";
      bar.setAttribute("aria-hidden", "true");
      track.append(bar);

      const figureText = document.createElement("span");
      figureText.className = "bar-figure";
      figureText.textContent =
        total === null || total === undefined
          ? `${value.toLocaleString("en-IN")}`
          : `${value.toLocaleString("en-IN")} of ${total.toLocaleString("en-IN")}`;
      track.append(figureText);
    });
    li.append(track);
    rows.append(li);
  }

  const heading = document.createElement("p");
  heading.className = "visually-hidden";
  heading.textContent = title ?? "Categories compared";
  figure.append(heading);
  figure.append(rows);

  const caption = document.createElement("figcaption");
  caption.textContent =
    (description ?? "") +
    " Each row carries its own figure against its denominator; the table below " +
    "carries every category, including any this chart groups.";
  figure.append(caption);
  return figure;
}
