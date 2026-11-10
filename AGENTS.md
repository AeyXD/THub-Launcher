# AGENTS.md — คู่มือสำหรับ AI agent ที่ทำงานใน repo นี้

> อ่านก่อนแตะโค้ดทุกครั้ง · สถานะงานล่าสุด: `.handover/HANDOVER.md` (symlink → repo รวม `handover-notes/THub-Launcher` — **commit HANDOVER ที่ repo รวม ไม่ใช่ที่นี่**) · แนวทางเขียน HANDOVER: `handover-notes/GUIDE.md` · แผนที่ ecosystem: `../docs/architecture.md` (workspace "THub Studio" เหนือ repo นี้ — ครอบ 3 repos)

## Pipeline ภาษาไทย (หัวใจของ fork นี้)

```
ไฟล์เกม/สื่อ → แตกไฟล์ (Game Tools) → ตาราง TStudio → แปล AI (Z.ai GLM)
    → ตรวจ QA (GLQA) → Thai Wrap (thaiwrap) → Deploy/Pack กลับ (Game Tools/Core)
```

Whisper ถอดเสียง (TVox) → SRT ร่าง → วิ่งเข้า pipeline เดียวกันผ่าน Subtitles Game Tool

## โครงสร้างสำคัญ

```
main.py                         ← THub Launcher (CustomTkinter) — อย่าสับสนกับ TStudio
core/                           ← โมดูลของ root Launcher
  tool_launcher.py              ← FLAGSHIP_TOOLS registry + resolve_app_python() (venv รายแอป)
  knowledge_service.py          ← Modding-Knowledge scanner (env/config → LOCAL_KB fallback)
  open_utils.py                 ← open_path() ข้าม platform (แทน os.startfile)
  i18n.py / config_manager.py   ← i18n + config ของ root Launcher (locales/ ที่ root)
locales/{th,en,...}.json        ← i18n ของ root Launcher (main.py)
tools/flagship/TStudio/         ← engine แปลหลัก (PyQt6)
  tstudio_app.py                ← หน้าต่างหลัก: workspace_stack (0=Welcome · 1=CAT · 2=TRun)
  tstudio_dashboard.py          ← WelcomeScreen (หน้า 0) + DashboardPanel (dock ขวา)
  tstudio_wizard.py             ← Workflow Wizard: stepper 6 ขั้น dock ซ้าย (orchestration — เรียก method เดิม)
  tstudio_thaiwrap.py           ← Thai Wrap (subprocess → thaiwrap CLI + resolve_mode auto)
  tstudio_game_tools.py         ← Game Tools: manifest-driven unpack/pack (subprocess CLI)
  tstudio_qa_bridge.py          ← QA bridge (subprocess → thai_qa.py + --json)
  tstudio_delegates.py          ← StatusPill/TagIcon/Html delegates (ใช้ themed_color)
  tstudio_analyzer_dialog.py    ← Analyzer (ใช้ _themed())
  file_converter.py             ← ประตูรับไฟล์ 4 ชั้น (built-in → plugin → cloud → AI)
  plugin_manager_ui.py          ← Plugin Manager: 3 แท็บ (installed/cloud/Game Tools)
  CustomParsers/                ← parser ต่อฟอร์แมต (สัญญา: convert_to_csv(filepath, parent_widget))
  CustomParsers/GameTools/      ← Game Tools ที่ติดตั้ง (ไม่ track ใน git)
  locales/{th,en}.json          ← i18n ของ TStudio (แก้คีย์ UI TStudio ที่นี่)
tools/flagship/TVox/            ← FMV/Dubbing + Whisper (สืบทอด TStudio ทั้งหมด)
  tvox_stt.py                   ← สะพาน thaistt CLI (QProcess + progress + cancel)
  tvox_app.py                   ← TVoxApp(TranslationStudio) + mpv player + A-B loop
  tvox_i18n.py                  ← i18n ของ TVox (merge TStudio → TVox locale keys)
  locales/{th,en,...}.json      ← i18n ของ TVox (แก้คีย์ UI TVox ที่นี่)
tools/flagship/Core/            ← โมดูลกลางทุกแอปใช้ร่วม
  tstudio_core.py               ← CoreAI.generate_content() + config + profiles + engine
  tpua_engine.py                ← PUA encode/decode (mapping.json: hex string + literal char)
  tstudio_ui_shared.py          ← SettingsDialog + ApiWorker + prompts (ใช้ _themed())
  translation_transport/        ← Codex Web GPT bridge (Windows-only)
development/tests/boot_test.py  ← ทดสอบบูต offscreen (16 จุด ต้องผ่าน 100%)
.handover                       ← symlink → ../../handover-notes/THub-Launcher
```

## เครื่องมือภายนอก (subprocess — ไม่ bundle ไม่ import)

| เครื่องมือ | ที่อยู่บนเครื่องนี้ | config key | ใช้ทำอะไร |
|---|---|---|---|
| thaiwrap | `Playgound/thaiwrap/publish/osx-arm64/ThaiWrap.Cli` | `thaiwrap_cli_path` + `thaiwrap_mode` | แทรก ZWSP/hairspace/space ที่รอยต่อคำไทย |
| thaistt | `Playgound/thaistt/thaistt.py` | `stt_cli_path` | Whisper ถอดเสียงเป็น SRT ร่าง |
| GLQA checker | workspace `game-localization-qa/checker/thai_qa.py` | `qa_checker_path` + `qa_gate_before_deploy` | ตรวจคำแปล (empty-target, typo, ฯลฯ) |
| TFormat-Plugins | GitHub `AeyXD/TFormat-Plugins` | (ผ่าน Plugin Manager) | parser + Game Tools (manifest-driven) |

ทุกตัว: ไม่ตั้ง path → ฟีเจอร์ disabled + tooltip แนะนำ · ตั้งแล้วใช้ offline ได้

## Config keys ที่สำคัญ (Core/config.json — runtime state ห้าม commit)

| คีย์ | ค่าตัวอย่าง | ใช้ที่ไหน |
|---|---|---|
| `provider` / `model` | `"Z.ai (GLM)"` / `"glm-5.3-flash"` | แปล AI — dropdown บน header |
| `zai_key` / `deepseek_key` / `openai_key` / ... | API key | Settings → API Keys |
| `ui_theme` | `"system"` / `"dark"` / `"light"` | View → ธีม |
| `origin_file` | path ของไฟล์เกม/สื่อต้นทาง | deploy/Pack กลับ — ผูกอัตโนมัติตอนแตกไฟล์ |
| `thaiwrap_cli_path` / `thaiwrap_mode` | path / `"auto"` / `"zwsp"` / `"off"` | Settings → Thai Wrap |
| `stt_cli_path` | path ถึง thaistt | Settings → thaistt (TVox) |
| `qa_checker_path` / `qa_gate_before_deploy` | path / `true` | Settings → QA |

## กฎเหล็ก

1. **ข้อความ UI ผ่าน `_(key)`** — มี 3 ชุด locale แยกกัน:
   - **root Launcher** (main.py): `locales/{th,en}.json` + `core/i18n.py`
   - **TStudio** (tstudio_app): `tools/flagship/TStudio/locales/{th,en}.json` + `tstudio_i18n`
   - **TVox**: `tools/flagship/TVox/locales/{th,en}.json` + `tvox_i18n` (merge TStudio keys แล้ว override)
   เพิ่มคีย์ใน th + en พร้อมกันเสมอ ตามแอปที่แก้
2. **สี UI ผ่าน stylesheet กลางเท่านั้น** — `MASTERPIECE_SS` (มืด) / `LIGHT_SS` (generate จาก `_MOCHA_TO_LATTE`):
   - เพิ่มสี hex ใหม่ใน QSS หรือ inline stylesheet → **ต้องเพิ่มคู่ใน `_MOCHA_TO_LATTE`** ไม่งั้น Light มีสีมืดค้าง
   - `QColor(...)`/painter ตรง ๆ → ใช้ `themed_color()` จาก `tstudio_app` หรือ `_themed()` lazy wrapper
   - ห้าม `setStyleSheet` inline ที่มีค่าสี — ใช้ `setObjectName()` + กฎใน stylesheet
3. **โค้ดรันได้ทั้ง macOS และ Windows** — guard ทุกจุด:
   - `creationflags=... if os.name == 'nt' else 0` (POSIX ห้าม non-zero)
   - ห้าม `os.startfile()` บน macOS — ใช้ `core/open_utils.open_path()`
   - ทดสอบ: `QT_QPA_PLATFORM=offscreen`
4. **Atomic write** สำหรับ config/ไฟล์สำคัญ — `.tmp` แล้ว `shutil.move` ทับ
5. **ห้าม commit runtime state** — `Core/config.json`, `Core/prompts.json`, `translation*.csv`, `.venv*`, `__pycache__`, `.handover`
6. **ห้ามแตะ legacy**: `*_bak*`, `*_clean.py`, `patch_*.py` — ซากการพัฒนา
7. **Parser plugin contract** — `convert_to_csv(filepath, parent_widget=None)` คืน CSV path
   (`ID, Source, Translation, AI_Reference`, utf-8-sig, ID แบบ `namespace::key::hash`) ·
   **Game Tools แยกช่องทาง**: `CustomParsers/GameTools/<Game>/tool.json` → subprocess CLI เท่านั้น
   (ห้ามเสียบเข้า auto-import ของ file_converter) · `tools/flagship/Plugins/` = inert ของ upstream
   ห้ามเพิ่มเกมใหม่ที่นี่ — ไปเพิ่มที่ TFormat-Plugins (`Game_Extractors/`)
8. **ทดสอบก่อนส่งมอบ** — `python development/tests/boot_test.py` ต้องผ่าน 16/16
9. **fork ↔ upstream** — push ได้เฉพาะ origin (`AeyXD/THub-Launcher`) · ⛔ PR กลับ upstream
   ต้องรอคำสั่งเจ้าของเท่านั้น ห้าม agent สร้าง/ส่ง/เตรียม branch เอง (กฎ `../AGENTS.md` ข้อ 1)
   · PR candidates: บั๊ก PUA (PR #2 รอ review), KB index links, Tool Library OS-aware + ffmpeg brew
10. **NOTICE = ของ fork ห้ามรวมใน PR กลับ upstream** — เพิ่ม dependency/พอร์ตโค้ด/ทรัพย์สินใหม่
    ต้องอัปเดต `NOTICE` ที่ root ใน commit เดียวกัน (กติกา `../docs/notices-plan.md` §4)
    · ห้ามแก้หัวไฟล์ license ของ upstream เอง เช่น main.py ที่อ้าง GPL-3.0 ขณะที่ root = AGPL-3.0
      (ความไม่สอดคล้องจาก upstream — บันทึกไว้ใน HANDOVER เท่านั้น)
10. **HANDOVER อยู่ใน repo รวม** — `.handover` = symlink → `../../handover-notes/THub-Launcher`
    (repo private `AeyXD/handover-notes`) · commit HANDOVER **ที่ repo รวม** · GUIDE: `handover-notes/GUIDE.md`

## คำสั่งที่ใช้บ่อย

```bash
# เปิด TStudio (macOS — สร้าง venv อัตโนมัติครั้งแรก + เลือก Python 3.12)
tools/flagship/TStudio/run_tstudio_macos.sh

# เปิด Launcher หลัก (root — CustomTkinter + ทุกแอป flagship)
.venv/bin/python main.py

# ทดสอบบูต (CI ใช้ได้ ไม่ต้องมีจอ)
python development/tests/boot_test.py

# ทดสอบธีม/สีเฉพาะจุด
QT_QPA_PLATFORM=offscreen python -c "..."

# Commit HANDOVER (ที่ repo รวม — ไม่ใช่ repo นี้!)
cd ../../handover-notes && git add THub-Launcher/ && git commit -m "..." && git push
```

### ตั้งเครื่องใหม่ (macOS)

```bash
brew install python@3.12 ffmpeg

# root venv (Launcher)
python3.12 -m venv .venv
.venv/bin/pip install customtkinter pillow markdown packaging ddgs PyQt6 Pillow numpy

# TStudio venv — สร้างอัตโนมัติโดย run_tstudio_macos.sh (PyQt6 requests numpy)
#   + edge-tts (พากย์ AI) และ UnityPy (ไฟล์ Unity .bundle) ติดตั้งเพิ่มด้วย pip

# เครื่องมือภายนอก (subprocess — ไม่ bundle)
# thaiwrap: Playgound/thaiwrap (build หรือโหลด publish/osx-arm64)
# thaistt:  Playgound/thaistt (Python stdlib + whisper.cpp จาก brew)
# GLQA:     THub Studio/game-localization-qa (Python stdlib)

# External game tools บน macOS:
# ✅ ติดตั้งแล้ว: pylocres (venv) · QuickBMS (/opt/homebrew/bin/quickbms)
#                ffmpeg · whisper-cpp (brew)
# ❌ ไม่มี mac build ทางการ — ใช้ทางเลือกแทน:
#   repak → TPakManager (built-in) หรือ QuickBMS · ติดตั้งจริง: cargo install repak-cli
#   FModel → QuickBMS (extract ได้เหมือนกัน) · build จาก dotnet ถ้าจำเป็น
#   UTMT / ttarchext → Windows .exe เท่านั้น
```

## จุดที่มักพลาด (เคยเกิดแล้วจริง)

- **3 ชุด locale แยกกัน** — แก้ UI ของแอปไหนก็เพิ่มคีย์ใน locale ของแอปนั้น (TStudio ≠ TVox ≠ root)
- **เพิ่มโมเดลใหม่** ต้องแก้ทั้ง `TOP_BAR_SUBMODELS` (tstudio_app.py) และ `models_by_provider` (tstudio_ui_shared.py)
- **เพิ่มแอป flagship ใหม่** ต้องแก้ทั้ง `FLAGSHIP_TOOLS` (core/tool_launcher.py) และ `registry_data` (main.py)
- Inline stylesheet มีสี → ธีมสว่างมี widget มืดค้าง — แก้ตามกฎข้อ 2
- `subprocess.Popen(..., creationflags=nonzero)` บน macOS → ValueError — guard เป็น 0 เสมอ
- `os.startfile()` ไม่มีบน macOS — ใช้ `core/open_utils.open_path()`
- ชื่อตัวแปร `_` ใช้เป็น discard (`path, _ = ...`) แล้วเรียก `_(key)` i18n ในฟังก์ชันเดียวกัน
  → UnboundLocalError — ใช้ `_sel` / `_ext` สำหรับ discard
- Refactor ฟังก์ชันยาว: ระวัง indentation ของโค้ดกลางที่ไม่ได้อ่าน — ตรวจ `ast.parse` ทุกครั้ง
- เปลี่ยน/ลบ signal เชื่อมกับ DashboardPanel → อัปเดตทั้ง `dataChanged` และ `modelReset`
- `mapping.json` ของ PUA เก็บ "อักขระ PUA ตรง" — `_to_codepoint()` รองรับทั้งสองฟอร์แมต อย่าย้อนกลับ
- `Core/prompts.json` โดนแก้โดยการรันแอป — **อย่า `git add .` เด็ดขาด** ระบุไฟล์เฉพาะเจาะจงเสมอ
- `pack_back_to_game` เทียบ manifest ด้วย `is` — ต้องเทียบชื่อเกม (`manifest.get("game")`) เพราะ `tool_for_file()` อ่าน tool.json ใหม่ทุกครั้ง
