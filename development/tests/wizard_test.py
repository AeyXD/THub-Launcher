#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wizard + Quick wins offscreen test (spec-workflow-wizard.md ระยะ 0 + ระยะ 1)

ตรวจ:
  1. ระยะ 0-1: เมนู "📁 ไฟล์" บน menubar ครบชุด (wizard/เปิด/บันทึก/Deploy/Merge/ส่งออก/โปรไฟล์/ออก)
  2. ระยะ 0-3: Ctrl+O เจอ .srt → dialog เสนอ Game Tool Subtitles (จับ route ผ่าน fake QMessageBox)
  3. ระยะ 1: wizard dock จอดซ้าย + stepper 6 ขั้น + สถานะอัตโนมัติ + ข้าม/ย่อ + จำขั้นล่าสุด
  4. TVox สืบทอด wizard + ปุ่มอีโมจิมีข้อความกำกับ (ระยะ 0-2)

วิธีใช้: QT_QPA_PLATFORM=offscreen python development/tests/wizard_test.py
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

HERE = os.path.dirname(os.path.abspath(__file__))
TSTUDIO_DIR = os.path.abspath(os.path.join(HERE, "..", "..", "tools", "flagship", "TStudio"))
sys.path.insert(0, TSTUDIO_DIR)

import tstudio_app  # noqa: E402
from tstudio_core import TStudioCore  # noqa: E402

failures = []

def check(name, cond):
    print(f"  {'OK' if cond else 'FAIL'}  {name}")
    if not cond:
        failures.append(name)

print("[1] boot + เมนู 📁 ไฟล์ (ระยะ 0-1)")
app = tstudio_app.QApplication(sys.argv)
win = tstudio_app.TranslationStudio()
menubar = win.top_menu_bar
menus = [a.text() for a in menubar.actions() if a.menu()]
check("menubar มีเมนูไฟล์เป็นตัวแรก", menus and menus[0] == "📁 ไฟล์")
file_menu = menubar.actions()[0].menu()
file_titles = [a.text() for a in file_menu.actions() if a.text()]
check("เมนูไฟล์มี wizard (Ctrl+Shift+N)", any("🧭" in t and "เริ่มงานใหม่" in t for t in file_titles))
check("เมนูไฟล์มีเปิด/บันทึก/Deploy/Merge/ส่งออก/โปรไฟล์/ออก", all(any(k in t for t in file_titles) for k in
      ("เปิดโปรเจกต์", "บันทึก", "ติดตั้งเข้าเกม", "รวมไฟล์แปล", "ส่งออกไฟล์เฉพาะทาง", "สลับโปรไฟล์เกม", "ออกจากโปรแกรม")))
wiz_act = next(a for a in file_menu.actions() if "🧭" in a.text())
check("shortcut wizard = Ctrl+Shift+N", wiz_act.shortcut().toString().lower() == "ctrl+shift+n")
check("breadcrumb ยังอยู่ (ไม่ลบของเดิม)", hasattr(win, "btn_breadcrumb"))

print("[2] ระยะ 0-3: .srt เสนอ Game Tool ก่อน parser ทั่วไป")
class _FakeButton:
    def __init__(self, role_key):
        self.role_key = role_key

class FakeMB(tstudio_app.QMessageBox):
    """ถาม route แล้วตอบตาม class attr `answer` (gt | generic | cancel) แทนคลิกจริง
    clickedButton ต้องคืน 'วัตถุเดิม' ที่ addButton สร้าง เพราะโค้ดจริงเทียบด้วย is"""
    answer = "gt"
    called = []
    def __init__(self, *args):
        super().__init__(*args)
        self._btns = []
    def addButton(self, *args):
        label = args[0] if args else ""
        if isinstance(label, str):
            key = "gt" if "Game Tool" in label else "generic" if "parser" in label.lower() or "ทั่วไป" in label else "cancel"
            FakeMB.called.append(key)
            btn = _FakeButton(key)
        else:
            btn = _FakeButton("cancel")
        self._btns.append(btn)
        return btn
    def exec(self):
        return 0
    def clickedButton(self):
        for b in self._btns:
            if b.role_key == FakeMB.answer:
                return b
        return None

real_mb = tstudio_app.QMessageBox
tstudio_app.QMessageBox = FakeMB
route_calls = []
win.open_draft_in_table = lambda p: route_calls.append(p)
try:
    srt_path = os.path.join(HERE, "route_test.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("1\n00:00:01,000 --> 00:00:02,000\nสวัสดี\n")
    FakeMB.answer, FakeMB.called = "gt", []
    win.new_project_from_file(srt_path)
    check("ตอบ Game Tool → open_draft_in_table ถูกเรียกด้วย path srt", route_calls == [srt_path])
    check("dialog เสนอครบ 3 ทาง (Game Tool/parser/ยกเลิก)", FakeMB.called.count("gt") == 1 and FakeMB.called.count("generic") == 1)
    FakeMB.answer, FakeMB.called = "cancel", []
    before_csv = win.csv_path
    win.new_project_from_file(srt_path)
    check("ตอบยกเลิก → ไม่เข้า parser ใด (csv_path เดิม)", win.csv_path == before_csv and len(route_calls) == 1)
finally:
    tstudio_app.QMessageBox = real_mb
    try:
        os.remove(srt_path)
    except OSError:
        pass

print("[3] wizard dock + stepper (ระยะ 1)")
check("wizard_dock สร้างตอน boot + ซ่อน default", hasattr(win, "wizard_dock") and win.wizard_dock.isHidden())
win.show()
app.processEvents()
win.open_workflow_wizard()
app.processEvents()
check("open_workflow_wizard → แสดง + จอดซ้าย", not win.wizard_dock.isHidden()
      and win.dockWidgetArea(win.wizard_dock) == tstudio_app.Qt.DockWidgetArea.LeftDockWidgetArea)
wz = win.wizard_dock
check("stepper 6 ขั้น", wz.pages.count() == 6 and wz.step == 1)
check("ขั้น ① glyph ปัจจุบัน ●", wz.step_rows[0].text().startswith("●"))

wz._set_mode("video")
app.processEvents()
check("เลือกวิดีโอ → ขั้น ② mode=video ①=✓", wz.step == 2 and wz.mode == "video" and 1 in wz.done)
check("TStudio ไม่มี STT → ปุ่มถอดเสียง disabled + มีโน้ตชี้ TVox",
      not wz.btn_s2_stt.isEnabled() and not wz.lbl_s2_stt_note.isHidden() and not wz.frm_s2_video.isHidden())
check("game frame ซ่อน", wz.frm_s2_game.isHidden())

print("[4] สถานะอัตโนมัติ: นำเข้า CSV → ② ✓ ไป ③")
win.csv_path = os.path.join(HERE, "tstudio_test.csv")
win._load_csv()
app.processEvents()
wz._tick()
app.processEvents()
check("นำเข้าแล้ว → ขั้น ② ✓ + ไปขั้น ③ อัตโนมัติ", 2 in wz.done and wz.step == 3)
check("ขั้น ③ สรุปจำนวนแถว (5)", "5" in wz.lbl_s3_summary.text())
wz._confirm_draft()
check("ยืนยันร่าง → ขั้น ④ ③ ✓", wz.step == 4 and 3 in wz.done)
check("โชว์โมเดลปัจจุบันจาก config", wz.lbl_s4_model.text().startswith("โมเดลปัจจุบัน:"))

print("[5] แปลครบ → ③④ ✓ ไป ⑤ (จุดแก้ 'ต้องรู้เองว่าถึงไหน')")
for item in win.model._data:
    item["trans"] = "แปลแล้ว"
wz._tick()
app.processEvents()
check("แปลครบ → ขั้น ④ ✓ ไป ⑤ อัตโนมัติ", 4 in wz.done and wz.step == 5)
check("progress n/N = 5/5", "5/5" in wz.lbl_s4_progress.text())

print("[6] ข้ามขั้น + ย่อ wizard + เส้นทาง video ขั้น ⑥")
wz.skip_current()
check("ข้าม ⑤ → ⑥ (สถานะ ↷)", wz.step == 6 and 5 in wz.skipped and wz.step_rows[4].text().startswith("↷"))
check("โหมดวิดีโอ: ปุ่มส่งออกซับ + พากย์ แพ็กเกมซ่อน",
      not wz.btn_s6_srt.isHidden() and wz.btn_s6_pack.isHidden())
wz.toggle_collapse()
check("ย่อ wizard ได้ (เนื้อหาซ่อน)", wz.pages.isHidden())
wz.toggle_collapse()
check("ขยายกลับได้", not wz.pages.isHidden())

print("[7] จำขั้นล่าสุด (runtime config — ห้าม commit)")
state = TStudioCore.load_config().get("wizard_state", {})
check("wizard_state บันทึก step/mode/csv", state.get("step") == 6 and state.get("mode") == "video"
      and state.get("csv") == win.csv_path)
wz.reset()
check("เริ่มงานใหม่ → ขั้น ① ล้าง done/skipped/mode (ลืมงานเดิม)",
      wz.step == 1 and not wz.done and not wz.skipped and wz.mode is None)

print("[7b] regression: งานเก่าไม่แอบอ้างขั้นหลัง 'เริ่มงานใหม่' (บั๊กที่เจ้าของเจอจริง)")
wz._set_mode("video")
wz._tick()
app.processEvents()
check("ตารางยังเปิดไฟล์เก่า แต่ wizard รอนำเข้าใหม่ที่ ② (ไม่กระโดดไป ③)",
      wz.step == 2 and 2 not in wz.done and "ยังไม่มีไฟล์" in wz.lbl_s2_status.text())
wz._stale_csv = ""  # จำลองผู้ใช้กดปุ่มนำเข้าไฟล์ใหม่ของขั้น ② (ปุ่มเคลียร์ stale เสมอ)
wz._tick()
app.processEvents()
check("นำเข้าใหม่แล้ว → ② ✓ ไป ③ ตามปกติ", 2 in wz.done and wz.step == 3)
wz.step_rows[0].click()
check("คลิกแถวขั้นใน stepper กระโดดขั้นได้ (กลับ ①)", wz.step == 1)

print("[8] TVox สืบทอด wizard + ปุ่มมีข้อความ (ระยะ 0-2)")
TVOX_DIR = os.path.abspath(os.path.join(TSTUDIO_DIR, "..", "TVox"))
sys.path.insert(0, TVOX_DIR)
import tvox_app as tvox_mod  # noqa: E402
vapp = tvox_mod.QApplication.instance() or app
vwin = tvox_mod.TVoxApp()
app.processEvents()
check("TVox มี wizard dock อัตโนมัติ", hasattr(vwin, "wizard_dock"))
check("open_draft_in_table สืบทอดจาก TranslationStudio (ไม่ override ใน TVox)",
      "open_draft_in_table" not in vars(type(vwin)))
check("ปุ่มเปิดวิดีโอมีข้อความ", vwin.btn_open_video.text().strip() == "📂 เปิดวิดีโอ")
check("ปุ่มถอดเสียงมีข้อความ", vwin.btn_stt.text().strip() == "🧬 ถอดเสียง")
check("ปุ่มพากย์ AI มีข้อความ", vwin.btn_tts.text().strip() == "🎙️ พากย์ AI")
check("wizard TVox: STT ใช้ได้ (มี open_stt_dialog)", vwin.wizard_dock.btn_s2_stt.isEnabled())
vwin.close()

win.close()
# เคลียร์ wizard_state ทิ้ง — อย่าฝืนเครื่องผู้ทดสอบ
try:
    cfg = TStudioCore.load_config()
    cfg.pop("wizard_state", None)
    TStudioCore.save_config(cfg)
except Exception:
    pass

if failures:
    print(f"\nผล: FAIL ({len(failures)} จุด) — {failures}")
    sys.exit(1)
print("\nผล: ALL OK — wizard + ระยะ 0 ผ่านทุกจุด")
