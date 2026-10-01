"""
llm.py — Provider abstraction pra LLMs (OpenAI-compatible).

Suporta:
  - OpenAI  (OPENAI_API_KEY)
  - DeepSeek (DEEPSEEK_API_KEY, base_url=https://api.deepseek.com)
  - Custom (LLM_BASE_URL + LLM_API_KEY) — qualquer endpoint /v1/chat/completions

Tudo via OpenAI Python SDK com base_url customizável.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class LLMConfig:
    provider: str
    model: str
    api_key: Optional[str]
    base_url: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.2

    @classmethod
    def from_env(cls) -> "LLMConfig":
        # prioridade: custom > deepseek > openai
        custom_key = os.environ.get("LLM_API_KEY")
        custom_url = os.environ.get("LLM_BASE_URL")
        custom_model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

        if custom_key:
            return cls(
                provider="custom",
                model=custom_model,
                api_key=custom_key,
                base_url=custom_url,
            )

        deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
        if deepseek_key:
            return cls(
                provider="deepseek",
                model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
                api_key=deepseek_key,
                base_url="https://api.deepseek.com",
            )

        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            return cls(
                provider="openai",
                model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                api_key=openai_key,
                base_url=None,
            )

        # Modo demo: sem API key, retorna mock
        return cls(
            provider="demo",
            model="mock",
            api_key=None,
            base_url=None,
        )


def chat_completion(
    cfg: LLMConfig,
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: str = "auto",
    max_steps: int = 20,
) -> Dict[str, Any]:
    """
    Faz chat completion. Modo demo (sem key) retorna mock determinístico
    baseado nas tools disponíveis — útil pra desenvolvimento sem API.
    """
    if cfg.provider == "demo" or cfg.api_key is None:
        return _demo_completion(messages, tools)

    # tenta importar OpenAI SDK
    try:
        from openai import OpenAI
    except ImportError:
        return {"error": "openai SDK não instalado. pip install openai"}

    client_kwargs: Dict[str, Any] = {"api_key": cfg.api_key}
    if cfg.base_url:
        client_kwargs["base_url"] = cfg.base_url

    client = OpenAI(**client_kwargs)

    kwargs: Dict[str, Any] = {
        "model": cfg.model,
        "messages": messages,
        "max_tokens": cfg.max_tokens,
        "temperature": cfg.temperature,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice

    try:
        resp = client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        result: Dict[str, Any] = {
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [],
        }
        if msg.tool_calls:
            for tc in msg.tool_calls:
                import json as _json
                try:
                    args = _json.loads(tc.function.arguments)
                except Exception:
                    args = {}
                result["tool_calls"].append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": args,
                    },
                })
        return result
    except Exception as e:
        return {"error": str(e), "messages": messages}


def _demo_completion(
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Modo demo sem API: detecta intent na última user message e escolhe tools.
    Heurística simples — útil pra testar o agent loop end-to-end.
    """
    last_user = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user = m.get("content", "").lower()
            break

    if not tools:
        return {"role": "assistant", "content": "[demo mode] No tools provided.", "tool_calls": []}

    tool_names = [t["function"]["name"] for t in tools]

    # heurística de roteamento
    chosen: List[Dict[str, Any]] = []

    if any(k in last_user for k in ["voxel", "minecraft", "sponge", "cubiquity"]):
        if "cubiquity_generate" in tool_names:
            chosen.append(("cubiquity_generate", {"algorithm": "menger_sponge", "size": 64}))
    if any(k in last_user for k in ["terrain", "terreno", "bycob", "mapa"]):
        if "bycob_world" in tool_names:
            chosen.append(("bycob_world", {"test": "terrain"}))
    if any(k in last_user for k in ["blender", "lod", "process", "decimate"]):
        if "blender_process" in tool_names:
            chosen.append(("blender_process", {"input": "x.obj", "output": "y.glb"}))
    if any(k in last_user for k in ["godot", "jogo", "scene"]):
        if "godot_build_scene" in tool_names:
            chosen.append(("godot_build_scene", {"glb": "y.glb", "output": "scene/"}))
    if any(k in last_user for k in ["validate", "check", "verify"]):
        if "gltf_validate" in tool_names:
            chosen.append(("gltf_validate", {"input": "y.glb"}))
    if any(k in last_user for k in ["pipeline", "run", "execute"]):
        if "pipeline_verified_real" in tool_names:
            chosen.append(("pipeline_verified_real", {}))

    # fallback: nada bateu, executa pipeline_verified_real se existir
    if not chosen and "pipeline_verified_real" in tool_names:
        chosen.append(("pipeline_verified_real", {}))

    if chosen:
        tool_calls = []
        for i, (name, args) in enumerate(chosen):
            tool_calls.append({
                "id": f"call_demo_{i}_{int(time.time())}",
                "type": "function",
                "function": {"name": name, "arguments": args},
            })
        return {
            "role": "assistant",
            "content": f"[demo mode] Vou executar: {', '.join(n for n, _ in chosen)}",
            "tool_calls": tool_calls,
        }

    return {
        "role": "assistant",
        "content": "[demo mode] Não reconheci intent. Tente: 'criar voxel world', 'gerar terrain', 'run pipeline'.",
        "tool_calls": [],
    }
