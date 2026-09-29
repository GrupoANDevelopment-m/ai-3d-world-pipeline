#!/bin/bash
# run_3dworld_screenshot.sh
set -e
OUT_DIR="${1:-/workspace/3dworld_screenshots}"
mkdir -p "$OUT_DIR"

LOG="$OUT_DIR/3dworld_run.log"
SS_BASE="3dworld_$(date +%s)"

# Kill any stale Xvfb / 3dworld
pkill -9 Xvfb 2>/dev/null || true
pkill -9 -f "/workspace/tools/3DWorld/obj/3dworld" 2>/dev/null || true
rm -f /tmp/.X*-lock 2>/dev/null || true
sleep 1

# Start Xvfb manually
Xvfb :88 -screen 0 1280x720x24 -ac +extension GLX >"$OUT_DIR/xvfb.log" 2>&1 &
XVFB_PID=$!
echo "[run] Xvfb started PID=$XVFB_PID"
sleep 4

export DISPLAY=:88

# Verify
if ! xdpyinfo -display $DISPLAY >/dev/null 2>&1; then
    echo "[ERR] xdpyinfo failed. xvfb.log:"
    cat "$OUT_DIR/xvfb.log"
    kill -9 $XVFB_PID 2>/dev/null
    exit 1
fi
echo "[run] X server ok: $(xdpyinfo -display $DISPLAY 2>/dev/null | grep 'dimensions' | head -1)"

# Launch 3DWorld
cd /workspace/tools/3DWorld
echo "[run] launching 3dworld..."
./obj/3dworld mapx/config_mapx.txt >"$LOG" 2>&1 &
XW_PID=$!
echo "[run] 3dworld PID=$XW_PID"

# Wait for render
sleep 12
DISPLAY=$DISPLAY scrot "$OUT_DIR/${SS_BASE}_a.png" 2>&1 || echo "scrot a failed"
sleep 4
DISPLAY=$DISPLAY scrot "$OUT_DIR/${SS_BASE}_b.png" 2>&1 || echo "scrot b failed"
sleep 4
DISPLAY=$DISPLAY scrot "$OUT_DIR/${SS_BASE}_c.png" 2>&1 || echo "scrot c failed"

# Cleanup
kill $XW_PID 2>/dev/null || true
sleep 1
pkill -9 -f "/workspace/tools/3DWorld/obj/3dworld" 2>/dev/null || true
kill -9 $XVFB_PID 2>/dev/null || true
sleep 1

echo ""
echo "[run] screenshots:"
ls -la "$OUT_DIR"/*.png 2>&1 | head -10
echo ""
echo "[run] 3dworld log tail:"
tail -25 "$LOG"
