#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TStudio offscreen boot test — ทดสอบบูตแบบไม่ต้องมีจอ (macOS / Linux / Windows)

วิธีใช้ (ต้องมี PyQt6 + requests ใน environment):
    python development/tests/boot_test.py

สิ่งที่ตรวจ:
  1. import + สร้าง QApplication + สร้างหน้าต่าง TranslationStudio
  2. เริ่มต้นอยู่หน้า Welcome + dashboard ซ่อน
  3. โหลด tstudio_test.csv → สลับไปหน้าตาราง + dashboard แสดง
  4. TPUAEngine encode/decode กลับได้ตรงตัว
  5. ระบบธีม: สลับ light/dark ได้ + remap inline + บันทึก ui_theme + คืนค่าเดิม
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

HERE = os.path.dirname(os.path.abspath(__file__))
TSTUDIO_DIR = os.path.abspath(os.path.join(HERE, "..", "..", "tools", "flagship", "TStudio"))
sys.path.insert(0, TSTUDIO_DIR)

import tstudio_app  # noqa: E402

failures = []

def check(name, cond):
    print(f"  {'OK' if cond else 'FAIL'}  {name}")
    if not cond:
        failures.append(name)

print("[1] boot หน้าต่าง")
app = tstudio_app.QApplication(sys.argv)
win = tstudio_app.TranslationStudio()

print("[2] สถานะเริ่มต้น")
check("เริ่มที่หน้า Welcome (workspace_stack index 0)", win.workspace_stack.currentIndex() == 0)
check("dashboard ซ่อนตอนเริ่ม", win.dashboard_dock.isHidden())

print("[3] โหลดไฟล์ทดสอบ")
win.csv_path = os.path.join(HERE, "tstudio_test.csv")
win._load_csv()
app.processEvents()
check("สลับไปหน้า CAT Studio (index 1)", win.workspace_stack.currentIndex() == 1)
check("dashboard แสดงอัตโนมัติ", not win.dashboard_dock.isHidden())
check("โหลดได้ 5 บรรทัด", len(win.model._data) == 5)

print("[4] TPUA engine")
from tpua_engine import TPUAEngine  # noqa: E402
eng = TPUAEngine()
for sample in ("ที่นี่", "ผู้หญิงคนนี้", "ป่า น้ำ หญิง"):
    ok = eng.decode(eng.encode(sample)) == sample and eng.encode(sample) != sample
    check(f"round-trip {sample!r}", ok)

print("[5] Theme system (system/dark/light)")
_saved_theme = None
try:
    _saved_theme = tstudio_app.TStudioCore.load_config().get("ui_theme")
except Exception:
    pass
win.set_ui_theme("light")
_light_ss = app.styleSheet()
check("โหมดสว่าง: stylesheet เปลี่ยนเป็น Latte", "#eff1f5" in _light_ss and "#4c4f69" in _light_ss)
check("โหมดสว่าง: ไม่เหลือสีหลัก Mocha", "#1e1e2e" not in _light_ss and "#11111b" not in _light_ss)
check("โหมดสว่าง: remap สี inline ของ widget (statusBar)", "#dce0e8" in win.statusBar().styleSheet())
win.set_ui_theme("dark")
check("โหมดมืด: กลับเป็น Mocha", "#1e1e2e" in app.styleSheet() and "#11111b" in app.styleSheet())
check("โหมดมืด: คืนสี inline เดิม", "#11111b" in win.statusBar().styleSheet())
check("config บันทึก ui_theme=dark", tstudio_app.TStudioCore.load_config().get("ui_theme") == "dark")
# คืนค่า preference เดิมของเครื่องผู้ใช้
if _saved_theme is not None:
    win.set_ui_theme(_saved_theme)
    check("คืน ui_theme เดิมให้ผู้ใช้", tstudio_app.TStudioCore.load_config().get("ui_theme") == _saved_theme)

win.close()

if failures:
    print(f"\nผล: FAIL ({len(failures)} จุด) — {failures}")
    sys.exit(1)
print("\nผล: ALL OK — TStudio boot ปกติ")
