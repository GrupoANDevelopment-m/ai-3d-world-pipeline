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

    # Se não tiver output, gera um temp
    if not output_obj:
        output_obj = f"/tmp/libigl_out_{int(__import__('time').time())}.obj"

    Path(output_obj).parent.mkdir(parents=True, exist_ok=True)
    cmd = [LIBIGL_BIN, str(inp), str(output_obj)]

    print(f"[libigl] cmd: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return result.returncode
    return 0


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Analyze mesh with libigl")
    p.add_argument("input_pos", nargs="?", help="Input OBJ (positional)")
    p.add_argument("--input", dest="input", help="Input OBJ (flag)")
    p.add_argument("--output", help="Output OBJ (optional)")
    args = p.parse_args()

    inp = args.input or args.input_pos
    if not inp:
        print(__doc__)
        sys.exit(1)
    sys.exit(analyze(inp, args.output))
