#!/usr/bin/env python3
"""Portable behavioral regression tests and generated report/slides review examples."""
import argparse
import copy
import json
from pathlib import Path
import tempfile
import unittest
import draft_revise as dr

ROOT = None


def pdf_text(path, blocks, slides=False):
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import simpleSplit
    c = canvas.Canvas(str(path), pagesize=(960,540) if slides else (612,792))
    width,height = (960,540) if slides else (612,792)
    y=height-60
    for b in blocks:
        if not b['revised']: continue
        size=24 if slides else (17 if b.get('kind')=='heading' else 11)
        for line in simpleSplit(b['revised'],'Helvetica',size,width-120):
            if y<70:c.showPage();y=height-60
            c.setFont('Helvetica',size)
            if 'x2' in line or 'x3' in line:
                from reportlab.pdfbase.pdfmetrics import stringWidth
                exponent='2' if 'x2' in line else '3';left,right=line.split('x'+exponent,1)
                c.drawString(60,y,left+'x');x=60+stringWidth(left+'x','Helvetica',size)
                c.setFont('Helvetica',size*.7);c.drawString(x,y+size*.5,exponent)
                c.setFont('Helvetica',size);c.drawString(x+size*.5,y,right)
            else:c.drawString(60,y,line)
            y-=size*1.5
        y-=15
    c.save()


def report_fixture(folder):
    folder.mkdir(parents=True,exist_ok=True)
    pairs=[('Overview','Overview'),
        ('A repeated term appears here; a repeated term appears there.','A repeated term appears here; a revised label appears there.'),
        ('Remove this aside. Main finding remains.','Main finding remains.'),
        ('The report presents observations.','The report presents observations. Inputs are supplied measurements.'),
        ('Outdated heading. This method is useful.','This method is useful because it separates observed inputs from assumptions.'),
        ('The conclusions are preliminary.','The results is preliminary.'),
        ('The model uses x2.','The model uses x3.'),
        ('First statement lacks context. Second statement repeats it.','The first statement introduces the observed trend. The second explains its limited scope.'),
        ('This entire paragraph is redundant.',''),
        ('Unverified dataset and conflicting interpretation remain unchanged.','Unverified dataset and conflicting interpretation remain unchanged.')]
    blocks=[{'id':'b'+str(i),'original':a,'revised':b,'kind':'heading' if i==0 else 'paragraph'} for i,(a,b) in enumerate(pairs)]
    blocks[6]['html']='The model uses <math><msup><mi>x</mi><mn>3</mn></msup></math>.'
    pdf_text(folder/'report_original.pdf',[dict(b,revised=b['original']) for b in blocks])
    pdf_text(folder/'report_revised_v1.pdf',blocks)
    (folder/'report_revised_v1.txt').write_text('\n\n'.join(b['revised'] for b in blocks))
    d={'schema_version':1,'document':{'id':'doc-report','title':'Report revision example','kind':'report','language':'en','review_language':'zh-CN','version':1,'edition_id':'report-edition-1','source_pdf':dr.file_entry(folder/'report_original.pdf'),'source_match':{'status':'matched','reason':'Synthetic fixture generated from the paired source blocks.'},'artifacts':[]},'inventories':[],'comments':[],'requirements':[],'changes':[],'blocks':blocks,'pages':[],'issues':[],'verification':[],'excluded_annotations':[]}
    for name,role in [('report_original.pdf','original_pdf'),('report_revised_v1.pdf','revised_pdf'),('report_revised_v1.txt','revised_source')]:
        d['document']['artifacts'].append({**dr.file_entry(folder/name),'role':role,'label':name})
    def comment(n,raw):
        d['comments'].append({'id':'c'+str(n),'raw_text':raw,'author':'Reviewer A' if n%2 else 'Reviewer B','source':{**d['document']['source_pdf'],'page':1},'text_origin':'embedded','recognized_text':''})
    def req(r,c,kind='explicit',status='implemented',reason='逐字落实批注指定的替换、插入或删除操作。',needs=None):
        q={'id':r,'comment_ids':['c'+str(c)],'kind':kind,'status':status,'change_ids':[],'reason':reason}
        if needs:q['needs']=needs
        d['requirements'].append(q);return q
    def change(n,r,bi,old,new,quote=None,kind='replace',start=None):
        text=blocks[bi]['revised']
        anchor=({'type':'deletion','start':start or 0,'end':start or 0,'quote':''} if not new else dr.locate(text,quote or new))
        anchor['block_id']=blocks[bi]['id']
        ch={'id':'m'+str(n),'requirement_ids':[r['id']],'operation':kind,'status':'implemented','original':old,'revised':new,'reason':r['reason'],'anchors':[anchor]}
        if old:
            oa=dr.locate(blocks[bi]['original'],old,occurrence=2 if n in [1,10] else None)
        else:
            at=len(blocks[bi]['original']);oa={'type':'point','start':at,'end':at,'quote':''}
        ch['original_anchors']=[dict(oa,block_id=blocks[bi]['id'])]
        r['change_ids'].append(ch['id']);d['changes'].append(ch);return ch
    comment(1,'Replace only the second "repeated" with "revised".')
    r=req('r1',1);ch=change(1,r,1,'repeated','revised');ch['explicit_checks']=[{'requirement_id':'r1','specified_text':'revised'}]
    comment(2,'Delete "Remove this aside."');change(2,req('r2',2),2,'Remove this aside. ','',kind='delete')
    comment(3,'Add "Inputs are supplied measurements."');change(3,req('r3',3),3,'','Inputs are supplied measurements.',kind='insert')
    comment(4,'Delete the outdated heading and explain why the method is useful.')
    change(4,req('r4a',4),4,'Outdated heading. ','',kind='delete')
    change(5,req('r4b',4,'open',reason='根据所提供的方法说明，补充区分观测输入与假设这一作用，直接回应为什么有用的要求。'),4,'This method is useful.','This method is useful because it separates observed inputs from assumptions.')
    comment(5,'Use "The results is preliminary." exactly.')
    ch=change(6,req('r5',5),5,'The conclusions are preliminary.','The results is preliminary.');ch['explicit_checks']=[{'requirement_id':'r5','specified_text':ch['revised']}]
    d['issues'].append({'id':'issue-grammar','change_ids':['m6'],'problem':'Specified text has subject-verb disagreement.','suggestion':'The results are preliminary.','adopted':False})
    comment(6,'Replace the exponent 2 with 3.');change(7,req('r6',6),6,'2','3')
    comment(7,'Clarify the relationship between the two statements.')
    ch=change(8,req('r7',7,'open',reason='第一句明确观测趋势，第二句限定适用范围，回应句间关系的要求；没有补造实验结果。'),7,pairs[7][0],pairs[7][1])
    ch['anchors']=[dict(dr.locate(blocks[7]['revised'],s),block_id='b7') for s in ['The first statement introduces the observed trend.','The second explains its limited scope.']]
    comment(8,'Delete the entire redundant paragraph.');change(9,req('r8',8),8,pairs[8][0],'',kind='delete')
    comment(9,'Reviewer A asks to assert causation; Reviewer B forbids that unsupported conclusion.')
    req('r9',9,'conflict','needs_decision','Preserved the affected claim because the requirements conflict.',['Choose wording consistent with available evidence.'])
    comment(10,'Add the unavailable private dataset analysis.')
    req('r10',10,'open','needs_material','The private dataset is unavailable; no results were invented.',['Supply authorized dataset and completed analysis.'])
    comment(11,'')
    req('r11',11,'ambiguous','needs_decision','A highlight alone does not specify a modification.',['Clarify the intended change at the marked region.'])
    comment(12,'Replace "term" in the second clause with "label".')
    change(10,req('r12',12),1,'term','label')
    original=dr.render_pages(folder/'report_original.pdf',folder/'original_pages')
    revised=dr.render_pages(folder/'report_revised_v1.pdf',folder/'revised_pages')
    for i,p in enumerate(revised):d['pages'].append({'id':'p'+str(i+1),'number':i+1,'status':'revised','original_image':str(original[min(i,len(original)-1)]),'revised_image':str(p)})
    d['verification']=[{'check':'Synthetic source and PDF generated from the same full block list','artifact_sha256':dr.sha(folder/'report_revised_v1.pdf'),'result':'pass'}]
    dr.write(folder/'report_revised_v1.json',d)
    dr.render(d,folder,folder/'report_revised_v1.html')
    return d


def slides_fixture(folder):
    from reportlab.pdfgen import canvas
    folder.mkdir(parents=True,exist_ok=True)
    for version,color in [('original','#B8C8D5'),('revised_v1','#236B51')]:
        c=canvas.Canvas(str(folder/('slides_'+version+'.pdf')),pagesize=(960,540))
        c.setFillColorRGB(.97,.98,.96);c.rect(0,0,960,540,fill=1,stroke=0)
        c.setFillColorRGB(.12,.22,.19);c.setFont('Helvetica-Bold',36);c.drawString(60,440,'Observed inputs and assumptions')
        c.setFillColor(color);c.roundRect(60,120,380,250,14,fill=1,stroke=0)
        c.setFillColorRGB(1,1,1);c.setFont('Helvetica',26);c.drawString(90,310,'Observed inputs')
        c.setFillColorRGB(.12,.22,.19);c.drawString(510,310,'Assumptions')
        c.setFont('Helvetica',18);c.drawString(510,260,'No new experimental claims.');c.save()
    orig=dr.render_pages(folder/'slides_original.pdf',folder/'original_pages')[0]
    rev=dr.render_pages(folder/'slides_revised_v1.pdf',folder/'revised_pages')[0]
    d={'schema_version':1,'document':{'id':'doc-slides','title':'Slide region revision example','kind':'slides','language':'en','review_language':'zh-CN','version':1,'edition_id':'slides-edition-1','source_pdf':dr.file_entry(folder/'slides_original.pdf'),'source_match':{'status':'matched','reason':'Fixture source generated locally.'},'artifacts':[dict(dr.file_entry(folder/'slides_revised_v1.pdf'),role='revised_pdf',label='Revised slides PDF')]},'inventories':[],'comments':[{'id':'c1','raw_text':'Use dark green for the observed-inputs card to improve contrast.','author':'Design reviewer','text_origin':'embedded','recognized_text':'','source':{**dr.file_entry(folder/'slides_original.pdf'),'page':1,'rects':[[.0625,.3148,.4584,.7778]]}}],'requirements':[{'id':'r1','comment_ids':['c1'],'kind':'explicit','status':'implemented','change_ids':['m1'],'reason':'Applied the specified dark green to the card.'}],'changes':[{'id':'m1','requirement_ids':['r1'],'operation':'visual','status':'implemented','original':'Light blue card with white text','revised':'Dark green card with white text','reason':'将卡片填色改为指定的深绿色，保留页面尺寸和内容层级，使白色文字更易辨认。','anchors':[{'type':'region','page_id':'p1','side':'revised','rect':[.0625,.3148,.4584,.7778]}],'original_anchors':[{'type':'region','page_id':'p1','side':'original','rect':[.0625,.3148,.4584,.7778]}],'restore':{'fill':'#B8C8D5'}}],'blocks':[],'pages':[{'id':'p1','number':1,'status':'revised','original_image':str(orig),'revised_image':str(rev)}],'issues':[],'verification':[],'excluded_annotations':[]}
    dr.write(folder/'slides_revised_v1.json',d);dr.render(d,folder,folder/'slides_revised_v1.html');return d


def annotated_fixture(folder):
    from pypdf import PdfReader,PdfWriter
    from pypdf.generic import DictionaryObject,NameObject,TextStringObject,ArrayObject,FloatObject
    base=folder/'annotation_base.pdf';pdf_text(base,[{'revised':'Repeated term and original claim. Another repeated term.'}])
    w=PdfWriter();w.add_page(PdfReader(base).pages[0]);refs=[]
    def annot(kind,n,text='',quad=False):
        a=DictionaryObject({NameObject('/Type'):NameObject('/Annot'),NameObject('/Subtype'):NameObject('/'+kind),NameObject('/NM'):TextStringObject(n),NameObject('/Contents'):TextStringObject(text),NameObject('/T'):TextStringObject('Reviewer'),NameObject('/Rect'):ArrayObject(map(FloatObject,[60,720,155,744]))})
        if quad:a[NameObject('/QuadPoints')]=ArrayObject(map(FloatObject,[60,744,155,744,60,720,155,720]))
        ref=w._add_object(a);refs.append(ref);return a,ref
    a,ar=annot('StrikeOut','replace-old',quad=True);b,br=annot('Caret','replace-new','new phrase');a[NameObject('/IRT')]=br
    a,ar=annot('StrikeOut','reverse-old',quad=True);b,br=annot('Caret','reverse-new','reverse replacement');b[NameObject('/IRT')]=ar
    annot('StrikeOut','delete',quad=True);annot('Caret','insert','Insert text')
    annot('Highlight','highlight',quad=True);annot('Ink','handwriting');annot('Circle','circle');annot('Text','note','Explain evidence.');annot('Popup','popup','not a comment')
    w.pages[0][NameObject('/Annots')]=ArrayObject(refs)
    path=folder/'annotated_report.pdf'
    with path.open('wb') as f:w.write(f)
    return path


def feedback(d,decisions):
    entries=[]
    for ch in d['changes']:
        cid=ch['id'];value=decisions.get(cid,'unreviewed');decision,note=value if isinstance(value,tuple) else (value,'')
        reqs=[r for r in d['requirements'] if r['id'] in ch['requirement_ids']]
        entries.append({'change_id':cid,'requirement_ids':ch['requirement_ids'],'comment_ids':sorted({c for r in reqs for c in r['comment_ids']}),'decision':decision,'note':note})
    return {'schema_version':2,'pending_entries':[{'requirement_id':r['id'],'comment_ids':r['comment_ids'],'decision':'unreviewed','note':''} for r in d['requirements'] if r['status']!='implemented'],'document_id':d['document']['id'],'version':d['document']['version'],'edition_id':d['document']['edition_id'],'ledger_fingerprint':dr.fingerprint(d),'entries':entries}


class Regression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=ROOT;cls.d=report_fixture(ROOT/'report');cls.slides=slides_fixture(ROOT/'slides')
        cls.annotated=annotated_fixture(ROOT)

    def test_report_slide_outputs_and_text(self):
        self.assertEqual(dr.validate(self.d,self.folder)['comments'],12)
        self.assertEqual(dr.validate(self.slides,self.folder)['changes'],1)
        checks=dr.verify_text(self.d,ROOT/'report/report_revised_v1.pdf')['checks']
        self.assertTrue(checks);self.assertTrue(all(x['revised_text_found'] for x in checks))

    def test_repeated_word_and_unicode(self):
        with self.assertRaises(ValueError):dr.locate('same same','same')
        self.assertEqual(dr.locate('same same','same',before='same ')['start'],5)
        self.assertEqual(dr.locate('😀 x x','x',occurrence=2)['start'],4)

    def test_exact_typo_is_not_autocorrected(self):
        self.assertEqual(self.d['changes'][5]['revised'],'The results is preliminary.')
        d=copy.deepcopy(self.d);d['changes'][5]['revised']='The results are preliminary.'
        with self.assertRaisesRegex(ValueError,'silently'):dr.validate(d,ROOT)

    def test_anchors_and_requirement_coverage(self):
        d=copy.deepcopy(self.d);d['changes'][0]['anchors'][0]['start']=0
        with self.assertRaisesRegex(ValueError,'range mismatch'):dr.validate(d,ROOT)
        d=copy.deepcopy(self.d);d['requirements'].pop()
        with self.assertRaises(ValueError):dr.validate(d,ROOT)
        d=copy.deepcopy(self.d);d['changes'][0]['anchors'][0]['end']=10000
        with self.assertRaises(ValueError):dr.validate(d,ROOT)

    def test_proposal_and_missing_artifact(self):
        d=copy.deepcopy(self.d);d['document']['artifacts']=[]
        with self.assertRaisesRegex(ValueError,'saved revised'):dr.validate(d,ROOT)
        d=copy.deepcopy(self.d);d['blocks'][1]['status']='proposal'
        with self.assertRaisesRegex(ValueError,'Proposal-only'):dr.validate(d,ROOT)
        d=copy.deepcopy(self.d);d['document']['artifacts'][1]['sha256']='wrong'
        with self.assertRaisesRegex(ValueError,'hash'):dr.validate(d,ROOT)

    def test_safe_rich_math(self):
        self.assertEqual(''.join(dr.SafeHTML('<math><msup><mi>x</mi><mn>3</mn></msup></math>').text),'x3')
        for raw in ['<script>alert(1)</script>','<span onclick="x">x</span>','<span style="background:url(http://x)">x</span>']:
            with self.assertRaises(ValueError):dr.SafeHTML(raw)
        d=copy.deepcopy(self.d);d['blocks'][6]['html']='<math><mi>wrong</mi></math>'
        with self.assertRaisesRegex(ValueError,'differs'):dr.validate(d,ROOT)
        d=copy.deepcopy(self.d);d['comments'][0]['raw_text']='</script><script>alert(1)</script>'
        path=ROOT/'escaped.html';dr.render(d,ROOT,path)
        self.assertNotIn('</script><script>alert(1)',path.read_text())

    def test_feedback_identity_and_link_validation(self):
        f=feedback(self.d,{'m1':'accept','m2':'reject','m3':('discuss','Please explain.')})
        self.assertEqual(dr.check_feedback(self.d,f)['entries'],10)
        for key in ['version','edition_id','ledger_fingerprint','document_id']:
            bad=copy.deepcopy(f);bad[key]='incorrect'
            with self.assertRaises(ValueError):dr.check_feedback(self.d,bad)
        bad=copy.deepcopy(f);bad['entries'][0]['comment_ids']=['wrong']
        with self.assertRaises(ValueError):dr.check_feedback(self.d,bad)
        bad=copy.deepcopy(f);bad['entries'].append(bad['entries'][0])
        with self.assertRaises(ValueError):dr.check_feedback(self.d,bad)

    def test_new_feedback_rejects_old_or_incomplete_exports(self):
        f=feedback(self.d,{})
        for change in [dict(schema_version=1),dict(pending_entries=None),dict(entries=f['entries'][:-1]),dict(pending_entries=f['pending_entries'][:-1])]:
            bad=copy.deepcopy(f);bad.update(change)
            with self.assertRaises(ValueError):dr.check_feedback(self.d,bad)
        for change in [dict(requirement_id='unknown'),dict(comment_ids=['wrong']),dict(decision='accept'),dict(note=3)]:
            bad=copy.deepcopy(f);bad['pending_entries'][0].update(change)
            with self.assertRaises(ValueError):dr.check_feedback(self.d,bad)
        bad=copy.deepcopy(f);bad['pending_entries'].append(copy.deepcopy(bad['pending_entries'][0]))
        with self.assertRaises(ValueError):dr.check_feedback(self.d,bad)

    def test_pending_feedback_reaches_next_plan_without_completing_work(self):
        f=feedback(self.d,{})
        for e,state in zip(f['pending_entries'],['revise','keep','discuss']):e.update(decision=state,note='Next round: verify the supplied evidence.' if state=='revise' else '')
        before=dr.fingerprint(self.d);n=dr.next_plan(self.d,f)
        self.assertEqual(before,dr.fingerprint(self.d))
        actions={r['requirement_id']:r for r in n['continuation']['pending_instructions']}
        self.assertEqual(actions['r9']['action'],'interpret_pending_feedback')
        self.assertEqual(actions['r10']['action'],'retain_current_pending')
        self.assertEqual(actions['r11']['action'],'needs_decision')
        self.assertIn('verify',actions['r9']['note'])
        self.assertEqual([r['status'] for r in n['requirements']], [r['status'] for r in self.d['requirements']])

    def test_explicit_default_accepts_only_completed_explicit_changes(self):
        from review_model import prepare
        before=dr.fingerprint(self.d);v=prepare(self.d,dr.SafeHTML)
        self.assertEqual(v['review_defaults']['m1']['decision'],'accept')
        self.assertEqual(v['review_defaults']['m5']['decision'],'unreviewed')
        self.assertEqual(before,dr.fingerprint(self.d))
        d=copy.deepcopy(self.d);d['changes'][0]['review']={'decision':'reject','note':'Keep the original.'}
        self.assertEqual(prepare(d,dr.SafeHTML)['review_defaults']['m1']['decision'],'reject')
        d=copy.deepcopy(self.d);d['requirements'][0]['status']='partial';d['changes'][0]['status']='partial'
        self.assertEqual(prepare(d,dr.SafeHTML)['review_defaults']['m1']['decision'],'unreviewed')

    def test_precise_contexts_keep_repeated_occurrence_math_and_deleted_paragraph(self):
        from review_model import prepare
        v=prepare(self.d,dr.SafeHTML)
        ctx=v['review_contexts']['m1']['contexts'][0]
        self.assertEqual(ctx['original']['snippet'],'repeated')
        self.assertGreater(ctx['original']['focus'][0],20)
        self.assertEqual(ctx['revised']['snippet'],'revised')
        ctx=v['review_contexts']['m7']['contexts'][0]
        self.assertIn('<math>',ctx['revised']['html']);self.assertEqual(ctx['revised']['snippet'],'3')
        ctx=v['review_contexts']['m9']['contexts'][0]
        self.assertEqual(ctx['original']['snippet'],'This entire paragraph is redundant.')
        self.assertEqual(ctx['revised']['text'],'');self.assertEqual(ctx['revised']['focus'],[0,0])
        self.assertEqual(v['review_contexts']['m4']['contexts'][0]['revised']['snippet'],'')
        self.assertTrue(v['review_contexts']['m5']['contexts'][0]['revised']['snippet'])

    def test_detached_context_and_hierarchy_are_checked(self):
        from review_model import prepare
        d=copy.deepcopy(self.d)
        d['blocks'][0].update(heading_level=0,toc_include=False)
        d['blocks'][1].update(kind='heading',heading_level=2)
        d['changes'][0]['contexts']=[{'original':{'text':'A source sentence.','focus':[2,8]},'revised':{'block_id':'b1','focus':[d['blocks'][1]['revised'].index('revised'),d['blocks'][1]['revised'].index('revised')+7]}}]
        v=prepare(d,dr.SafeHTML)
        self.assertEqual(v['review_toc'][0]['level'],2)
        self.assertEqual(v['review_contexts']['m1']['contexts'][0]['original']['snippet'],'source')
        for side,value in [('original',{'text':'safe','html':'<script>safe</script>','focus':[0,4]}),('original',{'text':'safe','focus':[0,99]}),('revised',{'block_id':'missing','focus':[0,1]})]:
            bad=copy.deepcopy(d);bad['changes'][0]['contexts'][0][side]=value
            with self.assertRaises((ValueError,KeyError)):prepare(bad,dr.SafeHTML)

    def test_next_round_no_mutation_and_dependency_conflict(self):
        d=copy.deepcopy(self.d);d['changes'][1]['depends_on']=['m1'];d['changes'][2]['depends_on']=['m2']
        before=dr.fingerprint(d);f=feedback(d,{'m1':'reject','m2':'reject','m3':'accept','m7':'discuss','m8':('accept','Clarify further.')})
        n=dr.next_plan(d,f);self.assertEqual(dr.fingerprint(d),before)
        with self.assertRaisesRegex(ValueError,'continuation'):dr.render(n,ROOT,ROOT/'unapplied.html')
        self.assertEqual(n['document']['version'],2);self.assertEqual(n['document']['artifacts'],[])
        actions={x['change_id']:x for x in n['continuation']['instructions']}
        self.assertEqual(actions['m1']['action'],'needs_decision');self.assertIn('m3',actions['m1']['blockers'])
        self.assertEqual(actions['m3']['action'],'retain');self.assertEqual(actions['m7']['action'],'needs_decision')
        self.assertEqual(actions['m8']['action'],'interpret_feedback')
        n=dr.next_plan(self.d,feedback(self.d,{'m2':'reject'}))
        self.assertEqual(next(x for x in n['continuation']['instructions'] if x['change_id']=='m2')['action'],'restore_and_reassess')

    def test_overlap_and_cycle(self):
        d=copy.deepcopy(self.d);d['changes'][9]['anchors']=copy.deepcopy(d['changes'][0]['anchors'])
        n=dr.next_plan(d,feedback(d,{'m1':'reject','m10':'accept'}))
        self.assertEqual(n['continuation']['instructions'][0]['action'],'needs_decision')
        d['changes'][0]['depends_on']=['m2'];d['changes'][1]['depends_on']=['m1']
        with self.assertRaisesRegex(ValueError,'cycle'):dr.validate(d,ROOT)

    def test_extract_group_popup_ink_and_immutable_evidence(self):
        inv=dr.extract(self.annotated,ROOT/'inventory.json',images=True)
        self.assertEqual(len(inv['comments']),8)
        self.assertEqual(sum(len(c['annotation_ids']) for c in inv['comments']),10)
        self.assertEqual(sum(c['annotation_type']=='Replace' for c in inv['comments']),2)
        self.assertTrue(any(c['annotation_type']=='Ink' for c in inv['comments']))
        d=dr.init(ROOT/'inventory.json',ROOT/'initial.json');dr.validate(d,ROOT)
        d['comments'][0]['author']='changed'
        with self.assertRaisesRegex(ValueError,'evidence changed'):dr.validate(d,ROOT)

    def test_rotated_cropped_geometry(self):
        self.assertEqual(dr.page_rect([10,20,30,40],[0,0,100,200],0),[.1,.8,.3,.9])
        self.assertEqual(dr.page_rect([10,20,30,40],[0,0,100,200],90),[.1,.1,.2,.3])
        self.assertEqual(dr.page_rect([10,20,30,40],[10,20,110,220],0),[0,.9,.2,1])

    def test_duplicate_annotation_names_preserve_all_records(self):
        from pypdf import PdfReader,PdfWriter
        from pypdf.generic import NameObject,TextStringObject
        w=PdfWriter();w.add_page(PdfReader(self.annotated).pages[0])
        anns=[x.get_object() for x in w.pages[0]['/Annots']]
        anns[-2][NameObject('/NM')]=TextStringObject('duplicate')
        anns[-3][NameObject('/NM')]=TextStringObject('duplicate')
        path=ROOT/'duplicate_names.pdf'
        with path.open('wb') as f:w.write(f)
        one=dr.extract(path,ROOT/'duplicate_inventory.json')
        two=dr.extract(path,ROOT/'duplicate_inventory_repeat.json')
        self.assertEqual(len(one['comments']),8)
        self.assertEqual(len({c['id'] for c in one['comments']}),8)
        self.assertEqual([c['id'] for c in one['comments']],[c['id'] for c in two['comments']])

    def test_cropped_rotated_pdf_evidence(self):
        from pypdf import PdfReader,PdfWriter
        w=PdfWriter();page=PdfReader(self.annotated).pages[0]
        page.cropbox.lower_left=(50,100);page.cropbox.upper_right=(500,760);page.rotate(90);w.add_page(page)
        path=ROOT/'rotated_crop.pdf'
        with path.open('wb') as f:w.write(f)
        inv=dr.extract(path,ROOT/'rotated_inventory.json',images=True)
        self.assertEqual(inv['pages'][0]['rotation'],90)
        self.assertTrue(inv['comments'][0]['selected_text'])
        self.assertTrue(all(0<=n<=1 for c in inv['comments'] for q in c['source']['rects'] for n in q))
        self.assertTrue(Path(inv['comments'][0]['source']['image']).is_file())

    def test_independent_review_scanned_and_source_mismatch(self):
        from PIL import Image,ImageDraw
        from reportlab.pdfgen import canvas
        review=ROOT/'separate_review.pdf';pdf_text(review,[{'revised':'Reviewer: explain the assumption on page 1. Delete the redundant paragraph.'}])
        inv=dr.extract(review,ROOT/'separate_inventory.json',role='review',images=True)
        self.assertFalse(inv['comments']);self.assertIn('explain the assumption',inv['pages'][0]['text'])
        image=Image.new('RGB',(612,792),'white');draw=ImageDraw.Draw(image);draw.text((50,70),'Scanned report with unclear handwritten comment',fill='black');draw.ellipse((50,95,280,135),outline='red',width=3);image.save(ROOT/'scan.png')
        c=canvas.Canvas(str(ROOT/'scan.pdf'));c.drawImage(str(ROOT/'scan.png'),0,0,612,792);c.save()
        inv=dr.extract(ROOT/'scan.pdf',ROOT/'scan_inventory.json',images=True)
        self.assertFalse(inv['pages'][0]['text']);self.assertTrue(inv['warnings'])
        d=copy.deepcopy(self.d);d['document']['source_match']={'status':'partial','reason':'Last section differs from annotated PDF.'}
        d['comments']=[{'id':'scan-comment','raw_text':'','recognized_text':'unclear handwritten note','text_origin':'transcription','author':'Unknown','source':{**dr.file_entry(ROOT/'scan.pdf'),'page':1,'rects':[[.08,.1,.5,.2]]}}]
        d['requirements']=[{'id':'scan-requirement','comment_ids':['scan-comment'],'kind':'ambiguous','status':'needs_decision','change_ids':[],'reason':'Cannot reliably decipher the mark or match the source section.','needs':['Confirm transcription and matching source.']}];d['changes']=[]
        dr.validate(d,ROOT)
        dr.write(ROOT/'scan_pending.json',d)


def main():
    global ROOT
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output');parser.add_argument('--annotated-pdf');parser.add_argument('--expected-comments',type=int);args=parser.parse_args()
    context=tempfile.TemporaryDirectory(prefix='draft-revise-') if not args.output else None
    ROOT=Path(args.output or context.name).resolve();ROOT.mkdir(parents=True,exist_ok=True)
    if any(ROOT.iterdir()):raise SystemExit('Use an empty output directory to preserve existing fixtures.')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Regression))
    if args.annotated_pdf:
        inv=dr.extract(args.annotated_pdf,ROOT/'provided_inventory.json',images=True)
        print(json.dumps({'provided_comments':len(inv['comments']),'annotation_members':sum(len(c['annotation_ids']) for c in inv['comments']),'types':{k:sum(c['annotation_type']==k for c in inv['comments']) for k in sorted({c['annotation_type'] for c in inv['comments']})}},indent=2))
        if args.expected_comments is not None and len(inv['comments'])!=args.expected_comments:raise SystemExit('Provided PDF comment count mismatch')
    print('Fixtures:',ROOT)
    if context:context.cleanup()
    raise SystemExit(0 if result.wasSuccessful() else 1)

if __name__=='__main__':main()
