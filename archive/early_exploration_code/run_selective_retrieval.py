"""Claim-sensitive selective retrieval and evidence-constrained rewriting."""
from __future__ import annotations
import argparse, json, os, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from .evaluate_mcq import call_chat_completion

SYSTEM = """You are an evidence-constrained factual editor. Answer the user using ONLY the supplied web evidence. Correct or remove unsupported draft details. If the evidence is insufficient, explicitly say what cannot be confirmed. Do not invent citations. Keep the response concise."""

def retrieve(query: str) -> list[dict]:
    url = 'https://api.duckduckgo.com/?' + urllib.parse.urlencode({'q':query,'format':'json','no_html':1,'skip_disambig':1})
    with urllib.request.urlopen(url, timeout=30) as r: data=json.loads(r.read().decode('utf-8'))
    evidence=[]
    if data.get('AbstractText'): evidence.append({'url':data.get('AbstractURL',''),'text':data['AbstractText']})
    for item in data.get('RelatedTopics',[]):
        if isinstance(item,dict) and item.get('Text') and item.get('FirstURL'): evidence.append({'url':item['FirstURL'],'text':item['Text']})
        if len(evidence)>=3: break
    if not evidence:
        wiki = 'https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode({'action':'query','list':'search','srsearch':query,'srlimit':3,'format':'json','utf8':1})
        with urllib.request.urlopen(wiki, timeout=30) as r: results=json.loads(r.read().decode('utf-8'))
        for item in results.get('query',{}).get('search',[]):
            title=item.get('title','')
            snippet=item.get('snippet','').replace('<span class="searchmatch">','').replace('</span>','')
            if title and snippet:
                evidence.append({'url':'https://en.wikipedia.org/wiki/' + urllib.parse.quote(title.replace(' ','_')),'text':snippet})
    return evidence

def main() -> None:
 p=argparse.ArgumentParser(); p.add_argument('--config',required=True); p.add_argument('--input',required=True); p.add_argument('--out',required=True); p.add_argument('--threshold',type=int,required=True); p.add_argument('--limit',type=int); a=p.parse_args()
 cfg=json.loads(Path(a.config).read_text(encoding='utf-8')); key=os.environ.get(cfg['api_key_env'])
 if not key: raise RuntimeError(f"Missing environment variable: {cfg['api_key_env']}")
 vc={**cfg,'system_prompt':SYSTEM,'max_tokens':768}; n=used=0; Path(a.out).parent.mkdir(parents=True,exist_ok=True)
 with Path(a.input).open(encoding='utf-8-sig') as src,Path(a.out).open('w',encoding='utf-8') as sink:
  for line in src:
   if not line.strip() or (a.limit is not None and n>=a.limit): continue
   row=json.loads(line); direct=row['direct']; high=row.get('risk_score',0)>=a.threshold; final=direct['raw_output']; evidence=[]; meta=None
   if high:
    evidence=retrieve(direct['prompt']); block='\n'.join(f"SOURCE: {x['url']}\n{x['text']}" for x in evidence) or 'NO RETRIEVED EVIDENCE.'
    prompt=f"QUESTION:\n{direct['prompt']}\n\nDRAFT:\n{direct['raw_output']}\n\nWEB EVIDENCE:\n{block}\n\nREVISED ANSWER:"
    final,_,usage,latency,model=call_chat_completion(vc,key,prompt); used+=1; meta={'returned_model':model,'usage':usage,'latency_s':latency,'timestamp_utc':datetime.now(timezone.utc).isoformat()}
   sink.write(json.dumps({'item':direct['item'],'method':'consc_selective_retrieval','risk_score':row.get('risk_score'),'threshold':a.threshold,'retrieved':high,'evidence':evidence,'direct_output':direct['raw_output'],'final_output':final,'annotation':None,'metadata':meta},ensure_ascii=False)+'\n'); n+=1; print(f"completed {n}: {direct['item']['id']} retrieved={high} evidence={len(evidence)}")
 print(json.dumps({'n':n,'retrieved_n':used,'out':a.out},ensure_ascii=False))
if __name__=='__main__': main()
