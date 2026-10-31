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
check("เริ่มที่หน้า Welcome", win.view_stack.currentIndex() == 0)
check("dashboard ซ่อนตอนเริ่ม", win.dashboard_dock.isHidden())

print("[3] โหลดไฟล์ทดสอบ")
win.csv_path = os.path.join(HERE, "tstudio_test.csv")
win._load_csv()
app.processEvents()
check("สลับไปหน้าตาราง", win.view_stack.currentIndex() == 1)
check("dashboard แสดงอัตโนมัติ", not win.dashboard_dock.isHidden())
check("โหลดได้ 5 บรรทัด", len(win.model._data) == 5)

print("[4] TPUA engine")
from tpua_engine import TPUAEngine  # noqa: E402
eng = TPUAEngine()
for sample in ("ที่นี่", "ผู้หญิงคนนี้", "ป่า น้ำ หญิง"):
    ok = eng.decode(eng.encode(sample)) == sample and eng.encode(sample) != sample
    check(f"round-trip {sample!r}", ok)

win.close()

if failures:
    print(f"\nผล: FAIL ({len(failures)} จุด) — {failures}")
    sys.exit(1)
print("\nผล: ALL OK — TStudio boot ปกติ")
