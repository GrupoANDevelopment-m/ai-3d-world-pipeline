"""
agent.py — Agent loop estilo dsh-agent-loop (ReactLoopAgent simplificado).

Loop:
  1. Envia mensagem do user + tools pra LLM
  2. Se LLM responde com tool_calls → executa cada tool, anexa tool_results
  3. Volta pra LLM (step)
  4. Repete até LLM responder sem tool_calls ou max_steps atingido

Tudo persiste em session.jsonl.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .llm import LLMConfig, chat_completion
from .session import Session
from .skills import SkillRegistry
from .tools import ToolRegistry


SYSTEM_PROMPT = """You are the **ai-3d-world-pipeline agent**. You control a suite of REAL tools for 3D world generation that all run on CPU.

## Your capabilities

You can call tools to generate, process, validate, and export 3D content. Each tool returns `ok: bool` and stdout/stderr — read those to decide next steps.

## Workflow pattern

1. **Read** the user request carefully.
2. **Plan** which tools to call (1-N tools, in order).
3. **Call** the first tool, read its result.
4. **Decide** if you need more tools (e.g., a generated OBJ needs to be converted to GLB → validate → export to Godot).
5. **Continue** until the user's goal is achieved.
6. **Report** final result in plain text.

## Important rules

- ALWAYS inspect tool results before next step.
- If a tool fails (ok=false), try an alternative OR explain the limitation.
- Prefer **pipelines** (composite tools like pipeline_verified_real) when they fit the request.
- For voxel worlds: cubiquity_generate → optionally combine with bycob terrain.
- For terrain: bycob_world → blender_process → gltf_validate → godot_build_scene.
- For photogrammetry: colmap_reconstruct → opensplat_train.
- For OSM cities: rsgeotools_generate → blender_process → godot_build_scene.

## Output format

After all tool calls complete, give a SHORT summary in Portuguese/English:
  - O que foi feito
  - Onde estão os outputs (paths)
  - Próximos passos se houver
"""


@dataclass
class AgentOptions:
    max_steps: int = 20
    verbose: bool = True
    category_filter: Optional[str] = None   # restringe tools por categoria
    skill_names: Optional[List[str]] = None  # skills injetadas no system prompt


class Agent:
    """Driver de turno estilo dsh-agent-loop."""

    def __init__(
        self,
        llm_cfg: Optional[LLMConfig] = None,
        options: Optional[AgentOptions] = None,
        tool_registry: Optional[ToolRegistry] = None,
        skill_registry: Optional[SkillRegistry] = None,
        session: Optional[Session] = None,
    ):
        self.llm = llm_cfg or LLMConfig.from_env()
        self.opts = options or AgentOptions()
        self.tools = tool_registry or ToolRegistry()
        self.skills = skill_registry or SkillRegistry()
        self.session = session or Session()

    def _system_messages(self) -> List[Dict[str, Any]]:
        """Monta system prompt: base + skills."""
        content = SYSTEM_PROMPT
        skills_text = self.skills.render_for_prompt(self.opts.skill_names)
        if skills_text:
            content += "\n\n" + skills_text
        return [{"role": "system", "content": content}]

    def step(self, user_msg: str) -> str:
        """Executa um turno completo (até LLM parar de chamar tools)."""
        self.session.add_user(user_msg)
        messages = self._system_messages() + self.session.to_messages()
        tools = self.tools.as_openai_tools(self.opts.category_filter)

        if self.opts.verbose:
            print(f"\n[agent] LLM provider={self.llm.provider} model={self.llm.model}")
            print(f"[agent] {len(tools)} tools disponíveis\n")

        final_text = ""
        called_tools: List[str] = []   # pra detectar demo mode loop
        for step_idx in range(self.opts.max_steps):
            if self.opts.verbose:
                print(f"--- step {step_idx + 1}/{self.opts.max_steps} ---")

            resp = chat_completion(
                self.llm, messages, tools=tools, tool_choice="auto",
            )
            if "error" in resp:
                self.session.add_error(resp["error"])
                return f"[agent] erro: {resp['error']}"

            content = resp.get("content", "")
            tool_calls = resp.get("tool_calls", [])

            self.session.add_assistant(content, tool_calls)
            if content and self.opts.verbose:
                print(f"[assistant] {content}")

            if not tool_calls:
                final_text = content
                break

            # demo-mode loop guard: se LLM chama mesma tool 2x seguidas, para
            current_calls = [c["function"]["name"] for c in tool_calls]
            if current_calls == called_tools[-len(current_calls):] if called_tools else False:
                if self.opts.verbose:
                    print("[agent] demo loop detectado, encerrando")
                final_text = content or "(demo loop encerrado)"
                break
            called_tools.extend(current_calls)

            # executa tools
            for call in tool_calls:
                name = call["function"]["name"]
                args = call["function"]["arguments"]
                call_id = call["id"]

                self.session.add_tool_call(call_id, name, args)
                tool = self.tools.get(name)
                if tool is None:
                    err = {"ok": False, "error": f"tool '{name}' não encontrada"}
                    self.session.add_tool_result(call_id, err)
                    if self.opts.verbose:
                        print(f"[tool:{name}] ERROR: tool não encontrada")
                    continue

                if self.opts.verbose:
                    print(f"[tool:{name}] args={json.dumps(args)[:200]}")
                    t0 = time.time()
                try:
                    result = tool.execute(args)
                except Exception as e:
                    result = {"ok": False, "error": str(e)}

                self.session.add_tool_result(call_id, result)

                if self.opts.verbose:
                    dt = time.time() - t0
                    ok_str = "✓" if result.get("ok") else "✗"
                    print(f"[tool:{name}] {ok_str} ({dt:.1f}s)")
                    if not result.get("ok") and result.get("error"):
                        print(f"  error: {result['error'][:200]}")
                    if result.get("stdout"):
                        so = result["stdout"].strip().splitlines()[-3:]
                        for line in so:
                            print(f"  | {line[:150]}")

            # rebuild messages with tool results
            messages = self._system_messages() + self.session.to_messages()
        else:
            final_text = "[agent] max_steps atingido sem conclusão."

        return final_text or "(sem texto final)"
