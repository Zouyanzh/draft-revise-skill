# Revision ledger contract

Use `scripts/draft_revise.py` with Python 3.9+. The JSON ledger is the editable record of decisions and saved output, not an automatic rewriting engine. All paths resolve relative to the ledger. Write each edition to new filenames; the tools refuse to overwrite outputs. Keep inventories, page images, sources, artifacts and ledger together or retain valid paths.

## Commands

```sh
python "$SKILL_DIR/scripts/draft_revise.py" extract draft-comments.pdf draft_inventory.json --images
python "$SKILL_DIR/scripts/draft_revise.py" extract review.pdf review_inventory.json --role review --images
python "$SKILL_DIR/scripts/draft_revise.py" init draft_inventory.json draft_revised_v1.json --kind paper --review-language zh-CN
python "$SKILL_DIR/scripts/draft_revise.py" locate paragraph.txt 'specific phrase' --before 'verified preceding text '
python "$SKILL_DIR/scripts/draft_revise.py" validate draft_revised_v1.json
python "$SKILL_DIR/scripts/draft_revise.py" verify-text draft_revised_v1.json draft_revised_v1.pdf
python "$SKILL_DIR/scripts/draft_revise.py" render draft_revised_v1.json draft_revised_v1.html
```

`SKILL_DIR` means the discovered installation folder, not a fixed personal path. `init` copies inventory comments and creates unresolved requirements; populate it before delivery. For flattened/independent reviews without annotation objects, add comments from verified page evidence manually. Keep all inventories in `inventories`; textual comments manually derived from an independent PDF are additional records, not missing annotation objects. Exclude non-editorial annotation objects only with recorded reasons.

## Fields

Top level: `schema_version: 1`, `document`, `inventories` (JSON paths), `comments`, `requirements`, `changes`, `blocks`, `pages`, `excluded_annotations`, `issues`, `verification`.

`document`: stable `id`, `title`, `kind` (`paper/report/slides/other`), original `language`, `review_language`, integer `version` starting at 1, unique `edition_id`, `source_pdf: {path, sha256}`, `source_match: {status, reason, checks?, differences?}`, and `artifacts`. Artifact: `{role, label, path, sha256}`; roles include `revised_pdf`, `revised_source`, `original_pdf`, `proposal`, `support`. Save hash values after saving files. An implemented change requires a revised artifact. For sources, record matched/partial/unmatched based on actual comparison; do not infer from names.

`comments`: immutable `id`, full `raw_text`, `author`, `text_origin`, `recognized_text`, `source: {path, sha256, page, rects?, image?}`. `image` is optional rendered comment-source evidence, particularly useful for handwriting and independent review PDFs; it is deduplicated and embedded in HTML. Pages start at 1; rects use normalized top-left coordinates. Extracted records also contain `annotation_type`, `annotation_ids`, `selected_text`, `members` and related annotation evidence. Preserve these. OCR/transcription has empty `raw_text` and nonempty `recognized_text`; also preserve page imagery. External extracted text uses `text_origin: external-extracted`. Never replace full raw text with a summary or a split requirement. Missing text in deletion markup is legitimate.

`requirements`: `id`, `comment_ids`, `kind` (`explicit/open/ambiguous/conflict`), `status` (`implemented/partial/needs_material/needs_decision`), `change_ids`, specific `reason`, and `needs` for unresolved items. Mixed comments split into explicit/open requirements; there is no separate mixed enum. Optional `evidence: [{kind, title, path?, url?, supports}]`. Every comment needs at least one requirement; every requirement has an outcome. Many-to-many links must be reciprocal.

`changes`: `id`, `title?`, `requirement_ids`, `operation` (`replace/insert/delete/visual/move`), `status`, minimal exact `original` and `revised` snippets (or accurate visual descriptions), `reason`, `anchors`, `original_anchors`, optional `depends_on` change IDs. Multiple anchors may span sentences/blocks/pages. Snippets describe the actual individual edit, not an entire related paragraph. For insertions original is empty; for deletions revised is empty. Specify restoration information for non-text edits in optional `restore` (source/region/style before the change). Mark semantic dependencies, not only geometric overlap.

Optional `review: {decision, note, carried_from?}` seeds a new edition with unchanged accepted decisions. Keep prior feedback in top-level `review_history`; reset changed edits to unreviewed.

For literal replacements/insertions add `explicit_checks: [{requirement_id, specified_text}]`; this must equal that change's revised text. If a single explicit operation has several distinct text replacements, create separate changes/checks. Agent verifies literal deletions, moves and visual formats against comment evidence as well. Do not auto-fix a suspected typo in specified text. Record `issues: [{id, change_ids?, requirement_ids?, problem, suggestion, adopted: false}]` instead.

`review_policy` (optional) defaults to `{explicit_default: "accept", completed_open: "retain_without_individual_review", review_only_pending: true}`. Use `explicit_default: "unreviewed"` only when the user requests manual confirmation; supplied `changes[].review` and valid local/imported feedback override defaults. This is a review preference, never execution status. Feedback is schema 2 only; see [HTML and feedback](review.md).

`blocks`: ordered reading content `{id, kind?, heading?, original, revised, html?, status?}`. `kind: heading` creates a heading. Include the **complete document**, even unchanged content; not just edited excerpts. Status defaults to revised, or is `original/proposal`. Optional rich `html` is restricted to safe formatting, tables and native MathML. Its decoded concatenated text must exactly equal `revised` (including whitespace). Native math text is a semantic text layer, so PDF comparison needs visual/formula verification. No embedded scripts, external fonts, SVG or event handlers. Use page regions for complex formulas/figures that cannot be faithfully reexpressed; keep the full pages accessible.

Heading blocks can set `heading_level: 1..6` and `toc_include: true` for the left directory. Use level 0 / `toc_include: false` for the document title. Local labels (Definition, Remark, Assumption, Theorem, Proof) remain in reading content but normally are not directory entries. Specify real hierarchy rather than inferring it from heading text. Optional `original_html` must decode exactly to `original`. A separate raster `image` file (PNG/JPEG/WebP) can accompany a figure block; it is embedded by the renderer, with optional `image_alt`. Do not put active image/SVG markup in block HTML.

For every implemented change, `original_anchors` identifies its verified pre-change location: a text range in `block.original`, an insertion `type: point` with equal start/end and empty quote, or a region with `side: original` in an original page image. This preserves which repeated occurrence was edited and enables safe restoration. Do not infer it later from the first matching word.

Text anchor: `{type: "text", block_id, start, end, quote}`. Ranges are half-open Unicode **code-point** offsets in `block.revised`, with `quote == revised[start:end]`. Python indexes directly; JS must use `Array.from`. `locate` refuses repeated ambiguous text unless verified context/occurrence is supplied. Anchors can overlap independently. A deletion uses `{type: "deletion", block_id, start, end: start, quote: ""}` at its original insertion boundary. For a whole deleted paragraph retain an empty block with full `original`; do not anchor to unrelated retained text.

`changes[].contexts` and `requirements[].contexts` (optional): checked pairs for per-edit fragments and complete sentences. Each context has `original`, `revised`, optional `comment_ids` (a subset of its owner’s comments), and optional `note`. The revised side always references an existing reading block; the original side references `block.original`, or carries detached source text and safe HTML when the original source unit differs from the revised reading block. All ranges are Unicode code points.

```json
{
  "contexts": [{
    "comment_ids": ["c1"],
    "original": {"block_id":"b1","focus":[4,7],"sentence":[0,14]},
    "revised": {"block_id":"b1","focus":[4,7],"sentence":[0,14]}
  }]
}
```

Alternatively an original side is `{text: "Use old label.", html: "Use old label.", focus: [4,7], sentence: [0,14]}`. Source text and decoded HTML must agree exactly; focus lies within the sentence and all offsets are bounded. Empty equal endpoints represent inserted/deleted boundaries. Omit `sentence` to derive a sentence envelope outside MathML. Do not relabel a whole sentence as this edit’s minimal snippet. Supply one context per actual location when an edit spans sentences or blocks. Different changes from a mixed comment need their own contexts. Never replace `changes[].original/revised` minimal snippets with entire sentence text merely for display.

When contexts are absent, the renderer derives pairs from verified text `original_anchors` and `anchors`; page geometry by itself cannot reconstruct revised textual context. For pending requirements, optional `anchors` uses the same text/region contract. If a pending `contexts` pair is supplied without anchors, its revised focus supplies an exact reading anchor. If precise text is unavailable use the original region; do not guess a revised sentence. The validator sanitizes all context HTML/ranges before it reaches the browser.

`pages`: `{id, number, label?, status, original_image?, revised_image?}` with PNG/JPEG/WebP images. Status original means unchanged evidence, revised means actual output, proposal means unimplemented layout. Region anchor: `{type: "region", page_id, side: "original"|"revised", rect: [left,top,right,bottom]}` where `0 <= left < right <= 1`. Validate geometry against rendered pages, including crops/rotation. A visual deletion can use its original region with accurate revised outcome. Do not place an original page under a revised label.

`excluded_annotations`: `[{comment_id, reason}]` for inventory objects that are not editorial comments. Do not count these as fulfilled requirements. Report both raw annotation member count and logical comment count when useful. Replacement insertion/deletion members count once; popup windows count zero.

`verification`: agent records checks, results, artifact SHA-256 and limitations (PDF page visual inspection, source unchanged, text consistency, HTML viewports/links/offline/feedback). The validator checks structure, hashes, reciprocal links, exact ranges, original evidence, explicit text and dependency cycles. It cannot judge interpretation, full-document completeness, output truth, source equivalence or layout. Inspect those separately.

## Minimal linked edit example

These are fragments to populate an initialized ledger, not a standalone valid file:

```json
{
  "requirements": [{"id":"r1","comment_ids":["c1"],"kind":"explicit","status":"implemented","change_ids":["m1"],"reason":"Applied the exact replacement."}],
  "blocks": [{"id":"b1","original":"Use old label.","revised":"Use new label."}],
  "changes": [{"id":"m1","requirement_ids":["r1"],"operation":"replace","status":"implemented","original":"old","revised":"new","reason":"Uses the specified label.","original_anchors":[{"type":"text","block_id":"b1","start":4,"end":7,"quote":"old"}],"explicit_checks":[{"requirement_id":"r1","specified_text":"new"}],"anchors":[{"type":"text","block_id":"b1","start":4,"end":7,"quote":"new"}]}]
}
```
