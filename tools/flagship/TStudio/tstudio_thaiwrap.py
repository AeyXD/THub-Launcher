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

MODES = ("off", "zwsp", "hairspace", "space")


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
    if mode not in MODES or mode == "off":
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
