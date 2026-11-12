# Pattern Bench

A browser-based, drag-and-drop canvas for composing integration message-flow
patterns ("lego blocks") and — the actual end goal — evaluating how a
version change to any one block ripples upstream and downstream through an
end-to-end flow.

Single HTML file, zero dependencies, zero build step. Open
`pattern-bench.html` in any modern browser.

## What it does today

- An infinite, pannable, zoomable canvas (SVG + HTML hybrid).
- A dark/light theme toggle in the toolbar (in-memory only — resets to dark
  on reload, since artifacts can't use localStorage).
- A **Base Flow Design** component library, organized into two columns:
  Entry-Route and Exit-Route. Dragging a compatible block onto the canvas
  auto-docks it to the correct open end of the flow — no manual positioning.
- The palette is **compatibility-aware**: once a flow exists, only blocks
  that can actually extend one of its two open ends stay draggable; every
  other block greys out. The canvas is deliberately restricted to composing
  **one** end-to-end flow at a time.
- Blocks are arrow-shaped tiles (notch on the entry side, point on the exit
  side) that nest into each other, so the shape itself shows the flow
  direction. The connector two blocks share sits once, on the join.
- **Symbol shape = connector type**: API (tapered plate), Process (cog in a
  hexagon), Topic (one-to-many fan-out), Queue (pipe with waiting
  messages), File (folder with a file).
- **Colour = platform owner**: teal for iPaaS, amber for Message Broker,
  grey for external. A soft band in the owner's colour sits behind
  everything that platform owns (this replaces the dashed boundary boxes).
- One solid flow line runs through the whole flow.
- Dragging any block moves the whole assembled flow together.
- **Undo / Redo** (toolbar, or Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z) covers every
  flow change: add, delete, move, rename, clear and import.
- **Export / Import** saves the flow as a small JSON file and loads it back
  (see *Flow file format* below). Imports are validated: unknown patterns or
  blocks that don't fit together are rejected with a message.
- **Start from a description**: type e.g. "file to API" or "API to API via
  event" above the library. Plain keyword rules (no AI at runtime) find every
  end-to-end route between the two end applications; the library shows only
  the blocks on those routes, and if exactly one block can start them it is
  placed on an empty canvas. Unrecognised text changes nothing and offers
  clickable end-to-end examples; a topic is never a start or an end.
- A second palette, **Versioned Artifacts**, is a real 2×2 grid with its
  axes labelled: rows Entry route / Exit route, columns Internal (process
  change) / External (contract change). Only the versions of blocks in the
  flow are shown; an empty quadrant says "Nothing for this flow". All 8 base
  blocks have versions (27 in total).
- **Versioned copy.** Dropping a versioned block onto its base block creates
  a versioned copy, block-for-block aligned with the base. The mode decides
  which view gets the whole canvas: in versioning mode (Versioned Artifacts
  tab) the copy is big and the base is a small reference window at the top
  right; in Base Flow Design the base is big and the copy sits in a small
  window at the bottom right. Clicking the small window swaps the views (and
  the library tab). The copy is linked, not cloned — it's re-derived
  from the base flow plus the applied versions, so renaming, moving or
  deleting a base block is mirrored in the copy (deleting a base block also
  drops its version). Select a versioned block in the copy and press
  Delete (or ×) to remove that version; with no versions left the copy
  and its small window close.
- **Version roles** inside a versioned block (violet is used for
  versioning only): solid violet symbol + filled `v2` badge = the object
  that actually changed; dashed violet outline + outlined `v2` badge =
  versioned as a side-effect; grey dotted link = retired v1 link. A legend
  sits in the copy pane.
- **Building at either end**: a block that fits both open ends goes to the
  end you drop it nearer. Or select the first or last block first: the
  library then shows only what fits that end, and dropped blocks attach
  there.
- **Platform containers**: each asset (a run of connectors on one platform)
  gets an outer frame behind the tiles, labelled with its type. Click the
  label to set platform and asset name. End applications (target API, SFTP
  folders) have a dashed frame.
- **Click to version** (in versioning mode — the Versioned Artifacts tab): click a connector (API, process, topic, queue,
  file) to highlight the versions that change it; for a connector on a join,
  choose upstream or downstream in the card, then drag a highlighted version
  anywhere onto the canvas.
- **Dependencies**: neighbouring blocks share a connector, so a version
  that brings a new version of it (e.g. Process v2) opens a decision on the
  direct neighbour, upstream or downstream. The neighbour turns amber in the
  copy, a card next to it asks how it should handle the change and offers
  the matching versioned blocks, and the library marks them Suggested.
  Suggestions are the neighbour's versions in which that new connector
  version is the changed object. "Decide later" keeps it as a pending mark.
  The chain beyond the direct neighbour is deliberately not followed yet.
- **Ripple of a contract change**: a contract version that keeps a shared,
  unchanged process (e.g. "New API v2 · shared Process", "same Queue
  subscribes to both", "Target API v2 · same Process") hands the new schema
  to that process. The neighbour sharing it is asked, in either direction:
  **Absorb here** (a code change in the same version, marked `v1 Δ`; the
  ripple stops) or **Pass it on**, followed by "does the process need a code
  change?". Passed on, the change lands on what lies beyond: an end
  application's API or folder gets **⚠ dependent logic**, an exposed API
  flags its callers, and a topic opens a version decision on that block.
  One step at a time; answered questions show as a pill (click to change).
- **Calling application**: placing an exposed API (API-to-Process /
  API-to-Publish) at the start asks whether an end application calls it.
  Yes adds a CALLER container joined to the API; a new version of the API,
  or a ripple reaching it, flags the caller. Answered No? Click the API's
  open left side to add it later. Adding a block in front removes it.
- **Ripple forecast**: for every contract change, a band above the copy
  shows how far it could travel. A toggle switches between **Best case**
  (absorbed at the first process) and **Worst case** (reaches the end
  application or caller), with blocks, assets and owner boundaries counted.
  A worst case validated as not happening can be dismissed; then only the
  best case stays.
- **Independent panes**: the base flow and the versioned copy pan and zoom
  separately (drag or scroll inside either one). The toolbar's zoom buttons
  act on the pane touched last; Reset view re-aligns both.
- **Resizable library**: drag the library's right edge to widen it. Cards
  keep their size and wrap, so a wider library shows more cards per row;
  double-click the edge to reset.

## Current base patterns

| Block | Route | Entry connector | Exit connector |
|---|---|---|---|
| API-to-Process | Entry | API | Process |
| File-to-Process | Entry | File (SFTP-style folder pickup) | Process |
| Consume-to-Process | Entry | Topic/Queue | Process |
| API-to-Publish | Entry | API | Topic |
| Process-to-Publish | Exit | Process | Topic |
| Process-to-API | Exit | Process | API |
| Process-to-File | Exit | Process | File |
| Consume-to-API | Exit | Topic/Queue | API |

The bridge patterns (API-to-Publish, Consume-to-API)
connect two real-world touchpoints directly, with no separate processing
step called out. Route classification (Entry vs. Exit) is a purely visual
grouping in the palette — it doesn't affect docking compatibility, which is
always driven by `entryType`/`exitType` matching regardless of `route`.

## Architecture notes (for whoever picks this up next)

Everything lives in one `<script>` block inside `pattern-bench.html`.

- **Templates**: each block is a plain object — `id`, `label`, `route`
  (`entry`/`exit`), `entryType`/`exitType` (the connector type at each
  port — `api`, `file`, `topic`, `process`) and `size`.
- **Rendering**: a block element is only its tile (`tilePath`) and label.
  Everything on top — the flow line, connector symbols, platform bands,
  version badges — is drawn by one flow-level renderer:
  `buildFlowModel()` turns the chain into stations (one per connector,
  shared connectors appear once) and `renderFlowLayer()` draws them into a
  single SVG layer per pane. There is no per-block icon merging or z-order
  juggling any more; the layer is simply re-rendered after every change.
- **Templates** describe their connectors as data (`entry`, optional
  `mid`, `exit`, each with a `type` and an `owner` platform) instead of a
  drawing function.
- **Chain model**: `chainOrder` is the single flow's blocks, left to right.
  `getChainOpenRequirements()` reads the two open ends' required connector
  types; `isTemplateCompatible()` / `refreshPaletteAvailability()` drive the
  palette greying; `attachToChain()` docks a dropped block onto the correct
  end regardless of where it's dropped.

## Flow file format (v1)

```json
{
  "format": "pattern-bench-flow",
  "version": 1,
  "origin": { "x": 150, "y": 260 },
  "blocks": [
    { "pattern": "api-to-process",     "label": "Order API" },
    { "pattern": "process-to-publish", "label": "Process-to-Publish" }
  ],
  "buildOrder": [0, 1],
  "versions": [ { "block": 0, "variant": "a2p-process-switch" } ],
  "savedAt": "2026-11-03T21:30:00.000Z"
}
```

- `blocks` are in left-to-right flow order; `pattern` is a template id.
- `origin` is the leftmost block's position; every other position follows
  from docking.
- `buildOrder` (optional) is the order blocks were added, as indices into
  `blocks`. It's replayed on load so merged seam icons come out exactly as
  they were. If omitted, blocks are added left to right.
- `containers` (optional) lists container names: `block` index, `at`
  (`in`, `out` or `m0`… for the connector), `platform`, `asset`.
- `versions` (optional) lists the versioned blocks applied in the copy:
  `block` is an index into `blocks`, `variant` must belong to that block's
  pattern.
- `caller` (optional, boolean): the first block's exposed API has a calling
  application (its name is a `containers` entry with `at: "caller"`).
- `ripples` (optional): answered ripple questions — `block` (the source
  version's block), `choice` (`absorb` | `pass`), `code` (true | false | null).
- `dismissedWorstCase` (optional): block indices whose worst-case forecast
  was dismissed.

## Tests

`tests/test_history_io.py` (Python Playwright) builds a flow and checks
undo/redo, drag, rename, delete, export → clear → import (pixel-identical),
and rejection of bad files: `python3 tests/test_history_io.py`.
`tests/test_versioning.py` covers the versioned palette and copy (create,
replace, mirror on rename/move/delete, undo, export/import, in-app confirm):
`python3 tests/test_versioning.py`.
`tests/test_dependency.py` covers the dependency decisions:
`python3 tests/test_dependency.py`.
`tests/test_canvas_tools.py` covers building at either end, containers,
click-to-version and the Consume-to-Process versions.
`tests/test_layout.py` covers independent pane pan/zoom and the resizable
library: `python3 tests/test_layout.py`.
`tests/test_ripple.py` covers the ripple questions and markers, the calling
application, the ripple forecast and starting from a description:
`python3 tests/test_ripple.py`.

## Known scope / next steps

- **Versioned blocks** exist only for API-to-Process so far; the other
  base blocks' versions are still to be defined. One versioned copy only.
- **Persistence is file-based** (Export / Import). Nothing is saved
  automatically; the canvas still resets on reload.
- **Deletion is end-only** by design: removing a block from the middle of
  the chain would split one flow into two, which the tool intentionally
  doesn't support, so it prompts to reset the whole flow instead.

## Development history

See `CHANGELOG.md`. It's a milestone-level reconstruction of one long
working session, not a literal commit-by-commit replay (intermediate file
states weren't preserved during that session) — real, granular version
history starts from this repository's first commit onward.
