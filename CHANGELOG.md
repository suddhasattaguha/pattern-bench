# Changelog

This is a milestone-level reconstruction of the working session that
produced this tool, written up for context. It's organized as logical
stages, not literal commits — from this point forward, commits should be
one logical change each with a real diff behind them.

## Stage 1 — Canvas foundation
- Basic HTML/CSS/JS framework: infinite pan/zoom canvas, quadrant-style
  component palette, drag-and-drop block placement, block selection,
  deletion, inline label renaming.

## Stage 2 — First real blocks and puzzle-piece docking
- Replaced generic placeholder blocks with the first real pattern,
  API-to-Process, rendered as an interlocking puzzle-piece silhouette
  (concave notch on entry, convex tab on exit) instead of a plain
  rectangle, so two docked blocks read as one continuous shape.
- Added Process-to-Publish, and the first version of icon fusion: when two
  blocks share a "process" icon at the touching ports, they merge into a
  single shared icon instead of showing two side by side.

## Stage 3 — Asset boundaries
- Introduced dashed "asset boundary" rectangles to show which
  platform/asset a component belongs to.
- Added Consume-to-Process (two boundaries in one block — a broker
  asset and an independent processing asset) and Process-to-API, completing
  a 4-block end-to-end chain.
- Multiple rounds of visual refinement: per-icon arrowheads showing flow
  direction, port indicators that disappear once merged, a tapered
  "home-plate" icon shape for API touchpoints (entry point always tapered,
  exit point flat), and keeping every icon fully contained within its own
  block's shell rather than overflowing it.

## Stage 4 — Root-causing a real rendering bug
- Diagnosed and fixed a genuine z-order/stacking bug: a merged icon or its
  boundary box could be visually painted over by whichever neighboring
  block happened to be later in paint order, depending purely on the order
  two blocks were dragged onto the canvas. Fixed with a temporary z-index
  boost ("z-boost") applied to whichever block currently owns a merged
  icon. Verified with automated headless-browser pixel tests (forcing a
  neighbor to a bright test color and confirming the icon still rendered
  on top), not just visual inspection.
- Settled the final asset-boundary model: API/File-type connectors are
  fixed, permanent thresholds that sit at the edge of their box; Process/
  Topic-type connectors are genuinely internal/shared, so their owning box
  extends past the block's physical edge to fully enclose the icon once it
  slides to the seam on merge.

## Stage 5 — Guided flow-builder mode
- Reframed the canvas from a free-form sandbox into a constrained,
  single-flow builder: the palette greys out any block that can't extend
  the current flow's two open ends; dropping a compatible block anywhere on
  the canvas auto-docks it to the correct end; dragging any block moves the
  whole assembled flow together; only one end-to-end flow can exist on the
  canvas at a time.

## Stage 6 — Broader base palette + versioning framing
- Reframed the tool's actual purpose: composing a base flow is step one,
  in service of a later step — evaluating the versioning impact of a block
  change on its upstream/downstream neighbors.
- Added a second, currently-empty "Versioned Artifacts" palette (own tab,
  own quadrant shell) reserved for that future phase.
- Added File-to-Process and Process-to-File (a folder-with-a-file icon,
  representing an SFTP-style pickup/drop), rounding the base palette out to
  three Entry-Route and three Exit-Route blocks.
- Simplified the base palette's categorization from a 2×2 quadrant
  (Entry/Exit × External/Internal) down to a plain two-column Entry-Route /
  Exit-Route split.

## Open for next session
- Design the Versioned Artifacts palette's axes and block set.
- Design how a versioned-artifact block attaches to a base-flow block.
- Add persistence (export/import, or `window.storage` if hosted as an
  artifact).
