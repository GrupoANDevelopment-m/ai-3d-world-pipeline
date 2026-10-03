"""
WorldGen-Lite: CPU-compatible 3D scene generation.

Adapta https://github.com/ZiYang-xie/WorldGen (ZiYang-xie) para hardware
limitado. Skipa partes GPU-only (FLUX, Nunchaku, ml-sharp, DA-2) mas
mantém a estrutura geral: text → panorama → depth → mesh.
"""
__version__ = "0.1.0"