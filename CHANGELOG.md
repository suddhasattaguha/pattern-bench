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

## Stage 7 — Theme toggle + broader base palette (v1.3)
- Added a dark/light mode toggle button to the toolbar. All icon colors
  (fills, strokes, dashed asset-boundary lines) now route through CSS
  custom properties instead of hardcoded hex, so already-rendered blocks
  re-theme live without needing to regenerate any markup — verified this
  works by testing that SVG presentation attributes resolve `var()` at
  computed-style time. Theme state is in-memory only (artifacts can't use
  localStorage), so it resets to dark on reload.
- Added four new "bridge" pattern blocks that connect two real-world
  touchpoints directly, with no intermediate processing step called out:
  Consume-to-API, Consume-to-Publish (topic-to-topic relay), API-to-Publish,
  and File-to-API. Base palette is now 10 blocks, still split cleanly into
  Entry-Route / Exit-Route (the rule: Entry-Route if the block's entry
  connector is a real-world touchpoint — api/file/topic — Exit-Route if its
  entry connector is "process").

## Stage 8 — Palette cleanup (v1.4)
- Removed File-to-API (redundant bridge pattern for now — File-to-Process
  already covers the File connector's main use case).
- Reclassified Consume-to-API from Entry-Route to Exit-Route (purely a
  palette-grouping change; docking compatibility is unaffected, since that's
  driven by `entryType`/`exitType`, not `route`).
- Palette column headers (Entry-Route / Exit-Route) are now sticky — they
  stay pinned at the top of their column while the block list beneath
  scrolls, instead of scrolling away with the content.

## Stage 9 — Legibility labels (v1.5)
- Every asset-boundary box that contains a "process" icon now shows a tiny
  "iPaaS" subheader; every box containing a topic and/or queue icon shows
  "Message Broker". Boxes with only an API or File icon stay unlabeled
  (not requested).
- Every non-API icon now carries a small caption naming its role: gear ->
  "Process Flow", topic -> "Topic", queue -> "Queue", the folder icon ->
  "SFTP". (API already had its own "API" text baked into the home-plate
  shape, so it was left as-is per the request.) Captions are nested inside
  each icon's own `<g>`, same as the existing arrowheads and boundary
  boxes, so they travel, hide, and reappear correctly when icons merge.

