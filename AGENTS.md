# AGENTS.md — คู่มือสำหรับ AI agent ที่ทำงานใน repo นี้

> อ่านก่อนแตะโค้ดทุกครั้ง · ประวัติงานล่าสุดดู `.handover/HANDOVER.md` · แผนที่ระบบทั้ง ecosystem ดู `../docs/architecture.md` (อยู่ที่โฟลเดอร์ workspace "THub Studio" เหนือ repo นี้ — ครอบคลุมทั้ง 3 repos)

## โครงสร้างสำคัญ

```
main.py                         ← THub Launcher (CustomTkinter) — อย่าสับสนกับ TStudio
tools/flagship/TStudio/         ← engine แปลหลัก (PyQt6)
  tstudio_app.py                ← หน้าต่างหลัก + ธีม (DARK_SS/LIGHT_SS) + Welcome/Dashboard
  tstudio_dashboard.py          ← WelcomeScreen + DashboardPanel
  file_converter.py             ← ประตูรับไฟล์ 4 ชั้น (built-in → plugin → cloud → AI)
  CustomParsers/                ← parser ต่อฟอร์แมต (สัญญา: convert_to_csv(filepath, parent_widget))
  locales/{th,en}.json          ← คำแปล UI
tools/flagship/Core/            ← โมดูลกลางทุกแอปใช้ร่วม (tstudio_core, tpua_engine, TLM, utmt...)
development/                    ← เครื่องมือ dev: tests/, ui-screenshots/
.handover/HANDOVER.md           ← เอกสารส่งต่องาน (ฉบับล่าสุด)
```

## กฎเหล็ก

1. **ข้อความ UI ทุกอย่างผ่าน `_(key)`** + เพิ่มคีย์ใน `locales/th.json` และ `en.json` พร้อมกัน — ห้าม hardcoded ข้อความใน widget
2. **สี UI ผ่านธีมเท่านั้น** — widget ที่ต้องการสีเป็นของตัวเอง: `setObjectName("ชื่อ")` แล้วเพิ่มกฎ
   ใน **ทั้ง** `DARK_SS` และ `LIGHT_SS` — ห้าม `setStyleSheet` inline ที่มีค่าสี (มัน override ธีม)
3. **โค้ดต้องรันได้ทั้ง macOS และ Windows** — อะไรที่เป็นของ Windows ให้ guard
   (`creationflags=... if os.name == 'nt' else 0` / try-except รอบ `ctypes.windll`) และทดสอบด้วย
   `QT_QPA_PLATFORM=offscreen`
4. **เขียนไฟล์ config/สำคัญด้วย atomic pattern** — เขียน `.tmp` แล้ว `shutil.move` ทับ (ตามที่มีอยู่ใน `tstudio_core`)
5. **ห้าม commit runtime state** — `Core/config.json`, `Core/prompts.json`, `translation*.csv`,
   โฟลเดอร์ `.venv*`/`__pycache__` คือของเครื่องผู้ใช้ (ใน repo มีแค่าตัวอย่าง `config.example.json`)
6. **ห้ามแตะไฟล์ legacy**: `tstudio_app_bak2.py`, `tstudio_app_clean.py`, `*_bak*`, `patch_*.py`
   — เป็นซากการพัฒนา ไม่ได้ถูกเรียกใช้
7. **Parser plugin contract** — ทุก parser (รวมถึงที่ AI สร้าง) ต้องมี
   `convert_to_csv(filepath, parent_widget=None)` คืน absolute path ของ CSV
   (`ID, Source, Translation, AI_Reference`, utf-8-sig) — ใช้ `ID` แบบ `namespace::key::hash` เพื่อ deploy กลับได้
8. **ทดสอบก่อนส่งมอบ** — อย่างน้อย `python development/tests/boot_test.py` ต้องผ่านทั้งหมด

## คำสั่งที่ใช้บ่อย

```bash
# เปิด TStudio (macOS)
tools/flagship/TStudio/run_tstudio_macos.sh

# ทดสอบบูตแบบไม่ต้องมีจอ (CI ใช้ได้)
python development/tests/boot_test.py

# ทดสอบธีม/สีเฉพาะจุด (จับสี pixel จาก widget.grab())
QT_QPA_PLATFORM=offscreen python -c "..."
```

## จุดที่มักพลาด (เคยเกิดแล้วจริง)

- Inline stylesheet ทำให้ธีมสว่างมี widget มืดค้าง — แก้ตามกฎข้อ 2
- `mapping.json` ของ PUA เก็บ "อักขระ PUA ตรง" ไม่ใช่ hex string — `tpua_engine._to_codepoint()`
  รองรับทั้งคอลัมน์แล้ว อย่ากลับไปใช้ `int(x, 16)` เพียงอย่างเดียว
- การ refactor ฟังก์ชันยาว (อย่าง `new_project_from_file` → `start_import`) ระวัง indentation
  ของโค้ดกลางที่ไม่ได้อ่าน — ตรวจด้วย `python -c "import ast; ast.parse(...)"`
- เปลี่ยน/ลบ signal ที่เชื่อมกับ DashboardPanel ต้องอัปเดตทั้ง `dataChanged` และ `modelReset`
