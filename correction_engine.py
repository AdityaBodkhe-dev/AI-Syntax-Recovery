"""Context-aware ranking and conservative diagnostics for the project's Mini-C grammar.

The ranker orders parser/heuristic candidates; it does not generate arbitrary code.
Semantic checks are intentionally best-effort and are not a substitute for a compiler.
"""
from pathlib import Path
import json
import math
import re

_MODEL_PATH = Path(__file__).with_name("correction_ranker.json")
try:
    _MODEL = json.loads(_MODEL_PATH.read_text(encoding="utf-8"))
except (OSError, ValueError):
    _MODEL = {"features": [], "weights": [], "bias": 0.0, "model_type": "heuristic-fallback"}

IDENT = r"[A-Za-z_]\w*"
DECL_RE = re.compile(r"\b(int|float|void)\s+([^;{}()]+)")

def _sigmoid(z):
    z = max(-30.0, min(30.0, z))
    return 1.0 / (1.0 + math.exp(-z))

def _strip_comments_and_strings(source):
    source = re.sub(r'"(?:\\.|[^"\\])*"', '""', source)
    source = re.sub(r"//[^\n]*|/\*[\s\S]*?\*/", lambda m: "\n" * m.group(0).count("\n"), source)
    return source

def _declarations(source):
    """Return first-seen variable types and declaration positions for simple declarations."""
    clean = _strip_comments_and_strings(source)
    types, positions, duplicates = {}, {}, []
    for match in DECL_RE.finditer(clean):
        kind, names_text = match.groups()
        # Avoid interpreting function declarations as variable declarations.
        if "(" in names_text or ")" in names_text:
            continue
        for item in names_text.split(","):
            nm = re.fullmatch(r"\s*(" + IDENT + r")\s*", item)
            if not nm:
                continue
            name = nm.group(1)
            pos = match.start(2) + nm.start(1)
            if name in types:
                duplicates.append((name, pos))
            else:
                types[name], positions[name] = kind, pos
    return types, positions, duplicates

def _target_and_rhs(source):
    # Prefer the last assignment statement, rather than an '=' in a comparison.
    matches = list(re.finditer(r"(?m)^\s*(" + IDENT + r")\s*=\s*([^;\n]*)", source))
    return matches[-1].groups() if matches else (None, "")

def candidate_features(option, all_sources, original):
    src = option.get("source", "")
    label = (option.get("label") or "").lower()
    declared_types, _, _ = _declarations(original)
    declared = list(declared_types)
    identifiers = set(re.findall(r"\b" + IDENT + r"\b", src))
    target, rhs = _target_and_rhs(src)
    rhs_ids = set(re.findall(r"\b" + IDENT + r"\b", rhs))
    original_target, original_rhs = _target_and_rhs(original)
    original_rhs_ids = set(re.findall(r"\b" + IDENT + r"\b", original_rhs))
    # Compare to the *original* incomplete expression. The repaired candidate itself
    # naturally contains its proposed operand, so using candidate RHS here is wrong.
    target_for_context = original_target or target
    usable = [n for n in declared if n != target_for_context and n not in original_rhs_ids]
    selected_name = next((n for n in declared if re.search(r"\b" + re.escape(n) + r"\b", label)), None)
    selected_unused = bool(selected_name and selected_name in usable)
    declared_identifier = float(bool(selected_name) or ("variable" in label and bool(usable)))
    numeric = float("numeric" in label or "fallback" in label or bool(re.search(r"[+*/-]\s*0\b", rhs)))
    old_tokens = re.findall(r"[A-Za-z_]\w*|\d+(?:\.\d+)?|[^\s]", original)
    new_tokens = re.findall(r"[A-Za-z_]\w*|\d+(?:\.\d+)?|[^\s]", src)
    edit_ratio = abs(len(new_tokens) - len(old_tokens)) / max(1, len(old_tokens))
    preserved = float(all(x in src for x in re.findall(r"\b(?:print|return)\s*\([^;]*\)\s*;", original)))
    # Statements after the repair point should survive candidate generation.
    original_statements = [s.strip() for s in re.split(r"[;\n]", original) if s.strip()]
    candidate_statements = [s.strip() for s in re.split(r"[;\n]", src) if s.strip()]
    preserved_statements = sum(1 for s in original_statements if s in candidate_statements) / max(1, len(original_statements))
    balanced = float(all(src.count(a) == src.count(b) for a, b in [("(", ")"), ("{", "}"), ("[", "]")]))
    duplicate = float(sum(s == src for s in all_sources) > 1)
    target_type = declared_types.get(target)
    rhs_type_compatible = 1.0
    if target_type == "int" and re.search(r"\d+\.\d+", rhs):
        rhs_type_compatible = 0.0
    elif target_type == "void":
        rhs_type_compatible = 0.0
    # Penalize an operand that repeats an existing RHS identifier when an unused
    # declared alternative exists; this is a preference, not a semantic rule.
    repeated_operand = float(any(n in rhs_ids for n in declared if n != target) and bool(usable) and not selected_unused and bool(re.search(r"[+*/-]\s*(?:" + IDENT + r"|\d+)", rhs)))
    features = {
        "syntax_valid": float(bool(option.get("syntax_valid"))),
        "declared_identifier": declared_identifier,
        "unused_in_expression": float(selected_unused),
        "numeric_fallback": numeric,
        "small_edit": float(abs(len(src.splitlines()) - len(original.splitlines())) <= 1),
        "preserves_following_statement": preserved,
        "duplicate_candidate": duplicate,
        "speculative": float(numeric or "alternative:" in label or "fallback" in label),
        "has_semicolon_coverage": float(src.count(";") >= original.count(";")),
        "balanced_delimiters": balanced,
        "local_token_edit": float(edit_ratio <= 0.25),
        "uses_declared_operand": float(any(n in rhs_ids and n != target for n in declared)),
        "preserves_original_statements": preserved_statements,
        "type_compatible": rhs_type_compatible,
        "prefers_unused_operand": float(selected_unused),
        "avoids_repeated_operand": 1.0 - repeated_operand,
    }
    return features

def rank_candidates(options, original):
    sources = [o.get("source", "") for o in options]
    for option in options:
        features = candidate_features(option, sources, original)
        names, weights = _MODEL.get("features", []), _MODEL.get("weights", [])
        score = float(_MODEL.get("bias", 0.0)) + sum(float(w) * features.get(n, 0.0) for n, w in zip(names, weights))
        # Transparent, hand-designed context adjustments complement trained weights.
        score += (0.8 * features["syntax_valid"] + 0.4 * features["balanced_delimiters"]
                  + 0.35 * features["type_compatible"] + 0.35 * features["preserves_original_statements"]
                  + 0.3 * features["prefers_unused_operand"] + 0.2 * features["local_token_edit"]
                  - 0.45 * features["speculative"] - 0.8 * features["duplicate_candidate"])
        option["rank_score"] = round(_sigmoid(score), 4)
        option["ranking_model"] = _MODEL.get("model_type", "heuristic-fallback")
        option["feature_summary"] = {k: bool(v) for k, v in features.items()}
        option["ranking_notes"] = _ranking_notes(features)
    # Sort by validity first, then the final combined model + context score.
    options.sort(key=lambda x: (bool(x.get("syntax_valid")), x.get("rank_score", 0.0)), reverse=True)
    for option in options:
        option.pop("_raw_rank_score", None)
    return options

def _ranking_notes(features):
    notes = []
    if features["syntax_valid"]: notes.append("passes the configured syntax validator")
    if features["balanced_delimiters"]: notes.append("delimiters are balanced")
    if features["prefers_unused_operand"]: notes.append("uses a declared identifier not already in the expression")
    if not features["type_compatible"]: notes.append("may conflict with the target variable's declared type")
    if features["numeric_fallback"]: notes.append("uses a generic numeric fallback")
    if not features["preserves_original_statements"]: notes.append("changes or omits one or more original statements")
    return notes or ["ranked using available syntax and context features"]

def semantic_diagnostics(source):
    """Best-effort warnings for a deliberately small C-like subset."""
    diagnostics = []
    clean = _strip_comments_and_strings(source)
    line_starts = [0] + [m.end() for m in re.finditer(r"\n", source)]
    import bisect
    def line_at(pos): return bisect.bisect_right(line_starts, pos)
    types, positions, duplicates = _declarations(clean)
    for name, pos in duplicates:
        diagnostics.append({"kind":"semantic", "code":"DUPLICATE_DECLARATION", "message":f"Identifier '{name}' appears to be declared more than once.", "line":line_at(pos), "identifier":name, "severity":"warning"})
    keywords = {"int", "float", "void", "if", "else", "while", "return", "print"}
    # Approximate function parameters as declared names; full lexical scoping is not modeled.
    for m in re.finditer(r"\b(?:int|float|void)\s+" + IDENT + r"\s*\(([^)]*)\)", clean):
        for p in re.finditer(r"\b(int|float)\s+(" + IDENT + r")\b", m.group(1)):
            types.setdefault(p.group(2), p.group(1)); positions.setdefault(p.group(2), m.start(1)+p.start(2))
    for m in re.finditer(r"\b" + IDENT + r"\b", clean):
        name, pos = m.group(), m.start()
        if name in keywords or any(n == name and p == pos for n, p in positions.items()): continue
        before, after = clean[:pos], clean[m.end():]
        if re.match(r"\s*=", after): continue  # assignment LHS / function-like declaration name
        if re.search(r"\b(?:int|float|void)\s+$", before) and re.match(r"\s*\(", after): continue
        if name in types: continue
        # Exclude function calls, and only warn where a name is likely an expression operand.
        if re.match(r"\s*\(", after): continue
        expr_context = bool(re.search(r"[=+*/%<>!-]", before[max(0, pos-120):]) or re.search(r"\b(?:print|return)\s*\([^)]*$", before) or re.search(r"\breturn\s+$", before))
        if expr_context:
            diagnostics.append({"kind":"semantic", "code":"UNDECLARED_IDENTIFIER", "message":f"Identifier '{name}' may be used without a declaration.", "line":line_at(pos), "identifier":name, "severity":"warning"})
    # Simple assignment type warning: integer target assigned a decimal literal.
    for m in re.finditer(r"\b(" + IDENT + r")\s*=\s*([^;\n]+)", clean):
        target, rhs = m.group(1), m.group(2)
        if types.get(target) == "int" and re.search(r"\b\d+\.\d+\b", rhs):
            diagnostics.append({"kind":"semantic", "code":"POSSIBLE_TYPE_MISMATCH", "message":f"'{target}' is declared int but is assigned a decimal literal; check whether conversion is intended.", "line":line_at(m.start()), "identifier":target, "severity":"warning"})
        if types.get(target) == "void":
            diagnostics.append({"kind":"semantic", "code":"INVALID_VOID_ASSIGNMENT", "message":f"'{target}' is declared void and is used as an assignment target.", "line":line_at(m.start()), "identifier":target, "severity":"warning"})
    for m in re.finditer(r"\b(" + IDENT + r")\s*=\s*\1\s*;", clean):
        diagnostics.append({"kind":"semantic", "code":"SELF_ASSIGNMENT", "message":f"'{m.group(1)}' is assigned to itself; check whether this was intended.", "line":line_at(m.start()), "identifier":m.group(1), "severity":"info"})
    # Avoid noisy unused warnings for comma declarations; only simple single-name declarations.
    for m in re.finditer(r"\b(?:int|float)\s+(" + IDENT + r")\s*;", clean):
        name = m.group(1)
        rest = clean[m.end():]
        if not re.search(r"\b" + re.escape(name) + r"\b", rest):
            diagnostics.append({"kind":"semantic", "code":"DECLARED_BUT_UNUSED", "message":f"'{name}' is declared but not used later in this source.", "line":line_at(m.start()), "identifier":name, "severity":"info"})
    # Common suspicious constructs. These are intentionally warnings, not hard errors.
    for m in re.finditer(r"\b(if|while)\s*\(\s*\)", clean):
        diagnostics.append({"kind":"semantic", "code":"EMPTY_CONDITION", "message":f"'{m.group(1)}' has an empty condition.", "line":line_at(m.start()), "severity":"warning"})
    for m in re.finditer(r"(?m)^\s*([A-Za-z_]\w*)\s*=\s*;", clean):
        diagnostics.append({"kind":"semantic", "code":"EMPTY_ASSIGNMENT", "message":f"Assignment to '{m.group(1)}' has no right-hand expression.", "line":line_at(m.start()), "identifier":m.group(1), "severity":"warning"})
    # A bare return value in a void function, and a bare return in a non-void
    # function, are likely issues in this subset; function boundaries are approximate.
    for fn in re.finditer(r"\b(void|int|float)\s+([A-Za-z_]\w*)\s*\([^)]*\)\s*\{", clean):
        body_start = fn.end()
        depth, body_end = 1, body_start
        while body_end < len(clean) and depth:
            if clean[body_end] == "{": depth += 1
            elif clean[body_end] == "}": depth -= 1
            body_end += 1
        body = clean[body_start:body_end]
        for ret in re.finditer(r"\breturn\b([^;]*);", body):
            expr = ret.group(1).strip()
            bad = (fn.group(1) == "void" and bool(expr)) or (fn.group(1) != "void" and not expr)
            if bad:
                diagnostics.append({"kind":"semantic", "code":"RETURN_TYPE_MISMATCH", "message":f"Return statement may not match the '{fn.group(1)}' return type of function '{fn.group(2)}'.", "line":line_at(body_start + ret.start()), "identifier":fn.group(2), "severity":"warning"})
    seen, unique = set(), []
    for d in diagnostics:
        key = (d["code"], d.get("identifier"), d["line"])
        if key not in seen: seen.add(key); unique.append(d)
    return unique
