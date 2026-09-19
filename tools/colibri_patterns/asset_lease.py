"""
asset_lease.py — Lifecycle explícito para assets (lookup/release).

Adaptado de JustVugg/colibri (c/expert_store.h):
  - Lease contract: lookup() followed by exactly one release()
  - On lookup failure, view is cleared
  - release() on already-cleared view is a no-op
  - Stats: requests, hits, misses, bytes_read, resident_bytes

Aqui expomos uma classe Python AssetLease que segue o mesmo contrato,
com métricas para o pipeline saber quantos assets estão ativos.
"""
from __future__ import annotations

import time
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class LeaseStats:
    requests: int = 0
    hits: int = 0
    misses: int = 0
    prefetched: int = 0
    bytes_read: int = 0
    resident_bytes: int = 0

    def to_dict(self) -> dict:
        return {
            "requests": self.requests,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / max(1, self.requests), 4),
            "bytes_read": self.bytes_read,
            "resident_bytes": self.resident_bytes,
            "resident_mb": round(self.resident_bytes / 1_048_576, 2),
        }


class AssetView:
    """Handle retornado por lookup(). NÃO compartilhe entre threads."""

    def __init__(self, name: str, path: Path, size: int):
        self.name = name
        self.path = path
        self.size = size
        self._released = False
        self._leased_at = time.time()

    def is_valid(self) -> bool:
        return not self._released

    def release(self):
        self._released = True


class AssetLease:
    """Gerencia ciclo de vida de assets com lease explícito.

    Exemplo:
        lease = AssetLease()
        with lease.lookup("scene.glb") as view:
            if view.is_valid():
                # usar view...
                pass
        # ao sair do with, view é liberado automaticamente
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._active: dict[str, AssetView] = {}
        self.stats = LeaseStats()

    @contextmanager
    def lookup(self, name: str, path: Path):
        """Adquire lease para um asset. Yield view válida ou inválida."""
        self.stats.requests += 1
        view: AssetView | None = None

        with self._lock:
            if name in self._active and self._active[name].is_valid():
                # Reuse lease
                view = self._active[name]
                self.stats.hits += 1
            else:
                # Novo lease
                if path.exists():
                    size = path.stat().st_size
                    view = AssetView(name, path, size)
                    self._active[name] = view
                    self.stats.bytes_read += size
                    self.stats.resident_bytes += size
                    self.stats.hits += 1
                else:
                    self.stats.misses += 1
                    view = AssetView(name, path, 0)

        try:
            yield view
        finally:
            # Release automático (como Colibri exige)
            if view and view.is_valid():
                with self._lock:
                    self.stats.resident_bytes -= view.size
                    view.release()
                    if name in self._active and self._active[name] is view:
                        del self._active[name]


def main():
    """Demo: pega e libera 3 assets."""
    lease = AssetLease()

    # Asset que existe
    p1 = Path("/workspace/ai-3d-world-pipeline/README.md")
    # Asset que NÃO existe
    p2 = Path("/tmp/inexistente.xyz")
    # Asset real do pipeline
    p3 = Path("/workspace/bycob_terrain.glb")

    for name, p in [("readme", p1), ("ghost", p2), ("terrain", p3)]:
        with lease.lookup(name, p) as view:
            if view.is_valid():
                print(f"  ✓ {name}: leased {view.size:,} bytes")
            else:
                print(f"  ✗ {name}: miss")

    print("\nStats:")
    import json
    print(json.dumps(lease.stats.to_dict(), indent=2))


if __name__ == "__main__":
    main()
