#!/usr/bin/env python3
"""
pipeline_runner.py — Carrega um YAML de pipeline e executa os estágios.

Cada estágio referencia um tool via `tool:`. O runner resolve o tool para
o wrapper apropriado em tools/cli-wrappers/ ou tools/python/.

Uso:
    python tools/python/pipeline_runner.py --pipeline pipelines/reconstruction.yaml \\
        --var photos_dir=./input --var engine=godot4
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

try:
    import yaml
except ImportError:
    print("Erro: PyYAML não instalado. pip install pyyaml")
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parents[2]
WRAPPERS_DIR = REPO_ROOT / "tools" / "cli-wrappers"


def resolve_wrapper(tool: str):
    """Resolve nome do tool → path do wrapper (.sh) OU módulo Python."""
    candidate = WRAPPERS_DIR / f"{tool}.sh"
    if candidate.exists():
        return ("sh", candidate)
    # Tenta módulo Python em tools/python/<tool>.py
    py_candidate = REPO_ROOT / "tools" / "python" / f"{tool}.py"
    if py_candidate.exists():
        return ("py", py_candidate)
    raise FileNotFoundError(f"Wrapper nem módulo encontrado para tool={tool}")


def run_stage(stage: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Executa um estágio."""
    stage_id = stage.get("id", "unnamed")
    tool = stage["tool"]
    params = stage.get("params", {})

    print(f"\n[pipeline_runner] >>> Estágio: {stage_id} (tool={tool})")

    # Substitui variáveis {{var}} nos parâmetros
    rendered_params = render_params(params, ctx)

    kind, wrapper = resolve_wrapper(tool)

    if kind == "sh":
        cmd = ["bash", str(wrapper)]
        for key, value in rendered_params.items():
            if isinstance(value, bool):
                if value:
                    cmd.append(f"--{key.replace('_', '-')}")
            elif isinstance(value, (list, tuple)):
                cmd.extend([f"--{key.replace('_', '-')}", ",".join(map(str, value))])
            else:
                cmd.extend([f"--{key.replace('_', '-')}", str(value)])

        print(f"[pipeline_runner] $ {' '.join(cmd)}")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        rc, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
    else:  # py
        # Para módulos Python, chamamos como `python3 -m tools.python.<tool>`
        # e passamos args via CLI
        module = f"tools.python.{tool}"
        cmd = ["python3", "-m", module]
        for key, value in rendered_params.items():
            if isinstance(value, bool):
                if value:
                    cmd.append(f"--{key.replace('_', '-')}")
            else:
                cmd.extend([f"--{key.replace('_', '-')}", str(value)])

        print(f"[pipeline_runner] $ {' '.join(cmd)}")
        proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
        rc, stdout, stderr = proc.returncode, proc.stdout, proc.stderr

    log_path = REPO_ROOT / "outputs" / "logs" / f"{stage_id}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(stdout + "\n--- STDERR ---\n" + stderr)

    # Exit code 2 = "skip" (gpu_gate ou similar). Honra continue_on_skip.
    if rc == 2:
        if stage.get("continue_on_skip", False):
            print(f"[pipeline_runner] ⏭  Estágio {stage_id} pulou (exit 2, continue_on_skip=true)")
            return {
                "stage": stage_id, "tool": tool, "kind": kind,
                "params": rendered_params, "log": str(log_path),
                "status": "skipped",
            }
        print(f"[pipeline_runner] ✗ Estágio {stage_id} skipou (exit 2) sem continue_on_skip")
        raise RuntimeError(f"Stage {stage_id} skipped")

    if rc != 0:
        print(f"[pipeline_runner] ✗ Estágio {stage_id} falhou (exit {rc})")
        print(stderr[-1000:] if stderr else "")
        raise RuntimeError(f"Stage {stage_id} failed")

    print(f"[pipeline_runner] ✓ Estágio {stage_id} ok")
    return {"stage": stage_id, "tool": tool, "kind": kind, "params": rendered_params, "log": str(log_path)}


def render_params(params: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Substitui {{var}} nos valores pelos do contexto."""
    rendered = {}
    for key, value in params.items():
        if isinstance(value, str) and "{{" in value:
            for var_name, var_value in ctx.items():
                value = value.replace(f"{{{{{var_name}}}}}", str(var_value))
        rendered[key] = value
    return rendered


def parse_var(s: str) -> tuple:
    key, _, value = s.partition("=")
    return key.strip(), value.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Pipeline runner (YAML-driven).")
    parser.add_argument("--pipeline", required=True, help="Caminho do YAML")
    parser.add_argument("--var", action="append", default=[],
                        help="Variável de contexto (key=value), pode repetir")
    parser.add_argument("--dry-run", action="store_true",
                        help="Só imprime o que rodaria, sem executar")
    args = parser.parse_args()

    pipeline_path = Path(args.pipeline)
    if not pipeline_path.exists():
        print(f"Erro: pipeline não encontrado: {pipeline_path}")
        return 1

    spec = yaml.safe_load(pipeline_path.read_text())
    print(f"[pipeline_runner] Pipeline: {spec.get('name')} v{spec.get('version')}")

    ctx = {}
    for v in args.var:
        k, val = parse_var(v)
        ctx[k] = val

    # variáveis built-in
    ctx.setdefault("output_root", str(REPO_ROOT / "outputs"))
    ctx.setdefault("repo_root", str(REPO_ROOT))

    results = []
    for stage in spec.get("stages", []):
        if args.dry_run:
            print(f"[DRY] {stage.get('id')} → tool={stage['tool']} params={stage.get('params')}")
            continue
        res = run_stage(stage, ctx)
        results.append(res)

    # relatório
    report_path = REPO_ROOT / "outputs" / f"{spec.get('name')}_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps({
        "pipeline": spec.get("name"),
        "version": spec.get("version"),
        "stages": results,
        "context": ctx,
    }, indent=2))
    print(f"\n[pipeline_runner] ✓ Relatório: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
