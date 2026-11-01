# HANDOVER — ส่งต่องานพัฒนา TStudio

**วันที่:** 2026-10-30 · **โดย:** Prawith T. (AeyXD) ร่วมกับ ZCode (GLM)
**ขอบเขตงานรอบนี้:** พอร์ต TStudio ให้ใช้งานบน macOS ได้ + แก้บั๊กแฝง + ระบบธีม + UI facelift + Welcome Screen & Dashboard

---

## 1. บริบท

- ต้นทาง: upstream `memolyviza2012-max/THub-Launcher` → fork ที่ `AeyXD/THub-Launcher` (clone ไว้ที่
  `~/My Workspace/Playgound/THub Studio/THub-Launcher`)
- ภาพรวมทั้ง ecosystem (3 repos): ดู `../docs/architecture.md` — อยู่ที่โฟลเดอร์ workspace "THub Studio" เหนือ repo นี้
- Workspace รอบ ๆ: `../game-localization-qa` (fork ของเราเอง — QA checker v1.2.0), `../TFormat-Plugins`

## 2. สิ่งที่ส่งมอบ (เรียงตามลำดับที่ทำ)

1. **พอร์ต macOS สำเร็จ** — บูต/ใช้งานได้จริงบน macOS (Python 3.9 + PyQt6) พร้อม launcher
   `tools/flagship/TStudio/run_tstudio_macos.sh` (สร้าง venv + ติดตั้ง deps ให้อัตโนมัติครั้งแรก)
2. **แก้บั๊ก PUA engine** (`Core/tpua_engine.py`) — เดิม mapping.json เก็บ "อักขระ PUA ตรง" (`\uf000`)
   แต่โค้ด parse เป็น hex string (`int(x,16)`) ทำให้ **encode PUA เป็น no-op มาตลอดทั้งบน Windows ด้วย**
   ตอนนี้รองรับทั้งสองฟอร์แมต (ทดสอบ round-trip ผ่าน 1,978 mappings)
3. **แก้บั๊ก crash ตอนเปิด** (`Core/tstudio_core.py`) — `load_profiles` เคย `UnboundLocalError`
   เมื่อ project path สร้างโฟลเดอร์ไม่ได้ → เพิ่ม fallback กลับไปใช้ path มาตรฐาน
4. **ระบบธีม 3 โหมด** — เมนู View → ธีม (ตามระบบ/มืด/สว่าง), default **ตามระบบ**,
   สลับทันที จำค่าใน `Core/config.json` คีย์ `ui_theme`, ตรวจธีม OS ได้ทั้ง macOS (`defaults read`)
   และ Windows (registry `AppsUseLightTheme`) + Qt `colorScheme()` เป็นทางหลัก
5. **UI facelift ทันสมัยทั้งชุด** — เขียน `DARK_SS`/`LIGHT_SS` ใหม่ทั้งหมด (โค้งมน 8px แบน
   hover/pressed/focus ชัด scrollbar บาง เมนู/แท็บ/combobox สมัยใหม่) ดูภาพเทียบที่
   `development/ui-screenshots/`
6. **Welcome Screen + Dashboard** — หน้าแรกมีการ์ด quick action 4 ใบ + รายการ "เปิดล่าสุด"
   (จำใน `config.json` คีย์ `recent_files` 8 ไฟล์), dashboard dock สถิติแปลสด (ผ่าน dataChanged
   + throttle 250ms), กลับหน้าแรกได้ด้วย `Ctrl+Shift+H`

## 3. รายการไฟล์ที่เปลี่ยน

| ไฟล์ | สถานะ | เนื้อหา |
|---|---|---|
| `tools/flagship/Core/tpua_engine.py` | แก้ | `_to_codepoint()` รองรับ hex string + literal char |
| `tools/flagship/Core/tstudio_core.py` | แก้ | guard `target_path` ใน `load_profiles` |
| `tools/flagship/TStudio/tstudio_app.py` | แก้ (หลัก) | ธีม+LIGHT_SS ใหม่ + Welcome/Dashboard wiring + `start_import()` refactor + ถอด auto-load `translation.csv` ตอนเปิด |
| `tools/flagship/TStudio/tstudio_dashboard.py` | เขียนใหม่ | `WelcomeScreen` + `DashboardPanel` (ตัวเดิมเป็น dialog ไม่ได้ใช้ + `_` undefined) |
| `tools/flagship/TStudio/locales/th.json`, `en.json` | แก้ | +24 คีย์ (ธีม + welcome + dashboard) |
| `tools/flagship/TStudio/run_tstudio_macos.sh` | ใหม่ | launcher macOS |
| `development/tests/boot_test.py` | ใหม่ | ทดสอบบูต offscreen 9 จุด ใช้ได้ทุก OS |
| `development/tests/tstudio_test.csv` | ใหม่ | ข้อมูลทดสอบ 6 บรรทัด |
| `development/ui-screenshots/*.png` | ใหม่ (5) | before / after dark / after light / welcome / welcome+recent |
| `../docs/architecture.md` (workspace "THub Studio") | ใหม่ | แผนที่สถาปัตยกรรมครอบทั้ง 3 repos |
| `.handover/HANDOVER.md`, `AGENTS.md` | ใหม่ | เอกสารส่งต่อ (ไฟล์นี้) และคู่มือ agent |

## 4. วิธีรัน

```bash
# macOS (แนะนำ)
tools/flagship/TStudio/run_tstudio_macos.sh

# ด้วย venv ที่มีอยู่แล้ว
cd tools/flagship/TStudio && python tstudio_app.py [path/to/โปรเจกต์]

# Windows — เหมือนเดิม
tools\flagship\TStudio\run_tstudio.bat
```

## 5. วิธีทดสอบ (ไม่ต้องมีจอ — CI ใช้ได้)

```bash
python development/tests/boot_test.py
# หรือทดสอบธีมเฉพาะ: QT_QPA_PLATFORM=offscreen python <สคริปต์>
```

## 6. สถานะ Git — ✅ commit 4 ชุด + ✅ merge upstream 2.2 แล้ว (31/10/2026)

- งาน fork: `fix:` c431d7b · `feat:` ธีม e64fc8e · `feat:` dashboard 529d8b9 · `docs:` 31d853f
- **merge 2.2:** ccf227a — ยอมรับ UI shell "Masterpiece" ของ upstream เป็นฐาน แล้ว graft ของเรากลับ:
  Welcome เป็นหน้า 0 ของ workspace_stack (โหมด CAT/TRun คลายเป็น 1/2) · Dashboard เป็น dock ขวา ·
  recent files + Ctrl+Shift+H · กฎ QSS `#ws*`/`#dash*` ผนวกท้าย MASTERPIECE_SS · ถอด auto-load
  `translation.csv` ที่ upstream คืนมาอีกครั้ง · `load_profiles` ใช้ของ upstream (multi-path — ดีกว่า guard เดิม)
- ⚠️ **ธีม 3 โหมดถูกพักไว้**: MASTERPIECE_SS เป็นมืดคงที่ การคืนระบบธีมต้องเขียน Light variant
  ของ MASTERPIECE_SS ก่อน (ต้นแบบ + logic อยู่ใน commits e64fc8e/529d8b9)
- ทดสอบหลัง merge: boot_test **9/9** + เปิด GUI จริงบน macOS ผ่าน · สถานะ: push ครบแล้ว (31/10) —
  main ล่าสุด `93cf7b8` (แก้บั๊ก QHBoxLayout ของ QA dialog + acceptance 4/4 ตาม spec-qa-bridge.md)

## 7. การตัดสินใจออกแบบที่ควรรู้

- **ธีม default = "ตามระบบ"** ตามเจ้าของสั่ง — ผลข้างเคียง: ผู้ใช้ Windows เดิมที่เครื่อง Light mode
  จะเห็น UI สว่างขึ้นหลังอัปเดต (เดิมมืดบังคับ) ถ้าต้องการ backward compat เปลี่ยน default เป็น "dark"
  ได้ที่ `resolve_theme_mode()` บรรทัดเดียว
- **สี UI ทุกชิ้นต้องผ่านธีม** — widget ที่ต้องการสีเป็นของตัวเองให้ตั้ง `setObjectName()` แล้วเพิ่มกฎใน
  DARK_SS/LIGHT_SS (ห้าม `setStyleSheet` inline สี — จะ override ธีม ตามที่เคยเจอกับหน้าต่าง
  ต้นฉบับ/แปล AI/progress bar)
- **เปิดโปรแกรม = หน้า Welcome เสมอ** — ถอดการโหลด `translation.csv` อัตโนมัติตอน startup ออก
  (เดิมโหลด template ทำให้ข้าม welcome)
- **recent_files เก็บใน config.json** ไม่ได้แยกไฟล์ — ทำตาม pattern เดิมของ `last_dir`

## 8. งานค้าง / ข้อเสนอ

1. ~~**Propagate PUA fix ไป TPUA standalone**~~ ✅ **เสร็จ (31/10/2026 · 17f2142)** พร้อมแก้ความเข้าใจผิดเดิม:
   TPUA standalone **ไม่เคยมีบั๊ก no-op เหมือน Core** (มี guard `len==1` อยู่แล้วทั้งไฟล์) — สิ่งที่เจอจริงคือ
   latent bug ชื่อไฟล์: โค้ดหา `mapping.json` แต่ไฟล์จริงชื่อ `Mapping.json` ซึ่งเงียบหายบน filesystem
   case-sensitive (Linux/APFS บางแบบ) → แก้ให้ case-tolerant แล้ว (round-trip ผ่านครบ 2,208 mappings)
2. ~~เชื่อม QA checker~~ ✅ **เสร็จ (31/10 · 2b2d8c6)** — เมนู Tools → ตรวจ QA คำแปล (dry-run/รายงาน/auto-fix)
   + QA gate ก่อน deploy (opt-in) + Settings ช่อง QA Checker (`qa_checker_path`) — รายละเอียด `../docs/spec-qa-bridge.md`
   · **ระยะสองเสร็จด้วย (31/10 · b0d761c)**: bridge ใช้ `--json` เป็นแหล่งความจริง (counts/สรุป i18n `qa_summary_total`
   /report path) + fallback รันซ้ำแบบไม่มี --json ให้ checker เก่า · acceptance ระยะสอง 4/4 + ระยะแรกรันซ้ำผ่าน +
   GLQA CI 64/64 · ตามมาแก้บั๊กแฝง: QHBoxLayout ขาดหายทำให้ dialog ผล QA เปิดไม่ได้ (93cf7b8) และพาสี
   painter/QColor 36 จุดเข้าระบบธีมผ่าน `themed_color()` (b6a8ea0)

3. ~~ทดสอบ AI แปลจริงบน macOS~~ ✅ **เสร็จ (1/11/2026)** — ผ่าน **Z.ai (GLM)** ที่เพิ่งเพิ่มเป็น provider
   first-class (503eafc · key เก็บใน config `zai_key`) · โมเดล **glm-5.3** (บัญชีเข้าถึง 11 โมเดล รวม
   glm-5.3-flash/flashx สำหรับงานแปลจำนวนมากที่ต้องการถูก/เร็ว) · ทดสอบ offscreen ผ่าน engine จริง
   ของแอปทั้ง 2 เส้นทาง: `retranslate_single` ("Weaver said: meet me at the salvage yard" →
   "วีฟเวอร์บอกว่า: มาพบกับฉันที่ลานขูดและตัด" · 52 วิ) และ `retranslate_batch` ("Press {0} to interact" →
   "กด {0} เพื่อโต้ตอบ" · 4.6 วิ · รักษา placeholder ครบ) · auto-save เขียนลง CSV จริง · dashboard
   80% (4/5) ถูกต้อง — แถวที่เหลือเป็น source ภาษาไทย (fixture) ไม่เข้าเกณฑ์ EN→TH · ระหว่างทางปิด
   code smell `_infer_provider` นิยามซ้ำใน SettingsDialog ด้วย (eaf821f)
7. ~~**Game Tools Phase B+C**~~ ✅ **เสร็จ (1/11/2026 · f752da1)** — ตาม `../docs/spec-game-tools.md`
   (Phase A ของ TFP จบที่ 3204d9b) · Plugin Manager มีแท็บ Game Tools
   (เห็น 8 เกม ติดตั้ง/อัพเดตทั้งหมูลง CustomParsers/GameTools/<Game>/) · เมนู Tools →
   แตกไฟล์เกม + Pack กลับ (ขับเสนอใน deploy flow เมื่อ origin_file ตรงเกม) ·
   ขับเคลือนด้วย manifest ล้วน subprocess (โมดูลใหม่ tstudio_game_tools.py) ·
   acceptance ครบ 17/17 (รวม Boltgun round-trip จริง + offline + MetroExodus .lng จริง) · boot_test ผ่าน ·
   หมายเหตุ: หลัง Pack กลับแล้ว unpack ซ้ำ ค่าที่แก้จะอยู่คอลัมน์ Source
   (ไฟล์เกมเก็บสตริงเดียวต่อ entry) — เป็นพฤติกรรมที่ถูกต้อง
8. ~~**Thai Wrap ก่อน deploy**~~ ✅ **เสร็จ (1/11/2026 · 8a5deaa)** — ตาม `../docs/spec-thaiwrap-bridge.md`
   (เครื่องมือ thaiwrap v0.8.0 อยู่นอก workspace ที่ `Playgound/thaiwrap` — CLI: `publish/osx-arm64/ThaiWrap.Cli`) ·
   stage ใน deploy_to_game ตามลำดับสเปก: save → QA gate → Thai Wrap → deploy · wrap เกิดกับ temp copy เท่านั้น
   (working CSV สะอาดไร้ ZWSP เสมอ) · ทุกเส้นทาง deploy อ่านจาก `deploy_source` (Core MESG/LANG/UTMT/PAK/landb +
   GameTools pack + template fallback · meta ยังอิงไฟล์ต้นฉบับ) · Settings: `thaiwrap_cli_path` + โหมด
   off/zwsp/hairspace/space · exit≠0 เตือน+เลือกยกเลิก/deploy ไม่ wrap · acceptance 19/19 + boot_test ·
   แก้บั๊กแฝงพบ: `pack_back_to_game` เทียบ manifest ด้วย `is` ทั้งที่ tool_for_file อ่าน tool.json ใหม่ทุกครั้ง
   (ถามไฟล์ต้นฉบับซ้ำ—ตอนนี้เทียบชื่อเกม) · pipeline ไทยในแอปครบวงจร: แปล AI → QA (GLQA) → Thai Wrap → Deploy/Pack
   · **ระยะสองเสร็จต่อ (1/11 · 6632fa7)**: โหมด `auto` ใน dropdown (default ยัง off) — resolve ตามลำดับ
   `line_break` จาก tool.json ของ Game Tool ที่ผูก origin → ตารางนามสกุล `EXT_BREAK_TABLE` (เริ่มต้นทุกอัน = zwsp,
   เติมข้อยกเว้นเมื่อพิสูจน์แล้ว) → zwsp · โหมดเจาะจงชนะเสมอ · UI โปร่งใสตอน deploy แสดงค่า+ที่มา ·
   acceptance ระยะสอง 20/20 (รวม regression รอบแรก) · หมายเหตุ: ฝั่ง TFP ยังไม่เติม line_break เกมไหนเลย (omit จนพิสูจน์ —
   เมื่อเติม commit เดียวจบ ฝั่งเราไม่ต้องแก้)
4. locale ภาษาอื่น (ja/zh/ru ฯลฯ) ยังไม่มีคีย์ใหม่ — fallback แสดงคีย์/ไทย
5. ~~แจ้งบั๊ก/ส่ง PR กลับ upstream~~ ✅ **ส่งแล้ว (31/10/2026 · [upstream PR #2](https://github.com/memolyviza2012-max/THub-Launcher/pull/2))**
   บั๊ก PUA ของ Core (c431d7b) — branch `fix/pua-mapping-format` (9bbfad3) แตกจาก upstream/main
   ตรง ๆ เอาเฉพาะ `tpua_engine.py` (ส่วน `load_profiles` ไม่ขอไปเพราะ upstream 2.2 เขียนใหม่เป็น
   multi-path แล้ว) · ทดสอบ reproduce กับโค้ด+mapping ของ upstream จริงก่อนส่ง (round-trip 1,978/1,978)
   · PR เป็นภาษาไทย — **รอ maintainer review**
6. ~~**คืนระบบธีม 3 โหมด**~~ ✅ **เสร็จ (31/10/2026 · bdd851f)** — เมนู View → ธีม (ตามระบบ/มืด/สว่าง)
   กลับมาบนฐาน Masterpiece shell: `LIGHT_SS` ถูก generate จาก `MASTERPIECE_SS` ผ่านตาราง remap เดียว
   `_MOCHA_TO_LATTE` (46 คู่, Mocha→Latte) — ตารางเดียวกัน remap inline stylesheet ที่ upstream
   2.2 hardcode ไว้ ~128 จุดตอนสลับธีม (event filter `Polish`/`StyleChange` คุม widget ใหม่/สีที่เปลี่ยน
   ภายหลังด้วย) · dark mode ไม่ถูกแตะแม้แต่ไบต์เดียว · boot_test เพิ่ม section [5] ธีม (รวม 16 จุด ผ่านครบ)
   + ภาพเทียบ `development/ui-screenshots/masterpiece-{light,dark}.png` (โหมดสว่าง: พิกเซลสว่าง 97% ไม่มีมืดค้าง) ·
   แถมแก้ `.gitignore`: `tests/` → `/tests/` เพราะเดิมไปครอบ `development/tests/` จน add ไม่ได้

9. ~~**งานจิ๋ว: กฎ fork↔upstream + ซ่อมความพกพา Modding-Knowledge**~~ ✅ **เสร็จ (1/11/2026 · b785304)**
   · AGENTS.md เพิ่มกฎเหล็กข้อ 9: push ได้เฉพาะ origin · ⛔ PR กลับ upstream ต้องรอคำสั่งเจ้าของเท่านั้น
   (ห้ามเตรียม branch เอง — ตามแบบ TFP/GLQA, อ้างอิง ../AGENTS.md ข้อ 1) ·
   knowledge_service: `EXTERNAL_KB` (E:\ hardcode → root_kb เป็น None บน macOS ทั้งระบบเงียบ) แก้เป็น resolve:
   env `THUB_KB_PATH` → config `kb_external_path` → legacy E:\ → LOCAL_KB · ทดสอบ macOS จริง: 60 engines,
   ค้น Metro Exodus/Avowed/Wasteland 3 เจอครบ, env override ทำงาน · ลิงก์ index แปลง 407 จาก
   `file:///E%3A/...` เป็น relative — **ตรวจครบทั้ง 407 ชี้ถึงไฟล์จริง 100%** · **PR candidate (ตามกฎ ⛔ ยังไม่เตรียม
   branch): ลิงก์ absolute ใน _Index เป็น bug ที่ upstream ควรได้รับด้วย** · PROJECT_STATE.json (IP บ้าน/GPU farm/
   conversation id) git rm --cached + gitignore (ยอมรับ divergence เล็ก) · boot_test ผ่าน

10. ~~**Whisper ใน TVox (Phase S2)**~~ ✅ **เสร็จ (1/11/2026 · e13d87a)** — ตาม `../docs/spec-vox-whisper.md`
    · Settings: `stt_cli_path` (path เดียวถึง thaistt — ตัวมันจัดการ ffmpeg/โมเดลเอง · ไม่ตั้ง → ปุ่ม disabled
    + tooltip แนะนำ) · ปุ่ม 🌿 ใน transport bar: แหล่ง (ไฟล์เล่นอยู่/เลือกใหม่) + ช่วง (ทั้งไฟล์/A–B ตาม mark) +
    ภาษา (auto) · QProcess + QProgressDialog + progress % จาก stderr + ยกเลิกได้ + timeout max(300s, ความยาวสื่อ) ·
    จบเสนอ "เปิดฉบับร่างในตาราง" (Subtitles Game Tool → CSV + origin_file + ID ฝังเวลา) / "เปิดไฟล์ SRT" + เตือน
    ตรวจต้นฉบับก่อนแปล · acceptance 20/20: ถอดคลิปอังกฤษจริง (whisper.cpp large-v3-turbo local) ตรงสาระ 8/8 คำหลัก ·
    ปิดท้ายไปป์ไลน์ครบ: แก้ → QA gate (รันจริง) → Thai Wrap zwsp → Pack back → SRT ไทยเวลาตรงเดิมทุก ms + ZWSP ·
    ✅ **ขา AI จริงรันซ้ำผ่านแล้ว (1/11 · key ใหม่)** — S2 สมบูรณ์ 100% ไม่มีส่วนจำลอง:
    ถอดเสียงจริง → แก้ transcript → **แปล AI จริง glm-4.5-flash** (52 วิ → "เจ้าพ่อประภาคารเก่าบอก") →
    QA gate จริง → Thai Wrap จริง → Pack back → SRT ไทยเวลาตรงเดิม 4/4 cues · หมายเหตุ: แพ็กเกจของ key
    ใหม่ครอบเฉพาะ glm-4.5-flash (glm-5.3/4.6 ยัง 429 — งาน production คุณภาพสูงควรเติมแพ็กเกจระดับสูงกว่า)
    · boot_test ผ่าน · ระหว่างพัฒนา: ติดตั้ง numpy ให้ venv (waveform ของ TVox ใช้ — ของเครื่อง ไม่แตะ repo)

11. ~~**ปรับ run_tstudio_macos.sh ใช้ Python 3.12 ก่อน**~~ ✅ **เสร็จ (1/11 · 5e497ca)** — ตามการตัดสินใจ
    ย้ายเวอร์ชันของเจ้าของ (3.9 EOL · root venv ย้ายแล้ว) · ลำดับ: TSTUDIO_PYTHON ยังชนะ → หา python3.12
    (/opt/homebrew/bin → /usr/local/bin → PATH) → fallback python3 · venv เก่าคนละรุ่นสร้างใหม่อัตโนมัติครั้งเดียว
    · deps เพิ่ม numpy (waveform ของ TVox ต้องใช้ — เครื่องใหม่เคยเงียบหาย) · ทดสอบจริงบนเครื่องนี้:
    สคริปต์ rebuild 3.9→3.12.16 + แอปบูตผ่านสคริปต์ + boot_test 16/16 · venv ปัจจุบันของเครื่องเป็น 3.12 แล้ว

## 9. ข้อจำกัดที่ทราบ (macOS)

- `.exe` ภายนอกใช้ไม่ได้: UTMT (GameMaker .win), ttarchext (Telltale) — ต้องมีตัวรันข้าม OS เอง
- `.locres` ต้อง `pip install pylocres` เพิ่ม
- ฟีเจอร์อื่นทั้งหมด (CSV/JSON/TXT/SRT, แปล AI ทุกค่าย, Glossary, TLM, PUA, deploy CSV) ใช้ได้ครบ
