"""
pipeline_gateway.py — API HTTP estilo OpenAI pra orquestrar o pipeline.

Adaptado de JustVugg/colibri (c/openai_server.py + c/serve_codec.h):
  - POST /v1/pipeline/run    — roda um pipeline
  - GET  /v1/pipeline/status — status de uma run
  - GET  /v1/tier/plan       — plano de tier dos assets registrados
  - GET  /v1/gpu/probe       — detecção de GPU
  - GET  /v1/health          — health check
  - GET  /v1/pipelines       — lista pipelines disponíveis

Uso:
    python3 -m tools.colibri_patterns.cli serve --port 8765
    # Em outro terminal:
    curl -X POST http://localhost:8765/v1/pipeline/run \\
        -H 'Content-Type: application/json' \\
        -d '{"pipeline": "verified_real", "vars": {"output_dir": "./outputs/x/"}}'
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .gpu_probe import detect as detect_gpu
from .tier_manager import TierManager
from .asset_lease import AssetLease


REPO_ROOT = Path(__file__).resolve().parents[2]


# Estado global (em produção real, use Redis/SQLite)
@dataclass
class RunState:
    run_id: str
    pipeline: str
    started_at: float
    status: str = "running"   # running | completed | failed
    finished_at: float = 0.0
    log: str = ""
    error: str = ""
    result: dict = field(default_factory=dict)


class GatewayState:
    def __init__(self):
        self.runs: dict[str, RunState] = {}
        self.tier = TierManager(ram_budget_mb=2048)
        self.lease = AssetLease()
        self.lock = threading.Lock()

    def start_run(self, pipeline: str, vars: dict) -> RunState:
        run_id = str(uuid.uuid4())[:8]
        with self.lock:
            state = RunState(
                run_id=run_id,
                pipeline=pipeline,
                started_at=time.time(),
            )
            self.runs[run_id] = state
        return state

    def update_run(self, run_id: str, **kwargs):
        with self.lock:
            if run_id in self.runs:
                for k, v in kwargs.items():
                    setattr(self.runs[run_id], k, v)


STATE = GatewayState()


def run_pipeline_sync(state: RunState, pipeline: str, vars: dict) -> int:
    """Executa pipeline_runner.py como subprocess."""
    cmd = [
        sys.executable,
        str(REPO_ROOT / "tools" / "python" / "pipeline_runner.py"),
        "--pipeline", str(REPO_ROOT / "pipelines" / f"{pipeline}.yaml"),
    ]
    for k, v in vars.items():
        cmd.extend(["--var", f"{k}={v}"])

    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=3600)
    STATE.update_run(
        state.run_id,
        log=proc.stdout[-5000:],
        error=proc.stderr[-2000:] if proc.returncode != 0 else "",
        finished_at=time.time(),
        status="completed" if proc.returncode == 0 else "failed",
        result={"exit_code": proc.returncode},
    )
    return proc.returncode


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silencia o log padrão do BaseHTTPRequestHandler (ruidoso)
        sys.stderr.write(f"[{time.strftime('%H:%M:%S')}] {format % args}\n")

    def _send_json(self, status: int, payload: Any):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def do_GET(self):
        if self.path == "/v1/health":
            self._send_json(200, {"status": "ok", "ts": time.time()})

        elif self.path == "/v1/gpu/probe":
            self._send_json(200, detect_gpu().to_dict())

        elif self.path == "/v1/tier/plan":
            self._send_json(200, STATE.tier.status())

        elif self.path == "/v1/lease/stats":
            self._send_json(200, STATE.lease.stats.to_dict())

        elif self.path == "/v1/pipelines":
            pl_dir = REPO_ROOT / "pipelines"
            pipelines = []
            for y in pl_dir.glob("*.yaml"):
                pipelines.append(y.stem)
            self._send_json(200, {"pipelines": pipelines})

        elif self.path.startswith("/v1/pipeline/status/"):
            run_id = self.path.split("/")[-1]
            with STATE.lock:
                state = STATE.runs.get(run_id)
            if not state:
                self._send_json(404, {"error": "run not found", "run_id": run_id})
            else:
                self._send_json(200, asdict(state))

        elif self.path == "/":
            self._send_json(200, {
                "service": "ai-3d-world-pipeline gateway",
                "version": "1.0.0",
                "inspired_by": "JustVugg/colibri",
                "endpoints": [
                    "GET  /v1/health",
                    "GET  /v1/gpu/probe",
                    "GET  /v1/tier/plan",
                    "GET  /v1/lease/stats",
                    "GET  /v1/pipelines",
                    "GET  /v1/pipeline/status/<run_id>",
                    "POST /v1/pipeline/run",
                ],
            })

        else:
            self._send_json(404, {"error": "not found", "path": self.path})

    def do_POST(self):
        if self.path == "/v1/pipeline/run":
            body = self._read_body()
            pipeline = body.get("pipeline")
            vars = body.get("vars", {})
            async_run = body.get("async", True)

            if not pipeline:
                self._send_json(400, {"error": "missing 'pipeline'"})
                return

            state = STATE.start_run(pipeline, vars)

            if async_run:
                t = threading.Thread(
                    target=run_pipeline_sync,
                    args=(state, pipeline, vars),
                    daemon=True,
                )
                t.start()
                self._send_json(202, {
                    "run_id": state.run_id,
                    "status": "started",
                    "status_url": f"/v1/pipeline/status/{state.run_id}",
                })
            else:
                rc = run_pipeline_sync(state, pipeline, vars)
                self._send_json(200 if rc == 0 else 500, asdict(state))

        else:
            self._send_json(404, {"error": "POST not supported here", "path": self.path})


def serve(host: str = "127.0.0.1", port: int = 8765):
    """Sobe o gateway."""
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"🐦 pipeline_gateway listening on http://{host}:{port}", flush=True)
    print(f"   Inspired by JustVugg/colibri — same OpenAI-style API pattern", flush=True)
    print(f"   Repo: {REPO_ROOT}", flush=True)
    print(f"   Endpoints: GET / (root) para lista completa", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[gateway] shutting down")
        server.shutdown()


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    args = p.parse_args()
    serve(args.host, args.port)
