"""
session.py — Persistência de sessões em JSONL.

Inspirado em @deepseek-ai/dsh-session (append-only SessionEvent log).
Aqui simplificamos: cada linha é um evento (role, content, tool_call, tool_result).
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_SESSIONS_DIR = Path("/workspace/ai-3d-world-pipeline/outputs/sessions")


@dataclass
class Event:
    """Um evento na sessão (mensagem, tool call, tool result, system)."""
    type: str            # "user" | "assistant" | "tool_call" | "tool_result" | "system" | "error"
    ts: float
    data: Dict[str, Any] = field(default_factory=dict)
    event_id: str = ""

    def __post_init__(self):
        if not self.event_id:
            self.event_id = uuid.uuid4().hex[:12]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Session:
    """Sessão append-only (estilo dsh-session SessionEvent)."""

    def __init__(self, session_id: Optional[str] = None, sessions_dir: Path = DEFAULT_SESSIONS_DIR):
        self.session_id = session_id or f"session_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        self.sessions_dir = sessions_dir
        self.path = sessions_dir / f"{self.session_id}.jsonl"
        self.events: List[Event] = []
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        # cria header
        self._append(Event(type="header", ts=time.time(), data={"session_id": self.session_id}))

    def _append(self, event: Event):
        self.events.append(event)
        with self.path.open("a") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

    def add_user(self, content: str):
        self._append(Event(type="user", ts=time.time(), data={"role": "user", "content": content}))

    def add_assistant(self, content: str, tool_calls: Optional[List[Dict]] = None):
        self._append(Event(
            type="assistant", ts=time.time(),
            data={"role": "assistant", "content": content, "tool_calls": tool_calls or []},
        ))

    def add_tool_call(self, call_id: str, name: str, args: Dict[str, Any]):
        self._append(Event(
            type="tool_call", ts=time.time(),
            data={"call_id": call_id, "name": name, "args": args},
        ))

    def add_tool_result(self, call_id: str, result: Dict[str, Any]):
        self._append(Event(
            type="tool_result", ts=time.time(),
            data={"call_id": call_id, "result": result},
        ))

    def add_system(self, content: str):
        self._append(Event(type="system", ts=time.time(), data={"content": content}))

    def add_error(self, error: str):
        self._append(Event(type="error", ts=time.time(), data={"error": error}))

    def to_messages(self) -> List[Dict[str, Any]]:
        """Converte events pra OpenAI-style messages."""
        out: List[Dict[str, Any]] = []
        for ev in self.events:
            if ev.type == "user":
                out.append({"role": "user", "content": ev.data["content"]})
            elif ev.type == "assistant":
                msg: Dict[str, Any] = {"role": "assistant", "content": ev.data["content"]}
                if ev.data.get("tool_calls"):
                    msg["tool_calls"] = ev.data["tool_calls"]
                out.append(msg)
            elif ev.type == "tool_result":
                out.append({
                    "role": "tool",
                    "tool_call_id": ev.data["call_id"],
                    "content": json.dumps(ev.data["result"])[:8000],
                })
        return out

    def tail(self, n: int = 10) -> List[Event]:
        return self.events[-n:]

    @classmethod
    def load(cls, path: Path) -> "Session":
        sess = cls(session_id=path.stem, sessions_dir=path.parent)
        sess.events = []   # já escreveu header de novo, vamos recarregar
        sess.path.unlink()  # remove o header duplicado
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            ev = Event(
                type=d["type"], ts=d["ts"],
                data=d["data"], event_id=d.get("event_id", ""),
            )
            sess.events.append(ev)
        # regrava tudo no novo path (mantém consistência)
        with sess.path.open("w") as f:
            for e in sess.events:
                f.write(json.dumps(e.to_dict()) + "\n")
        return sess
