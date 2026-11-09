#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wizard + Quick wins offscreen test (spec-workflow-wizard.md ระยะ 0 + ระยะ 1)

ตรวจ:
  1. ระยะ 0-1: เมนู "📁 ไฟล์" บน menubar ครบชุด (wizard/เปิด/บันทึก/Deploy/Merge/ส่งออก/โปรไฟล์/ออก)
  2. ระยะ 0-3: Ctrl+O เจอ .srt → dialog เสนอ Game Tool Subtitles (จับ route ผ่าน fake QMessageBox)
  3. ระยะ 1: wizard dock จอดซ้าย + stepper 6 ขั้น + สถานะอัตโนมัติ + ข้าม/ย่อ + จำขั้นล่าสุด
  4. TVox สืบทอด wizard + ปุ่มอีโมจิมีข้อความกำกับ (ระยะ 0-2)
  5. ระยะ 2-1: การ์ด ▶️ ทำงานต่อ หน้า Welcome (คลิกเดียว: โหลด CSV + กลับขั้นค้าง)
  6. ระยะ 2-2: tvox_video_export — regex เดียวกับ srt_packer + readiness + ทำวิดีโอจริงผ่าน ffmpeg
     (dub พร้อมซับ mov_text language=tha · mix ducking · -c:v copy · ชื่อ _TH_dub/_TH_mix)
  7. ระยะ 2-3: strip สรุปหน้างานบนหัว wizard + จำนวนจุด QA รอบล่าสุด

วิธีใช้: QT_QPA_PLATFORM=offscreen python development/tests/wizard_test.py (ต้องมี ffmpeg ใน PATH)
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

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
# เคลียร์ wizard_state จากรอบก่อนหน้า — boot ของเทสนี้ต้องเริ่มที่ขั้น ① เสมอ (deterministic)
try:
    _cfg = TStudioCore.load_config()
    _cfg.pop("wizard_state", None)
    TStudioCore.save_config(_cfg)
except Exception:
    pass
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
check("TVox มีปุ่ม 🎬 ทำวิดีโอพากย์ (ระยะ 2-2)", hasattr(vwin, "open_video_export_dialog"))
check("TVox readiness: ยังไม่มีวิดีโอ → เหตุผล vexp_need_video",
      vwin.can_make_dub_video() == (False, "vexp_need_video"))
vwin.close()

print("[9] ระยะ 2-1: การ์ด ▶️ ทำงานต่อ หน้า Welcome")
wz._set_mode("video")
wz.goto(4)  # ทิ้งงานค้างไว้ขั้น ④
win.show_welcome()
app.processEvents()
card = win.welcome_screen.btn_resume
check("การ์ดทำงานต่อแสดงเมื่อมีงานค้าง", not card.isHidden() and "ทำงานต่อ" in card.text())
check("การ์ดบอกชื่อไฟล์ + ขั้นที่ค้าง (4)", "tstudio_test.csv" in card.text() and "4" in card.text())
card.click()
app.processEvents()
check("คลิกการ์ด → โหลด CSV + กลับขั้น ④ ในคลิกเดียว", wz.step == 4 and not wz.isHidden())
check("state มี current_step ตามสเปก", TStudioCore.load_config().get("wizard_state", {}).get("current_step") == 4)
# resume โหลด CSV ใหม่จากดิสก์ (คำแปลใน memory ถูกแทน) — ใส่คำแปลกลับเพื่อทดสอบ strip สรุป
for item in win.model._data:
    item["trans"] = "แปลแล้ว"

print("[10] ระยะ 2-3: strip สรุปหน้างานบนหัว wizard")
wz._refresh()
sumtxt = wz.lbl_summary.text()
check("สรุปครบ: แถว/แปล/QA/โหมด", "5 แถว" in sumtxt and "แปลแล้ว 5" in sumtxt
      and "QA" in sumtxt and "วิดีโอ" in sumtxt)
real_qa = win.run_qa_check
win.run_qa_check = lambda *a, **k: None  # offscreen: ไม่เปิด dialog จริง
qa_file = os.path.join(os.path.dirname(win.csv_path), "qa_audit.csv")
with open(qa_file, "w", encoding="utf-8") as f:
    f.write("Severity,Row,Message\nerror,1,ก\nwarn,2,ข\nerror,3,ค\n")
try:
    wz._run_qa()
finally:
    win.run_qa_check = real_qa
    os.remove(qa_file)
check("QA นับจุดรอบล่าสุดจาก qa_audit.csv = 3", wz._qa_issues == 3 and "QA 3 จุด" in wz.lbl_summary.text())
check("state บันทึก qa_issues + current_step ไปขั้น ⑥",
      TStudioCore.load_config().get("wizard_state", {}).get("qa_issues") == 3
      and TStudioCore.load_config().get("wizard_state", {}).get("current_step") == 6)

print("[11] ระยะ 2-2: ทำวิดีโอพากย์ — module จริงผ่าน ffmpeg")
import tvox_video_export as ve
check("regex เวลาเดียวกับ srt_packer", ve.SRT_ID_RE.pattern == r'^srt::(\d+)::(\d+)::(\d+)$')
_packersrc = os.path.join(TSTUDIO_DIR, "CustomParsers", "GameTools", "Subtitles", "srt_packer.py")
if os.path.isfile(_packersrc):
    _m = re.search(r"_ID_RE = re\.compile\(r'([^']+)'\)", open(_packersrc, encoding="utf-8").read())
    check("pattern ตรงกับ srt_packer ที่ติดตั้งจริง", bool(_m) and _m.group(1) == ve.SRT_ID_RE.pattern)
_fs = type("S", (), {"player": None, "model": None, "csv_path": ""})()
check("readiness: ไม่มี player → vexp_need_video", ve.video_export_readiness(_fs) == (False, "vexp_need_video"))
_fs2 = type("S", (), {
    "player": type("P", (), {"path": "/tmp/x.mp4"})(),
    "csv_path": "/tmp/x.csv",
    "model": type("M", (), {"_data": [{"id": "srt::1::0::900"}, {"id": "row_9"}]})()})()
check("readiness: วิดีโอ+ซับครบ → พร้อม", ve.video_export_readiness(_fs2) == (True, ""))
_fs2.model._data = [{"id": "row_9"}]
check("readiness: CSV ไม่ใช่ซับ → vexp_need_srt_csv", ve.video_export_readiness(_fs2) == (False, "vexp_need_srt_csv"))

_tmp = tempfile.mkdtemp(prefix="wz_vexp_")
try:
    _vid = os.path.join(_tmp, "test.mp4")
    _r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                         "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=10",
                         "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", _vid],
                        capture_output=True)
    assert os.path.isfile(_vid), _r.stderr.decode()[:300]
    _w1 = os.path.join(_tmp, "srt_1_0_1000.wav")
    _w2 = os.path.join(_tmp, "srt_2_1500_2200.wav")
    for _w, _f in ((_w1, 600), (_w2, 900)):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                        "-i", f"sine=frequency={_f}:duration=0.8", "-c:a", "pcm_s16le", _w],
                       capture_output=True, check=True)
    _srt = os.path.join(_tmp, "test_TH.srt")
    with open(_srt, "w", encoding="utf-8") as f:
        f.write("1\n00:00:00,000 --> 00:00:01,000\nสวัสดี\n\n2\n00:00:01,500 --> 00:00:02,200\nครับ\n\n")
    _items = [(0, _w1), (1500, _w2)]
    check("build_items ได้เวลาจาก ID + WAV ที่มีจริง",
          ve.build_items([{"id": "srt::2::1500::2200"}, {"id": "srt::1::0::1000"}, {"id": "srt::3::9::9"}],
                         _tmp) == _items)
    _ok, _out = ve.export_dubbed_video(_vid, _items, "", "dub", "ffmpeg", parent=None, srt_path=_srt)
    check("dub: สำเร็จ + ชื่อ _TH_dub.mp4 ข้างวิดีโอ", _ok and _out == os.path.join(_tmp, "test_TH_dub.mp4"))
    _probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                             "stream=codec_type,codec_name", "-of", "csv=p=0", _out],
                            capture_output=True, text=True)
    _streams = [l.strip() for l in _probe.stdout.splitlines() if l.strip()]
    check("dub: มี 3 แทร็ก (วิดีโอ copy + เสียง aac + ซับ mov_text)",
          any("video" in s for s in _streams) and any("audio" in s for s in _streams)
          and any(("mov_text" in s and "subtitle" in s) for s in _streams))
    _lang = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "s",
                            "-show_entries", "stream_tags=language", "-of", "csv=p=0", _out],
                           capture_output=True, text=True).stdout.strip()
    check("dub: แทร็กซับ language=tha", _lang == "tha")
    _dur = ve.probe_duration_sec("ffmpeg", _out)
    check("dub: ความยาวตามวิดีโอต้นทาง (~2s)", _dur is not None and 1.5 <= _dur <= 2.6)
    _ok2, _out2 = ve.export_dubbed_video(_vid, _items, "", "mix", "ffmpeg", parent=None)
    check("mix: สำเร็จ + ชื่อ _TH_mix.mp4", _ok2 and _out2 == os.path.join(_tmp, "test_TH_mix.mp4"))
    _probe2 = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                              "stream=codec_type", "-of", "csv=p=0", _out2],
                             capture_output=True, text=True).stdout.split()
    check("mix: วิดีโอ + เสียง (ไม่มีซับ)", "video" in _probe2 and "audio" in _probe2 and len(_probe2) == 2)
finally:
    shutil.rmtree(_tmp, ignore_errors=True)

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
