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

## Stage 10 — Root-causing the "shortened boundary" artifact (v1.6)
- Finally diagnosed the boundary-box-looks-incomplete-after-merging issue
  that kept resurfacing: it was never a z-index/stacking bug (the z-boost
  mechanism from Stage 4 was working correctly the whole time). The real
  cause is a sub-pixel rendering quirk: a plain `stroke-width="1"` SVG line
  centered on an integer coordinate straddles two physical pixel rows at
  ~50% coverage each, so it always partially blends with whatever renders
  underneath, independent of z-index. Quantitatively verified with a
  forced-color test: the affected dashed line was rendering at an
  *effective* opacity of ~0.435 instead of its intended 0.85 — roughly
  half strength — which reads as a faded/incomplete box exactly where a
  box overshoots into a neighboring block.
  Fix: added `shape-rendering="crispEdges"` to the four border lines in
  `assetBox()`, which snaps them to a single full-coverage pixel row.
  Re-verified with the same forced-color technique: effective opacity is
  now ~0.855, matching the intended 0.85 almost exactly, on both the
  topic/queue (Message Broker) and process (iPaaS) merge cases.
- Elongated the single-icon nested boxes (used for non-owner Process/Topic
  icons showing standalone) from 50×52 to 62×52, for a more spacious,
  deliberate look even when only one icon is present.

## v1.7 — Undo/redo and JSON export/import
- Undo / Redo buttons and Ctrl+Z / Ctrl+Y (Ctrl+Shift+Z) over a snapshot
  history (100 steps) covering add, delete, move, rename, clear and import.
- Export the flow to `pattern-bench-flow.json`; Import validates format,
  version, pattern ids, seam compatibility and build order before loading.
- Reload replays the original build order so icon merges are identical
  (verified pixel-for-pixel against the original canvas).
- Fix: double-click to rename a block label never fired in v1.6 — the drag
  handler's pointer capture retargeted the double-click to the block.
- Added `tests/test_history_io.py` and a `window.__debug` test hook.
- Header version label updated (was still "v0.3").

## v1.8 — Versioned Artifacts palette and versioned copy
- Versioned Artifacts palette is now a 2×2 grid: Entry / Exit-Route ×
  Internal (process) / External (contract) change.
- Four versioned blocks for API-to-Process: New API v2 · own Process v2,
  New API v2 · shared Process (contract); New Process v2 · own API v2,
  New Process v2 · same API (process).
- Dropping a versioned block splits the canvas: base on top, linked
  versioned copy below, aligned block-for-block. The copy mirrors base
  renames, moves and deletions; versions can be replaced or removed.
- Role styling: changed (solid violet), side-effect (dashed violet),
  retired v1 link (dotted, faded); legend in the copy pane.
- Versions are included in undo/redo and in export/import (`versions`).
- Fix: Clear canvas did nothing in viewers that block the browser
  confirm() dialog. Replaced with an in-app confirmation (also used for
  the middle-block delete prompt).
- Added `tests/test_versioning.py` (30 checks).

## v1.9 — Visual redesign, independent panes, resizable library
- Blocks redrawn as arrow-shaped tiles that nest into each other; shared
  connectors sit once on the join; one flow line runs through the flow.
- New symbols: Process (cog in hexagon), Topic (fan-out), Queue (pipe with
  messages), File (folder with file). API keeps its v1.8 orientation.
- Colour now means platform owner (teal iPaaS, amber Message Broker, grey
  external), shown as soft bands that replace the dashed boundary boxes.
  Violet is reserved for versioning.
- Dot grid, larger labels, redesigned palette cards. Top toolbar unchanged.
- Rendering rewritten around a flow-level layer (`buildFlowModel` /
  `renderFlowLayer`); per-block icon merging and `z-boost` removed.
- Base flow and versioned copy pan and zoom independently; toolbar zoom
  follows the pane touched last; Reset view re-aligns both.
- Library panel is resizable by dragging its right edge (double-click to
  reset; width remembered where the browser allows it).
- Fix: a pane drag could be cancelled by the browser's text-selection drag
  and leave panning stuck on.
- Added `tests/test_layout.py` (19 checks).
