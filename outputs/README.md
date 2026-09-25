# outputs/

Esta pasta é **gitignored**. Ela recebe todos os artefatos gerados pelas execuções do pipeline:

```
outputs/
├── logs/                        ← logs por estágio (run logs)
├── reports/                     ← relatórios JSON de cada execução
└── <pipeline_name>/             ← artefatos de uma execução
    ├── splat/                   ← Gaussian Splats (Caminho A)
    ├── mesh/                    ← meshes processadas
    ├── terrain/                 ← heightmaps + meshes de terreno (Caminho B)
    ├── scene.godot/             ← projeto Godot final
    └── report.json              ← relatório consolidado
```

**Tamanho típico de uma execução completa**:
- Drone → Splat: 200 MB – 2 GB
- Text → World: 50 MB – 500 MB
- Digital Twin híbrido: 500 MB – 3 GB

Limpe regularmente com:

```bash
rm -rf outputs/*/  # mantém a pasta, remove conteúdo
```
