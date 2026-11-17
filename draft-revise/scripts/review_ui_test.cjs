#!/usr/bin/env node
// Optional DOM regression check. Supply jsdom via your runtime's module search path.
const fs=require('fs'),path=require('path'),assert=require('assert');
const {JSDOM,VirtualConsole}=require('jsdom');
const input=path.resolve(process.argv[2]||''),out=process.argv[3],fileMode=process.argv.includes('--file');
if(!fs.statSync(input).isFile())throw Error('Usage: review_ui_test.cjs REVIEW.html [FEEDBACK.json] [--file]');
const errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(fs.readFileSync(input,'utf8'),{url:fileMode?'file://'+input:'https://offline-review.invalid/',runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,beforeParse(w){w.ResizeObserver=class{observe(){}};w.HTMLElement.prototype.scrollIntoView=function(){};if(!fileMode){w.CSS={highlights:new Map()};w.Highlight=class{};}else w.innerWidth=390;}});
const w=dom.window,d=w.document,e=s=>w.eval(s),get=s=>d.querySelector(s);
assert.deepEqual(errors,[]);
const original=(s)=>{const copy=s.cloneNode(true);copy.querySelectorAll('.insertion-caret').forEach(n=>n.remove());return copy.textContent;};
const data=e('data'),count=e('items.length');let contexts=0,locations=0;
for(let i=0;i<count;i++){
 e(`showItem(${i},false)`);const item=e(`items[${i}]`),views=e(`view(items[${i}])`);
 const expected=e(`cmts(items[${i}]).map(c=>c.raw_text||c.recognized_text)`),shown=[...d.querySelectorAll('#detail .comment')].map(n=>n.textContent);
 expected.filter(Boolean).forEach(c=>assert(shown.includes(c),'raw comment not preserved'));
 assert.equal(d.querySelectorAll('#detail .original-pages').length,0,'page expander belongs only in page view');
 const snippets=[...d.querySelectorAll('#detail .edit-pair')],sentences=[...d.querySelectorAll('#detail .sentence-comparison')];
 if(views.contexts.length){assert.equal(snippets.length,views.contexts.length);assert.equal(sentences.length,views.contexts.length);}
 views.contexts.forEach((c,j)=>{for(const [old,cls]of [[true,'original'],[false,'revised']]){const p=snippets[j].querySelector(old?'.edit-before':'.edit-after'),text=p.querySelector('.focus-fragment');if(c[cls].snippet)assert.equal(text.textContent,c[cls].snippet);else assert(p.querySelector('.empty-fragment'));
 const node=sentences[j].querySelector(old?'.sentence-before .rich-sentence':'.sentence-after .rich-sentence');assert.equal(original(node),Array.from(c[cls].text).slice(...c[cls].sentence).join(''));}contexts++;});
 const needs=item.reqs.filter(r=>r.status!=='implemented');assert.equal(d.querySelectorAll('#detail .pending-editor').length,needs.length);
 if(!needs.length){assert.equal(d.querySelectorAll('#detail textarea').length,0);assert(!get('#detail .policy-settings')?.open);}
 if(views.contexts.length&&views.anchors.length)assert(get('#detail .sentence-after .jump'),'locate must be below revised sentence');
 for(let j=0;j<views.anchors.length;j++){const a=views.anchors[j];if(a.block_id){const text=e(`textNodes(document.querySelector('#block-${a.block_id} .content')).map(n=>n.textContent).join('')`);assert.equal(Array.from(text).slice(a.start,a.end).join(''),a.quote);assert(d.getElementById('anchor-'+item.id+'-'+j));}else assert(d.getElementById('region-'+item.id+'-'+j));e(`reveal(items[${i}],${j})`);locations++;}
 for(const node of d.querySelectorAll('#detail math msup,#detail math msub,#detail math mfrac,#detail math mroot,#detail math mover,#detail math munder'))assert.equal(node.children.length,2,'partial math must keep valid arity');
}
assert.equal(d.querySelectorAll('#summary .pending-card').length,data.requirements.filter(r=>r.status!=='implemented').length);
assert.equal(d.querySelectorAll('#toc-tree .toc-link').length,data.review_toc.length);
assert.equal(d.querySelectorAll('#toc-tree .toc-main').length,1);
const before=e('exportFeedback()');assert.equal(before.schema_version,2);assert.equal(before.entries.length,data.changes.length);assert.equal(before.pending_entries.length,data.requirements.filter(r=>r.status!=='implemented').length);assert.equal(e('validateImported(exportFeedback()).feedback')&&true,true);
for(const field of ['version','edition_id','document_id','ledger_fingerprint'])assert.throws(()=>e(`validateImported({...exportFeedback(),${field}:'wrong'})`));
assert.throws(()=>e('validateImported({...exportFeedback(),schema_version:1})'));
assert.throws(()=>e('validateImported({...exportFeedback(),pending_entries:undefined})'));
if(before.entries.length)assert.throws(()=>e('validateImported({...exportFeedback(),entries:exportFeedback().entries.slice(1)})'));
if(before.pending_entries.length){assert.throws(()=>e('validateImported({...exportFeedback(),pending_entries:exportFeedback().pending_entries.slice(1)})'));assert.throws(()=>e('validateImported({...exportFeedback(),pending_entries:[...exportFeedback().pending_entries,exportFeedback().pending_entries[0]]})'));
 const r=data.requirements.find(r=>r.status!=='implemented'),idx=e(`items.findIndex(i=>i.reqs.some(r=>r.id===${JSON.stringify(r.id)}))`);e(`showItem(${idx},false)`);const editor=get('#detail .pending-editor'),note=editor.querySelector('textarea');note.value='Next round: verify the source, then revise the stated assumption.';note.dispatchEvent(new w.Event('input'));editor.querySelector('[data-pending-decision=revise]').click();
 const other=[...d.querySelectorAll('#summary .pending-editor')].find(n=>n.dataset.pendingId===editor.dataset.pendingId);assert.equal(other.querySelector('textarea').value,note.value);const f=e('exportFeedback()');assert(f.pending_entries.some(q=>q.note===note.value&&q.decision==='revise'));assert.equal(data.requirements.find(q=>q.id===r.id).status,r.status);
}
// Language switch and narrow-screen controls must preserve decisions and source text.
get('#language').value='en';get('#language').dispatchEvent(new w.Event('change'));assert.equal(get('[data-view=summary]').textContent,'Pending items');
if(count){e('showItem(0,false)');w.innerWidth=390;e('reveal(items[0],0)');get('#close').click();assert(get('#panel').classList.contains('collapsed'));get('#show-comments').click();assert(!get('#panel').classList.contains('collapsed'));}
assert.deepEqual(errors,[]);
const feedback=e('exportFeedback()');if(out&&out!=='--file')fs.writeFileSync(out,JSON.stringify(feedback,null,2));
console.log(JSON.stringify({items:count,contexts,locations,default_accepted:before.entries.filter(v=>v.decision==='accept').length,pending_forms:before.pending_entries.length,file_mode:fileMode,errors},null,2));
w.close();
