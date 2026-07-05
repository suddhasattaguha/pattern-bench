# Pattern Bench

A browser-based, drag-and-drop canvas for composing integration message-flow
patterns ("lego blocks") and — the actual end goal — evaluating how a
version change to any one block ripples upstream and downstream through an
end-to-end flow.

Single HTML file, zero dependencies, zero build step. Open
`pattern-bench.html` in any modern browser.

## What it does today

- An infinite, pannable, zoomable canvas (SVG + HTML hybrid).
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
- A second palette, **Versioned Artifacts**, is scaffolded (empty, axes
  marked "TBD") — this is where the actual versioning-impact evaluation
  workflow will live once we design it.

## Current base patterns

| Block | Route | Connector |
|---|---|---|
| API-to-Process | Entry | API |
| File-to-Process | Entry | File (SFTP-style folder pickup) |
| Consume-to-Process | Entry | Topic/Queue |
| Process-to-Publish | Exit | Topic |
| Process-to-API | Exit | API |
| Process-to-File | Exit | File |

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

## Known scope / next steps

- **Versioned Artifacts palette** is an empty shell (`versionGrid` in the
  HTML). Still to design: its axes, its block set, and — most
  importantly — the interaction model for how a versioned-artifact block
  actually attaches to (replaces? sits alongside for comparison? annotates?)
  a block already in the base flow.
- **No persistence** yet. The canvas resets on reload. Worth considering a
  simple export/import of `chainOrder` state to JSON, or `window.storage`
  if this ends up hosted as a Claude artifact.
- **Deletion is end-only** by design: removing a block from the middle of
  the chain would split one flow into two, which the tool intentionally
  doesn't support, so it prompts to reset the whole flow instead.

## Development history

See `CHANGELOG.md`. It's a milestone-level reconstruction of one long
working session, not a literal commit-by-commit replay (intermediate file
states weren't preserved during that session) — real, granular version
history starts from this repository's first commit onward.
