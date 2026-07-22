"""Freeze a ConSC-Verify risk threshold on the development set only."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def main() -> None:
    p = argparse.ArgumentParser(); p.add_argument("--input", required=True); p.add_argument("--out", required=True); p.add_argument("--target-error-recall", type=float, default=.80)
    a = p.parse_args()
    rows = [json.loads(x) for x in Path(a.input).read_text(encoding="utf-8-sig").splitlines() if x.strip()]
    rows = [x for x in rows if x.get("risk_score") in {1,2,3,4,5} and x["direct"].get("annotation", {}).get("label") in {"supported","unsupported","undecidable"}]
    bad = [x for x in rows if x["direct"]["annotation"]["label"] == "unsupported"]
    if not bad: raise ValueError("No unsupported labels to calibrate")
    curve=[]
    for t in range(1,6):
        routed=[x for x in rows if x["risk_score"]>=t]; caught=[x for x in bad if x["risk_score"]>=t]
        curve.append({"threshold":t,"verification_rate":len(routed)/len(rows),"error_recall":len(caught)/len(bad),"routed_n":len(routed),"unsupported_caught_n":len(caught)})
    q=[x for x in curve if x["error_recall"]>=a.target_error_recall]
    chosen=min(q,key=lambda x:x["verification_rate"]) if q else max(curve,key=lambda x:x["error_recall"])
    result={"n":len(rows),"unsupported_n":len(bad),"target_error_recall":a.target_error_recall,"curve":curve,"selected":chosen}
    Path(a.out).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8"); print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__ == "__main__": main()
