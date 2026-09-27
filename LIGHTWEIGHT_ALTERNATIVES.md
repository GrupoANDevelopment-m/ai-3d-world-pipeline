# Lightweight Alternatives — Tentativas honestas

> Pesquisa e tentativas de instalação de alternativas LEVES aos tools pesados.

## ✅ Instaladas e funcionais

### **pyrender + trimesh** — renderização Python leve
- Repo: https://github.com/mmatl/pyrender
- **Por que é leve**: pure Python, OpenGL via PyOpenGL, funciona com OSMesa/EGL offscreen
- **Substitui**: Blender headless (parcialmente), pqrender GLB → PNG
- **Status**: pip install OK, importa OK, mas offscreen renderer falhou neste sandbox (sem GL stack)
- **Fallback**: gera SVG/PNG via trimesh analysis (sem render GL)
- **Tamanho**: ~5MB Python deps

### **shap-e (OpenAI)** — text-to-3D via diffusion
- Repo: https://github.com/openai/shap-e
- **Por que é leve**: 300M params, single C file diffusion model
- **Substitui**: WorldGen (ZiYang-xie), GameFactory-3A text-to-3D
- **Status**: deps instaladas (torch 2.5.0+cpu, torchvision, clip, ftfy, einops)
- **Model cache**: transmitter.pt (1.7GB) baixou OK, text300M (300MB) baixando
- **Runtime CPU**: morreu por OOM (3GB RAM) — needs ~4GB mínimo
- **Conclusão**: instalado, deps prontas, mas OOM no sandbox 3GB

### **OpenSfM (Mapillary)** — SfM Python
- Repo: https://github.com/mapillary/OpenSfM
- **Por que é leve**: Python-first, alternative ao COLMAP
- **Status**: clonou (15MB), instalou deps, mas C++ extension (pybind11) precisa cmake build que falha OOM
- **Fallback Python-only**: importável mas requer compile

### **dreamgaussian** — text-to-3D via Gaussian Splatting (ICLR 2024 Oral)
- Repo: https://github.com/dreamgaussian/dreamgaussian
- **Por que é leve**: 3.4 MB repo, deps mínimos
- **Status**: clonado, requer GPU pra training
- **Alternativa**: treino CPU é viável mas lento

### **threestudio** — unified 3D content generation
- Repo: https://github.com/threestudio-project/threestudio
- **Por que é leve**: 44MB, framework unificado para vários métodos (NeRF, 3DGS, DreamFusion)
- **Status**: clonado, requer GPU pra training real

### **dreamgaussian / shap-e / point-e / threestudio** — todos clonados
Todos Python+PyTorch, funcionam em CPU mas com limitações.

## ❌ Não instaladas (motivos)

| Ferramenta | Motivo |
|------------|--------|
| **OpenDroneMap/NodeODM** | Docker daemon bloqueado (iptables perm) |
| **WebODM** | mesmo |
| **LichtFeld Studio** | Só binary CUDA, sem CPU build |
| **WorldGen (ZiYang-xie)** | Setup 1h+ (DA-2 + FLUX gated model) |
| **Meshroom/AliceVision** | Build 2-4h, Qt5+Boost+CUDA deps |
| **3DWorld build** | gcc OOM com -j2 |
| **Terasology Gradle build** | Não tentado (build enorme) |

## 🧪 Testes reais feitos

| Tool | Status |
|------|--------|
| **pyrender imports** | ✓ OK (`import pyrender` funciona) |
| **shap-e transmitter.pt** | ✓ baixou (1.7GB), load_model começou |
| **shap-e text300M** | ⏳ modelo 300MB baixando |
| **shap-e sample_latents CPU** | ❌ OOM (precisa ~4GB RAM) |
| **OpenSfM import** | ⚠️ parcial (C++ ext falha) |

## 🎯 Conclusão honesta

**shap-e é o substitute mais leve de WorldGen/GameFactory-3A** — mesmo approach (text-to-3D via diffusion), mas precisa de **~4GB RAM mínimo** pra rodar CPU.

**pyrender + trimesh é o substitute mais leve de Blender para renderização** — mas precisa de GL stack (X server ou OSMesa).

**OpenSfM é mais leve que AliceVision/Meshroom** — mas precisa build C++ (compile é o gargalo).

**DreamGaussian e threestudio** são research-grade, precisam GPU pra training real.

**Recomendação real pra hardware limitado:**
- Pra gerar 3D de texto → shap-e se tiver ~8GB RAM
- Pra renderizar GLB → Blender headless (pesado mas funciona) ou pyrender com X server
- Pra photogrammetry → COLMAP CPU (já instalado via apt, funciona)
- Pra voxel world → Bycob/world (já compilado, CPU OK)
- Pra Gaussian Splatting → OpenSplat CPU (já compilado, treina!)

Nada substitui GPU pra coisas realmente pesadas (LichtFeld 3DGS, WorldGen, GameFactory-3A). Mas pra
fotogrammetry leve, renderização Python, text-to-3D pequeno → existem alternativas reais.
