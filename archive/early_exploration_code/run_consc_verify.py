"""Apply selective factual verification and conservative rewriting to high-risk rows."""
from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from .evaluate_mcq import call_chat_completion

SYSTEM = """You are a factual verification editor. Check the draft answer against your independent knowledge. Rewrite it conservatively: remove or qualify details you cannot support, correct contradictions, never invent sources, and answer the user directly. Keep it under 220 English words or equivalent."""

def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument('--config',required=True); p.add_argument('--input',required=True); p.add_argument('--out',required=True); p.add_argument('--threshold',type=int,required=True); p.add_argument('--limit',type=int)
    a=p.parse_args(); cfg=json.loads(Path(a.config).read_text(encoding='utf-8')); key=os.environ.get(cfg['api_key_env'])
    if not key: raise RuntimeError(f"Missing environment variable: {cfg['api_key_env']}")
    vc={**cfg,'system_prompt':SYSTEM,'max_tokens':768}; n=verified=0; Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    with Path(a.input).open(encoding='utf-8-sig') as src, Path(a.out).open('w',encoding='utf-8') as sink:
      for line in src:
        if not line.strip() or (a.limit is not None and n>=a.limit): continue
        row=json.loads(line); direct=row['direct']; high=row.get('risk_score',0)>=a.threshold; final=direct['raw_output']; meta=None
        if high:
          prompt=f"USER QUESTION:\n{direct['prompt']}\n\nDRAFT ANSWER:\n{direct['raw_output']}\n\nREVISED ANSWER:"
          final,_,usage,latency,model=call_chat_completion(vc,key,prompt); verified+=1
          meta={'returned_model':model,'usage':usage,'latency_s':latency,'timestamp_utc':datetime.now(timezone.utc).isoformat()}
        sink.write(json.dumps({'item':direct['item'],'method':'consc_verify','risk_score':row.get('risk_score'),'threshold':a.threshold,'verified':high,'direct_output':direct['raw_output'],'final_output':final,'annotation':None,'verification_metadata':meta},ensure_ascii=False)+'\n'); n+=1
        print(f"completed {n}: {direct['item']['id']} verified={high}")
    print(json.dumps({'n':n,'verified_n':verified,'verification_rate':verified/n if n else 0,'out':a.out},ensure_ascii=False))
if __name__=='__main__': main()
