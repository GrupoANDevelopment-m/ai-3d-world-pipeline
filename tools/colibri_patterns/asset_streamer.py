"""
asset_streamer.py — Streaming para assets grandes (splats, point clouds, heightmaps).

Adaptado de JustVugg/colibri:
  - mmap() para evitar cópia (c/colibri.c usa mmap via mman.h)
  - Buffered pread (c/uring.h para async I/O)
  - Lazy load on demand
  - Pre-fetch one layer ahead (c/uring prefetch hint)

Aqui simplificamos para Python com:
  - Streaming por chunks para arquivos grandes
  - MMap quando possível
  - Cache LRU limitado
  - Pre-fetch baseado em "próximo provável"
"""
from __future__ import annotations

import hashlib
import mmap
import os
from collections import OrderedDict
from pathlib import Path
from typing import Iterator, Optional


class StreamedAsset:
    """Wrapper de leitura streaming para um asset.

    Suporta:
      - read(offset, size): lê N bytes em qualquer offset
      - chunks(chunk_size): iterator sobre chunks
      - mmap(): memory map para acesso zero-copy
    """

    def __init__(self, path: Path, prefer_mmap: bool = True):
        self.path = path
        self.size = path.stat().st_size
        self._fh = open(path, "rb")
        self._mmap: mmap.mmap | None = None
        if prefer_mmap and self.size > 0:
            try:
                self._mmap = mmap.mmap(self._fh.fileno(), 0, access=mmap.ACCESS_READ)
            except (OSError, ValueError):
                self._mmap = None  # arquivo vazio ou outro erro

    def read(self, offset: int, size: int) -> bytes:
        if self._mmap:
            return self._mmap[offset:offset + size]
        self._fh.seek(offset)
        return self._fh.read(size)

    def chunks(self, chunk_size: int = 1_048_576) -> Iterator[bytes]:
        """Itera em chunks de N bytes (default 1 MB)."""
        if self._mmap:
            pos = 0
            while pos < self.size:
                end = min(pos + chunk_size, self.size)
                yield self._mmap[pos:end]
                pos = end
        else:
            while True:
                data = self._fh.read(chunk_size)
                if not data:
                    break
                yield data

    def hash(self) -> str:
        """SHA256 do conteúdo (para cache key)."""
        h = hashlib.sha256()
        for chunk in self.chunks(64 * 1024):
            h.update(chunk)
        return h.hexdigest()

    def close(self):
        if self._mmap:
            self._mmap.close()
        self._fh.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


class AssetCache:
    """LRU cache de StreamedAssets com tamanho máximo em MB."""

    def __init__(self, max_mb: int = 512):
        self.max_bytes = max_mb * 1_048_576
        self.current_bytes = 0
        self._cache: OrderedDict[str, StreamedAsset] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, path: Path) -> StreamedAsset:
        key = str(path)
        if key in self._cache:
            self._cache.move_to_end(key)
            self.hits += 1
            return self._cache[key]
        self.misses += 1

        asset = StreamedAsset(path)
        self._cache[key] = asset
        self.current_bytes += asset.size

        # Evict LRU
        while self.current_bytes > self.max_bytes and self._cache:
            evict_key, evict_asset = self._cache.popitem(last=False)
            self.current_bytes -= evict_asset.size
            evict_asset.close()

        return asset

    def stats(self) -> dict:
        return {
            "cache_mb": round(self.current_bytes / 1_048_576, 2),
            "max_mb": round(self.max_bytes / 1_048_576, 2),
            "cached_items": len(self._cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / max(1, self.hits + self.misses), 4),
        }


def main():
    """Demo: stream o terrain.glb que geramos."""
    import json
    p = Path("/workspace/bycob_terrain.glb")
    if not p.exists():
        print("ERRO: /workspace/bycob_terrain.glb não existe")
        return

    print(f"Streaming {p} ({p.stat().st_size:,} bytes)")

    cache = AssetCache(max_mb=128)

    asset = cache.get(p)
    print(f"  Primeiros 16 bytes (header GLB): {asset.read(0, 16).hex()}")

    print(f"  Lendo em chunks de 1 MB:")
    total = 0
    n = 0
    for chunk in asset.chunks(1_048_576):
        total += len(chunk)
        n += 1
    print(f"    {n} chunks, {total:,} bytes total (esperado: {p.stat().st_size:,})")

    print(f"\nCache stats:")
    print(json.dumps(cache.stats(), indent=2))


if __name__ == "__main__":
    main()
