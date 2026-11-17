"""Checked, portable reading contexts and presentation policy. No document-specific matching."""
import copy
import html
import re
from html.parser import HTMLParser

DEFAULT_POLICY = {"explicit_default": "accept", "completed_open": "retain_without_individual_review",
                  "review_only_pending": True, "pending_feedback_field": "pending_entries"}
PENDING_DECISIONS = {"unreviewed", "revise", "keep", "discuss"}


def default_review(change, requirements, policy=None):
    if change.get("review"):
        return copy.deepcopy(change["review"])
    policy = policy or DEFAULT_POLICY
    linked = [requirements[r] for r in change["requirement_ids"]]
    accept = (policy.get("explicit_default") == "accept" and change["status"] == "implemented"
              and all(r["kind"] == "explicit" and r["status"] == "implemented" for r in linked))
    return {"decision": "accept" if accept else "unreviewed", "note": "", "defaulted_by_policy": accept}


def checked_html(markup, text, safe_html):
    value = safe_html(markup)
    if "".join(value.text) != text:
        raise ValueError("Review context HTML text differs from its source")
    return "".join(value.parts)


def checked_range(value, text, label):
    if (not isinstance(value, (list, tuple)) or len(value) != 2
            or any(type(i) is not int for i in value) or not 0 <= value[0] <= value[1] <= len(text)):
        raise ValueError("Invalid review context " + label + " range")
    return list(value)


class MathSpans(HTMLParser):
    def __init__(self, markup):
        super().__init__(convert_charrefs=True)
        self.at = 0; self.depth = 0; self.start = 0; self.spans = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        if tag == "math":
            if not self.depth: self.start = self.at
            self.depth += 1

    def handle_endtag(self, tag):
        if tag == "math":
            self.depth -= 1
            if not self.depth: self.spans.append((self.start, self.at))

    def handle_data(self, text):
        self.at += len(text)


def sentence_range(text, start, end, markup=""):
    """Sentence envelope outside native math; never infer which repeated word was edited."""
    spans = MathSpans(markup).spans if markup else []
    cuts = [0]
    for m in re.finditer(r"[.!?。！？](?=\s|$)", text):
        at = m.end()
        if any(a <= at - 1 < b for a, b in spans): continue
        if re.search(r"(?:\be\.g|\bi\.e|\bet al|\bFig|\bEq|\bThm)\.$", text[:at], re.I): continue
        cuts.append(at)
    cuts.append(len(text))
    left = max((i for i in cuts if i <= start), default=0)
    right = min((i for i in cuts if i >= max(end, start + 1)), default=len(text))
    while left < right and text[left].isspace(): left += 1
    return [min(left, start), max(right, end)]


def side(source, side_name, blocks, safe_html):
    """One full source text + precise sentence and edit ranges, checked before browser use."""
    value = copy.deepcopy(source)
    if side_name == "revised":
        block = blocks[value["block_id"]]
        text = block["revised"]; markup = block.get("html", html.escape(text))
    elif value.get("block_id"):
        block = blocks[value["block_id"]]
        text = block["original"]; markup = block.get("original_html", html.escape(text))
    else:
        text = value.get("text", ""); markup = value.get("html", html.escape(text))
    if not isinstance(text, str): raise ValueError("Review source text must be a string")
    markup = checked_html(markup, text, safe_html)
    focus = checked_range(value.get("focus", [0, len(text)]), text, "focus")
    sentence = checked_range(value.get("sentence", sentence_range(text, *focus, markup)), text, "sentence")
    if not sentence[0] <= focus[0] <= focus[1] <= sentence[1]:
        raise ValueError("Review focus must lie inside its complete sentence")
    return dict(text=text, html=markup, focus=focus, sentence=sentence,
                block_id=value.get("block_id"), snippet=text[focus[0]:focus[1]])


def normalize_context(context, blocks, safe_html):
    result = {k: copy.deepcopy(v) for k, v in context.items() if k in {"comment_ids", "operation", "note"}}
    result["original"] = side(context["original"], "original", blocks, safe_html)
    result["revised"] = side(context["revised"], "revised", blocks, safe_html)
    return result


def legacy_context(c, blocks, safe_html):
    """Read the previous review's checked comment_locations without paper-specific code."""
    markup = c["original_html"]; text = "".join(safe_html(markup).text)
    f = c.get("focus", {}); original_focus = f.get("old_range", c["old_range"])
    revised_focus = f.get("new_range")
    if revised_focus is None:
        a = next((a for a in c.get("anchors", []) if a.get("block_id")), None)
        revised_focus = [a["start"], a["end"]] if a else c["sentence_range"]
    # Earlier editions sometimes kept a caret in the adjacent sentence: include that boundary honestly.
    old_sentence = [min(c["old_range"][0], original_focus[0]), max(c["old_range"][1], original_focus[1])]
    new_sentence = [min(c["sentence_range"][0], revised_focus[0]), max(c["sentence_range"][1], revised_focus[1])]
    return normalize_context(dict(original=dict(text=text, html=markup, focus=original_focus, sentence=old_sentence),
                                  revised=dict(block_id=c["revised_block"], focus=revised_focus, sentence=new_sentence),
                                  operation=f.get("operation"), note=f.get("note", "")), blocks, safe_html)


def prepare(data, safe_html):
    """Build render-only view data. The saved ledger/fingerprint is never mutated."""
    blocks = {b["id"]: b for b in data["blocks"]}
    reqs = {r["id"]: r for r in data["requirements"]}
    comments = {c["id"]: c for c in data["comments"]}
    views = {}; legacy = data.get("comment_locations", {})
    for item in [*data["changes"], *data["requirements"]]:
        is_change = "requirement_ids" in item
        cids = list(dict.fromkeys(cid for r in item["requirement_ids"] for cid in reqs[r]["comment_ids"])) if is_change else item["comment_ids"]
        contexts = []; anchors = copy.deepcopy(item.get("anchors", []))
        if "contexts" in item:
            contexts = [normalize_context(c, blocks, safe_html) for c in item["contexts"]]
        elif legacy and all(cid in legacy for cid in cids):
            for cid in cids:
                ctx = legacy_context(legacy[cid], blocks, safe_html); ctx["comment_ids"] = [cid]; contexts.append(ctx)
            if not anchors: anchors = [copy.deepcopy(a) for cid in cids for a in legacy[cid].get("anchors", [])]
        else:
            text_anchors = [a for a in anchors if a.get("block_id")]
            old_anchors = [a for a in item.get("original_anchors", []) if a.get("block_id")]
            for i, a in enumerate(text_anchors):
                block = blocks[a["block_id"]]
                context = {"revised": dict(block_id=block["id"], focus=[a["start"], a["end"]]),
                           "operation": item.get("operation", "pending")}
                if old_anchors:
                    oa = old_anchors[min(i, len(old_anchors) - 1)]
                    context["original"] = dict(block_id=oa["block_id"], focus=[oa["start"], oa["end"]])
                elif not is_change:
                    # Requirements without a pre-change edit may link current content, not fabricated old text.
                    context["original"] = dict(text=block["revised"], html=block.get("html", html.escape(block["revised"])), focus=[a["start"], a["end"]])
                else:
                    continue  # A region-only original has page evidence; do not guess its textual counterpart.
                contexts.append(normalize_context(context, blocks, safe_html))
            if not anchors and not is_change:
                # Geometry is original evidence only, never a guessed location in the revised text.
                for cid in cids:
                    source = comments[cid]["source"]
                    for p in data["pages"]:
                        if p["number"] == source["page"] and source.get("sha256") == data["document"].get("source_pdf", {}).get("sha256"):
                            anchors.extend(dict(type="region", page_id=p["id"], side="original", rect=r) for r in source.get("rects", []))
        if not anchors and contexts and not is_change:
            anchors=[dict(type="text",block_id=ctx["revised"]["block_id"],start=ctx["revised"]["focus"][0],end=ctx["revised"]["focus"][1],quote=ctx["revised"]["snippet"]) for ctx in contexts]
        for anchor in anchors:
            if anchor.get("type") in {"text","deletion"}:
                block=blocks.get(anchor.get("block_id"))
                if block is None:raise ValueError("Unknown review anchor block")
                a,b=checked_range([anchor.get("start"),anchor.get("end")],block["revised"],"anchor")
                if anchor.get("quote")!=block["revised"][a:b] or (anchor["type"]=="deletion" and a!=b):raise ValueError("Review anchor quote mismatch")
            elif anchor.get("type")=="region":
                page=next((p for p in data["pages"] if p["id"]==anchor.get("page_id")),None)
                r=anchor.get("rect",[])
                if page is None or anchor.get("side") not in {"original","revised"} or len(r)!=4 or not 0<=r[0]<r[2]<=1 or not 0<=r[1]<r[3]<=1:raise ValueError("Invalid review region anchor")
            else:raise ValueError("Unknown review anchor type")
        for ctx in contexts:
            if ctx.get("comment_ids") and not set(ctx["comment_ids"]) <= set(cids):
                raise ValueError("Review context comment links differ from its item")
        views[item["id"]] = dict(contexts=contexts, anchors=anchors)
    toc = []
    for b in data["blocks"]:
        if b.get("kind") != "heading": continue
        level = b.get("heading_level", b.get("toc_level", 1))
        if type(level) is not int or not 0 <= level <= 6: raise ValueError("Invalid heading level")
        included = b.get("toc_include", level > 0)
        if not isinstance(included, bool): raise ValueError("toc_include must be boolean")
        if included and level: toc.append(dict(block_id=b["id"], title=b["revised"], level=level))
    policy = {**DEFAULT_POLICY, **data.get("review_policy", {})}
    if policy.get("explicit_default") not in {"accept","unreviewed"}:raise ValueError("Invalid explicit default review policy")
    for change in data["changes"]:
        if change.get("review") and (change["review"].get("decision") not in {"unreviewed","accept","reject","discuss"} or not isinstance(change["review"].get("note",""),str)):raise ValueError("Invalid seeded review decision")
    defaults = {c["id"]: default_review(c, reqs, policy) for c in data["changes"]}
    return dict(review_contexts=views, review_toc=toc, review_policy=policy, review_defaults=defaults)


def validate_extras(data, safe_html):
    for b in data["blocks"]:
        if "original_html" in b: checked_html(b["original_html"], b["original"], safe_html)
        if b.get("image_data") and not re.fullmatch(r"data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/=\s]+", b["image_data"]):
            raise ValueError("Only embedded raster figure images are supported")
    prepare(data, safe_html)
