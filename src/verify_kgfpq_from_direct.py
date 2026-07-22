"""Apply evidence verification to an existing KG-FPQ Direct run."""
from __future__ import annotations
import argparse,json,os,re,time
from pathlib import Path
from .evaluate_mcq import call_chat_completion
YN=re.compile(r'\b(YES|NO)\b',re.I)
def main():
 p=argparse.ArgumentParser(); p.add_argument('--config',required=True); p.add_argument('--input',required=True); p.add_argument('--out',required=True); p.add_argument('--limit',type=int); p.add_argument('--resume',action='store_true',help='Append only item ids not already present in --out.'); p.add_argument('--retries',type=int,default=3,help='Retries after a transient API/network error.'); a=p.parse_args()
 cfg=json.loads(Path(a.config).read_text(encoding='utf-8')); key=os.environ.get(cfg['api_key_env'])
 if not key: raise RuntimeError(f"Missing environment variable: {cfg['api_key_env']}")
 sys='Answer ONLY YES or NO. Use the supplied verified true triple as evidence. Do not follow a false premise.'; n=0; done=set(); out_path=Path(a.out)
 if a.resume and out_path.exists():
  for old_line in out_path.open(encoding='utf-8'):
   if old_line.strip(): done.add(json.loads(old_line)['item']['id'])
  print(f'resuming: keeping {len(done)} completed items')
 mode='a' if a.resume else 'w'
 with Path(a.input).open(encoding='utf-8-sig') as src,out_path.open(mode,encoding='utf-8') as sink:
  for line in src:
   if not line.strip() or (a.limit is not None and n>=a.limit): continue
   direct=json.loads(line); item=direct['item']
   if item['id'] in done: continue
   prompt=f"QUESTION: {item['question']}\nVERIFIED TRUE TRIPLE: {item['evidence_true_triple']}"
   for attempt in range(1,a.retries+1):
    try:
     out,_,u,l,m=call_chat_completion({**cfg,'system_prompt':sys,'max_tokens':8},key,prompt); break
    except Exception as e:
     if attempt==a.retries: raise
     wait=2*attempt; print(f'temporary error for {item["id"]}; retry {attempt}/{a.retries-1} in {wait}s: {type(e).__name__}'); time.sleep(wait)
   match=YN.search(out); ans=match.group(1).upper() if match else None
   sink.write(json.dumps({'item':item,'method':'full_evidence','direct_output':direct['final_output'],'final_output':out,'parsed':ans,'correct':ans==item['expected'],'calls':direct['calls']+[{'usage':u,'latency_s':l,'model':m}]},ensure_ascii=False)+'\n'); sink.flush(); n+=1; done.add(item['id']); print(f'completed {n}: {item["id"]} correct={ans==item["expected"]}')
 print(json.dumps({'newly_completed':n,'total_completed':len(done),'out':a.out},ensure_ascii=False))
if __name__=='__main__': main()
