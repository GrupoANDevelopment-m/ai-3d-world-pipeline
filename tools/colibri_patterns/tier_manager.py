"""
tier_manager.py — Gerencia o que fica em RAM vs streaming de disco.

Adaptado de JustVugg/colibri (c/tier.h + c/expert_store.h):
  - LFRU score (frequency + recency) para decidir promoção/democão
  - Lease-based: cada asset tem lookup/release explícito
  - RAM budget rígido: nunca excede N MB
  - Disk tier: mmap'd para leitura sem cópia

Aqui simplificamos para Python puro, com a mesma semântica:
  - Plan: dado um conjunto de assets, decide quem fica em RAM e quem vai pra disk
  - Acquire/Release: lifecycle explícito
  - Stream: lazy read sob demanda
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Asset:
    """Um asset com tamanho, caminho no disco e estado."""
    name: str
    size_bytes: int
    disk_path: Path
    last_access_ts: float = 0.0
    access_count: int = 0
    in_ram: bool = False
    pinned: bool = False  # não pode ser despejado

    def lfru_score(self, now: float) -> float:
        """LFRU = frequency * 256 + recency (0..255).
        Inspirado em c/tier.h:tier_lfru_score.
        """
        age = min(255.0, now - self.last_access_ts)
        recency = max(0.0, 255.0 - age)
        return (self.access_count << 8) | int(recency)


@dataclass
class TierPlan:
    """Decisão: quem fica em RAM, quem é streaming."""
    resident: list[str] = field(default_factory=list)
    streaming: list[str] = field(default_factory=list)
    evicted: list[str] = field(default_factory=list)
    ram_used_bytes: int = 0
    ram_budget_bytes: int = 0
    disk_total_bytes: int = 0

    def to_dict(self) -> dict:
        return {
            "resident": self.resident,
            "streaming": self.streaming,
            "evicted": self.evicted,
            "ram_used_bytes": self.ram_used_bytes,
            "ram_budget_bytes": self.ram_budget_bytes,
            "disk_total_bytes": self.disk_total_bytes,
            "ram_used_mb": round(self.ram_used_bytes / 1_048_576, 1),
            "ram_budget_mb": round(self.ram_budget_bytes / 1_048_576, 1),
            "disk_total_mb": round(self.disk_total_bytes / 1_048_576, 1),
        }


class TierManager:
    """Decide placement de assets entre RAM (resident) e disk (streaming).

    Inspirado em c/expert_store.h:ColiExpertStore do Colibri.
    """

    def __init__(self, ram_budget_mb: int = 2048):
        self.ram_budget_bytes = ram_budget_mb * 1_048_576
        self.assets: dict[str, Asset] = {}
        self.clock = 0.0

    def register(self, name: str, disk_path: Path, size_bytes: int, pinned: bool = False):
        """Registra um asset. NÃO lê do disco ainda."""
        self.assets[name] = Asset(
            name=name,
            size_bytes=size_bytes,
            disk_path=disk_path,
            pinned=pinned,
        )

    def touch(self, name: str):
        """Marca acesso (atualiza recência e frequência)."""
        if name not in self.assets:
            return
        a = self.assets[name]
        a.last_access_ts = time.time()
        a.access_count += 1

    def plan(self) -> TierPlan:
        """Calcula plano: quem fica em RAM, quem vai pro streaming."""
        plan = TierPlan(ram_budget_bytes=self.ram_budget_bytes)
        plan.disk_total_bytes = sum(a.size_bytes for a in self.assets.values())

        # Ordena por LFRU (maior = mais quente)
        now = time.time()
        ordered = sorted(
            self.assets.values(),
            key=lambda a: a.lfru_score(now),
            reverse=True,
        )

        # Pinned vão primeiro
        ram_used = 0
        for a in ordered:
            if a.pinned and ram_used + a.size_bytes <= self.ram_budget_bytes:
                a.in_ram = True
                plan.resident.append(a.name)
                ram_used += a.size_bytes
            elif a.pinned:
                # Pinned mas não cabe — warning
                plan.evicted.append(f"{a.name} (PINNED mas sem RAM!)")

        # Depois os quentes (LFRU)
        for a in ordered:
            if a.pinned or a.in_ram:
                continue
            if ram_used + a.size_bytes <= self.ram_budget_bytes:
                a.in_ram = True
                plan.resident.append(a.name)
                ram_used += a.size_bytes
            else:
                plan.streaming.append(a.name)

        plan.ram_used_bytes = ram_used
        return plan

    def acquire(self, name: str) -> bytes:
        """'Lease': carrega asset (ou parte dele) na RAM.

        Em produção real abriria um mmap e retornaria um view. Aqui retorna bytes.
        """
        if name not in self.assets:
            raise KeyError(f"asset não registrado: {name}")
        a = self.assets[name]
        self.touch(name)
        if not a.disk_path.exists():
            raise FileNotFoundError(a.disk_path)
        # Aqui não vamos realmente carregar tudo (memory safety); só indicamos intenção
        return b""

    def release(self, name: str):
        """Libera lease. Asset pode ser despejado se não pinned."""
        if name in self.assets:
            # Não liberamos realmente aqui; o plan() recalcula
            pass

    def status(self) -> dict:
        return {
            "ram_budget_mb": round(self.ram_budget_bytes / 1_048_576, 1),
            "assets_registered": len(self.assets),
            "plan": self.plan().to_dict(),
        }


def demo():
    """Demo: registra 5 assets, mostra plano."""
    m = TierManager(ram_budget_mb=2048)
    # Simula: 1 splat grande, 2 médias, 2 pequenas
    m.register("scene_main.ksplat", Path("/tmp/scene_main.ksplat"), 500_000_000)
    m.register("factory.glb", Path("/tmp/factory.glb"), 50_000_000)
    m.register("terrain.glb", Path("/tmp/terrain.glb"), 30_000_000)
    m.register("lighting_setup.json", Path("/tmp/lx.json"), 5_000_000)
    m.register("config.json", Path("/tmp/cfg.json"), 1_000_000, pinned=True)

    # Simula acessos
    for _ in range(10):
        m.touch("scene_main.ksplat")
    for _ in range(5):
        m.touch("factory.glb")
    m.touch("terrain.glb")
    m.touch("lighting_setup.json")

    print(json.dumps(m.status(), indent=2))


if __name__ == "__main__":
    demo()
