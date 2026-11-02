# AGENTS.md — คู่มือสำหรับ AI agent ที่ทำงานใน repo นี้

> อ่านก่อนแตะโค้ดทุกครั้ง · สถานะงานล่าสุด: `.handover/HANDOVER.md` (symlink → repo รวม `handover-notes/THub-Launcher` — **commit HANDOVER ที่ repo รวม ไม่ใช่ที่นี่**) · แนวทางเขียน HANDOVER: `handover-notes/GUIDE.md` · แผนที่ ecosystem ทั้ง 3 repos: `../docs/architecture.md` (โฟลเดอร์ workspace "THub Studio" เหนือ repo นี้)

## โครงสร้างสำคัญ

```
main.py                         ← THub Launcher (CustomTkinter) — อย่าสับสนกับ TStudio
tools/flagship/TStudio/         ← engine แปลหลัก (PyQt6) — UI shell "Masterpiece" + graft ของ fork
  tstudio_app.py                ← หน้าต่างหลัก: workspace_stack (0=Welcome · 1=CAT 3 คอลัมน์ · 2=TRun batch)
  tstudio_dashboard.py          ← WelcomeScreen (หน้า 0) + DashboardPanel (dock ขวา)
  tstudio_thaiwrap.py           ← Thai Wrap ก่อน deploy (subprocess → thaiwrap CLI)
  tstudio_game_tools.py         ← Game Tools: manifest-driven unpack/pack รายเกม (subprocess)
  tstudio_qa_bridge.py          ← QA bridge: subprocess → thai_qa.py (GLQA) + --json
  tstudio_editor/_delegates/_dialogs, trun_batch_dock, retrofit_cli ← โมดูลของ 2.2
  file_converter.py             ← ประตูรับไฟล์ 4 ชั้น (built-in → plugin → cloud → AI)
  CustomParsers/                ← parser ต่อฟอร์แมต (สัญญา: convert_to_csv(filepath, parent_widget))
  CustomParsers/GameTools/      ← Game Tools ที่ติดตั้งผ่าน Plugin Manager (ไม่ track ใน git)
  locales/{th,en}.json          ← คำแปล UI
tools/flagship/TVox/            ← FMV/Dubbing + Whisper ถอดเสียง (แชร์ engine กับ TStudio)
  tvox_stt.py                   ← สะพาน thaistt CLI (QProcess + progress + cancel)
  tvox_app.py                   ← TVoxApp(TranslationStudio) + player + A-B loop
tools/flagship/Core/            ← โมดูลกลางทุกแอปใช้ร่วม (tstudio_core, tpua_engine, TLM, utmt...)
core/                           ← โมดูลของ root Launcher (knowledge_service, tool_launcher, open_utils...)
development/                    ← เครื่องมือ dev: tests/boot_test.py, ui-screenshots/
.handover                       ← symlink → ../../handover-notes/THub-Launcher (ไม่ track ใน git)
```

## กฎเหล็ก

1. **ข้อความ UI ทุกอย่างผ่าน `_(key)`** + เพิ่มคีย์ใน `locales/th.json` และ `en.json` พร้อมกัน — ห้าม hardcoded ข้อความใน widget
2. **สี UI ผ่าน stylesheet กลางเท่านั้น** — ปัจจุบันคือ `MASTERPIECE_SS` (มืด, มี `DARK_SS = MASTERPIECE_SS` เป็น alias):
   widget ที่ต้องการสีเป็นของตัวเองให้ `setObjectName("ชื่อ")` แล้วเพิ่มกฎใน MASTERPIECE_SS —
   ห้าม `setStyleSheet` inline ที่มีค่าสี · **ระบบธีม 3 โหมด (System/Dark/Light/auto) ใช้งานอยู่**
   (เมนู View → ธีม, จำใน config `ui_theme`): `LIGHT_SS` ถูก generate จาก MASTERPIECE_SS ผ่านตาราง
   `_MOCHA_TO_LATTE` ตารางเดียว ซึ่ง remap ทั้ง QSS กลางและ inline styles ทั้งแอปตอนสลับธีม
   (event filter จับ widget ใหม่/สีที่ set ใหม่ให้ด้วย) —
   **ถ้าเพิ่มสี hex ใหม่ใน QSS หรือ inline stylesheet ต้องเพิ่มคู่ใน `_MOCHA_TO_LATTE` ด้วย** ไม่งั้นโหมดสว่างจะมีสีมืดค้าง ·
   จุดที่ใช้ `QColor(...)`/painter ตรง ๆ (delegate, `setForeground`) stylesheet ไปไม่ถึง — ใช้
   `themed_color(hex)` จาก `tstudio_app` (หรือ `_themed()` wrapper แบบ lazy ในโมดูลที่ไม่ import tstudio_app)
3. **โค้ดต้องรันได้ทั้ง macOS และ Windows** — อะไรที่เป็นของ Windows ให้ guard
   (`creationflags=... if os.name == 'nt' else 0` / try-except รอบ `ctypes.windll`) ·
   ห้ามส่ง `os.startfile` บน macOS — ใช้ `core/open_utils.open_path()` แทน · ทดสอบด้วย `QT_QPA_PLATFORM=offscreen`
4. **เขียนไฟล์ config/สำคัญด้วย atomic pattern** — เขียน `.tmp` แล้ว `shutil.move` ทับ (ตามที่มีอยู่ใน `tstudio_core`)
5. **ห้าม commit runtime state** — `Core/config.json`, `Core/prompts.json`, `translation*.csv`,
   โฟลเดอร์ `.venv*`/`__pycache__` คือของเครื่องผู้ใช้ (ใน repo มีแค่ตัวอย่าง `config.example.json`)
6. **ห้ามแตะไฟล์ legacy**: `tstudio_app_bak2.py`, `tstudio_app_clean.py`, `*_bak*`, `patch_*.py`
   — เป็นซากการพัฒนา ไม่ได้ถูกเรียกใช้
7. **Parser plugin contract** — ทุก parser (รวมถึงที่ AI สร้าง) ต้องมี
   `convert_to_csv(filepath, parent_widget=None)` คืน absolute path ของ CSV
   (`ID, Source, Translation, AI_Reference`, utf-8-sig) — ใช้ `ID` แบบ `namespace::key::hash` เพื่อ deploy กลับได้ ·
   **Game Tools แยกช่องทาง** (spec `../docs/spec-game-tools.md`): unpacker/packer รายเกมอยู่ที่
   `CustomParsers/GameTools/<Game>/tool.json` — ใช้ผ่าน subprocess CLI ตาม manifest เท่านั้น
   (เมนู Tools → แตกไฟล์เกม / Pack กลับ) **ห้าม**เสียบเข้า auto-import ของ file_converter ·
   `tools/flagship/Plugins/` เป็นของ **inert** ของ upstream (ไม่มีโค้ดเรียกใช้) — ห้ามเพิ่มเกมใหม่ที่นี่
   ให้เพิ่มที่ TFormat-Plugins (`Game_Extractors/`) แทน
8. **ทดสอบก่อนส่งมอบ** — อย่างน้อย `python development/tests/boot_test.py` ต้องผ่านทั้งหมด (16/16)
9. **fork ↔ upstream** — push ได้เฉพาะ origin (`AeyXD/THub-Launcher`) · ส่งกลับ
   `memolyviza2012-max/THub-Launcher` ด้วย PR เท่านั้น · **⛔ ต้องรอคำสั่งเจ้าของเท่านั้น —
   ห้าม agent สร้าง/ส่ง/เตรียม branch สำหรับ PR เองไม่ว่ากรณีใด แม้งานจะ "พร้อมส่ง" แล้ว**
   (กฎกลางของ workspace: `../AGENTS.md` ข้อ 1) · PR candidate ที่บันทึกไว้: บั๊ก PUA (upstream
   PR #2 — รอ review), ลิงก์ index ของ Modding-Knowledge, Tool Library OS-aware + ffmpeg brew (ดู HANDOVER หัวข้อ 3) —
   รวบรวม candidate ได้เสมอ แต่ห้ามเริ่มเตรียม branch จนกว่าจะมีคำสั่ง
10. **HANDOVER อยู่ใน repo รวม** — `.handover` เป็น symlink ไป `../../handover-notes/THub-Launcher`
    (repo private `AeyXD/handover-notes`) · แก้ HANDOVER แล้ว commit + push **ที่ repo รวม** ไม่ใช่ที่นี่
    · แนวทางเขียน: `handover-notes/GUIDE.md` · `.handover` ไม่ถูก track ใน git ของ repo นี้ (อยู่ใน `.gitignore`)

## คำสั่งที่ใช้บ่อย

```bash
# เปิด TStudio (macOS)
tools/flagship/TStudio/run_tstudio_macos.sh

# เปิด Launcher หลัก (root)
.venv/bin/python main.py

# ทดสอบบูตแบบไม่ต้องมีจอ (CI ใช้ได้)
python development/tests/boot_test.py

# ทดสอบธีม/สีเฉพาะจุด (จับสี pixel จาก widget.grab())
QT_QPA_PLATFORM=offscreen python -c "..."

# แต่งตั้งเครื่องใหม่ (macOS)
brew install python@3.12
# root venv: customtkinter pillow markdown packaging ddgs PyQt6 Pillow numpy
# TStudio venv: สร้างอัตโนมัติโดย run_tstudio_macos.sh (PyQt6 requests numpy)
```

## จุดที่มักพลาด (เคยเกิดแล้วจริง)

- Inline stylesheet ทำให้ธีมสว่างมี widget มืดค้าง — แก้ตามกฎข้อ 2
- `mapping.json` ของ PUA เก็บ "อักขระ PUA ตรง" ไม่ใช่ hex string — `tpua_engine._to_codepoint()`
  รองรับทั้งสองฟอร์แมตแล้ว อย่ากลับไปใช้ `int(x, 16)` เพียงอย่างเดียว
- การ refactor ฟังก์ชันยาว (อย่าง `new_project_from_file` → `start_import`) ระวัง indentation
  ของโค้ดกลางที่ไม่ได้อ่าน — ตรวจด้วย `python -c "import ast; ast.parse(...)"`
- เปลี่ยน/ลบ signal ที่เชื่อมกับ DashboardPanel ต้องอัปเดตทั้ง `dataChanged` และ `modelReset`
- `subprocess.Popen(..., creationflags=...)` บน macOS — ต้อง guard เป็น 0 เสมอ (POSIX ห้าม non-zero)
- `os.startfile()` ไม่มีบน macOS/Linux — ใช้ `core/open_utils.open_path()` แทน
- ชื่อตัวแปร `_` ใช้เป็น discard ใน tuple unpack (เช่น `path, _ = dialog`) แล้วเรียก `_(key)` i18n
  ในฟังก์ชันเดียวกัน → UnboundLocalError — ใช้ชื่ออื่นเช่น `_sel` สำหรับ discard
- เพิ่มแอป flagship ใหม่ใน Launcher: ต้องเพิ่มทั้ง `FLAGSHIP_TOOLS` (core/tool_launcher.py)
  และ `registry_data` (main.py) — เลือก Python ผ่าน `ToolLauncher.resolve_app_python()`
