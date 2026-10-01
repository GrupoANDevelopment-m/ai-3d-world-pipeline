"""
ai-3d-world-pipeline agent framework (tools/agent).

Inspirado em @deepseek-ai/dsh (Cordis + plugin + tool registry + agent loop),
adaptado pra Python e integrado com:
  - tools/cli-wrappers/    (15 wrappers shell já existentes)
  - tools/python/          (módulos Python já existentes)
  - pipelines/*.yaml       (pipelines compostas já existentes)
  - skills/*.md            (procedural patterns já existentes)
  - tools/colibri_patterns/ (JustVugg/colibri patterns já adaptados)

Usage:
    from tools.agent import Agent, ToolRegistry, SkillRegistry, LLMConfig
"""
from .agent import Agent, AgentOptions
from .llm import LLMConfig, chat_completion
from .session import Event, Session
from .skills import Skill, SkillRegistry
from .tools import Tool, ToolParameter, ToolRegistry

__all__ = [
    "Agent", "AgentOptions",
    "LLMConfig", "chat_completion",
    "Event", "Session",
    "Skill", "SkillRegistry",
    "Tool", "ToolParameter", "ToolRegistry",
]
