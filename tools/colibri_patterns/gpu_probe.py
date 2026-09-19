"""
gpu_probe.py — Detecta GPU e define flag COLI_GPU (inspirado em COLI_CUDA=1 do Colibri).

Adaptado de JustVugg/colibri (c/colibri.c:130-134):
  "GPU support is opt-in via COLI_CUDA=1 or COLI_HIP=1"
  "Default build is pure, dependency-free CPU"

Aqui detectamos a presença de GPU NVIDIA via:
  - nvidia-smi no PATH
  - /dev/nvidia* no Linux
  - Variáveis de ambiente CUDA_VISIBLE_DEVICES

Retorna TierConfig com:
  - has_gpu (bool)
  - gpu_tier ("cuda" | "rocm" | "metal" | "cpu")
  - vram_total_mb, vram_free_mb
  - recommended_policy ("cpu_only" | "hybrid" | "gpu_preferred")
"""
from __future__ import annotations

import os
import shutil
import subprocess
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal


GPU_TIER = Literal["cuda", "rocm", "metal", "cpu"]
POLICY = Literal["cpu_only", "hybrid", "gpu_preferred"]


@dataclass
class TierConfig:
    has_gpu: bool
    gpu_tier: GPU_TIER
    vram_total_mb: int = 0
    vram_free_mb: int = 0
    device_count: int = 0
    device_names: list[str] = None
    recommended_policy: POLICY = "cpu_only"
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def probe_nvidia_smi() -> dict | None:
    """Tenta nvidia-smi; retorna dict com info ou None."""
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return None
    try:
        out = subprocess.run(
            [nvidia_smi, "--query-gpu=index,name,memory.total,memory.free,driver_version",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if out.returncode != 0:
            return None
        devices = []
        for line in out.stdout.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 4:
                devices.append({
                    "index": int(parts[0]),
                    "name": parts[1],
                    "vram_total_mb": int(float(parts[2])),
                    "vram_free_mb": int(float(parts[3])),
                    "driver": parts[4] if len(parts) > 4 else "unknown",
                })
        return {"devices": devices}
    except (subprocess.TimeoutExpired, ValueError, IndexError) as e:
        return {"error": str(e)}


def probe_dev_nvidia() -> bool:
    """Verifica /dev/nvidia* no Linux."""
    return any(Path(f"/dev/nvidia{i}").exists() for i in range(8))


def probe_cuda_env() -> dict:
    """Lê variáveis de ambiente CUDA."""
    return {
        "CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES", ""),
        "NVIDIA_VISIBLE_DEVICES": os.environ.get("NVIDIA_VISIBLE_DEVICES", ""),
        "CUDA_HOME": os.environ.get("CUDA_HOME", ""),
    }


def detect() -> TierConfig:
    """Detecta GPU e retorna TierConfig."""
    notes = []

    # 1. nvidia-smi
    smi = probe_nvidia_smi()
    if smi and "devices" in smi:
        devices = smi["devices"]
        total_vram = sum(d["vram_total_mb"] for d in devices)
        free_vram = sum(d["vram_free_mb"] for d in devices)
        names = [d["name"] for d in devices]

        # Policy: muita VRAM livre + GPU forte → gpu_preferred
        # Pouca VRAM → hybrid
        # Sem VRAM → cpu_only
        if free_vram >= 16000:
            policy = "gpu_preferred"
        elif free_vram >= 4000:
            policy = "hybrid"
        else:
            policy = "cpu_only"
            notes.append(f"GPU detectada mas VRAM livre ({free_vram} MB) insuficiente para modo GPU")

        return TierConfig(
            has_gpu=True,
            gpu_tier="cuda",
            vram_total_mb=total_vram,
            vram_free_mb=free_vram,
            device_count=len(devices),
            device_names=names,
            recommended_policy=policy,
            notes="; ".join(notes) if notes else "GPU CUDA detectada via nvidia-smi",
        )

    # 2. /dev/nvidia* sem nvidia-smi (drivers mas sem userspace)
    if probe_dev_nvidia():
        return TierConfig(
            has_gpu=True,
            gpu_tier="cuda",
            device_count=1,
            recommended_policy="hybrid",
            notes="GPU detectada via /dev/nvidia* mas nvidia-smi ausente — instale drivers userspace",
        )

    # 3. ROCm (AMD)
    rocm_smi = shutil.which("rocm-smi")
    if rocm_smi:
        return TierConfig(
            has_gpu=True,
            gpu_tier="rocm",
            recommended_policy="hybrid",
            notes="GPU AMD detectada via rocm-smi (não testado neste ambiente)",
        )

    # 4. Metal (macOS — não testado aqui, mas simétrico)
    if sys.platform == "darwin":
        return TierConfig(
            has_gpu=True,
            gpu_tier="metal",
            recommended_policy="hybrid",
            notes="macOS detectado — Metal disponível",
        )

    # 5. Sem GPU
    return TierConfig(
        has_gpu=False,
        gpu_tier="cpu",
        device_count=0,
        recommended_policy="cpu_only",
        notes="Nenhuma GPU detectada — pipeline rodará em CPU-only mode",
    )


def main():
    config = detect()
    print(json.dumps(config.to_dict(), indent=2))

    # Exit code: 0 se detectou GPU, 1 se CPU-only
    return 0 if config.has_gpu else 1


if __name__ == "__main__":
    sys.exit(main())
