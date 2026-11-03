"""Train a reproducible lightweight candidate ranker on synthetic preference labels.

This is a ranking model, not a code generator. Synthetic validation scores do not
measure real-world repair correctness. Run: python train_correction_model.py
"""
import json, math, random
from pathlib import Path

FEATURES = [
    "syntax_valid", "declared_identifier", "unused_in_expression", "numeric_fallback",
    "small_edit", "preserves_following_statement", "duplicate_candidate", "speculative",
    "has_semicolon_coverage", "balanced_delimiters", "local_token_edit", "uses_declared_operand",
    "preserves_original_statements", "type_compatible", "prefers_unused_operand", "avoids_repeated_operand",
]
COEFFICIENTS = [2.8, 1.25, .25, -.25, .55, .95, -2.0, -.8, .6, .85, .65, .95, 1.2, .7, 1.0, .55]

def sigmoid(z):
    z = max(-30, min(30, z))
    return 1 / (1 + math.exp(-z))

def make_data(seed=20261029, n=30000):
    rng = random.Random(seed)
    rows = []
    for _ in range(n):
        x = [rng.randint(0, 1) for _ in FEATURES]
        # Create plausible correlations between features.
        x[1] = int(bool(x[1] and x[11]))
        x[3] = int(bool(x[3] and not x[1]))
        x[7] = int(bool(x[7] or x[3]))
        x[12] = int(bool(x[12] and x[5]))
        x[14] = int(bool(x[14] and x[11]))
        x[15] = int(bool(x[15] and not x[3]))
        x[6] = int(rng.random() < .06)
        latent = sum(w * v for w, v in zip(COEFFICIENTS, x)) - 3.9 + rng.gauss(0, 1.15)
        rows.append((x, int(latent > 0)))
    return rows

def train():
    rows = make_data()
    rng = random.Random(20261030)
    rng.shuffle(rows)
    split = int(len(rows) * .8)
    training, validation = rows[:split], rows[split:]
    weights = [0.0] * len(FEATURES)
    bias, lr, epochs, reg = 0.0, .12, 500, .0005
    for _ in range(epochs):
        grads, gb = [0.0] * len(weights), 0.0
        for x, y in training:
            error = sigmoid(sum(w*v for w, v in zip(weights, x)) + bias) - y
            for i, v in enumerate(x): grads[i] += error * v
            gb += error
        scale = lr / len(training)
        weights = [w - scale * (g + reg*w) for w, g in zip(weights, grads)]
        bias -= scale * gb
    correct, loss = 0, 0.0
    for x, y in validation:
        p = max(1e-8, min(1-1e-8, sigmoid(sum(w*v for w, v in zip(weights, x)) + bias)))
        correct += int((p >= .5) == bool(y))
        loss -= y*math.log(p) + (1-y)*math.log(1-p)
    artifact = {
        "model_type": "synthetic_logistic_candidate_ranker", "version": 4,
        "features": FEATURES, "weights": weights, "bias": bias, "seed": 20261029,
        "training_examples": len(training), "validation_examples": len(validation), "epochs": epochs,
        "validation_accuracy": round(correct/len(validation), 4),
        "validation_log_loss": round(loss/len(validation), 4),
        "training_note": "Trained on synthetic heuristic preference labels, not a real-world labeled code corpus. Metrics measure agreement with synthetic labels only; they do not measure real-world repair correctness."
    }
    path = Path(__file__).with_name("correction_ranker.json")
    path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"Training examples: {len(training)} | validation examples: {len(validation)} | epochs: {epochs}")
    print(f"Synthetic-label validation accuracy: {artifact['validation_accuracy']} | log loss: {artifact['validation_log_loss']}")
    print(f"Saved: {path.name} (model version {artifact['version']})")
    print("Limit: this ranks proposed repairs; it does not generate code or guarantee semantic correctness.")

if __name__ == "__main__": train()
