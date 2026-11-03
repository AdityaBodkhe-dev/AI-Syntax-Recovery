
const sourceCode = document.getElementById("sourceCode");
const strategySelect = document.getElementById("strategy");
const analyzeButton = document.getElementById("analyzeButton");
const buttonText = document.getElementById("buttonText");
const buttonSpinner = document.getElementById("buttonSpinner");
const requestMessage = document.getElementById("requestMessage");

const exampleSource = `int a
a = 10 + 5;
if (a > 10) {
    print(a);
}`;

function updateLineCount() {
    const count = sourceCode.value.split("\n").length;
    document.getElementById("lineCount").textContent =
        `${count} ${count === 1 ? "line" : "lines"}`;
}

function setText(id, value) {
    document.getElementById(id).textContent = String(value);
}

function showEmpty(container, message) {
    container.replaceChildren();
    const element = document.createElement("div");
    element.className = "empty-state";
    element.textContent = message;
    container.appendChild(element);
}

function createCell(value) {
    const cell = document.createElement("td");
    cell.textContent = value ?? "";
    return cell;
}

function renderTokens(tokens) {
    const tbody = document.getElementById("tokenResults");
    tbody.replaceChildren();

    if (!tokens.length) {
        const row = document.createElement("tr");
        const cell = createCell("No tokens found.");
        cell.colSpan = 4;
        cell.className = "empty-cell";
        row.appendChild(cell);
        tbody.appendChild(row);
        return;
    }

    for (const token of tokens) {
        const row = document.createElement("tr");
        row.appendChild(createCell(token.type));
        row.appendChild(createCell(token.value));
        row.appendChild(createCell(token.line));
        row.appendChild(createCell(token.column));
        tbody.appendChild(row);
    }
}

function renderErrors(errors, lexicalErrors) {
    const container = document.getElementById("errorResults");
    container.replaceChildren();

    if (!errors.length && !lexicalErrors.length) {
        showEmpty(container, "No syntax or lexical errors were reported.");
        return;
    }

    for (const error of lexicalErrors) {
        const card = document.createElement("article");
        card.className = "diagnostic";

        const title = document.createElement("div");
        title.className = "diagnostic-title";
        title.textContent = `Lexical error: ${error.message}`;

        const meta = document.createElement("div");
        meta.className = "diagnostic-meta";
        meta.textContent = `Line ${error.line}, column ${error.column}`;

        card.append(title, meta);
        container.appendChild(card);
    }

    for (const error of errors) {
        const card = document.createElement("article");
        card.className = "diagnostic";

        const title = document.createElement("div");
        title.className = "diagnostic-title";
        title.textContent = error.message || "Syntax error";

        const meta = document.createElement("div");
        meta.className = "diagnostic-meta";
        meta.textContent =
            `Line ${error.line}, column ${error.column}` +
            ` · Unexpected: ${error.unexpected ?? "unknown"}`;

        const expected = document.createElement("div");
        expected.className = "diagnostic-meta";
        expected.textContent =
            "Expected: " + (error.expected || []).join(", ");

        const action = document.createElement("div");
        action.className = "diagnostic-action";
        action.textContent = `Recovery action: ${error.action || "None"}`;

        card.append(title, meta, expected, action);
        container.appendChild(card);
    }
}

function renderTrace(trace) {
    const container = document.getElementById("traceResults");
    container.replaceChildren();

    if (!trace.length) {
        showEmpty(container, "No recovery actions were recorded.");
        return;
    }

    for (const step of trace) {
        const item = document.createElement("div");
        item.className = "trace-item";

        const meta = document.createElement("small");
        meta.textContent = `Line ${step.line} · Token: ${step.token}`;

        const action = document.createElement("div");
        action.textContent = step.action;

        item.append(meta, action);
        container.appendChild(item);
    }
}

function renderCorrectionOptions(options) {
    const container = document.getElementById("correctionOptions");
    container.replaceChildren();

    if (!options || !options.length) {
        showEmpty(container, "No correction options were generated.");
        return;
    }

    options.forEach((option, index) => {
        const card = document.createElement("article");
        card.className = "correction-option";

        const heading = document.createElement("div");
        heading.className = "correction-option-heading";
        const title = document.createElement("h4");
        title.textContent = `${index + 1}. ${option.label}`;
        const status = document.createElement("span");
        status.className = option.syntax_valid ? "option-status good" : "option-status bad";
        status.textContent = option.syntax_valid ? "Parses" : "Still has errors";
        heading.append(title, status);

        const description = document.createElement("p");
        description.className = "recovered-note";
        const score = Number.isFinite(Number(option.rank_score))
            ? ` · Relative rank score ${Number(option.rank_score).toFixed(3)} (not a probability)` : "";
        const notes = Array.isArray(option.ranking_notes) && option.ranking_notes.length
            ? ` ${option.ranking_notes.join("; ")}.` : "";
        description.textContent = (option.description || "Alternative repair proposal.") + score + (notes ? ` Ranking notes: ${notes}` : "");

        const code = document.createElement("textarea");
        code.className = "recovered-code option-code";
        code.readOnly = true;
        code.spellcheck = false;
        code.value = option.source || "";
        code.setAttribute("aria-label", `${option.label} source code`);

        const actions = document.createElement("div");
        actions.className = "option-actions";
        const useButton = document.createElement("button");
        useButton.className = "button secondary";
        useButton.textContent = "Use this proposal";
        useButton.addEventListener("click", () => {
            document.getElementById("recoveredSource").value = code.value;
            document.getElementById("recoveredMessage").textContent = `${option.label} selected. Original input remains unchanged.`;
        });
        const copyButton = document.createElement("button");
        copyButton.className = "button secondary";
        copyButton.textContent = "Copy option";
        copyButton.addEventListener("click", async () => {
            try {
                await navigator.clipboard.writeText(code.value);
                document.getElementById("recoveredMessage").textContent = `${option.label} copied to clipboard.`;
            } catch {
                code.focus(); code.select();
                document.getElementById("recoveredMessage").textContent = "Clipboard unavailable; selected the option for manual copying.";
            }
        });
        actions.append(useButton, copyButton);
        card.append(heading, description, code, actions);
        container.appendChild(card);
    });
}

function renderDiff(items) {
    const container = document.getElementById("diffResults");
    container.replaceChildren();
    if (!items || !items.length) {
        showEmpty(container, "No line-level changes detected.");
        return;
    }
    for (const item of items) {
        const line = document.createElement("div");
        line.className = `diff-line ${item.kind || "equal"}`;
        const marker = document.createElement("span");
        marker.className = "diff-marker";
        marker.textContent = item.kind === "insert" ? "+" : item.kind === "delete" ? "−" : "·";
        const code = document.createElement("code");
        code.textContent = item.text || " ";
        line.append(marker, code);
        container.appendChild(line);
    }
}

function renderOutline(outline) {
    const container = document.getElementById("parseOutline");
    container.replaceChildren();
    if (!outline) { showEmpty(container, "No structure available."); return; }
    const summary = document.createElement("p");
    summary.className = "outline-summary";
    summary.textContent = `${(outline.functions || []).length} function name(s) · ${(outline.declarations || []).length} declaration name(s) · ${(outline.statements || []).length} non-empty line(s)`;
    container.appendChild(summary);
    for (const statement of (outline.statements || [])) {
        const row = document.createElement("div");
        row.className = "outline-row";
        const meta = document.createElement("span");
        meta.textContent = `L${statement.line} · ${statement.kind}`;
        const code = document.createElement("code");
        code.textContent = statement.text;
        row.append(meta, code);
        container.appendChild(row);
    }
}

async function runBenchmark() {
    const container = document.getElementById("benchmarkResults");
    container.textContent = "Running benchmark…";
    const button = document.getElementById("runBenchmark");
    button.disabled = true;
    try {
        const response = await fetch("/benchmark");
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Benchmark failed");
        container.replaceChildren();
        const summary = document.createElement("p");
        summary.className = "benchmark-summary";
        summary.textContent = `${data.passed}/${data.total} sanity cases passed (${Math.round(data.pass_rate * 100)}%).`;
        container.appendChild(summary);
        const note = document.createElement("p");
        note.className = "recovered-note";
        note.textContent = data.scope;
        container.appendChild(note);
        for (const item of data.cases || []) {
            const row = document.createElement("div");
            row.className = `benchmark-row ${item.passed ? "pass" : "fail"}`;
            row.textContent = `${item.passed ? "PASS" : "FAIL"} · ${item.name} — expected ${item.expected_valid ? "valid" : "invalid"}, observed ${item.observed_valid ? "valid" : "invalid"}`;
            container.appendChild(row);
        }
    } catch (error) {
        showEmpty(container, `Benchmark error: ${error.message}`);
    } finally { button.disabled = false; }
}

function renderResult(result) {
    const tokens = result.tokens || [];
    const errors = result.errors || [];
    const lexicalErrors = result.lexical_errors || [];
    const trace = result.trace || [];

    setText("tokenCount", tokens.length);
    setText("errorCount", errors.length);
    setText("lexicalCount", lexicalErrors.length);
    setText("recoveryCount", trace.length);

    const badge = document.getElementById("resultBadge");
    badge.className = "badge";

    if (result.success) {
        badge.textContent = "Syntax valid";
        badge.classList.add("good");
    } else {
        badge.textContent = "Errors detected";
        badge.classList.add("bad");
    }

    document.getElementById("recoveredSource").value =
        typeof result.recovered_source === "string"
            ? result.recovered_source
            : sourceCode.value;

    const recoveryValidation = result.recovery_validation || {};
    document.getElementById("recoveredMessage").textContent =
        recoveryValidation.passed === false
            ? (recoveryValidation.message || "No whole-program-valid repair was found. The original code is shown instead.")
            : result.recovered_source === sourceCode.value
                ? "No source insertions were made."
                : "Proposed source passed whole-program syntax validation.";

    renderTokens(tokens);
    renderErrors(errors, lexicalErrors);
    renderTrace(trace);
    renderCorrectionOptions(result.correction_options || []);
    renderDiff(result.source_diff || []);
    renderOutline(result.parse_outline);

    requestMessage.textContent = result.recovery_success
        ? "Analysis complete. Recovery actions were recorded."
        : "Analysis complete. Check the diagnostics and recovery trace.";
}

async function analyzeProgram() {
    analyzeButton.disabled = true;
    buttonSpinner.classList.remove("hidden");
    buttonText.textContent = "Analyzing...";
    requestMessage.textContent = "Sending source code to the parser...";

    try {
        const response = await fetch("/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                source: sourceCode.value,
                strategy: strategySelect.value
            })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Analysis failed.");
        }

        renderResult(result);
    } catch (error) {
        requestMessage.textContent =
            `Error: ${error.message}. Check that Flask is running.`;
        console.error(error);

        const badge = document.getElementById("resultBadge");
        badge.className = "badge bad";
        badge.textContent = "Request failed";
    } finally {
        analyzeButton.disabled = false;
        buttonSpinner.classList.add("hidden");
        buttonText.textContent = "Analyze program";
    }
}

document.getElementById("loadExample").addEventListener("click", () => {
    sourceCode.value = exampleSource;
    updateLineCount();
    requestMessage.textContent = "Example program loaded.";
});

document.getElementById("clearCode").addEventListener("click", () => {
    sourceCode.value = "";
    updateLineCount();
    requestMessage.textContent = "Editor cleared.";
    sourceCode.focus();
});
document.getElementById("runBenchmark").addEventListener("click", runBenchmark);

document.getElementById("copyRecovered").addEventListener("click", async () => {
    const recovered = document.getElementById("recoveredSource");
    const message = document.getElementById("recoveredMessage");

    try {
        await navigator.clipboard.writeText(recovered.value);
        message.textContent = "Recovered source copied to clipboard.";
    } catch {
        recovered.focus();
        recovered.select();
        message.textContent =
            "Clipboard access blocked. Select the code and copy manually.";
    }
});

sourceCode.addEventListener("input", updateLineCount);
analyzeButton.addEventListener("click", analyzeProgram);

updateLineCount();
