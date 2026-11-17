# Comment handling

## Extraction is evidence, not interpretation

`extract` preserves annotation IDs, exact `/Contents`, rich contents, author, type, relations, page coordinates, selected text and page text. Popup annotations are excluded. A strikeout associated with an insertion through `/IRT` is one replacement; arbitrary replies are not replacements. Rectangles use normalized **top-left** page coordinates; pdfplumber handles page geometry. Check rendered evidence for unusual rotation/crops. A missing selected string needs visual inspection, not omission.

The inventory includes non-popup highlights, ink, shapes, replies, links and stamps. Classify non-editorial objects explicitly in `excluded_annotations` with a reason; do not silently discard unclear marks. Replacement members share one comment ID; replies retain their relationship. Exact embedded comment text is immutable.

Flattened/scanned comments may have no annotation records. Inspect pages and attempt OCR/visual transcription; record `text_origin: ocr` or `transcription`, `recognized_text`, and source page/region. Keep `raw_text` empty when no embedded original exists. Mark unclear wording/locations pending. Highlight or circles alone do not inherently mean delete or rewrite.

For independent review PDFs identify individual comments from page text/renderings. Stable IDs derive from review file identity and recorded region/text range. Preserve full comments, reviewer headings and quote context; match against the draft using page/section/quoted text plus surrounding context. Global comments may target multiple locations or a described global task. Unmatched requirements still need a disposition.

## Classification

- “Replace A with B”; “delete sentence 2”; “make the axis label 14 pt” -> explicit.
- “The motivation is unclear”; “explain the distinction”; “make the slide less crowded” -> open.
- “Delete sentence 1 and strengthen the explanation” -> explicit + open requirements under one original comment.
- “Add an ablation proving X” -> evidence-dependent; propose/perform only authorized supported work. A writing task does not justify claiming experiments happened.
- Exact sentence with typo -> use verbatim, issue `suspected_language_error`, proposed correction separate with `adopted: false`.
- Conflicting reviewers/requested false statement -> original retained, `needs_decision`, concrete options and rationale.

Execution states: `implemented` = revision actually exists; `partial` = only part exists; `needs_material` = missing inputs/evidence; `needs_decision` = ambiguity/conflict. Suggestions are not implementations. Link all conflicting requirements and make no implemented edit to disputed content.

Evidence entries contain `kind` (`local`/`external`/`author_data`), title, path or URL, and what it supports. Prefer primary/authoritative sources for technical claims. External findings never become author data. Missing data goes in `needs`. Reasons state exactly what changed, which requirement it answers, and why it fits the evidence; explicit edits need only short explanations.
