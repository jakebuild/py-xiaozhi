#!/bin/bash
echo "=========================================="
echo " Starting Xiaozhi with Custom Tkinter UI"
echo "=========================================="
cd "$(dirname "$0")"

echo "[1/3] Cleaning up old processes..."
pkill -f "main.py --mode cli" 2>/dev/null
pkill -f "xiaozhi_face_ui.py" 2>/dev/null
sleep 1

export DISPLAY=:0
export XDG_RUNTIME_DIR=/run/user/1000

echo "[2/3] Starting Core Engine (CLI Mode)..."
~/miniconda3/envs/py-xiaozhi/bin/python main.py --mode cli </dev/null &
CORE_PID=$!

sleep 3

echo "[3/3] Starting Face UI..."
~/miniconda3/envs/py-xiaozhi/bin/python xiaozhi_face_ui.py

echo "UI closed. Shutting down core engine..."
kill $CORE_PID 2>/dev/null
echo "Done."
