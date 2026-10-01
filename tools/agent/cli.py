"""
cli.py — Entry point CLI do agent (estilo ./coli + dsh CLI).

Uso:
    # modo one-shot (executa e sai):
    python3 -m tools.agent.cli "criar voxel world com cubiquity"
    python3 -m tools.agent.cli "gerar terrain + GLB + Godot scene"

    # REPL interativo:
    python3 -m tools.agent.cli repl

    # listar tools/skills:
    python3 -m tools.agent.cli tools
    python3 -m tools.agent.cli skills

    # rodar com session específica:
    python3 -m tools.agent.cli --session my_session "run pipeline"
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Permite usar como `python3 -m tools.agent.cli` adiciona path raiz
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.agent.agent import Agent, AgentOptions
from tools.agent.llm import LLMConfig
from tools.agent.session import Session
from tools.agent.skills import SkillRegistry
from tools.agent.tools import ToolRegistry


def cmd_run(args):
    """One-shot: executa um prompt e sai."""
    session = None
    if args.session:
        from pathlib import Path
        path = Path("/workspace/ai-3d-world-pipeline/outputs/sessions") / f"{args.session}.jsonl"
        if path.exists():
            session = Session.load(path)
        else:
            session = Session(session_id=args.session)

    agent = Agent(
        llm_cfg=LLMConfig.from_env(),
        options=AgentOptions(
            max_steps=args.max_steps,
            verbose=not args.quiet,
            category_filter=args.category,
            skill_names=args.skills.split(",") if args.skills else None,
        ),
        session=session,
    )
    prompt = " ".join(args.prompt)
    print(f"[a3dw] session: {agent.session.session_id}")
    print(f"[a3dw] prompt: {prompt}\n")
    result = agent.step(prompt)
    print("\n" + "=" * 60)
    print("[a3dw] RESULTADO FINAL:")
    print("=" * 60)
    print(result)
    print("=" * 60)
    print(f"[a3dw] session log: {agent.session.path}")
    return 0


def cmd_repl(args):
    """REPL interativo."""
    agent = Agent(
        llm_cfg=LLMConfig.from_env(),
        options=AgentOptions(
            max_steps=args.max_steps,
            verbose=not args.quiet,
        ),
    )
    print(f"[a3dw] REPL interativo. session: {agent.session.session_id}")
    print("[a3dw] comandos: /tools, /skills, /quit")
    print("[a3dw] qualquer outra coisa = prompt pro agente\n")

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[a3dw] tchau!")
            break
        if not user_input:
            continue
        if user_input == "/quit":
            break
        if user_input == "/tools":
            reg = ToolRegistry()
            for cat, names in reg.categories().items():
                print(f"\n[{cat}]")
                for n in names:
                    print(f"  - {n}")
            continue
        if user_input == "/skills":
            reg = SkillRegistry()
            for s in reg.all():
                print(f"  [{s.name}] v{s.version} — {s.description[:80]}")
            continue
        print()
        result = agent.step(user_input)
        print(f"\n[a3dw] → {result}\n")


def cmd_tools(args):
    reg = ToolRegistry()
    print(f"Total: {len(reg.all())} tools\n")
    for cat, names in reg.categories().items():
        print(f"[{cat}] ({len(names)})")
        for n in names:
            t = reg.get(n)
            if t:
                print(f"  - {n} ({t.backend}, timeout={t.timeout_s}s)")
                print(f"      {t.description[:100]}")


def cmd_skills(args):
    reg = SkillRegistry()
    print(f"Total: {len(reg.all())} skills\n")
    for s in reg.all():
        print(f"  [{s.name}] v{s.version}")
        print(f"      {s.description}")
        if s.triggers:
            print(f"      triggers: {', '.join(s.triggers)}")
        print()


def cmd_status(args):
    cfg = LLMConfig.from_env()
    print(f"LLM provider: {cfg.provider}")
    print(f"LLM model:    {cfg.model}")
    print(f"base_url:     {cfg.base_url or '(default)'}")
    print(f"api_key:      {'***' + cfg.api_key[-4:] if cfg.api_key else '(none — demo mode)'}")
    print()
    print("Tools:")
    reg = ToolRegistry()
    for cat, names in reg.categories().items():
        print(f"  [{cat}] {len(names)}")
    print()
    print("Skills:")
    sreg = SkillRegistry()
    print(f"  total: {len(sreg.all())}")


def main():
    p = argparse.ArgumentParser(
        description="ai-3d-world-pipeline agent (estilo DeepSeek Harness, em Python)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--max-steps", type=int, default=20)
    p.add_argument("--quiet", action="store_true")
    p.add_argument("--category", help="Filtra tools por categoria")
    p.add_argument("--skills", help="CSV de skills injetadas (ex: orchestrator,voxel-world)")
    p.add_argument("--session", help="Session ID (resume se existir)")

    sub = p.add_subparsers(dest="cmd")
    sub_run = sub.add_parser("run", help="One-shot run com prompt")
    sub_run.add_argument("prompt", nargs="+", help="Prompt pro agente")
    sub_run.set_defaults(func=cmd_run)

    sub.add_parser("tools", help="Lista tools registradas").set_defaults(func=cmd_tools)
    sub.add_parser("skills", help="Lista skills carregadas").set_defaults(func=cmd_skills)
    sub.add_parser("status", help="Status do LLM provider").set_defaults(func=cmd_status)
    sub.add_parser("repl", help="REPL interativo").set_defaults(func=cmd_repl)

    # backward-compat: se primeiro arg não é subcomando, trata como run
    if len(sys.argv) > 1 and sys.argv[1] not in ("run", "tools", "skills", "status", "repl", "-h", "--help"):
        sys.argv.insert(1, "run")

    args = p.parse_args()
    if not hasattr(args, "func"):
        p.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
