"""Evaluate the Flask repair-candidate generator on controlled mutations.

Requires project dependencies (`python -m pip install -r requirements.txt`).
Run: python evaluate_candidates.py --cases 500
Measures whether at least one offered candidate parses; not semantic correctness.
"""
import argparse, json, random
from pathlib import Path
from app import build_correction_options
from compiler.parser import validate_source

SEEDS = [
    "int a, b, c; a = b + c; print(a);",
    "int x; x = 10; print(x);",
    "int a, b; a = b * 3; print(a);",
    "int n; n = 0; while (n < 3) { n = n + 1; } print(n);",
    "int x; x = (3 + 4); print(x);",
]
def mutations(src):
    out=[]
    transforms=[
        ("missing_operand", lambda s:s.replace(" + c;", " + ;",1) if " + c;" in s else s.replace(" * 3;", " * ;",1) if " * 3;" in s else s.replace(" = 10;", " = ;",1) if " = 10;" in s else s),
        ("missing_semicolon", lambda s:s.replace("; print", " print",1)),
        ("missing_close_paren", lambda s:s.replace(");", ";",1)),
        ("missing_operator", lambda s:s.replace(" + ", " ",1) if " + " in s else s.replace(" * ", " ",1)),
        ("missing_rhs", lambda s:s.replace(" = 10;", " = ;",1) if " = 10;" in s else s.replace(" = 0;", " = ;",1)),
    ]
    for name, fn in transforms:
        broken=fn(src)
        if broken != src:
            out.append((name, broken))
    return out
def run(n):
    rng=random.Random(20261030)
    cases=[]
    while len(cases)<n:
        src=rng.choice(SEEDS)
        opts=mutations(src)
        if opts: cases.append((src,*rng.choice(opts)))
    by_type={}
    exceptions=0
    for original, kind, broken in cases:
        try:
            proposals=build_correction_options(broken, broken, "automatic")
            valid=[p for p in proposals if validate_source(p.get("source",""))]
            row=by_type.setdefault(kind,{"cases":0,"any_valid_candidate":0,"candidate_count":0})
            row["cases"]+=1
            row["any_valid_candidate"]+=int(bool(valid))
            row["candidate_count"]+=len(proposals)
        except Exception:
            exceptions+=1
            row=by_type.setdefault(kind,{"cases":0,"any_valid_candidate":0,"candidate_count":0})
            row["cases"]+=1
    total=sum(x["cases"] for x in by_type.values())
    passed=sum(x["any_valid_candidate"] for x in by_type.values())
    report={"evaluation":"Flask candidate-generator controlled mutations","requested_cases":n,"cases_evaluated":total,
            "cases_with_at_least_one_parse_valid_candidate":passed,
            "candidate_parse_validity_coverage":round(passed/max(total,1),4),
            "unhandled_exceptions":exceptions,"by_mutation":by_type,
            "limitations":["Synthetic small Mini-C examples only.","At least one candidate parsing is not the same as selecting the intended repair.",
                           "Semantic correctness is not measured."]}
    Path("candidate_evaluation_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
    print("Saved candidate_evaluation_report.json")
if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--cases",type=int,default=500)
    args=ap.parse_args(); run(max(1,args.cases))
