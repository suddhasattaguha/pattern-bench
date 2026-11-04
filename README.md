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
- Blocks dock via interlocking puzzle-piece silhouettes. When two blocks
  share a connector type at the touching ports (e.g. both have a "process"
  icon there), the icons fuse into one shared icon instead of showing two.
- Dashed **asset-boundary** rectangles show which platform/asset owns which
  part of the flow. API and File connectors are modeled as fixed, permanent
  thresholds (they sit at the edge of their box); Process and Topic
  connectors are modeled as genuinely internal/shared, so their boundary
  extends into the neighboring block to fully enclose the icon once merged.
- Dragging any block moves the whole assembled flow together.
- **Undo / Redo** (toolbar, or Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z) covers every
  flow change: add, delete, move, rename, clear and import.
- **Export / Import** saves the flow as a small JSON file and loads it back
  (see *Flow file format* below). Imports are validated: unknown patterns or
  blocks that don't fit together are rejected with a message.
- A second palette, **Versioned Artifacts**, is a 2×2 grid: rows are
  Entry-Route / Exit-Route, columns are Internal / process change and
  External / contract change. It currently holds four versioned blocks for
  API-to-Process (two per Entry quadrant); Exit quadrants are still empty.
- **Versioned copy.** Dropping a versioned block onto its base block splits
  the canvas: base flow on top, a versioned copy in the bottom half,
  block-for-block aligned. The copy is linked, not cloned — it's re-derived
  from the base flow plus the applied versions, so renaming, moving or
  deleting a base block is mirrored in the copy (deleting a base block also
  drops its version). Select a versioned block in the copy and press
  Delete (or ×) to remove that version; with no versions left the split
  closes.
- **Version roles** inside a versioned block: solid violet halo + filled
  `v2` badge = the object that actually changed; dashed violet halo +
  outlined `v2` badge = versioned as a side-effect; faded icon + dotted link
  = retired v1 link. A legend sits in the copy pane.

## Current base patterns

| Block | Route | Entry connector | Exit connector |
|---|---|---|---|
| API-to-Process | Entry | API | Process |
| File-to-Process | Entry | File (SFTP-style folder pickup) | Process |
| Consume-to-Process | Entry | Topic/Queue | Process |
| Consume-to-Publish | Entry | Topic/Queue | Topic (relay) |
| API-to-Publish | Entry | API | Topic |
| Process-to-Publish | Exit | Process | Topic |
| Process-to-API | Exit | Process | API |
| Process-to-File | Exit | Process | File |
| Consume-to-API | Exit | Topic/Queue | API |

The bridge patterns (Consume-to-Publish, API-to-Publish, Consume-to-API)
connect two real-world touchpoints directly, with no separate processing
step called out. Route classification (Entry vs. Exit) is a purely visual
grouping in the palette — it doesn't affect docking compatibility, which is
always driven by `entryType`/`exitType` matching regardless of `route`.

## Architecture notes (for whoever picks this up next)

Everything lives in one `<script>` block inside `pattern-bench.html`.

- **Templates**: each block is a plain object — `id`, `label`, `route`
  (`entry`/`exit`), `entryType`/`exitType` (the connector type at each
  port — `api`, `file`, `topic`, `process`), `size`, `color`, and a
  `diagram(w, h, color)` function that returns the block's inner SVG markup.
- **Rendering**: a block's outer shape is a puzzle-piece path
  (`puzzlePath` — concave notch on the entry edge, convex tab on the exit
  edge) with the template's `diagram` output layered inside it
  (`buildBlockMarkup`).
- **Merging** (`tryMergeIcons`): when two blocks dock and share an icon type
  at the touching ports, one side is chosen as the "owner" (survives,
  permanent) and the other fades entirely. API/File types are anchor-based
  (entry side always owns); Process/Topic types use a `data-boundary`
  ownership flag baked into specific templates (e.g. API-to-Process owns
  the shared "process" icon over Process-to-Publish).
- **Edge-fixed vs. sliding icons**: API/File icons (`data-fixed="true"`)
  always sit exactly at the block's physical edge and never move — their
  asset-boundary box is a fixed, permanent rectangle. Process/Topic icons
  live inset by default and slide to straddle the seam on merge
  (`data-half-x`/`data-half-y` give each icon's own geometry for that
  calculation); their owning box extends past the block's true edge by
  that icon's half-width so it still fully encloses the icon post-merge.
- **z-boost**: whichever block currently owns a merged icon gets a
  temporary `z-boost` class (higher z-index) so its icon/box can never be
  visually covered by whichever neighboring block happens to paint later in
  DOM order. This was a real, verified bug (see Development History) —
  don't remove this without re-testing the occlusion case.
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
- `versions` (optional) lists the versioned blocks applied in the copy:
  `block` is an index into `blocks`, `variant` must belong to that block's
  pattern.

## Tests

`tests/test_history_io.py` (Python Playwright) builds a flow and checks
undo/redo, drag, rename, delete, export → clear → import (pixel-identical),
and rejection of bad files: `python3 tests/test_history_io.py`.
`tests/test_versioning.py` covers the versioned palette and copy (create,
replace, mirror on rename/move/delete, undo, export/import, in-app confirm):
`python3 tests/test_versioning.py`.

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
