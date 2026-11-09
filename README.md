<div align="center">
  <img src="https://i.postimg.cc/HLncmbbK/THub-logo-game-mods-202606162214.jpg" alt="THub Logo" width="100"/>
  <h1>🚀 THub Launcher : The Flagship Suite</h1>
  <p><b>Ultimate Game Modding & Localization Environment — Thai Pipeline Edition</b></p>

  [![Version](https://img.shields.io/badge/Version-2.2.1_(fork)-blue.svg?style=for-the-badge)](#)
  [![Platform](https://img.shields.io/badge/Platform-macOS_·_Windows-lightgrey.svg?style=for-the-badge)](#)
  [![Python](https://img.shields.io/badge/Built_with-Python_3.12-yellow.svg?style=for-the-badge)](#)
  [![UI](https://img.shields.io/badge/UI-PyQt6_·_CustomTkinter-green.svg?style=for-the-badge)](#)
</div>

<br/>

> [!NOTE]
> Repository นี้เป็น **fork ของ [memolyviza2012-max/THub-Launcher](https://github.com/memolyviza2012-max/THub-Launcher)** (ฐาน THub 2.2 Flagship Suite) ดูแลโดย AeyXD —
> สิ่งที่ fork เพิ่มคือ **พอร์ต macOS · Pipeline แปลไทยครบวงจร (AI → QA → Thai Wrap → Deploy) · Whisper ถอดเสียง · AI Dubbing · Workflow Wizard** และเครื่องมือเสริมอีกหลายส่วน
> เครดิตฟีเจอร์เรือธงทั้งหมดเป็นของ upstream — รายละเอียดการพัฒนาต่อจาก fork ดูที่ `AGENTS.md`

**THub Launcher** คือศูนย์รวมเครื่องมือแปลเกมและม็อดเกม (Hub) ที่รวม **Flagship Suite 6 แอป** ไว้ในสภาพแวดล้อมเดียว
พร้อม Workspace ต่อโปรเจกต์ที่เชื่อมถึงกัน งานของ fork นี้โฟกัส **สายไทยครบวงจร**: ตั้งแต่แตกไฟล์เกม แปลด้วย AI ตรวจ QA
จัดวรรณยุกต์ไทย (Thai Wrap) จน Pack กลับเข้าเกม — และสายสื่อ: ถอดเสียงวิดีโอเป็นซับ แปล พากย์ AI แล้วส่งออกกลับ

---

## 🇹🇭 Pipeline ภาษาไทย (หัวใจของ fork นี้)

```text
ไฟล์เกม/สื่อ → แตกไฟล์ (Game Tools) → ตาราง TStudio → แปล AI (Z.ai GLM / อื่น ๆ)
    → ตรวจ QA (GLQA) → Thai Wrap (จัดรอยต่อคำไทย) → Deploy/Pack กลับเข้าเกม

Whisper ถอดเสียง (TVox) → SRT ร่าง → เข้า pipeline เดียวกันผ่าน Game Tool "Subtitles"
AI Dubbing (edge-tts) → WAV รายแถว + preview mix ฟังในเครื่องเล่น
```

**ตัวเชื่อมทั้งหมดเป็นเครื่องมือภายนอกแบบ subprocess (ไม่ bundle ใน repo):**

| เครื่องมือ | ใช้ทำอะไร | สถานะ |
|---|---|---|
| [thaiwrap](https://github.com/AeyXD/thaiwrap) | แทรก ZWSP/hairspace ที่รอยต่อคำไทย กันสระเกาะผิดตำแหน่ง | ✅ ใช้งาน (offline) |
| thaistt (Whisper) | ถอดเสียงวิดีโอ/เสียง → SRT ร่าง ใน TVox | ✅ ใช้งาน (offline) |
| GLQA checker | ตรวจคำแปล (empty / typo / ความยาว) + QA gate ก่อน deploy | ✅ ใช้งาน (offline) |
| [TFormat-Plugins](https://github.com/AeyXD/TFormat-Plugins) | Parser + Game Tools รายเกม/รายฟอร์แมต (manifest-driven) | ✅ ติดตั้งผ่าน Plugin Manager |

ไม่ตั้งค่าตัวไหน → ฟีเจอร์นั้น disabled อย่างสง่างาม + tooltip แนะนำ · ตั้งแล้วใช้งาน **offline ได้ทั้งหมด** (ยกเว้นการเรียก AI API)

---

## ✨ สิ่งที่ fork เพิ่มบนฐาน THub 2.2

- **🍎 พอร์ต macOS เต็มรูปแบบ** — ทุกแอปมี `run_*_macos.sh` ของตัวเอง · guard ครบทุก Windows-ism (`creationflags`, `os.startfile`) · ทดสอบบูต offscreen 6/6 แอป
- **🤖 Z.ai (GLM) Provider** — แปลจริงด้วยแพ็กเกจ GLM-5.3/flash/flashx พร้อม provider อื่น ๆ (DeepSeek, Gemini, Claude, OpenAI, OpenRouter, Local LLM)
- **🛡️ QA Bridge + Deploy Gate** — รัน GLQA จากใน TStudio/TVox ดูผลเป็น dialog แก้อัตโนมัติได้ · เลือกเปิด gate บังคับตรวจก่อน deploy
- **✍️ Thai Wrap 2 ระยะ** — resolve โหมดอัตโนมัติ (line_break ตาม Game Tool / zwsp) ใช้กับ temp copy ไม่แตะ working CSV
- **🧰 Game Tools (Phase C)** — แตกไฟล์เกม/ซับ → CSV → Pack กลับ ผ่าน manifest ของ TFormat-Plugins · รวมถึงตัว "Subtitles" (.srt ↔ ตาราง ↔ pack กลับ)
- **🎙️ Whisper ใน TVox (Phase S2)** — ถอดเสียงเป็นซับร่าง 100% local (thaistt + whisper.cpp) เลือกช่วง A–B ได้ · ร่างเขียนตรงเข้าตาราง
- **🔊 AI Dubbing เฟส 1** — edge-tts เสียงไทย (Premwadee/Niwat) + ffmpeg (atempo/ducking/loudnorm) → WAV รายแถว ฟังได้ในแถวนั้นทันที
- **🎬 Video Player Backend Abstraction** — Windows/Linux ใช้ mpv · macOS ใช้ Qt (QMediaPlayer + FFmpeg) รอบั๊ก python-mpv · ทุกฟีเจอร์เหมือนกัน (A-B loop, speed, ซับ)
- **🧭 Workflow Wizard** — ตัวช่วยทำงานเป็นขั้น ①–⑥ dock ซ้าย (เลือกงาน → นำเข้า → ตรวจ → แปล AI → QA → เสร็จงาน) ตรวจสถานะอัตโนมัติ จำขั้นค้างไว้ต่อรอบหน้า — มือใหม่ไม่ต้องเปิดคู่มือ
- **🏠 Welcome + Dashboard** — เปิดโปรแกรมมาที่หน้าแรกเสมอ พร้อมการ์ดทางลัด + ไฟล์ล่าสุด · Dashboard สถิติแปลสด ๆ ด้านขวา
- **🎨 ธีม 3 โหมด** — ตามระบบ / มืด (Catppuccin Mocha) / สว่าง (Latte) สลับได้ทันที ครบทั้งหน้าต่างและ dialog
- **🐍 Python 3.12 + venv รายแอป** — root venv (CustomTkinter) + venv ของ TStudio ที่ทุกแอป flagship แชร์กัน (PyQt6) · `resolve_app_python()` หำเบอร์ให้อัตโนมัติ
- **🧪 ชุดทดสอบ offscreen** — `boot_test.py` (16 จุด) + `wizard_test.py` (34 จุด) รันได้ไม่ต้องมีจอ (CI-friendly)

---

## 💎 The Flagship Suite (6 แอป)

### 1. 📝 TStudio (Advanced Translation Engine)
*หัวใจหลักของการแปลเกม* แปลไฟล์ข้อความด้วย AI แบบ line-by-line พร้อม Context/Glossary/TLM ช่วย · ตารางเทียบคู่ · นำเข้าได้ทุกฟอร์แมตที่มี parser (รวม plugin + Game Tools) · มี **Workflow Wizard** พาทำทีละขั้นและ Dashboard สถิติ

### 2. ⚡ TRun (Batch AI Runner)
แปลทีละหลายไฟล์/หลายพันแถวในรวดเดียว ประหยัด token ด้วยการรวมกลุ่ม + cache · resume ต่อได้เมื่อไฟดับ · ตั้งเวลาแปล off-peak สลับ provider อัตโนมัติ

### 3. 🅰️ TFont (PUA Text Mapper)
แก้ "สระลอย/สระจม" แบบ batch — วิเคราะห์สระ/วรรณยุกต์ไทยแล้ว shift เข้าโซน PUA ตาม profile ฟอนต์ · รับไฟล์ .csv จาก TStudio ตรง ๆ

### 4. 🔤 TPUA (PUA Font Manager)
จัดการ mapping อักษร PUA รายตัว (encode/decode) พร้อมเครื่องมือ F700 Legacy Font และ Visual Font Tuner

### 5. 🎨 TGlyph (Font Texture Generator)
Render ฟอนต์เป็น Texture Atlas (.dds/.png) + mapping พิกัด พร้อมโหมด Full PUA และ export profile รายเอนจิ้น

### 6. 🎬 TVox (FMV Subtitling & AI Dubbing)
เครื่องเล่นวิดีโอในตัว (mpv / Qt·FFmpeg ตามแพลตฟอร์ม) + waveform + A-B loop + ซับสดบนจอ · **ถอดเสียง Whisper** เป็นซับร่าง · **พากย์ AI** เสียงไทยรายแถว · สืบทอดความสามารถ TStudio ทั้งหมด (รวม wizard)

> ทั้ง 6 แอปเปิดจาก Launcher ได้ และแชร์ profile/API key/ค่าตั้งใน `Core/config.json` กันหมด — กรอกครั้งเดียวใช้ทุกแอป

---

## 🌟 ฟีเจอร์หลักของ Launcher

- **📁 Unified Project Dashboard** — Workspace มาตรฐาน 7 โฟลเดอร์ ต่อโปรเจกต์ (`01_Original_Backup` … `06_Releases` + `thub_project.json`)
- **🧭 Workflow Wizard (Ctrl+Shift+N)** — ทางเข้างานใหม่แบบพาทำทีละขั้น · เมนู/คีย์ลัดแบบเดิมใช้ได้ครบสำหรับ expert
- **🧩 Plugin Manager** — Parser + Cloud plugin + Game Tools 3 แท็บ ดึงจาก TFormat-Plugins
- **🛠️ Tool Library (OS-aware)** — QuickBMS, FModel, AssetStudio ฯลฯ แสดงเฉพาะที่มี build ของ OS นั้น
- **📚 Modding-Knowledge Base** — คลังความรู้ 428 รายการ (58 เอนจิ้น) ใช้ offline ได้ · ย้ายเครื่องได้ (LOCAL_KB fallback)
- **☁️ Cloud Registry & Auto-Update** — อัปเดต flagship tools OTA (fork นี้ชี้ registry ของตัวเอง)

---

## 📥 วิธีติดตั้ง

### macOS (รันจากซอร์ส — ทางหลักของ fork)

```bash
# 1) ตัวหลักที่ต้องมี
brew install python@3.12 ffmpeg

# 2) root venv (Launcher หลัก)
python3.12 -m venv .venv
.venv/bin/pip install customtkinter pillow markdown packaging ddgs PyQt6 Pillow numpy

# 3) เปิดแอป — ครั้งแรกระบบสร้าง venv ของ flagship เองอัตโนมัติ
.venv/bin/python main.py                                   # Launcher หลัก
tools/flagship/TStudio/run_tstudio_macos.sh                # หรือเข้าแอปตรง ๆ

# 4) (แนะนำ) เครื่องมือไทย pipeline — ดูตารางด้านบน แล้วชี้ path ใน Tools → Settings
#    เสริมใน venv ของ TStudio: edge-tts (พากย์ AI) · UnityPy (ไฟล์ Unity .bundle)
```

### Windows

1. ดาวน์โหลด **`THub_Release_v1.x.x.zip`** จาก [Releases ของ upstream](https://github.com/memolyviza2012-max/THub-Launcher/releases)
2. แตกไฟล์แล้วดับเบิลคลิก **`THub.exe`** → เมนู Flagship Products เพื่อติดตั้งแอป T-Series
3. รันจากซอร์สก็ได้เหมือน macOS (แต่ใช้ `run_*.bat` และ libmpv-2.dll วางข้าง TStudio สำหรับเครื่องเล่นวิดีโอ)

### ทดสอบ (ไม่ต้องมีจอ · ใช้ใน CI ได้)

```bash
python development/tests/boot_test.py      # TStudio boot 16 จุด
python development/tests/wizard_test.py   # wizard + ระยะ 0 quick wins 34 จุด
```

---

## ⚙️ สำหรับ Developer

- **Launcher หลัก** = `main.py` (CustomTkinter) ทำหน้าที่ host + registry · **แอป flagship** = PyQt6 อยู่ที่ `tools/flagship/<App>/`
- venv รายแอปโดย `core/tool_launcher.py: resolve_app_python()` (venv ของแอปถ้ามี → root venv เลือกให้อัตโนมัติ)
- โมดูลกลางร่วมที่ `tools/flagship/Core/` (config, AI engine, PUA, UI shared) · locale 3 ชุดแยก (root / TStudio / TVox)
- กฎเหล็กทั้งหมด (i18n, ธีม, atomic write, ห้าม commit runtime state, กฎ fork↔upstream) อยู่ที่ **[`AGENTS.md`](AGENTS.md)** — อ่านก่อนแตะโค้ดทุกครั้ง
- ทดสอบธีม/สีเฉพาะจุด: `QT_QPA_PLATFORM=offscreen python <สคริปต์>`

---

# คู่มือการใช้งานอย่างย่อ

## 1. THub (Launcher)
หน้าแรกของทุกงาน — สร้าง/เลือกโปรเจกต์ (โครงสร้าง 7 โฟลเดอร์สร้างให้อัตโนมัติ) แล้วเปิดแอป T-Series จากการ์ด · ทุกแอปแชร์ profile กันอัตโนมัติ

## 2. TStudio — เริ่มงาน 2 ทาง
- **มือใหม่:** การ์ด **🧭 เริ่มงานใหม่ (พาทำทีละขั้น)** ที่หน้า Welcome หรือ `Ctrl+Shift+N` — wizard จะพาทีละขั้น นำเข้า → ตรวจร่าง → แปล AI → QA → ส่งออก โดยข้ามขั้น/ย่อได้ตลอด
- **มืออาชีพ:** เมนู **📁 ไฟล์** / breadcrumb / คีย์ลัดเดิมทั้งหมด · เปิด `.srt` ระบบจะถามให้เลือกทางเข้า Game Tool Subtitles (แนะนำ — pack กลับได้) หรือ parser ทั่วไป
- ปุ่มสำคัญ: **⚡ แปล** (รายแถว/ทั้งหมด/TRun) · **Ctrl+D Deploy** (QA gate → Thai Wrap → Pack กลับ) · Dashboard สถิติด้านขวา · ธีมสลับที่ View → Theme

## 3. TRun
เลือกไฟล์/โฟลเดอร์ → Start · Pause/Stop ได้ระหว่างทาง · resume ต่อจากที่ค้าง + เลขไทย (๑-๙) ถูกแปลงเป็นอารบิกให้เบื้องหลังอัตโนมัติ

## 4. TFont / TPUA / TGlyph (สายฟอนต์ไทย)
TGlyph ทำ PUA glyph จาก .ttf → TPUA จูน mapping รายตัว → TFont แปลงข้อความแปลทั้งไฟล์เข้ารหัส PUA → พร้อม Pack เข้าเกม

## 5. TVox — ซับ + พากย์
เปิดวิดีโอ → ดูซับสดบนจอ + waveform จัดจังหวะ → **🧬 ถอดเสียง** (Whisper, เลือกช่วง A–B ได้) → ร่างเข้าตาราง TStudio ทันที → แปล → **🎙️ พากย์ AI** ฟังได้รายแถว → **ส่งออกซับ .srt** ผ่านปุ่ม Deploy (Thai Wrap อัตโนมัติ)

<div align="center">
  <b>Made with ❤️ for the Modding Community · Fork stack maintained by AeyXD</b>
</div>
