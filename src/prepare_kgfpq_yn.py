"""Create a frozen, balanced KG-FPQ false-premise Yes/No test set."""
from __future__ import annotations
import argparse,json,random,re
from pathlib import Path

def main():
 p=argparse.ArgumentParser(); p.add_argument('--raw-dir',default='data/kgfpq/raw'); p.add_argument('--out',required=True); p.add_argument('--per-stratum',type=int,default=20); p.add_argument('--seed',type=int,default=20260820); p.add_argument('--exclude',help='Existing KG-FPQ JSONL split whose source records must not be sampled.'); a=p.parse_args()
 rng=random.Random(a.seed); out=[]; excluded={domain:set() for domain in ('art','people','place')}
 if a.exclude:
  pattern=re.compile(r'^kgfpq-(art|people|place)-[1-6]-(.+)$')
  for line in Path(a.exclude).read_text(encoding='utf-8-sig').splitlines():
   if not line.strip(): continue
   item=json.loads(line); match=pattern.match(item['id'])
   if not match: raise ValueError(f"Cannot recover source record id from: {item['id']}")
   excluded[match.group(1)].add(match.group(2))
 for domain in ('art','people','place'):
  rows=json.loads((Path(a.raw_dir)/f'{domain}_YN.json').read_text(encoding='utf-8'))
  used=set(excluded[domain])
  for level in range(1,7):
   candidates=[row for row in rows if row['id'] not in used]
   chosen=rng.sample(candidates,a.per_stratum); used.update(row['id'] for row in chosen)
   for row in chosen:
    out.append({'id':f"kgfpq-{domain}-{level}-{row['id']}",'source_record_id':row['id'],'question':row[f'FPQ_{level}'],'expected':'NO','domain':domain,'confusability_level':level,'evidence_true_triple':row['Ttriple'],'source':'KG-FPQ YN'})
 rng.shuffle(out); Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in out),encoding='utf-8')
 print(json.dumps({'n':len(out),'per_stratum':a.per_stratum,'seed':a.seed,'exclude':a.exclude,'excluded_source_records':sum(len(v) for v in excluded.values()),'out':a.out},ensure_ascii=False))
if __name__=='__main__': main()
