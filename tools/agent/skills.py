"""
skills.py — Carrega as skills procedurais já existentes como contexto pro LLM.

Adaptado de @deepseek-ai/dsh-skill (ctx.skills.register / get / list).

Cada skill em skills/<name>.md vira system-prompt context.
O LLM pode listar, ler, e seguir o "playbook" procedural que escrevemos.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "skills"


@dataclass
class Skill:
    name: str
    version: str
    description: str
    triggers: List[str] = field(default_factory=list)
    body: str = ""
    path: Optional[Path] = None

    def render(self) -> str:
        """Renderiza a skill pro system prompt (estilo dsh-skill <skill_content>)."""
        out = [f'<skill name="{self.name}" version="{self.version}">']
        out.append(f"  description: {self.description}")
        if self.triggers:
            out.append(f"  triggers: {', '.join(self.triggers)}")
        out.append("")
        out.append(self.body)
        out.append("</skill>")
        return "\n".join(out)


_FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[Dict[str, str], str]:
    """Parse YAML frontmatter (leve, não usa PyYAML pra evitar dep)."""
    m = _FRONT_MATTER_RE.match(text)
    if not m:
        return {}, text
    meta: Dict[str, str] = {}
    fm_text, body = m.group(1), m.group(2)
    for line in fm_text.splitlines():
        line = line.rstrip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, body


class SkillRegistry:
    """Carrega skills/*.md em memória (estilo dsh-skill-filesystem)."""

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self.load_all()

    def load_all(self):
        if not SKILLS_DIR.exists():
            return
        for path in sorted(SKILLS_DIR.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            meta, body = _parse_frontmatter(text)
            name = meta.get("name", path.stem)
            triggers_raw = meta.get("triggers", "")
            triggers = [t.strip() for t in triggers_raw.split(",") if t.strip()]
            version = meta.get("version", "0.0.0")
            description = meta.get("description", "")
            if not description:
                # pega primeira linha do body
                first_lines = [l for l in body.splitlines() if l.strip() and not l.strip().startswith("#")]
                description = first_lines[0] if first_lines else ""

            skill = Skill(
                name=name,
                version=version,
                description=description,
                triggers=triggers,
                body=body,
                path=path,
            )
            self._skills[name] = skill

    def get(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

    def all(self) -> List[Skill]:
        return list(self._skills.values())

    def match_triggers(self, query: str) -> List[Skill]:
        """Retorna skills cujos triggers batem com a query."""
        q = query.lower()
        out: List[Skill] = []
        for s in self._skills.values():
            for trig in s.triggers:
                if trig.lower() in q:
                    out.append(s)
                    break
        return out

    def render_for_prompt(self, skill_names: Optional[List[str]] = None) -> str:
        """Renderiza skills selecionadas pra injetar no system prompt."""
        skills = (
            [self._skills[n] for n in skill_names if n in self._skills]
            if skill_names else self._skills.values()
        )
        if not skills:
            return ""
        out = ["# Available Skills (procedural patterns)\n"]
        for s in skills:
            out.append(s.render())
            out.append("")
        return "\n".join(out)


if __name__ == "__main__":
    reg = SkillRegistry()
    print(f"Loaded {len(reg.all())} skills:\n")
    for s in reg.all():
        print(f"  [{s.name}] v{s.version}  triggers: {s.triggers}")
    print("\n" + "=" * 60)
    print(reg.render_for_prompt(["orchestrator"]))
