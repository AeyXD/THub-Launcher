# -*- coding: utf-8 -*-
"""tstudio_thaiwrap.py — สะพาน Thai Wrap ก่อน deploy (spec: docs/spec-thaiwrap-bridge.md)

thaiwrap (repo นอก workspace) แทรกจุดตัดบรรทัดที่มองแทบไม่เห็น (ZWSP/hairspace/space)
ที่รอยต่อคำไทยให้เอนจินเกมตัดบรรทัดถูกจุด · หลักการ: subprocess loose coupling เหมือน QA
bridge · working CSV ต้องสะอาดเสมอ — wrap เกิดกับ temp copy ตอน deploy เท่านั้น
(ลำดับ pipeline: save → QA gate → Thai Wrap → deploy)
"""
import os
import subprocess
import tempfile

TIMEOUT = 120  # วินาที ตามสเปก

MODES = ("off", "auto", "zwsp", "hairspace", "space")
WRAP_MODES = ("zwsp", "hairspace", "space")  # ค่าที่ส่งให้ CLI ได้จริง

# ตาราง fallback ตามนามสกุลไฟล์ต้นทาง (mode=auto เมื่อไม่มี line_break จาก Game Tool)
# เริ่มต้นอนุรักษ์นิยม: ทุกนามสกุล → zwsp — เติมข้อยกเว้นเฉพาะค่าที่พิสูจน์จากเกมจริงแล้วเท่านั้น
# เช่นในอนาคต: {".tlk": "space"} (Aurora) · รูปแบบ Scaleform → "hairspace"
EXT_BREAK_TABLE = {}

# คำอธิบายที่มาของค่าที่ resolve (ใช้สร้างข้อความ UI โปร่งใสตอน deploy)
SOURCE_KEYS = {
    "explicit": None,  # ผู้ใช้เลือกโหมดเจาะจงเอง — ไม่ต้องระบุที่มา
    "gametool": "tw_resolved_gametool",
    "ext": "tw_resolved_ext",
    "default": "tw_resolved_default",
}


def resolve_mode(cfg, origin_file=None):
    """resolve โหมด Thai Wrap ตามสเปกระยะสอง — คืน (mode, source)

    mode เจาะจง (zwsp/hairspace/space) และ off ใช้ตรง ๆ (ชนะเสมอ — auto ไม่แตะ)
    mode=auto หยุดที่ค่าแรกที่เจอตามลำดับ:
      1. line_break จาก tool.json ของ Game Tool ที่ผูกกับ origin_file
      2. ตาราง fallback ตามนามสกุลไฟล์ (default ของตาราง = zwsp)
      3. ค่า default สุดท้าย: zwsp"""
    mode = str((cfg or {}).get("thaiwrap_mode", "off")).lower()
    if mode != "auto":
        return (mode if mode in ("off",) + WRAP_MODES else "off"), "explicit"
    # ── auto ──
    if origin_file:
        try:
            import tstudio_game_tools as gt
            manifest = gt.tool_for_file(origin_file)
            lb = (manifest or {}).get("line_break")
            if lb in WRAP_MODES:
                return lb, "gametool"
        except Exception:
            pass
        ext = os.path.splitext(origin_file)[1].lower()
        hit = EXT_BREAK_TABLE.get(ext, "zwsp")
        if hit in WRAP_MODES:
            return hit, "ext"
    return "zwsp", "default"


def resolved_message(mode, source, game=""):
    """ข้อความ UI โปร่งใสแสดงค่าที่ resolve + ที่มา (เฉพาะ auto — explicit คืน None)"""
    if source == "explicit":
        return None
    try:
        from tstudio_i18n import _
        key = SOURCE_KEYS.get(source) or "tw_resolved_ext"
        return _(key, mode=mode, game=game)
    except Exception:
        return f"Thai Wrap: auto → {mode} ({source})"


def find_cli(cfg):
    """คืน path ของ thaiwrap CLI ถ้าตั้งไว้ (thaiwrap_cli_path) และมีไฟล์จริง มิฉะนั้น None"""
    p = (cfg or {}).get("thaiwrap_cli_path", "")
    return p if p and os.path.isfile(p) else None


def wrap_csv(cli_path, csv_path, mode):
    """รัน thaiwrap กับ CSV → คืน (ok, temp_csv_path หรือ stderr_text)

    ตาม contract ของ thaiwrap: `-f csv --columns Translation --break-char <mode>`
    (ใช้ชื่อคอลัมน์ → ข้าม header + อนุรักษ์ทุกคอลัมน์อื่น byte-for-byte) ·
    CLI ไม่แต่ไฟล์ต้นทาง — ผลลัพธ์เขียนลง temp ของระบบ ชื่อ <name>.<mode>.csv ·
    exit 0 = สำเร็จ · อื่น = ปัญหา option/ไฟล์ (stderr เป็นภาษาไทย)
    """
    if mode not in WRAP_MODES:
        return False, "โหมด Thai Wrap ไม่ถูกต้อง: " + str(mode)
    if not os.path.isfile(csv_path):
        return False, "ไม่พบไฟล์ CSV: " + csv_path

    stem = os.path.splitext(os.path.basename(csv_path))[0]
    out_path = os.path.join(tempfile.mkdtemp(prefix="thaiwrap_"), f"{stem}.{mode}.csv")
    cmd = [cli_path, csv_path, "-f", "csv", "--columns", "Translation",
           "--break-char", mode, "-o", out_path]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=TIMEOUT,
            creationflags=0x08000000 if os.name == "nt" else 0
        )
    except subprocess.TimeoutExpired:
        return False, f"thaiwrap หมดเวลา {TIMEOUT} วินาที"
    except Exception as e:
        return False, str(e)
    if proc.returncode == 0 and os.path.isfile(out_path):
        return True, out_path
    err = ((proc.stdout or "") + (proc.stderr or "")).strip()
    return False, err or f"thaiwrap exit {proc.returncode}"
