#!/usr/bin/env python3
"""Deterministic PDF evidence, revision ledger, offline review and feedback tools.
Semantic interpretation and manuscript editing belong to the calling agent.
"""
import argparse
import base64
import copy
import hashlib
import html
from html.parser import HTMLParser
import json
import mimetypes
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
from review_model import prepare as prepare_review, validate_extras, PENDING_DECISIONS

SCHEMA = 1
FEEDBACK_SCHEMA = 2
STATES = {"implemented", "partial", "needs_material", "needs_decision"}
KINDS = {"explicit", "open", "ambiguous", "conflict"}
DECISIONS = {"unreviewed", "accept", "reject", "discuss"}
SKILL_ROOT = Path(__file__).resolve().parent.parent


def fail(message):
    raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, data, replace=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w" if replace else "x", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprint(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def stable(prefix, *parts):
    return prefix + "-" + hashlib.sha256(json.dumps(parts, ensure_ascii=False,
                                  sort_keys=True).encode()).hexdigest()[:16]


def resolved(base, path):
    p = Path(path)
    return p if p.is_absolute() else base / p


def file_entry(path):
    p = Path(path).resolve()
    return {"path": str(p), "sha256": sha(p)}


def page_rect(coords, box, rotation):
    """PDF user space -> cropped, rotated page top-left normalized rectangle."""
    left, bottom, right, top = map(float, box)
    width, height = right-left, top-bottom
    points = []
    for x, y in zip(coords[::2], coords[1::2]):
        x, y = (float(x)-left)/width, (float(y)-bottom)/height
        points.append({0: (x, 1-y), 90: (y, x), 180: (1-x, y),
                       270: (1-y, 1-x)}[rotation])
    xs, ys = zip(*points)
    return [max(0, min(1, min(xs))), max(0, min(1, min(ys))),
            max(0, min(1, max(xs))), max(0, min(1, max(ys)))]


def render_pages(pdf, target):
    target.mkdir(parents=True, exist_ok=True)
    try:
        import pypdfium2 as pdfium
    except ImportError:
        if not shutil.which("pdftoppm"):
            fail("Page rendering needs pypdfium2 or pdftoppm; extraction can run without --images.")
        subprocess.run(["pdftoppm", "-cropbox", "-scale-to", "1500", "-png", str(pdf),
                        str(target / "page")], check=True, stdout=subprocess.DEVNULL)
        return sorted(target.glob("page-*.png"), key=lambda p: int(p.stem.split("-")[-1]))
    doc = pdfium.PdfDocument(str(pdf))
    paths = []
    for i in range(len(doc)):
        page = doc[i]
        bitmap = page.render(scale=1500/max(page.get_size()))
        path = target / ("page-%04d.png" % (i+1))
        bitmap.to_pil().save(path)
        bitmap.close()
        page.close()
        paths.append(path)
    doc.close()
    return paths


def extract(pdf, output, role="draft", images=False):
    from pypdf import PdfReader
    import pdfplumber
    pdf, output = Path(pdf).resolve(), Path(output).resolve()
    if output.exists():
        fail("Inventory output exists; choose a new path.")
    identity = file_entry(pdf)
    reader = PdfReader(pdf)
    inventory = {"schema_version": SCHEMA, "role": role, "file": identity,
                 "pages": [], "comments": [], "warnings": []}
    paths = render_pages(pdf, output.parent / (output.stem+"_pages")) if images else []
    with pdfplumber.open(pdf) as visual:
        for index, page in enumerate(reader.pages):
            number, rotation = index+1, int(page.rotation or 0) % 360
            box = list(map(float, page.cropbox))
            raw = [ref.get_object() for ref in page.get("/Annots", [])]
            raw = [a for a in raw if a.get("/Subtype") != "/Popup"]
            aid = {id(a): str(a.get("/NM") or stable("a", number, i,
                       list(map(float, a.get("/Rect", []))), str(a.get("/Contents", ""))))
                   for i, a in enumerate(raw)}
            duplicate_names = {name for name in aid.values() if list(aid.values()).count(name)>1}
            for i,a in enumerate(raw):
                if aid[id(a)] in duplicate_names:
                    aid[id(a)] = stable("a",number,i,aid[id(a)])
            consumed = set()
            pp = visual.pages[index]
            words = pp.extract_words(x_tolerance=1, y_tolerance=3)
            pdata = {"number": number, "label": str(number), "rotation": rotation,
                     "cropbox": box, "text": pp.extract_text() or ""}
            if paths:
                pdata["image"] = str(paths[index])
            inventory["pages"].append(pdata)
            for a in raw:
                if aid[id(a)] in consumed:
                    continue
                group, kind = [a], str(a.get("/Subtype", "/Unknown")).lstrip("/")
                # Acrobat replacement: strikeout -> insertion. Other replies remain distinct.
                rel = a.get("/IRT")
                if rel:
                    other = rel.get_object()
                    if kind == "StrikeOut" and other.get("/Subtype") == "/Caret" and id(other) in aid:
                        group.append(other)
                        kind = "Replace"
                if kind == "StrikeOut":
                    counterpart=next((x for x in raw if x.get("/Subtype")=="/Caret"
                        and x.get("/IRT") and x["/IRT"].get_object() is a),None)
                    if counterpart is not None:
                        group.append(counterpart);kind="Replace"
                # Some producers link caret -> strikeout, or place the caret first.
                if kind == "Caret":
                    counterpart = next((x for x in raw if x.get("/Subtype") == "/StrikeOut"
                        and x.get("/IRT") and x["/IRT"].get_object() is a), None)
                    if counterpart is None and rel and rel.get_object().get("/Subtype") == "/StrikeOut":
                        counterpart = rel.get_object()
                    if counterpart is not None and id(counterpart) in aid:
                        group, kind = [counterpart, a], "Replace"
                gids = [aid[id(x)] for x in group]
                if any(x in consumed for x in gids):
                    continue
                consumed.update(gids)
                geom = next((x for x in group if x.get("/QuadPoints")), group[0])
                coords = list(map(float, geom.get("/QuadPoints", [])))
                if not coords:
                    rect = list(map(float, geom.get("/Rect", [0,0,0,0])))
                    coords = [rect[0],rect[1],rect[2],rect[3]]
                quads = [coords[j:j+8] for j in range(0,len(coords),8)]
                regions = [page_rect(q, box, rotation) for q in quads]
                selected = []
                # pdfplumber words use rotated media-page top-left coordinates.
                media = list(map(float, page.mediabox))
                mwidth, mheight = media[2]-media[0], media[3]-media[1]
                if rotation in (90,270):
                    mwidth, mheight = mheight, mwidth
                for word in words:
                    wx, wy = (word["x0"]+word["x1"])/2/mwidth, (word["top"]+word["bottom"])/2/mheight
                    media_regions = [page_rect(q, media, rotation) for q in quads]
                    if any(x0-.001 <= wx <= x1+.001 and y0-.001 <= wy <= y1+.001
                           for x0,y0,x1,y1 in media_regions):
                        selected.append(word["text"])
                textmember = next((x for x in reversed(group) if x.get("/Contents")), group[-1])
                relation = None
                if a.get("/IRT"):
                    o = a["/IRT"].get_object()
                    relation = str(o.get("/NM", ""))
                inventory["comments"].append({
                    "id": stable("c", identity["sha256"], number, gids),
                    "raw_text": str(textmember.get("/Contents", "")),
                    "rich_text": str(textmember.get("/RC", "")),
                    "author": str(textmember.get("/T", a.get("/T", ""))),
                    "annotation_type": kind, "annotation_ids": gids,
                    "text_origin": "embedded", "recognized_text": "",
                    "source": {**identity, "page": number, "rects": regions,
                               **({"image":str(paths[index])} if paths else {})},
                    "selected_text": " ".join(selected), "related_annotation": relation,
                    "members": [{"id": aid[id(x)], "name":str(x.get("/NM","")), "type": str(x.get("/Subtype", "")),
                                 "raw_text": str(x.get("/Contents", "")), "author":str(x.get("/T","")),
                                 "rich_text":str(x.get("/RC",""))} for x in group]})
    if not inventory["comments"]:
        inventory["warnings"].append("No annotation objects: inspect for flattened, scanned or separate comments.")
    write(output, inventory)
    return inventory


def init(inventory_path, output, title=None, kind="report", review_language="zh-CN"):
    inv = read(inventory_path)
    data = {"schema_version": SCHEMA, "document": {
        "id": stable("doc", inv["file"]["sha256"]), "title": title or Path(inv["file"]["path"]).stem,
        "kind": kind, "language": "", "review_language": review_language, "version": 1,
        "edition_id": str(uuid.uuid4()), "source_pdf": inv["file"],
        "source_match": {"status": "unmatched", "reason": "Not inspected yet"}, "artifacts": []},
        "inventories": [str(Path(inventory_path).resolve())], "comments": inv["comments"],
        "excluded_annotations": [], "requirements": [], "changes": [], "blocks": [],
        "pages": [], "issues": [], "verification": []}
    for c in data["comments"]:
        data["requirements"].append({"id": stable("r", c["id"], 1), "comment_ids": [c["id"]],
            "kind": "ambiguous", "status": "needs_decision", "change_ids": [],
            "reason": "Awaiting interpretation and location verification", "needs": ["Inspect original comment and document"]})
    for p in inv["pages"]:
        entry = {"id": "page-%d" % p["number"], "number": p["number"], "status": "original"}
        if p.get("image"):
            entry["original_image"] = p["image"]
        data["pages"].append(entry)
    write(output, data)
    return data


class SafeHTML(HTMLParser):
    TAGS = set("span strong em u b i code sub sup br p div ul ol li table thead tbody tr th td math mrow mi mn mo msup msub msubsup mfrac msqrt mroot mtext mfenced munder mover munderover mtable mtr mtd mstyle mspace".split())
    ATTRS = {"colspan", "rowspan", "display", "mathvariant", "stretchy", "fence", "separator", "encoding", "width", "height", "depth"}

    def __init__(self, content):
        super().__init__(convert_charrefs=True)
        self.parts, self.text, self.stack = [], [], []
        self.feed(content)
        self.close()
        if self.stack:
            fail("Unclosed rich HTML elements: "+str(self.stack))

    def handle_starttag(self, tag, attrs):
        if tag not in self.TAGS:
            fail("Unsafe/unsupported rich HTML tag: "+tag)
        safe = []
        for name, value in attrs:
            if name not in self.ATTRS or value is None:
                fail("Unsafe/unsupported HTML attribute: "+name)
            if name in {"width","height","depth"} and not re.fullmatch(r"[0-9.]+(?:em|ex|px|pt|%)?", value):
                fail("Unsupported dimension")
            safe.append(' %s="%s"' % (name, html.escape(value, quote=True)))
        self.parts.append("<"+tag+"".join(safe)+">")
        if tag != "br":
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag != "br":
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            fail("Unbalanced rich HTML element: "+tag)
        self.stack.pop()
        self.parts.append("</"+tag+">")

    def handle_data(self, data):
        self.text.append(data)
        self.parts.append(html.escape(data))

    def handle_comment(self, data):
        pass

    def handle_decl(self, decl):
        fail("HTML declarations are not allowed in blocks")


def unique(items, name):
    result = {}
    for x in items:
        key = x.get("id")
        if not isinstance(key,str) or not re.fullmatch(r"[A-Za-z0-9_-]+",key) or key in result:
            fail("Missing, duplicate or unsafe "+name+" id: "+str(key))
        result[key] = x
    return result


def check_refs(values, table, label):
    for v in values:
        if v not in table:
            fail("Unknown "+label+": "+str(v))


def validate(data, base, check_files=True):
    if data.get("schema_version") != SCHEMA:
        fail("Unsupported ledger schema")
    d = data["document"]
    for k in ("id","title","edition_id","version","kind","review_language"):
        if not d.get(k): fail("Missing document."+k)
    if type(d["version"]) is not int or d["version"] < 1: fail("Version must be a positive integer")
    if d["kind"] not in {"paper","report","slides","other"}: fail("Unknown document kind")
    comments = unique(data["comments"], "comment")
    reqs = unique(data["requirements"], "requirement")
    changes = unique(data["changes"], "change")
    blocks = unique(data["blocks"], "block")
    pages = unique(data["pages"], "page")
    if not comments: fail("Ledger has no comments; inspect scans or independent review first")
    for c in comments.values():
        if c.get("text_origin") not in {"embedded","external-extracted","ocr","transcription"}:
            fail("Comment needs text_origin: "+c["id"])
        if c["text_origin"] in {"ocr","transcription"} and c.get("raw_text"):
            fail("Do not label transcription as exact embedded raw text")
        if "source" not in c or not c["source"].get("page"):
            fail("Comment needs source page")
    covered = set()
    for r in reqs.values():
        if not r.get("comment_ids"): fail("Requirement needs comment_ids")
        check_refs(r["comment_ids"],comments,"comment")
        covered.update(r["comment_ids"])
        if r.get("kind") not in KINDS or r.get("status") not in STATES: fail("Bad requirement state/kind")
        if r["kind"] in {"ambiguous","conflict"} and r["status"]=="implemented":
            fail("Resolve ambiguity/conflict before marking implemented")
        if not r.get("reason"): fail("Requirement needs reason")
        check_refs(r.get("change_ids",[]),changes,"change")
        if r["status"]=="implemented" and not r.get("change_ids"): fail("Implemented requirement has no change")
        if r["status"] in {"needs_material","needs_decision"} and not r.get("needs"):
            fail("Unresolved requirement needs concrete needs")
        for cid in r.get("change_ids",[]):
            if r["id"] not in changes[cid].get("requirement_ids",[]): fail("Nonreciprocal change link")
    if covered != set(comments): fail("Every included comment must have a requirement")
    for b in blocks.values():
        if not isinstance(b.get("revised"),str) or not isinstance(b.get("original"),str): fail("Blocks need original/revised text")
        if b.get("status","revised") not in {"revised","original","proposal"}: fail("Bad block status")
        if "html" in b:
            h = SafeHTML(b["html"])
            if "".join(h.text) != b["revised"]: fail("Rich HTML text differs from revised: "+b["id"])
    for p in pages.values():
        if p.get("status") not in {"original","revised","proposal"}: fail("Page needs honest status")
        if p["status"] in {"revised","proposal"} and not p.get("revised_image"): fail("Revised/proposal page needs image")
    for ch in changes.values():
        if ch.get("status") not in STATES or not ch.get("reason"): fail("Change needs execution status/reason")
        if ch.get("operation") not in {"replace","insert","delete","visual","move"}: fail("Bad operation")
        if not ch.get("requirement_ids"): fail("Change needs requirement ids")
        check_refs(ch["requirement_ids"],reqs,"requirement")
        for rid in ch["requirement_ids"]:
            if ch["id"] not in reqs[rid].get("change_ids",[]): fail("Nonreciprocal requirement link")
        check_refs(ch.get("depends_on",[]),changes,"dependency")
        if ch["id"] in ch.get("depends_on",[]): fail("Self dependency")
        if not isinstance(ch.get("original"),str) or not isinstance(ch.get("revised"),str): fail("Change needs before/after snippets")
        if not ch.get("anchors"): fail("Change must have precise text or region anchor")
        for a in ch["anchors"]:
            if a.get("type") in {"text","deletion"}:
                if a.get("block_id") not in blocks: fail("Unknown anchor block")
                text = blocks[a["block_id"]]["revised"]
                start,end = a.get("start"),a.get("end")
                if type(start) is not int or type(end) is not int or not 0<=start<=end<=len(text): fail("Invalid code-point range")
                if text[start:end] != a.get("quote"): fail("Anchor quote/range mismatch: "+ch["id"])
                if a["type"]=="text" and start==end: fail("Empty text range; use deletion point")
                if a["type"]=="deletion" and start!=end: fail("Deletion must be zero-width point")
            elif a.get("type")=="region":
                if a.get("page_id") not in pages: fail("Unknown page anchor")
                p = pages[a["page_id"]]
                if a.get("side") not in {"original","revised"}: fail("Region side required")
                if not p.get(a["side"]+"_image"): fail("Region references missing page image")
                rect=a.get("rect",[])
                if len(rect)!=4 or not all(type(x) in (int,float) for x in rect): fail("Invalid region")
                if not 0<=rect[0]<rect[2]<=1 or not 0<=rect[1]<rect[3]<=1: fail("Region outside page")
            else: fail("Unknown anchor type")
        if ch["status"]=="implemented" and not ch.get("original_anchors"):
            fail("Implemented change needs a verified pre-change location")
        for a in ch.get("original_anchors",[]):
            if a.get("type") in {"text","point"}:
                if a.get("block_id") not in blocks:fail("Unknown original block")
                text=blocks[a["block_id"]]["original"];start,end=a.get("start"),a.get("end")
                if type(start) is not int or type(end) is not int or not 0<=start<=end<=len(text):fail("Invalid original range")
                if text[start:end]!=a.get("quote"):fail("Original anchor quote/range mismatch")
                if (start==end)!=(a["type"]=="point"):fail("Use point for zero-width original location")
            elif a.get("type")=="region":
                if a.get("page_id") not in pages:fail("Unknown original page")
                if a.get("side")!="original" or not pages[a["page_id"]].get("original_image"):fail("Original region needs original image")
                rect=a.get("rect",[])
                if len(rect)!=4 or not all(type(x) in (int,float) for x in rect):fail("Invalid original region")
                if not 0<=rect[0]<rect[2]<=1 or not 0<=rect[1]<rect[3]<=1:fail("Original region outside page")
            else:fail("Unknown original anchor type")
        for expected in ch.get("explicit_checks",[]):
            if expected["requirement_id"] not in ch["requirement_ids"]: fail("Explicit check requirement not linked")
            if ch["status"]=="implemented" and expected["specified_text"]!=ch["revised"]:
                fail("Explicit specified text was silently changed: "+ch["id"])
        if ch["status"]=="implemented":
            if not any(f.get("role") in {"revised_pdf","revised_source"} for f in d.get("artifacts",[])):
                fail("Implemented changes need a saved revised PDF or source artifact")
            if all((blocks[a["block_id"]].get("status","revised")=="proposal" if a.get("block_id")
                    else pages[a["page_id"]]["status"]=="proposal") for a in ch["anchors"]):
                fail("Proposal-only change cannot be implemented")
    for r in reqs.values():
        if r["status"]=="implemented" and any(changes[c]["status"]!="implemented" for c in r["change_ids"]):
            fail("Implemented requirement contains unresolved changes")
    # Inventory coverage catches forgotten ink/shapes and changed exact raw comments.
    excluded = {x["comment_id"]:x for x in data.get("excluded_annotations",[])}
    for invpath in data.get("inventories",[]):
        inv=read(resolved(base,invpath))
        for c in inv["comments"]:
            if c["id"] in comments:
                for key in ("raw_text","annotation_ids","author","source","members","text_origin"):
                    if comments[c["id"]].get(key)!=c.get(key): fail("Original comment evidence changed: "+key)
            elif c["id"] not in excluded or not excluded[c["id"]].get("reason"):
                fail("Inventory annotation missing without exclusion: "+c["id"])
    # Dependency cycles prevent a meaningful restore sequence.
    def visit(cid, active, done):
        if cid in active: fail("Dependency cycle")
        if cid in done: return
        active.add(cid)
        for dep in changes[cid].get("depends_on",[]): visit(dep,active,done)
        active.remove(cid);done.add(cid)
    done=set()
    for cid in changes: visit(cid,set(),done)
    if check_files:
        files=[d.get("source_pdf",{})]+d.get("artifacts",[])
        for f in files:
            if not f.get("path"): continue
            p=resolved(base,f["path"])
            if not p.is_file(): fail("Missing artifact: "+str(p))
            if not f.get("sha256") or sha(p)!=f["sha256"]: fail("Artifact hash missing/mismatch: "+str(p))
        for p in pages.values():
            for key in ("original_image","revised_image"):
                if p.get(key) and not resolved(base,p[key]).is_file(): fail("Missing image")
    validate_extras(data, SafeHTML)
    return {"comments":len(comments),"requirements":len(reqs),"changes":len(changes),"blocks":len(blocks),"pages":len(pages)}


def locate(text, quote, before=None, after=None, occurrence=None):
    if not quote: fail("Quote must not be empty")
    found=[]
    for m in re.finditer(re.escape(quote),text):
        if before is not None and not text[:m.start()].endswith(before): continue
        if after is not None and not text[m.end():].startswith(after): continue
        found.append(m.start())
    if occurrence is not None:
        if not 1<=occurrence<=len(found): fail("Occurrence outside matches")
        found=[found[occurrence-1]]
    if len(found)!=1: fail("Location ambiguous or absent (%d matches); provide context/occurrence" % len(found))
    return {"type":"text","start":found[0],"end":found[0]+len(quote),"quote":quote}


def data_image(path):
    mime=mimetypes.guess_type(str(path))[0]
    if mime not in {"image/png","image/jpeg","image/webp"}: fail("Embed raster page images, not active SVG/HTML")
    return "data:"+mime+";base64,"+base64.b64encode(Path(path).read_bytes()).decode()


def render(data, base, output, ledger_path=None):
    if data.get("continuation",{}).get("state")=="plan_only_not_applied":
        fail("Implement continuation before rendering a new edition")
    validate(data,base)
    payload=copy.deepcopy(data)
    payload["ledger_fingerprint"]=fingerprint(data)
    payload.update(prepare_review(data, SafeHTML))
    import os
    payload["ledger_href"]=Path(os.path.relpath(Path(ledger_path).resolve(),Path(output).resolve().parent)).as_posix() if ledger_path else None
    for b in payload["blocks"]:
        if b.get("image") and not b.get("image_data"): b["image_data"]=data_image(resolved(base,b["image"]))
        b["html"]= "".join(SafeHTML(b["html"]).parts) if "html" in b else html.escape(b["revised"])
    for page in payload["pages"]:
        for key in ("original_image","revised_image"):
            if page.get(key): page[key]=data_image(resolved(base,page[key]))
    payload["evidence_images"]={}
    for comment in payload["comments"]:
        source=comment["source"]
        if source.get("image"):
            path=resolved(base,source.pop("image"));iid=stable("img",sha(path))
            source["image_id"]=iid
            if iid not in payload["evidence_images"]:payload["evidence_images"][iid]=data_image(path)
    import os
    for a in payload["document"].get("artifacts",[]):
        a["href"]=Path(os.path.relpath(resolved(base,a["path"]),Path(output).resolve().parent)).as_posix()
    template=(SKILL_ROOT/"assets/review.html").read_text()
    template=template.replace("__DRAFT_REVISE_CSS__",(SKILL_ROOT/"assets/review.css").read_text())
    template=template.replace("__DRAFT_REVISE_JS__",(SKILL_ROOT/"assets/review.js").read_text())
    value=json.dumps(payload,ensure_ascii=False).replace("<","\\u003c").replace("\u2028","\\u2028").replace("\u2029","\\u2029")
    result=template.replace("__DRAFT_REVISE_DATA__",value)
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    with Path(output).open("x",encoding="utf-8") as f:f.write(result)
    return {"html":str(Path(output).resolve()),"fingerprint":payload["ledger_fingerprint"]}


def check_feedback(data, feedback):
    d=data["document"]
    if feedback.get("schema_version")!=FEEDBACK_SCHEMA: fail("Unsupported feedback schema; export the current review format")
    for key,expected in [("document_id",d["id"]),("version",d["version"]),
                         ("edition_id",d["edition_id"]),("ledger_fingerprint",fingerprint(data))]:
        if feedback.get(key)!=expected:fail("Feedback version/fingerprint mismatch: "+key)
    changes=unique(data["changes"],"change")
    seen=set()
    if not isinstance(feedback.get("entries"),list):fail("Feedback entries must be a list")
    for e in feedback.get("entries",[]):
        if e.get("change_id") not in changes or e["change_id"] in seen:fail("Unknown/duplicate feedback change")
        seen.add(e["change_id"])
        ch=changes[e["change_id"]]
        if not isinstance(e.get("requirement_ids"),list) or sorted(e["requirement_ids"])!=sorted(ch["requirement_ids"]):fail("Feedback requirement links changed")
        expected={cid for r in data["requirements"] if r["id"] in ch["requirement_ids"] for cid in r["comment_ids"]}
        if not isinstance(e.get("comment_ids"),list) or sorted(e["comment_ids"])!=sorted(expected):fail("Feedback comment links changed")
        if e.get("decision") not in DECISIONS or not isinstance(e.get("note",""),str):fail("Bad review decision/note")
    pending_seen=set()
    if not isinstance(feedback.get("pending_entries"),list):fail("Feedback needs pending_entries")
    reqs=unique(data["requirements"],"requirement")
    for entry in feedback["pending_entries"]:
        rid=entry.get("requirement_id");r=reqs.get(rid)
        if not r or r["status"]=="implemented" or rid in pending_seen:fail("Unknown, completed or duplicate pending requirement")
        pending_seen.add(rid)
        if not isinstance(entry.get("comment_ids"),list) or sorted(entry["comment_ids"])!=sorted(r["comment_ids"]):fail("Pending feedback comment links changed")
        if entry.get("decision") not in PENDING_DECISIONS or not isinstance(entry.get("note"),str):fail("Bad pending decision/note")
    if seen!=set(changes):fail("Feedback must include every change")
    if pending_seen!={r["id"] for r in reqs.values() if r["status"]!="implemented"}:fail("Feedback must include every pending requirement")
    return {"entries":len(seen),"unreviewed_missing":len(changes)-len(seen),"pending_entries":len(pending_seen)}


def next_plan(data, feedback):
    check_feedback(data,feedback)
    out=copy.deepcopy(data)
    d=out["document"]
    d["parent_edition_id"]=d["edition_id"]
    d["edition_id"]=str(uuid.uuid4());d["version"]+=1
    entries={e["change_id"]:e for e in feedback.get("entries",[])}
    changes={c["id"]:c for c in out["changes"]}
    # Build an undirected relation for dependencies and overlapping edit locations.
    adjacent={cid:set() for cid in changes}
    for c in changes.values():
        for dep in c.get("depends_on",[]):
            adjacent[c["id"]].add(dep);adjacent[dep].add(c["id"])
    vals=list(changes.values())
    for i,a in enumerate(vals):
        for b in vals[i+1:]:
            for field in ("anchors","original_anchors"):
              for x in a.get(field,[]):
                for y in b.get(field,[]):
                    conflict=False
                    if x.get("block_id") and x.get("block_id")==y.get("block_id"):
                        conflict=max(x["start"],y["start"])<=min(x["end"],y["end"])
                    elif x.get("page_id") and x.get("page_id")==y.get("page_id") and x.get("side")==y.get("side"):
                        p,q=x["rect"],y["rect"]
                        conflict=max(p[0],q[0])<min(p[2],q[2]) and max(p[1],q[1])<min(p[3],q[3])
                    if conflict:
                        adjacent[a["id"]].add(b["id"]);adjacent[b["id"]].add(a["id"])
    instructions=[]
    for cid,ch in changes.items():
        e=entries[cid]
        decision=e["decision"]
        if decision=="reject":
            # Any linked non-rejected edit makes automatic restore unsafe, transitively.
            linked=set();queue=list(adjacent[cid])
            while queue:
                n=queue.pop()
                if n==cid or n in linked:continue
                linked.add(n);queue.extend(adjacent[n]-linked)
            blockers=[n for n in linked if entries[n]["decision"]!="reject"]
            action="needs_decision" if blockers else "restore_and_reassess"
        elif decision=="discuss":action="needs_decision";blockers=[]
        elif e.get("note","").strip():action="interpret_feedback";blockers=[]
        elif decision=="accept":action="retain";blockers=[]
        else:action="retain_unreviewed";blockers=[]
        item={"change_id":cid,"action":action,"decision":decision,"note":e.get("note",""),"blockers":blockers}
        if decision=="reject":item["restore_text"]=ch["original"]
        instructions.append(item)
        ch["review"]={"decision":"accept" if action=="retain" else "unreviewed","note":""}
        if action=="retain":ch["review"]["carried_from"]=d["parent_edition_id"]
    pending={e["requirement_id"]:e for e in feedback.get("pending_entries",[])}
    pending_instructions=[]
    for r in out["requirements"]:
        if r["status"]=="implemented":continue
        e=pending[r["id"]]
        action="interpret_pending_feedback" if e.get("note","").strip() or e["decision"]=="revise" else "retain_current_pending" if e["decision"]=="keep" else "needs_decision" if e["decision"]=="discuss" else "retain_pending"
        pending_instructions.append({"requirement_id":r["id"],"comment_ids":r["comment_ids"],"decision":e["decision"],"note":e.get("note",""),"action":action})
    out["continuation"]={"state":"plan_only_not_applied","feedback_fingerprint":fingerprint(feedback),"instructions":instructions,"pending_instructions":pending_instructions}
    out.setdefault("review_history",[]).append({"edition_id":d["parent_edition_id"],"feedback":copy.deepcopy(feedback)})
    out["verification"]=[]
    # Keep current artifact identities as parent evidence, not a new edition's deliverables.
    out["parent_artifacts"]=d.get("artifacts",[]);d["artifacts"]=[]
    return out


def verify_text(data, pdf):
    from pypdf import PdfReader
    text="\n".join(p.extract_text() or "" for p in PdfReader(pdf).pages)
    normalize=lambda s:re.sub(r"\s+","",s)
    text=normalize(text)
    checks=[]
    for ch in data["changes"]:
        if ch["status"]!="implemented" or ch["operation"]=="visual":continue
        if ch["revised"]:
            checks.append({"change_id":ch["id"],"revised_text_found":normalize(ch["revised"]) in text})
    return {"pdf_sha256":sha(pdf),"checks":checks,"note":"Presence only; duplicates, deletions, equations and layout require separate verification."}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    s=p.add_subparsers(dest="command",required=True)
    e=s.add_parser("extract",help="Extract PDF annotations/pages without deciding edits")
    e.add_argument("pdf");e.add_argument("output");e.add_argument("--role",choices=["draft","review"],default="draft");e.add_argument("--images",action="store_true")
    e=s.add_parser("init",help="Create an unresolved inventory-backed ledger")
    e.add_argument("inventory");e.add_argument("output");e.add_argument("--title");e.add_argument("--kind",choices=["paper","report","slides","other"],default="report");e.add_argument("--review-language",default="zh-CN")
    for name in ("validate","render","feedback","next-plan","verify-text"):
        e=s.add_parser(name);e.add_argument("ledger")
        if name=="render":e.add_argument("output")
        elif name in {"feedback","next-plan"}:e.add_argument("feedback")
        if name=="next-plan":e.add_argument("output")
        if name=="verify-text":e.add_argument("pdf")
    e=s.add_parser("locate",help="Find one code-point range; refuse ambiguous occurrences")
    e.add_argument("text_file");e.add_argument("quote");e.add_argument("--before");e.add_argument("--after");e.add_argument("--occurrence",type=int)
    a=p.parse_args()
    if a.command=="extract":
        d=extract(a.pdf,a.output,a.role,a.images);result={"comments":len(d["comments"]),"pages":len(d["pages"]),"warnings":d["warnings"]}
    elif a.command=="init":
        d=init(a.inventory,a.output,a.title,a.kind,a.review_language);result={"document":d["document"]["id"],"version":1}
    elif a.command=="locate":result=locate(Path(a.text_file).read_text(),a.quote,a.before,a.after,a.occurrence)
    else:
        path=Path(a.ledger).resolve();d=read(path);base=path.parent
        result=validate(d,base)
        if a.command=="render":
            if d.get("continuation",{}).get("state")=="plan_only_not_applied":fail("Implement continuation before rendering a new edition")
            result=render(d,base,a.output,path)
        elif a.command=="feedback":result=check_feedback(d,read(a.feedback))
        elif a.command=="next-plan":
            write(a.output,next_plan(d,read(a.feedback)));result={"next_plan":a.output,"manuscript_modified":False}
        elif a.command=="verify-text":result=verify_text(d,a.pdf)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":
    try:main()
    except (ValueError,KeyError,TypeError,OSError,ImportError) as exc:
        print("draft-revise: "+str(exc),file=sys.stderr);sys.exit(2)
