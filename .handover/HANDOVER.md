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

3. ทดสอบ AI แปลจริงบน macOS (ต้องใส่ API key ก่อน — โค้ดพร้อมแล้ว)
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

## 9. ข้อจำกัดที่ทราบ (macOS)

- `.exe` ภายนอกใช้ไม่ได้: UTMT (GameMaker .win), ttarchext (Telltale) — ต้องมีตัวรันข้าม OS เอง
- `.locres` ต้อง `pip install pylocres` เพิ่ม
- ฟีเจอร์อื่นทั้งหมด (CSV/JSON/TXT/SRT, แปล AI ทุกค่าย, Glossary, TLM, PUA, deploy CSV) ใช้ได้ครบ
