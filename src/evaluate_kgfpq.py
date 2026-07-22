"""Evaluate Direct, full-evidence, or selective-evidence methods on KG-FPQ YN."""
from __future__ import annotations
import argparse,json,os,re
from pathlib import Path
from .evaluate_mcq import call_chat_completion
from .score_consc_risk import AUDITOR
YN=re.compile(r'\b(YES|NO)\b',re.I)
def parse(s):
 m=YN.search(s); return m.group(1).upper() if m else None
def ask(cfg,key,system,prompt,max_tokens=8): return call_chat_completion({**cfg,'system_prompt':system,'max_tokens':max_tokens},key,prompt)
def main():
 p=argparse.ArgumentParser(); p.add_argument('--config',required=True); p.add_argument('--input',required=True); p.add_argument('--out',required=True); p.add_argument('--method',choices=('direct','full_evidence','consc'),required=True); p.add_argument('--threshold',type=int,default=4); p.add_argument('--limit',type=int); a=p.parse_args()
 cfg=json.loads(Path(a.config).read_text(encoding='utf-8')); key=os.environ.get(cfg['api_key_env'])
 if not key: raise RuntimeError(f"Missing environment variable: {cfg['api_key_env']}")
 base='Answer ONLY YES or NO. Do not follow a false premise; answer NO if the asserted relation is false.'; evsys=base+' Use the supplied verified triple as evidence.'; n=0; Path(a.out).parent.mkdir(parents=True,exist_ok=True)
 with Path(a.input).open(encoding='utf-8-sig') as src,Path(a.out).open('w',encoding='utf-8') as sink:
  for line in src:
   if not line.strip() or (a.limit is not None and n>=a.limit): continue
   item=json.loads(line); q=item['question']; calls=[]; direct,_,u,l,m=ask(cfg,key,base,q); calls.append({'usage':u,'latency_s':l,'model':m})
   risk=None; final=direct; verified=False
   if a.method=='full_evidence':
    final,_,u,l,m=ask(cfg,key,evsys,f"QUESTION: {q}\nVERIFIED TRUE TRIPLE: {item['evidence_true_triple']}"); calls.append({'usage':u,'latency_s':l,'model':m}); verified=True
   elif a.method=='consc':
    raw,_,u,l,m=ask(cfg,key,AUDITOR,f"QUESTION: {q}\nPROPOSED ANSWER: {direct}\nRISK:"); calls.append({'usage':u,'latency_s':l,'model':m}); risk=int(raw.strip()[0]) if raw.strip()[:1] in '12345' else None
    if risk is not None and risk>=a.threshold:
     final,_,u,l,m=ask(cfg,key,evsys,f"QUESTION: {q}\nVERIFIED TRUE TRIPLE: {item['evidence_true_triple']}"); calls.append({'usage':u,'latency_s':l,'model':m}); verified=True
   ans=parse(final); sink.write(json.dumps({'item':item,'method':a.method,'direct_output':direct,'final_output':final,'parsed':ans,'correct':ans==item['expected'],'risk_score':risk,'verified':verified,'calls':calls},ensure_ascii=False)+'\n'); n+=1; print(f'completed {n}: correct={ans==item["expected"]} verified={verified}')
 print(json.dumps({'n':n,'method':a.method,'out':a.out},ensure_ascii=False))
if __name__=='__main__': main()
