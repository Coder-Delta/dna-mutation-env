# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
FastAPI application for the Dna Mutation Env Environment.

This module creates an HTTP server that exposes the DnaMutationEnvironment
over HTTP and WebSocket endpoints, compatible with EnvClient.

Endpoints:
    - POST /reset: Reset the environment
    - POST /step: Execute an action
    - GET /state: Get current environment state
    - GET /schema: Get action/observation schemas
    - WS /ws: WebSocket endpoint for persistent sessions

Usage:
    # Development (with auto-reload):
    uvicorn server.app:app --reload --host 0.0.0.0 --port 8000

    # Production:
    uvicorn server.app:app --host 0.0.0.0 --port 8000 --workers 4

    # Or run directly:
    python -m server.app
"""

import logging

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:  # pragma: no cover
    raise ImportError(
        "openenv is required for the web interface. Install dependencies with '\n    uv sync\n'"
    ) from e

try:
    from .config import SETTINGS
    from ..models import DnaMutationAction, DnaMutationObservation
    from .dna_mutation_env_environment import DnaMutationEnvironment
except (ModuleNotFoundError, ImportError):
    from server.config import SETTINGS
    from models import DnaMutationAction, DnaMutationObservation
    from server.dna_mutation_env_environment import DnaMutationEnvironment

logging.basicConfig(
    level=getattr(logging, SETTINGS.log_level),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
LOGGER = logging.getLogger(__name__)

APP_INFO = {
    "name": "DNA Mutation OpenEnv",
    "status": "running",
    "docs_url": "/docs",
    "schema_url": "/schema",
    "health_url": "/health",
    "ready_url": "/ready",
}

ROOT_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DNA Mutation OpenEnv</title>
  <style>
    :root {
      --bg: #09090b;
      --panel: #111317;
      --panel-2: #181b22;
      --line: rgba(255,255,255,0.08);
      --text: #f5f7fb;
      --muted: #98a2b3;
      --accent: #34d399;
      --accent-2: #60a5fa;
      --danger: #f87171;
      --shadow: 0 20px 50px rgba(0,0,0,0.35);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: "Segoe UI", "Trebuchet MS", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(52, 211, 153, 0.14), transparent 24%),
        radial-gradient(circle at top right, rgba(96, 165, 250, 0.14), transparent 24%),
        linear-gradient(180deg, #0b0c10 0%, #07080b 100%);
    }
    .wrap {
      width: min(1040px, calc(100% - 24px));
      margin: 22px auto 28px;
    }
    .hero, .panel {
      border: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)), var(--panel);
      border-radius: 20px;
      box-shadow: var(--shadow);
    }
    .hero {
      padding: 24px;
      margin-bottom: 16px;
    }
    .eyebrow {
      display: inline-block;
      font-size: 12px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--accent);
      font-weight: 700;
    }
    h1 {
      margin: 10px 0 8px;
      font-size: clamp(30px, 6vw, 42px);
      line-height: 0.98;
      letter-spacing: -0.04em;
    }
    .lede {
      margin: 0;
      max-width: 700px;
      color: var(--muted);
      line-height: 1.6;
      font-size: 15px;
    }
    .top-links, .button-row, .stats {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 16px;
    }
    a.button, button {
      appearance: none;
      border: 0;
      border-radius: 12px;
      padding: 11px 14px;
      font: inherit;
      text-decoration: none;
      cursor: pointer;
      transition: transform 120ms ease, opacity 120ms ease;
    }
    a.button:hover, button:hover { transform: translateY(-1px); }
    .primary {
      background: linear-gradient(135deg, var(--accent), #10b981);
      color: #03120d;
      font-weight: 700;
    }
    .secondary {
      background: rgba(255,255,255,0.05);
      color: var(--text);
      border: 1px solid var(--line);
    }
    .stat {
      padding: 10px 12px;
      border-radius: 999px;
      background: rgba(255,255,255,0.04);
      color: var(--muted);
      font-size: 13px;
      border: 1px solid var(--line);
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 16px;
    }
    .panel { padding: 18px; }
    .panel h2 {
      margin: 0 0 6px;
      font-size: 20px;
    }
    .panel p {
      margin: 0 0 10px;
      color: var(--muted);
      line-height: 1.55;
      font-size: 14px;
    }
    label {
      display: block;
      margin: 12px 0 6px;
      font-size: 13px;
      font-weight: 700;
      color: #e7ecf6;
    }
    input, select, textarea {
      width: 100%;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: var(--panel-2);
      color: var(--text);
      padding: 11px 12px;
      font: inherit;
    }
    textarea {
      min-height: 96px;
      resize: vertical;
    }
    .two-col {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }
    .status {
      margin-top: 12px;
      padding: 12px;
      border-radius: 12px;
      border: 1px solid rgba(52, 211, 153, 0.2);
      background: rgba(52, 211, 153, 0.08);
      color: #bbf7d0;
      min-height: 48px;
      font-size: 14px;
    }
    pre {
      margin: 0;
      border-radius: 16px;
      padding: 16px;
      background: #05060a;
      border: 1px solid var(--line);
      min-height: 280px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 12px;
      line-height: 1.55;
      color: #dbe5f5;
    }
    code {
      color: #c4b5fd;
      font-family: Consolas, monospace;
    }
    @media (max-width: 640px) {
      .two-col { grid-template-columns: 1fr; }
      .wrap { width: min(100% - 14px, 1040px); }
    }
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <span class="eyebrow">Compact Dark UI</span>
      <h1>DNA Mutation OpenEnv</h1>
      <p class="lede">
        A lightweight control panel for the deployed OpenEnv Space. Reset a task, send
        an action, and inspect the latest JSON response without leaving the homepage.
      </p>
      <div class="top-links">
        <a class="button primary" href="/docs" target="_blank" rel="noreferrer">REST Docs</a>
        <a class="button secondary" href="/schema" target="_blank" rel="noreferrer">Schema</a>
        <a class="button secondary" href="/health" target="_blank" rel="noreferrer">Health</a>
        <a class="button secondary" href="/ready" target="_blank" rel="noreferrer">Ready</a>
      </div>
      <div class="stats">
        <span class="stat">Tasks: easy, medium, hard</span>
        <span class="stat">Endpoints: /reset, /step, /schema</span>
        <span class="stat">Mode: FastAPI + OpenEnv</span>
      </div>
    </section>

    <section class="grid">
      <div class="panel">
        <h2>Reset Episode</h2>
        <p>Pick a task and optional seed, then request a fresh observation from <code>/reset</code>.</p>
        <label for="task-id">Task</label>
        <select id="task-id">
          <option value="easy_snv_short_read">easy_snv_short_read</option>
          <option value="medium_indel_low_coverage">medium_indel_low_coverage</option>
          <option value="hard_repeat_structural_variant">hard_repeat_structural_variant</option>
        </select>
        <label for="seed">Seed</label>
        <input id="seed" type="number" min="0" value="7">
        <div class="button-row">
          <button id="reset-btn" class="primary" type="button">Reset</button>
          <button id="easy-demo-btn" class="secondary" type="button">Easy Demo</button>
        </div>
        <div id="status-box" class="status">Ready.</div>
      </div>

      <div class="panel">
        <h2>Send Action</h2>
        <p>Compose an action payload and post it to <code>/step</code>.</p>
        <label for="action-type">Action Type</label>
        <select id="action-type">
          <option value="inspect_region">inspect_region</option>
          <option value="flag_snv">flag_snv</option>
          <option value="flag_indel">flag_indel</option>
          <option value="flag_structural_variant">flag_structural_variant</option>
          <option value="categorize_variant">categorize_variant</option>
          <option value="submit_answer">submit_answer</option>
        </select>
        <div class="two-col">
          <div>
            <label for="locus">Locus</label>
            <input id="locus" type="number" min="0" value="5">
          </div>
          <div>
            <label for="end">End</label>
            <input id="end" type="number" min="0" value="5">
          </div>
        </div>
        <div class="two-col">
          <div>
            <label for="variant-type">Variant Type</label>
            <select id="variant-type">
              <option value="">none</option>
              <option value="snv">snv</option>
              <option value="insertion">insertion</option>
              <option value="deletion">deletion</option>
              <option value="structural_variant">structural_variant</option>
              <option value="repeat_expansion">repeat_expansion</option>
              <option value="unknown">unknown</option>
            </select>
          </div>
          <div>
            <label for="confidence">Confidence</label>
            <input id="confidence" type="number" min="0" max="1" step="0.01" value="0.99">
          </div>
        </div>
        <div class="two-col">
          <div>
            <label for="ref-allele">Ref Allele</label>
            <input id="ref-allele" type="text">
          </div>
          <div>
            <label for="alt-allele">Alt Allele</label>
            <input id="alt-allele" type="text">
          </div>
        </div>
        <label for="reasoning">Reasoning</label>
        <textarea id="reasoning">Inspect the mismatch hotspot.</textarea>
        <div class="button-row">
          <button id="step-btn" class="primary" type="button">Send</button>
          <button id="prefill-inspect-btn" class="secondary" type="button">Prefill Inspect</button>
          <button id="prefill-submit-btn" class="secondary" type="button">Prefill Submit</button>
        </div>
      </div>
    </section>

    <section class="panel" style="margin-top: 16px;">
      <h2>Latest Response</h2>
      <p>The newest API response is shown below.</p>
      <pre id="response-viewer">No response yet. Reset an episode to begin.</pre>
    </section>
  </main>

  <script>
    const statusBox = document.getElementById("status-box");
    const responseViewer = document.getElementById("response-viewer");

    function setStatus(message, kind = "ok") {
      statusBox.textContent = message;
      if (kind === "error") {
        statusBox.style.background = "rgba(248, 113, 113, 0.10)";
        statusBox.style.borderColor = "rgba(248, 113, 113, 0.18)";
        statusBox.style.color = "#fecaca";
        return;
      }
      statusBox.style.background = "rgba(52, 211, 153, 0.08)";
      statusBox.style.borderColor = "rgba(52, 211, 153, 0.20)";
      statusBox.style.color = "#bbf7d0";
    }

    function setResponse(data) {
      responseViewer.textContent = JSON.stringify(data, null, 2);
    }

    function cleanValue(value) {
      return value === "" ? undefined : value;
    }

    async function postJson(url, payload) {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ? JSON.stringify(data.detail) : JSON.stringify(data));
      }
      return data;
    }

    async function resetEpisode(taskId, seed) {
      try {
        setStatus("Resetting...");
        const payload = { task_id: taskId };
        if (seed !== "" && !Number.isNaN(Number(seed))) {
          payload.seed = Number(seed);
        }
        const data = await postJson("/reset", payload);
        setResponse(data);
        setStatus(`Loaded ${data.observation.task_id}. Remaining budget: ${data.observation.action_budget_remaining}.`);
      } catch (error) {
        setStatus(`Reset failed: ${error.message}`, "error");
      }
    }

    async function sendAction() {
      try {
        setStatus("Sending action...");
        const action = {
          action_type: document.getElementById("action-type").value,
          confidence: Number(document.getElementById("confidence").value),
          reasoning: document.getElementById("reasoning").value,
        };
        const locus = cleanValue(document.getElementById("locus").value);
        const end = cleanValue(document.getElementById("end").value);
        const variantType = cleanValue(document.getElementById("variant-type").value);
        const refAllele = cleanValue(document.getElementById("ref-allele").value);
        const altAllele = cleanValue(document.getElementById("alt-allele").value);
        if (locus !== undefined) action.locus = Number(locus);
        if (end !== undefined) action.end = Number(end);
        if (variantType !== undefined) action.variant_type = variantType;
        if (refAllele !== undefined) action.ref_allele = refAllele;
        if (altAllele !== undefined) action.alt_allele = altAllele;

        const data = await postJson("/step", { action });
        setResponse(data);
        const reward = data.reward ?? 0;
        const done = data.done ? " Episode complete." : "";
        setStatus(`Action accepted. Reward: ${reward}.${done}`);
      } catch (error) {
        setStatus(`Action failed: ${error.message}`, "error");
      }
    }

    function prefillInspect() {
      document.getElementById("action-type").value = "inspect_region";
      document.getElementById("locus").value = "5";
      document.getElementById("end").value = "5";
      document.getElementById("variant-type").value = "";
      document.getElementById("ref-allele").value = "";
      document.getElementById("alt-allele").value = "";
      document.getElementById("confidence").value = "0.80";
      document.getElementById("reasoning").value = "Inspect the mismatch hotspot.";
      setStatus("Inspect payload ready.");
    }

    function prefillSubmit() {
      document.getElementById("action-type").value = "submit_answer";
      document.getElementById("locus").value = "5";
      document.getElementById("end").value = "5";
      document.getElementById("variant-type").value = "snv";
      document.getElementById("ref-allele").value = "A";
      document.getElementById("alt-allele").value = "G";
      document.getElementById("confidence").value = "0.99";
      document.getElementById("reasoning").value = "Submit the exact SNV call.";
      setStatus("Submit payload ready.");
    }

    document.getElementById("reset-btn").addEventListener("click", () => {
      resetEpisode(document.getElementById("task-id").value, document.getElementById("seed").value);
    });
    document.getElementById("easy-demo-btn").addEventListener("click", () => {
      document.getElementById("task-id").value = "easy_snv_short_read";
      document.getElementById("seed").value = "7";
      resetEpisode("easy_snv_short_read", "7");
    });
    document.getElementById("step-btn").addEventListener("click", sendAction);
    document.getElementById("prefill-inspect-btn").addEventListener("click", prefillInspect);
    document.getElementById("prefill-submit-btn").addEventListener("click", prefillSubmit);
  </script>
</body>
</html>
"""

# Create the app with web interface and README integration
app = create_app(
    DnaMutationEnvironment,
    DnaMutationAction,
    DnaMutationObservation,
    env_name="dna_mutation_env",
    max_concurrent_envs=SETTINGS.max_concurrent_envs,
)


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    """Convert environment input errors into clear client-facing responses."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    """Compact dark homepage for the deployed Space."""
    return HTMLResponse(ROOT_HTML)


@app.get("/app-info")
async def app_info() -> dict[str, object]:
    """Machine-readable metadata for the Space."""
    return APP_INFO


@app.get("/ready")
async def readiness() -> dict[str, str]:
    """Readiness probe endpoint for orchestrators like Kubernetes."""
    return {"status": "ready"}


def main(host: str = SETTINGS.host, port: int = SETTINGS.port):
    """
    Entry point for direct execution via uv run or python -m.

    This function enables running the server without Docker:
        uv run --project . server
        uv run --project . server --port 8001
        python -m dna_mutation_env.server.app

    Args:
        host: Host address to bind to (default: "0.0.0.0")
        port: Port number to listen on (default: 8000)

    For production deployments, consider using uvicorn directly with
    multiple workers:
        uvicorn dna_mutation_env.server.app:app --workers 4
    """
    import uvicorn

    LOGGER.info(
        "Starting dna_mutation_env host=%s port=%s workers=%s default_task=%s concurrent_envs=%s",
        SETTINGS.host,
        port,
        SETTINGS.workers,
        SETTINGS.default_task_id,
        SETTINGS.max_concurrent_envs,
    )
    uvicorn.run(app, host=host, port=port, workers=SETTINGS.workers)


if __name__ == "__main__":
    main()
