"""Deterministic large-scale recovery evaluation for the Mini-C grammar.

This measures parser recovery on controlled mutations of known-valid programs.
It does NOT claim semantic repair accuracy: the parser's recovered output is
compared for parse validity and preservation of selected unaffected fragments.
Run: python evaluate_recovery.py [--cases 1000]
"""
import argparse, json, random, time
from pathlib import Path
from compiler.parser import analyze_source, validate_source

SEEDS = [
    ("int a; a = 1; print(a);", "a = 1;", "print(a);"),
    ("int a, b; a = b + 2; print(a);", "a = b + 2;", "print(a);"),
    ("int x; x = (3 + 4); print(x);", "x = (3 + 4);", "print(x);"),
    ("int n; n = 9; if (n > 2) { print(n); }", "n = 9;", "print(n);"),
    ("int x, y; x = 2; y = x * 3; print(y);", "y = x * 3;", "print(y);"),
    ("int count; count = 0; while (count < 3) { count = count + 1; } print(count);", "count = count + 1;", "print(count);"),
    ("int a; a = 5 + 6; print(a);", "a = 5 + 6;", "print(a);"),
    ("int a, b, c; a = b + c; print(a);", "a = b + c;", "print(a);"),
]
def mutate(src, rng):
    lines = src.splitlines()
    choices = [
        ("missing_semicolon", lambda s: s.replace("; print", " print", 1)),
        ("missing_operand", lambda s: s.replace(" + ", " + ", 1).replace(" + c;", " + ;", 1) if " + c;" in s else s.replace(" + 2;", " + ;", 1) if " + 2;" in s else s.replace(" + 6;", " + ;", 1) if " + 6;" in s else s.replace(" * 3;", " * ;", 1) if " * 3;" in s else s.replace(" = 1;", " = ;", 1)),
        ("missing_close_paren", lambda s: s.replace(");", ";", 1) if ");" in s else s.replace(");", ";", 1)),
        ("missing_close_brace", lambda s: s[:-1] if s.endswith("}") else s),
        ("missing_assignment_rhs", lambda s: s.replace(" = 1;", " = ;", 1) if " = 1;" in s else s.replace(" = 2;", " = ;", 1)),
        ("operator_removed", lambda s: s.replace(" + ", " ", 1) if " + " in s else s.replace(" * ", " ", 1)),
    ]
    # Pick a mutation that actually changes source; otherwise try others.
    order = list(range(len(choices))); rng.shuffle(order)
    for idx in order:
        name, fn = choices[idx]
        candidate = fn(src)
        if candidate != src:
            return name, candidate
    return "unchanged_fallback", src + "\n"
def run(n):
    rng = random.Random(20261027)
    counts = {}
    examples = []
    valid_inputs = 0
    exceptions = 0
    recovered_valid = 0
    any_change = 0
    for i in range(n):
        seed, focus, preserve = rng.choice(SEEDS)
        if not validate_source(seed):
            continue
        valid_inputs += 1
        kind, broken = mutate(seed, rng)
        try:
            result = analyze_source(broken, "automatic")
            recovered = result.get("recovered_source", broken)
            valid = validate_source(recovered)
            changed = recovered != broken
            recovered_valid += int(valid)
            any_change += int(changed)
            rec = counts.setdefault(kind, {"cases":0,"valid_recovery":0,"changed":0,"exceptions":0})
            rec["cases"] += 1; rec["valid_recovery"] += int(valid); rec["changed"] += int(changed)
            if len(examples) < 12:
                examples.append({"mutation":kind,"input":broken,"recovered":recovered,"valid":valid,"errors_remaining":len(result.get("errors",[]))})
        except Exception as exc:
            exceptions += 1
            rec = counts.setdefault(kind, {"cases":0,"valid_recovery":0,"changed":0,"exceptions":0})
            rec["cases"] += 1; rec["exceptions"] += 1
    report = {
        "evaluation": "controlled synthetic syntax mutations",
        "seed": 20261027,
        "requested_cases": n,
        "valid_seed_programs": valid_inputs,
        "cases_evaluated": sum(x["cases"] for x in counts.values()),
        "recovered_outputs_that_parse": recovered_valid,
        "parse_validity_rate": round(recovered_valid / max(1, sum(x["cases"] for x in counts.values())), 4),
        "outputs_changed": any_change,
        "unhandled_exceptions": exceptions,
        "by_mutation": counts,
        "sample_cases": examples,
        "limitations": [
            "Synthetic controlled mutations only; not a real-world benchmark.",
            "Parse validity does not prove the repair matches the programmer's intent.",
            "Some generated mutations may remove more than one syntactic feature."
        ]
    }
    Path("evaluation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k not in ("sample_cases","by_mutation")}, indent=2))
    print("By mutation:")
    for k,v in counts.items(): print(f"  {k}: {v['valid_recovery']}/{v['cases']} parse-valid, {v['exceptions']} exceptions")
    print("Detailed report saved to evaluation_report.json")
if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=1000)
    args=parser.parse_args()
    run(max(1,args.cases))
