#!/bin/bash
# run_tpua_macos.sh — เปิด TPUA บน macOS
# ใช้ venv ของ TStudio (PyQt6 + numpy + requests แชร์กัน — ไม่สร้าง venv แยก)
#
# เลือก Python 3.12 ก่อน (fallback python3) — venv ของ TStudio จัดการสร้าง/เลือกรุ่นเอง
# ถ้า TStudio venv ยังไม่มี ให้รัน run_tstudio_macos.sh ก่อน หรือรันตัวนี้แล้วสร้างให้อัตโนมัติ
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
TSTUDIO_DIR="$(cd "$DIR/../TStudio" && pwd)"
VENV="$TSTUDIO_DIR/.venv"
APP_SCRIPT="$DIR/tpua_app.py"

# สร้าง venv ของ TStudio ถ้ายังไม่มี (เลือก Python 3.12 ก่อน)
if [ ! -x "$VENV/bin/python" ]; then
    echo "📦 ยังไม่มี venv ของ TStudio — สร้างให้อัตโนมัติ (~1 นาที)..."
    for cand in /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12; do
        [ -x "$cand" ] && { PY="$cand"; break; }
    done
    PY="${PY:-$(command -v python3.12 2>/dev/null || echo python3)}"
    "$PY" -m venv "$VENV"
    "$VENV/bin/pip" install --quiet --upgrade pip
    "$VENV/bin/pip" install --quiet PyQt6 requests numpy
fi

cd "$DIR"
exec "$VENV/bin/python" "$APP_SCRIPT" "$@"
