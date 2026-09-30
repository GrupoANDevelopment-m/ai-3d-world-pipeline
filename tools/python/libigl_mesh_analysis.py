"""
libigl_mesh_analysis.py
Wrapper Python sobre test_libigl.cpp para análise de mesh.
Lê OBJ, mostra stats, escreve OBJ processado.

Uso:
    python3 libigl_mesh_analysis.py input.obj [output.obj]
"""
import subprocess
import sys
from pathlib import Path

LIBIGL_BIN = "/workspace/tools/libigl/test_libigl"


def analyze(input_obj: str, output_obj: str = None) -> int:
    inp = Path(input_obj)
    if not inp.exists():
        print(f"ERRO: {inp} não existe")
        return 1

    cmd = [LIBIGL_BIN, str(inp)]
    if output_obj:
        Path(output_obj).parent.mkdir(parents=True, exist_ok=True)
        cmd.append(output_obj)

    print(f"[libigl] cmd: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    inp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    sys.exit(analyze(inp, out))
