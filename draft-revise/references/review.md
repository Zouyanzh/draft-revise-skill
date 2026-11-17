# HTML review and subsequent editions

## Default interface

`render` produces one offline HTML, inlining `assets/review.css` and `assets/review.js`. No project-specific patch script, CDN, external font or server is needed. Paper/report opens in reading view; slides opens in pages. The desktop layout has a left hierarchical directory, the complete manuscript in the center, and a sticky comment sidebar. Narrow screens use a collapsible directory and a persistent, collapsible bottom comment panel. Keep the toolbar opaque and account for its actual height when scrolling.

Use real document hierarchy in `blocks[].heading_level` (1–6; 0 for the document title) and `toc_include`. Omit local definition/theorem/remark/proof labels from the directory unless they are genuine section headings. Do not add a second directory above the reading content. The full manuscript still includes its actual headings, formulas, tables, figures and references. Raster figures can use a checked `image` path; the renderer embeds it. Native MathML must have an exact semantic text layer; do not display extracted PDF glyph garbage, raw TeX, or `(cid:...)` as a readable formula. Use page evidence where reliable conversion is unavailable.

The sidebar presents, in order:

1. Full original comment, author and source page (transcription separately labeled).
2. **Original · this edit fragment**, then **Revised · this edit result**. These are actual minimal edit snippets, distinct from the full sentence. Insertions say there is no original fragment; deletions say deleted; unresolved content is labeled unchanged/pending.
3. Reason for the change or current disposition.
4. Original and revised **complete sentences**, highlighting only this edit's exact range. Preserve native math ancestry; partial formula snippets must remain valid MathML. Show a boundary marker for insertions/deletions.
5. Locate button directly below the revised sentence; retain all locations for multi-location edits.
6. Expandable complete paragraphs and relevant needs, evidence and issues.

All comments have searchable number navigation, collapsed by default. Independent comments in the same sentence keep separate IDs, ranges and snippets. A mixed comment may yield multiple edits: use each change's own `contexts`, rather than reusing a single per-comment comparison. Region-only edits show honest before/after descriptions and locate the actual page region. Keep original/revised page evidence in **Page evidence**, not an extra original-page expander in the reading sidebar.

Use `changes[].contexts` and `requirements[].contexts` when the renderer cannot derive reliable sentence contexts from existing text anchors. See [ledger contract](ledger.md). Derived contexts use the verified occurrence in `original_anchors` and `anchors`; they never search for the first occurrence of an edit's text. PDF geometry cannot reliably discover a corresponding revised sentence by itself. Supply checked contexts or keep the region-only presentation. Pending requirements also need a precise text anchor, context or original-region location when identifiable.

## Review efficiency

The default `review_policy` accepts completed **explicit** changes automatically; explicit replacement/deletion/insertion does not require a click per comment. Keep completed open edits provisionally without representing them as human accepted. Honor a supplied `change.review` and browser feedback over defaults. A collapsed optional control can adjust completed-change decisions; it is not a required step.

Only unresolved requirements (`status != implemented`) appear in **Pending items** and get opinion forms. This includes pending material, ambiguity/conflict and partial requirements, even if they already have a proposal change. Use one form per requirement, not one per change or raw comment. Synchronize the sidebar and pending-list forms. Users can enter free text without choosing a button and export immediately; unanswered items remain pending. Choosing keep/revise/discuss never changes execution status or claims an edit was implemented.

## Feedback schema 2 only

HTML, CLI `feedback`, and `next-plan` support **only** the following feedback format. Reject schema 1 and earlier extension formats; do not add fallback import or migrate an old feedback file silently. Ledger schema remains 1 and is independent of feedback schema.

```json
{
  "schema_version": 2,
  "document_id": "stable-document-id",
  "version": 1,
  "edition_id": "unique-edition-id",
  "ledger_fingerprint": "sha256-of-canonical-ledger",
  "exported_at": "ISO-time",
  "entries": [{"change_id":"m1","requirement_ids":["r1"],"comment_ids":["c1"],"decision":"accept","note":""}],
  "pending_entries": [{"requirement_id":"r2","comment_ids":["c2"],"decision":"unreviewed","note":""}]
}
```

`entries` contains every concrete change exactly once, with `unreviewed/accept/reject/discuss`. Defaults are explicit in the export, independent of browser storage. `pending_entries` contains every unresolved requirement exactly once, with `unreviewed/revise/keep/discuss` and a free-text note. Empty arrays are required when there are no corresponding items. The renderer also exports its `review_policy` for clarity; the ledger remains authoritative for execution and identities.

Both validators reject wrong document/version/edition/fingerprint, omitted arrays or items, duplicates, unknown/completed requirement IDs, invalid states/notes and altered many-to-many links. Validate the entire file before applying either array; an invalid pending record must not partially apply completed-change decisions. `next-plan` preserves the complete feedback in history and emits both `continuation.instructions` (changes) and `continuation.pending_instructions` (unresolved requirements). It never silently drops pending notes.

Browser local storage is temporary, path dependent and may be disabled. Export is the portable handoff. The page never edits manuscript/source/PDF files. Artifact and optional ledger downloads use relative paths: move the associated files with the HTML. Images, CSS and JS remain embedded if only the HTML is moved. Keep the delivered ledger unchanged; changing it requires another edition and freshly rendered HTML.

## Applying the next round

```sh
python "$SKILL_DIR/scripts/draft_revise.py" feedback draft_revised_v1.json feedback.json
python "$SKILL_DIR/scripts/draft_revise.py" next-plan draft_revised_v1.json feedback.json draft_revised_v2.json
```

`next-plan` creates a **plan**, not a modified manuscript. `continuation.state: plan_only_not_applied` blocks rendering until the agent implements/reassesses it. Accepted changes are retained; a supplied note takes precedence over a bare retain decision. Restore rejected text only where dependencies and overlaps permit it, then reassess. Pending `revise` or any substantive note means interpret the instructions; `keep` means retain current content while reassessing the unresolved requirement; `discuss` needs a decision; unreviewed stays pending. No pending response supplies missing data or resolves a proof by itself.

Dependencies are conservative and transitive. A rejected edit overlapping or depending on non-rejected edits remains `needs_decision`. Do not mechanically undo accepted content. After actual work, update snippets, precise anchors/contexts, execution states, source artifacts and verification. Preserve stable IDs and review history; use new IDs for materially new edits. Reset review of changed content and carry accepted unchanged content with `review.carried_from`. Set continuation to applied only after implementation and revalidation.

## Verification

Run `validate`, then `render`; check actual output and artifact hashes. Exercise desktop and narrow layouts, exact/overlapping words, zero-length boundaries, multiple edits from one comment, multiple comments in one sentence, all locations, native math, table/figure content, directory hierarchy, search/filter/navigation, pending-form synchronization, default acceptance, export/import and `file://` storage-disabled fallbacks. Confirm legacy feedback is rejected. Inspect actual revised page evidence; structural/DOM tests alone do not prove visual fidelity.

`selftest.py` exercises report/slides and backend invariants. Optional `review_ui_test.cjs` exercises generated HTML using Node and `jsdom` (supply that dependency via the available runtime); it does not replace real browser layout inspection.
