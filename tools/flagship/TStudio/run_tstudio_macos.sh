#!/bin/bash
# run_tstudio_macos.sh — เปิด TStudio บน macOS
# ครั้งแรกจะสร้าง virtual environment (.venv) และติดตั้ง PyQt6 + requests ให้อัตโนมัติ
# ใช้ Python ของเครื่องอื่นได้ผ่าน:  TSTUDIO_PYTHON=/path/to/python ./run_tstudio_macos.sh
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$DIR/.venv"
PY="${TSTUDIO_PYTHON:-}"

if [ -z "$PY" ]; then
  if [ ! -x "$VENV/bin/python" ]; then
    echo "📦 สร้าง virtual environment ครั้งแรก (ติดตั้ง ~1 นาที)..."
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install --quiet --upgrade pip
    "$VENV/bin/pip" install --quiet PyQt6 requests
  fi
  PY="$VENV/bin/python"
fi

cd "$DIR"
exec "$PY" tstudio_app.py "$@"
