
from flask import Flask, render_template, request, jsonify
from compiler.parser import analyze_source, validate_source
from correction_engine import rank_candidates, semantic_diagnostics
import re
import difflib

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}

    source = data.get("source", "")
    strategy = data.get("strategy", "automatic")

    if not isinstance(source, str):
        return jsonify({"error": "Source code must be text."}), 400

    if not isinstance(strategy, str):
        return jsonify({"error": "Strategy must be text."}), 400

    try:
        result = analyze_source(source, strategy)
        # Try a bounded, conservative source-level repair pass for multiple local errors.
        # Only adopt it when the entire program validates and meaningful source tokens remain.
        pipeline_candidate = repair_source_iterative(source)
        if (pipeline_candidate != source and validate_source(pipeline_candidate)
                and _repair_preserves_program(source, pipeline_candidate)):
            result["recovered_source"] = pipeline_candidate
            result["recovery_success"] = True
        # Mandatory final gate: never present an unvalidated parser attempt as
        # repaired code. Keep the attempted output for diagnostics, but expose it
        # as recovered_source only if the complete program passes the Mini-C parser.
        recovery_attempt = result.get("recovered_source", source)
        try:
            recovery_attempt_valid = bool(validate_source(recovery_attempt))
            if recovery_attempt != source and not _repair_preserves_program(source, recovery_attempt):
                recovery_attempt_valid = False
        except Exception:
            recovery_attempt_valid = False
        result["recovery_attempt"] = recovery_attempt
        result["recovered_source_valid"] = recovery_attempt_valid
        result["recovery_validation"] = {
            "passed": recovery_attempt_valid,
            "scope": "configured Mini-C grammar; not full ISO C",
            "message": (
                "The complete proposed program passed syntax validation."
                if recovery_attempt_valid else
                "No whole-program-valid recovery was produced. The attempted output is not presented as corrected code; check diagnostics and confirm the input uses supported Mini-C syntax."
            ),
        }
        if not recovery_attempt_valid:
            result["recovered_source"] = source
            result["recovery_success"] = False
        else:
            result["recovered_source"] = recovery_attempt
            result["recovery_success"] = True

        raw_options = build_correction_options(source, recovery_attempt, strategy)
        ranked_options = rank_candidates(raw_options, source)
        # Only show unique, changed, syntax-valid repairs. Never invent weak options
        # merely to fill three slots; ranking determines which eligible candidates win.
        seen_repairs = set()
        eligible_options = []
        for option in ranked_options:
            candidate = option.get("source", "")
            if not candidate or candidate == source or candidate in seen_repairs:
                continue
            if not option.get("syntax_valid", False):
                continue
            seen_repairs.add(candidate)
            eligible_options.append(option)
        result["correction_options"] = eligible_options[:3]
        # If parser recovery failed, promote the highest-ranked candidate only
        # after the complete candidate has passed validation and preservation checks.
        if not recovery_attempt_valid and result["correction_options"]:
            best_repair = result["correction_options"][0]["source"]
            if validate_source(best_repair) and _repair_preserves_program(source, best_repair):
                result["recovered_source"] = best_repair
                result["recovery_attempt"] = best_repair
                result["recovered_source_valid"] = True
                result["recovery_success"] = True
                result["recovery_validation"] = {
                    "passed": True,
                    "scope": "configured Mini-C grammar; not full ISO C",
                    "message": "The complete recommended correction passed syntax validation and the source-preservation check.",
                }
        result["correction_options_meta"] = {
            "limit": 3,
            "returned": len(result["correction_options"]),
            "policy": "up to three unique, changed, syntax-valid candidates; fewer when fewer qualify",
        }
        result["semantic_diagnostics"] = semantic_diagnostics(result.get("recovered_source", source))
        # Explainable presentation data: line-level diff, compact structural outline,
        # and consistent source locations for diagnostics.
        recovered = result.get("recovered_source", source)
        result["source_diff"] = [
            {"kind": "equal" if line.startswith(" ") else "insert" if line.startswith("+") else "delete",
             "text": line[1:] if line[:1] in {" ", "+", "-"} else line}
            for line in difflib.unified_diff(source.splitlines(), recovered.splitlines(),
                                             fromfile="original", tofile="proposed", lineterm="")
            if not line.startswith(("---", "+++", "@@"))
        ]
        result["parse_outline"] = build_parse_outline(recovered)
        result["diagnostic_summary"] = {
            "syntax_errors": len(result.get("errors", [])),
            "lexical_errors": len(result.get("lexical_errors", [])),
            "semantic_warnings": len(result.get("semantic_diagnostics", [])),
            "locations": [{"line": e.get("line", 1), "column": e.get("column", 1),
                           "message": e.get("message", "Syntax error"),
                           "expected": e.get("expected", []), "unexpected": e.get("unexpected")}
                          for e in result.get("errors", [])]
        }
        from pathlib import Path
        import json
        try:
            model_meta = json.loads(Path(__file__).with_name("correction_ranker.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            model_meta = {}
        result["model_info"] = {
            "type": model_meta.get("model_type", "heuristic-fallback") + " + rule-based recovery",
            "artifact": "correction_ranker.json",
            "version": model_meta.get("version", 0),
            "training_examples": model_meta.get("training_examples", 0),
            "validation_examples": model_meta.get("validation_examples", 0),
            "synthetic_validation_accuracy": model_meta.get("validation_accuracy"),
            "note": model_meta.get("training_note", "No trained ranker metadata available; heuristic fallback is active.")
        }
        return jsonify(result)
    except Exception as exc:
        app.logger.exception("Analysis failed")
        return jsonify({"error": str(exc)}), 500


def build_parse_outline(source):
    """Return a lightweight, explicitly approximate structural outline for the UI."""
    clean = re.sub(r"//[^\n]*|/\*[\s\S]*?\*/", " ", source)
    declarations = re.findall(r"\b(int|float|void)\s+([A-Za-z_]\w*)", clean)
    functions = re.findall(r"\b(?:int|float|void)\s+([A-Za-z_]\w*)\s*\(", clean)
    statements = []
    for number, line in enumerate(clean.splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"(?:int|float|void)\b", stripped): kind = "declaration / function"
        elif re.match(r"if\b", stripped): kind = "conditional"
        elif re.match(r"while\b", stripped): kind = "loop"
        elif re.match(r"return\b", stripped): kind = "return statement"
        elif re.match(r"print\s*\(", stripped): kind = "print statement"
        elif "=" in stripped: kind = "assignment / expression"
        elif "{" in stripped or "}" in stripped: kind = "block delimiter"
        else: kind = "statement / token sequence"
        statements.append({"line": number, "kind": kind, "text": stripped[:140]})
    return {"kind": "Mini-C program outline (approximate)",
            "functions": list(dict.fromkeys(functions)),
            "declarations": [{"type": typ, "name": name} for typ, name in declarations],
            "statements": statements}


@app.route("/benchmark", methods=["GET"])
def benchmark():
    """Run a small transparent smoke benchmark; not a claim of general C accuracy."""
    cases = [
        {"name": "valid declaration", "source": "int a;", "expected_valid": True},
        {"name": "valid assignment", "source": "int a; a = 2;", "expected_valid": True},
        {"name": "missing semicolon", "source": "int a", "expected_valid": False},
        {"name": "missing operand", "source": "int a; a = 1 + ;", "expected_valid": False},
        {"name": "unclosed block", "source": "if (a > 0) { print(a);", "expected_valid": False},
        {"name": "valid function", "source": "int main() { int a; a = 1; return a; }", "expected_valid": True},
        {"name": "valid expression", "source": "int a, b; a = b + 2;", "expected_valid": True},
        {"name": "missing operator", "source": "int a, b; a = a b;", "expected_valid": False},
    ]
    results = []
    for case in cases:
        observed = bool(validate_source(case["source"]))
        results.append({**case, "observed_valid": observed, "passed": observed == case["expected_valid"]})
    passed = sum(item["passed"] for item in results)
    return jsonify({"title": "Mini-C smoke benchmark", "scope": "8 fixed sanity cases; not a generalization or real-world accuracy estimate",
                    "total": len(results), "passed": passed, "failed": len(results)-passed,
                    "pass_rate": round(passed / len(results), 4), "cases": results})


def repair_source_iterative(source):
    """Apply conservative local repairs, accepting only a whole-program-valid result."""
    if not isinstance(source, str) or not source.strip():
        return source
    candidate = source
    # Repair common malformed function-call punctuation and adjacent simple arguments.
    candidate = re.sub(
        r"\b([A-Za-z_]\w*)\s*;\s*\(([^()]*?)\)",
        lambda m: m.group(1) + "(" + re.sub(r"(?<=[A-Za-z0-9_)])\s+(?=[A-Za-z_(])", ", ", m.group(2).strip()) + ")",
        candidate,
    )
    # Repair a missing binary operator between two simple expression atoms
    # in an assignment (e.g. `int c = a b;` -> `int c = a + b;`).
    # This runs before parser recovery can turn the expression into `a ;b;`.
    adjacent_atoms = re.compile(
        r"(?m)(\b[A-Za-z_]\w*\s*=\s*)([A-Za-z_]\w*|\d+(?:\.\d+)?)"
        r"\s+([A-Za-z_]\w*|\d+(?:\.\d+)?)(\s*;)"
    )
    candidate = adjacent_atoms.sub(
        lambda m: m.group(1) + m.group(2) + " + " + m.group(3) + m.group(4),
        candidate,
    )
    # Remove an operator that appears immediately after another binary operator.
    candidate = re.sub(r"([+\-*/])\s+[*/]\s+(?=[A-Za-z_0-9(])", r"\1 ", candidate)
    # Insert missing ')' before an opening block brace in common if/while conditions.
    def close_control_condition(match):
        text = match.group(0)
        if text.count("(") > text.count(")"):
            return text[:-1].rstrip() + ") {"
        return text
    candidate = re.sub(r"(?m)\b(if|while)\s*\([^{}\n]*\s*\{", close_control_condition, candidate)
    candidate = re.sub(r"([+\-*/])\s*;", r"\1 0;", candidate)
    # Add semicolons at line boundaries when a statement is clearly unfinished.
    lines = candidate.splitlines(keepends=True)
    fixed=[]
    statement_start = re.compile(r"^(?:int|float|void)\s+|^[A-Za-z_]\w*\s*=|^return\b|^print\s*\(|^printf\s*\(")
    for i, line in enumerate(lines):
        body=line.rstrip("\r\n")
        ending=line[len(body):]
        stripped=body.strip()
        next_stripped=lines[i+1].strip() if i+1<len(lines) else ""
        # Only add a semicolon to a statement-looking line that is not a control/header/block line.
        if (stripped and next_stripped and statement_start.match(stripped)
            and not stripped.endswith((";", "{", "}", ","))
            and not re.search(r"\b(if|while|for)\s*\(.*\)\s*$", stripped)
            and not stripped.startswith("#")
            and not stripped.endswith("(")):
            body += ";"
        fixed.append(body+ending)
    candidate="".join(fixed)
    # Close any unmatched parenthesis/braces at EOF without deleting source.
    # Ignore delimiters inside string literals and comments for this simple balance pass.
    scrubbed=re.sub(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/', lambda m: " "*len(m.group()), candidate)
    for opening, closing in (("(", ")"), ("{", "}")):
        missing=max(0, scrubbed.count(opening)-scrubbed.count(closing))
        if missing:
            candidate=candidate.rstrip()+("\n" if candidate.endswith("\n") else "")+closing*missing
            scrubbed += closing*missing
    return candidate


def _repair_preserves_program(original_source, candidate):
    """Reject syntactically valid candidates that discard most of the program."""
    if not isinstance(candidate, str) or not candidate.strip():
        return False
    # Compare meaningful identifiers/numbers, ignoring keywords and punctuation.
    meaningful = re.compile(r"\b[A-Za-z_]\w*\b|\b\d+(?:\.\d+)?\b")
    ignored = {"int", "float", "void", "return", "if", "else", "while", "print"}
    original_tokens = [t for t in meaningful.findall(original_source) if t not in ignored]
    candidate_tokens = [t for t in meaningful.findall(candidate) if t not in ignored]
    if not original_tokens:
        return True
    remaining = list(candidate_tokens)
    preserved = 0
    for token in original_tokens:
        if token in remaining:
            remaining.remove(token)
            preserved += 1
    return preserved / len(original_tokens) >= 0.90


def build_correction_options(original_source, recovered_source, strategy):
    """Return up to three distinct, changed, whole-program-valid proposals."""
    proposals = []

    def add(label, explanation, candidate):
        if not isinstance(candidate, str) or any(p["source"] == candidate for p in proposals):
            return
        if candidate == original_source or not _repair_preserves_program(original_source, candidate):
            return
        try:
            valid = bool(validate_source(candidate))
        except Exception:
            valid = False
        if not valid:
            return
        proposals.append({
            "label": label,
            "description": explanation,
            "source": candidate,
            "syntax_valid": True,
        })

    add("Recommended repair", "Parser's preferred recovery for the selected strategy.", recovered_source)

    # Recover the common typo `add;(x y)` as `add(x, y)`. This is deliberately
    # a proposal, not a claim about the function's declared signature.
    malformed_call = re.compile(r"\b([A-Za-z_]\w*)\s*;\s*\(([^()]*?)\)")
    call_match = malformed_call.search(original_source)
    if call_match:
        args = call_match.group(2).strip()
        # Split only adjacent simple identifiers/numbers; avoid touching operators.
        args = re.sub(r"(?<=[A-Za-z0-9_)])\s+(?=[A-Za-z_(])", ", ", args)
        candidate = (original_source[:call_match.start()]
                     + f"{call_match.group(1)}({args})"
                     + original_source[call_match.end():])
        add("Repair malformed function call",
            "Removes a stray semicolon and separates adjacent simple arguments.", candidate)

    # Find simple identifiers from int/float declarations, including comma-separated names.
    declared = []
    for match in re.finditer(r"\b(?:int|float)\s+([^;{}]+);", original_source):
        for part in match.group(1).split(","):
            name_match = re.fullmatch(r"\s*([A-Za-z_]\w*)\s*", part)
            if name_match and name_match.group(1) not in declared:
                declared.append(name_match.group(1))

    # Detect a missing operand before a new statement/end-of-input in the original.
    missing_operand = re.search(
        r"([+*/-])\s*(?=;|\n\s*(?:print|if|while|return|int|float|void|\{)\b|\s*$)",
        original_source,
    )
    if missing_operand:
        # Locate the corresponding operator and its repaired operand in the proposal.
        repaired_operand = re.search(r"([+*/-])\s*([A-Za-z_]\w*|\d+(?:\.\d+)?)", recovered_source)
        if repaired_operand:
            prefix = recovered_source[:repaired_operand.start()]
            current_line = prefix.splitlines()[-1] if prefix.splitlines() else prefix
            assignment = re.search(r"([A-Za-z_]\w*)\s*=\s*(.*)$", current_line)
            target = assignment.group(1) if assignment else None
            expression_names = set(re.findall(r"\b[A-Za-z_]\w*\b", assignment.group(2) if assignment else current_line))
            preferred = [name for name in declared if name != target and name not in expression_names]
            other_declared = [name for name in declared if name != target and name not in preferred]
            candidate_names = preferred + other_declared
            for name in candidate_names:
                candidate = (recovered_source[:repaired_operand.start(2)] + name +
                             recovered_source[repaired_operand.end(2):])
                add(f"Use declared variable '{name}'", f"Alternative operand from the declaration list: {name}.", candidate)
                if len(proposals) >= 3:
                    break
            if len(proposals) < 3:
                candidate = (recovered_source[:repaired_operand.start(2)] + "0" +
                             recovered_source[repaired_operand.end(2):])
                add("Use numeric fallback 0", "A simple syntax repair; it may not match the intended meaning.", candidate)

    # Targeted local edits broaden coverage beyond missing operands. Each candidate
    # is validated by the same Mini-C parser before it is exposed as an option.
    if len(proposals) < 3:
        # Insert a missing semicolon at a likely statement boundary while preserving
        # the following statement. Only consider lines that look like assignments or returns.
        lines = original_source.splitlines(keepends=True)
        offset = 0
        for index, line in enumerate(lines):
            stripped = line.strip()
            next_line = lines[index + 1].strip() if index + 1 < len(lines) else ""
            looks_like_statement = bool(re.match(r"(?:[A-Za-z_]\w*\s*=|return\b|print\s*\()", stripped))
            next_starts_statement = bool(re.match(r"(?:int|float|void|if|while|return|print|[A-Za-z_]\w*\s*=)", next_line))
            if looks_like_statement and next_starts_statement and not stripped.endswith((";", "{", "}")):
                candidate = original_source[:offset + len(line.rstrip("\r\n"))] + ";" + original_source[offset + len(line.rstrip("\r\n")):]
                add("Insert missing semicolon", "Adds a statement terminator before the next statement.", candidate)
                if len(proposals) >= 3: break
            offset += len(line)

    if len(proposals) < 3:
        # Try a single missing closing delimiter at end-of-input. This is deliberately
        # conservative: validate_source rejects candidates that do not fit the grammar.
        stripped = original_source.rstrip()
        suffix = original_source[len(stripped):]
        for opening, closing, label in (("(", ")", "closing parenthesis"), ("{", "}", "closing brace"), ("[", "]", "closing bracket")):
            if stripped.count(opening) > stripped.count(closing):
                candidate = stripped + closing + suffix
                add(f"Insert missing {label}", f"Adds one unmatched closing {label} at end of input.", candidate)
                if len(proposals) >= 3: break

    if len(proposals) < 3:
        # Recover a likely missing binary operator between adjacent expression atoms.
        # Keep this conservative: only consider simple assignment/return expressions,
        # then expose a candidate only if the Mini-C parser validates the whole program.
        atom = r"(?:[A-Za-z_]\w*|\d+(?:\.\d+)?|\([^()]*\))"
        for line_match in re.finditer(r"(?m)^([^\n]*(?:=|\breturn\b)[^;\n]*);?", original_source):
            line = line_match.group(1)
            for gap in re.finditer(rf"({atom})\s+({atom})", line):
                left, right = gap.group(1), gap.group(2)
                # Do not reinterpret the assignment operator or adjacent keywords as expressions.
                if left in {"return", "int", "float", "void"} or right in {"return", "if", "while"}:
                    continue
                for operator in ("+", "-", "*", "/"):
                    repaired_line = line[:gap.start(2)] + operator + " " + line[gap.start(2):]
                    candidate = original_source[:line_match.start(1)] + repaired_line + original_source[line_match.end(1):]
                    add(f"Insert missing operator '{operator}'",
                        f"Inserts '{operator}' between adjacent expression atoms; check intended meaning.",
                        candidate)
                    if len(proposals) >= 3:
                        break
                if len(proposals) >= 3:
                    break
            if len(proposals) >= 3:
                break

    if len(proposals) < 3:
        # Offer single-operator alternatives only if the parser accepts the result.
        # These are lower-confidence alternatives because they can change semantics.
        repaired = recovered_source
        for match in list(re.finditer(r"(?<![=!<>])([+*/-])(?![=])", repaired)):
            current = match.group(1)
            for replacement in ("+", "-", "*", "/"):
                if replacement == current: continue
                candidate = repaired[:match.start(1)] + replacement + repaired[match.end(1):]
                add(f"Try operator '{replacement}'", f"Alternative operator substitution; review intended meaning.", candidate)
                if len(proposals) >= 3: break
            if len(proposals) >= 3: break

    # If there are not three distinct operand options, try other recovery strategies
    # to expose genuinely different parser-produced candidates.
    for alternate_strategy in ("automatic", "token insertion", "phrase-level recovery", "panic mode"):
        if len(proposals) >= 3:
            break
        try:
            alternate = analyze_source(original_source, alternate_strategy).get("recovered_source", original_source)
        except Exception:
            continue
        add(f"Alternative: {alternate_strategy}", f"Output produced by {alternate_strategy} recovery.", alternate)

    # If the input already parses, there is no syntax repair to suggest.
    if validate_source(original_source):
        return []
    # Filter out unchanged/duplicate/invalid candidates before returning. Do not pad
    # the list: one good repair is better than three speculative or invalid repairs.
    filtered = []
    seen = set()
    for proposal in proposals:
        candidate = proposal.get("source", "")
        if not candidate or candidate == original_source or candidate in seen:
            continue
        if not proposal.get("syntax_valid", False):
            continue
        seen.add(candidate)
        filtered.append(proposal)
    return filtered[:3]


if __name__ == "__main__":
    app.run(debug=True)
