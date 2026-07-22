"""Rewrite selected outputs using versioned local evidence only."""
from __future__ import annotations
import argparse,json,os
from pathlib import Path
from .evaluate_mcq import call_chat_completion
SYSTEM="Use ONLY the supplied evidence. Rewrite the draft to answer the question; remove claims the evidence cannot support. Do not invent citations."
def main():
 p=argparse.ArgumentParser(); p.add_argument('--config',required=True); p.add_argument('--input',required=True); p.add_argument('--evidence',required=True); p.add_argument('--out',required=True); a=p.parse_args()
 cfg=json.loads(Path(a.config).read_text(encoding='utf-8')); key=os.environ.get(cfg['api_key_env'])
 if not key: raise RuntimeError(f"Missing environment variable: {cfg['api_key_env']}")
 ev={x['id']:x for x in [json.loads(l) for l in Path(a.evidence).read_text(encoding='utf-8').splitlines() if l.strip()]}; vc={**cfg,'system_prompt':SYSTEM,'max_tokens':512}
 with Path(a.out).open('w',encoding='utf-8') as sink:
  for line in Path(a.input).read_text(encoding='utf-8-sig').splitlines():
   if not line.strip(): continue
   row=json.loads(line); ident=row['item']['id']
   if ident not in ev: continue
   e=ev[ident]; evidence_text=e['evidence'].encode('utf-8').decode('unicode_escape'); prompt=f"QUESTION:\n{row['item']['question']}\n\nDRAFT:\n{row['direct_output']}\n\nEVIDENCE ({e['source_url']}):\n{evidence_text}\n\nREVISED ANSWER:"
   out,_,usage,latency,model=call_chat_completion(vc,key,prompt); sink.write(json.dumps({'id':ident,'evidence':e,'final_output':out,'usage':usage,'latency_s':latency,'model':model},ensure_ascii=False)+'\n'); print('completed',ident)
if __name__=='__main__': main()
