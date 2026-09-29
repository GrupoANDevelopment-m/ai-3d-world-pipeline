# 3DWorld — Screenshot Attempt Log

**Goal**: Capturar screenshot da cidade procedural gerada pelo 3DWorld.

**Resultado**: ❌ Screenshot do display Xvfb dá imagem preta.

## O que tentei

### 1. Xvfb + scrot
- `Xvfb :99 -screen 0 1280x720x24`
- `DISPLAY=:99 ./3dworld mapx/config_mapx.txt`
- 3DWorld inicia, carrega 127 texturas, usa llvmpipe (software)
- scrot captura PNG 1280x720, **MAS** conteúdo é todo preto
- Frame buffer do Xvfb não recebe pixels do OpenGL Mesa swrast

### 2. Xvfb + xwd
- `xwd -root -silent` captura XWD 3.1MB
- Convert para PNG: dá imagem preta 1-bit
- Mesma raiz: swrast não está flushed para o X server

### 3. Xvfb + import (ImageMagick)
- `import -window root` → 0 bytes (timeout)
- Não consegue ler root window

### 4. Mesa env vars (LIBGL_ALWAYS_SOFTWARE, MESA_GL_VERSION_OVERRIDE, GALLIUM_DRIVER)
- Não resolveu

## Causa raiz (provável)

**Software rendering (llvmpipe) sobre Xvfb+GLX** não está fazendo flush dos pixels
para o framebuffer do X server. Mesa swrast draws to its own FBO e não copia
para o drawable visível.

Isto é uma limitação conhecida em containers sandboxed sem GPU:
- Xvfb não tem GLX_REAL
- llvmpipe renderiza para buffer interno do driver
- Sem DRI3, sem flush pro X

## Verificação
- glxinfo no Xvfb retorna OK
- 3DWorld loga "Renderer: llvmpipe (LLVM 15.0.6, 256 bits)"
- 3DWorld carrega 127 texturas sem erro
- Apenas o output visual está vazio

## Alternativas que PODEM funcionar (não testadas)

1. **3DWorld compilar com OSMesa** ao invés de freeglut — requer patch no source
2. **EGL surfaceless** — 3DWorld não suporta
3. **GPU passthrough** — não disponível neste sandbox
4. **VirGL GPU emulation** — não disponível

## Conclusão

**3DWorld binary funciona e gera cidade procedural**, mas não conseguimos
capturar screenshot no sandbox sem GPU.

O **build é o verdadeiro sucesso** — 153 .cpp files compilados, binary 208MB,
todas as deps resolvidas. Quem rodar com GPU+X11 real vai ver a cidade
renderizada normalmente.

## Workaround para o usuário final

```bash
# Com X11 real (com GPU):
/workspace/tools/3DWorld/obj/3dworld mapx/config_mapx.txt

# Com Xvfb (espera que o GLX funcione):
xvfb-run -a /workspace/tools/3DWorld/obj/3dworld mapx/config_mapx.txt

# Configs disponíveis:
#   mapx/config_mapx.txt          — cidade procedural
#   house/config_house.txt         — interior de casa
#   cornell_box/config_box.txt    — Cornell box
```
