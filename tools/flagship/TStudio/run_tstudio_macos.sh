#!/bin/bash
# run_tstudio_macos.sh — เปิด TStudio บน macOS
# ครั้งแรกจะสร้าง virtual environment (.venv) และติดตั้ง deps ให้อัตโนมัติ
#
# เลือก Python 3.12 ก่อน (ตามการตัดสินใจย้ายเวอร์ชันของเจ้าของ 1/11 — 3.9 EOL แล้ว):
#   หาจากตำแหน่งพบบ่อย (/opt/homebrew/bin, /usr/local/bin) แล้วจาก PATH
#   ไม่เจอค่อยใช้ python3 เดิมของเครื่อง
# venv เก่าที่สร้างจาก Python คนละรุ่นกับตัวที่เลือกได้ → สร้างใหม่อัตโนมัติครั้งเดียว
# เครื่องใหม่ที่ยังไม่มี 3.12:  brew install python@3.12
#
# ใช้ Python ของเครื่องอื่นได้ผ่าน:  TSTUDIO_PYTHON=/path/to/python ./run_tstudio_macos.sh
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$DIR/.venv"
PY="${TSTUDIO_PYTHON:-}"

resolve_python() {
  for cand in /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12; do
    [ -x "$cand" ] && { echo "$cand"; return 0; }
  done
  local p
  p="$(command -v python3.12 2>/dev/null || true)"
  if [ -n "$p" ]; then echo "$p"; return 0; fi
  echo python3
}

if [ -z "$PY" ]; then
  BASE="$(resolve_python)"
  BASE_VER="$("$BASE" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

  if [ -x "$VENV/bin/python" ]; then
    VENV_VER="$("$VENV/bin/python" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    if [ "$VENV_VER" != "$BASE_VER" ]; then
      echo "♻️  venv เดิมเป็น Python $VENV_VER → สร้างใหม่เป็น $BASE_VER อัตโนมัติ (ครั้งเดียว ~1 นาที)..."
      rm -rf "$VENV"
    fi
  fi

  if [ ! -x "$VENV/bin/python" ]; then
    echo "📦 สร้าง virtual environment ด้วย $BASE (Python $BASE_VER)..."
    "$BASE" -m venv "$VENV"
    "$VENV/bin/pip" install --quiet --upgrade pip
    # numpy ใช้โดย waveform ของ TVox (เปิดจาก TStudio ได้) — ใส่ไว้ให้เครื่องใหม่ใช้ได้ครบ
    "$VENV/bin/pip" install --quiet PyQt6 requests numpy
  fi
  PY="$VENV/bin/python"
fi

cd "$DIR"
exec "$PY" tstudio_app.py "$@"
