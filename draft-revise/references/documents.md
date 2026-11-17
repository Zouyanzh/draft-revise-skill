# Documents and visual revision

## Source matching

Search relevant provided directories, not unrelated personal files. Inventory candidate sources plus bibliography, assets, fonts and styles. Compare title, sections, representative passages, formulas, page sizes and each affected location. Filename alone is not version evidence. Record `source_match` (`matched`/`partial`/`unmatched`) with checks and differences. Work on a source copy and supporting dependencies in a new edition directory; edit only matched material.

Ledger blocks describe actual saved revisions, not preferred future text. `implemented` changes must exist in a verified artifact. Label proposed blocks/pages and don't call them completed edits. Save a reliable revision as `_revised_vN`; mockups use `_proposal_vN`.

## PDF-only work

Reliable local edits may use a PDF editor or rebuild affected pages. Inspect renderings, underlying text, clipping, fonts, links and math. White rectangles over old text are not dependable semantic edits: old text may remain extractable or reappear. Do not deliver such overlays as a clean revised manuscript. Actual replacement/redaction must preserve surrounding content, including non-text elements.

If reflow or figures need unavailable source/data, show the original region and a labeled proposal, list missing materials, and complete independent work. Preserve size, hierarchy, major style and readability, allowing necessary reflow; explain material layout differences. No promises of pixel-exact reconstruction or visual verification without rendering.

## Paper/report

Reading view preserves order, sections, lists, tables, figures, references and math. Multiple exact anchors can share a block. Offsets are Unicode **code points**, not JavaScript UTF-16 indices, and preserve whitespace. Repeated words need explicit before/after context, occurrence or geometry; `locate` rejects ambiguity.

Build readable math from the matched TeX/structured source when possible, resolving references and retaining tables, figures and bibliography. Verify converter output and source glyphs; PDF text extraction is evidence, not a faithful math renderer. Do not ship `(cid:...)`, raw TeX or displaced indices in the reading view.

Optional rich HTML/native MathML must have the exact same decoded text as the plain `revised` field. Do not show raw TeX as rendered math. Use checked MathML for equation/symbol anchors, or use original/revised page regions for complex equations. Text offsets are validated before rendering, not rediscovered by the browser's first text match.

## Slides/visual content

Use `document.kind: slides`, page view, rendered original/revised images and normalized top-left rectangles. Preserve aspect ratio. Where useful link both snippet and region. Multiple locations per edit and comments per edit are supported. For non-text edits use `operation: visual`, before/after descriptions and page-region anchors.

Changes to graphs require actual data when conclusions depend on it. Missing data -> pending material, optionally a labeled sketch. Unrevised pages show original images explicitly marked original, never as revised. Editing native formats may use available document/presentation tooling; this skill is not a universal PDF-to-PPT converter.

## Verification

Confirm input hashes unchanged. Compile/export saved source copies, inspect every revised page for overflow, missing glyphs, overlap, unwanted reflow, misleading graphics and malformed math. Compare actual HTML and images with saved output. Record verification against artifact SHA-256 values. Structural validation cannot certify correctness, source version matching or PDF visual quality.
