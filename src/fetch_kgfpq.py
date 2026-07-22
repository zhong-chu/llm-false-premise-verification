"""Download the official KG-FPQ Yes/No files without modifying their contents."""
from __future__ import annotations
import argparse, hashlib, json, urllib.request
from pathlib import Path

FILES = ('art_YN.json', 'people_YN.json', 'place_YN.json')
BASE = 'https://raw.githubusercontent.com/yanxuzhu/KG-FPQ/main/KG-FPQ-data/'

def main():
 p=argparse.ArgumentParser(); p.add_argument('--out-dir',default='data/kgfpq/raw'); a=p.parse_args(); root=Path(a.out_dir); root.mkdir(parents=True,exist_ok=True); manifest=[]
 for name in FILES:
  payload=urllib.request.urlopen(BASE+name,timeout=60).read(); path=root/name; path.write_bytes(payload)
  manifest.append({'file':name,'url':BASE+name,'sha256':hashlib.sha256(payload).hexdigest(),'bytes':len(payload)})
 (root/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8'); print(json.dumps(manifest,indent=2))
if __name__=='__main__': main()
