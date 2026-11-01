# -*- coding: utf-8 -*-
"""tvox_stt.py — สะพาน thaistt (Whisper ถอดเสียงเป็นซับร่าง) ใน TVox
ตาม docs/spec-vox-whisper.md Phase S2 · subprocess loose coupling แบบเดียวกับ QA
bridge/thaiwrap · local-only — whisper.cpp/ffmpeg/โมเดล/ชั้นจัดจังหวะเป็นหน้าที่ของ
thaistt ทั้งหมด THL รู้จักแค่ path เดียว (stt_cli_path)
"""
import os
import re
import sys

# รูปแบบ progress บน stderr ของ whisper.cpp ผ่าน thaistt (ชุดเดียวกับ _PROG_RE ของ thaistt)
PROGRESS_RE = re.compile(r"progress\s*=\s*(\d+)\s*%")

MEDIA_EXTS = (".mp4", ".mkv", ".wav", ".ogg", ".mp3", ".m4a", ".webm", ".avi", ".mov")

LANGS = ("auto", "en", "ja", "zh", "ko", "ru", "fr", "de", "es", "th")


def find_stt_cli(cfg):
    """คืน path ของ thaistt CLI ถ้าตั้งไว้ (stt_cli_path) และมีไฟล์จริง มิฉะนั้น None"""
    p = (cfg or {}).get("stt_cli_path", "")
    return p if p and os.path.isfile(p) else None


def build_cmd(cli_path, media, lang, out_srt, range_ab=None):
    """argv ตาม contract ของ thaistt: <cli> <media> -l <lang> -o <out> [--range A-B]
    (ไม่ใส่ --quiet — เราต้องการ progress % จาก stderr แสดงใน dialog)"""
    argv = [sys.executable, cli_path] if cli_path.lower().endswith(".py") else [cli_path]
    argv += [media, "-l", lang or "auto", "-o", out_srt]
    if range_ab:
        argv += ["--range", range_ab]
    return argv


def ab_range(mark_a, mark_b):
    """A–B → 'SS.ss-SS.ss' ตาม contract · None ถ้ายังไม่ครบ/สลับลำดับ"""
    if mark_a is None or mark_b is None or float(mark_b) <= float(mark_a):
        return None
    return f"{float(mark_a):.2f}-{float(mark_b):.2f}"


def timeout_for(duration_sec):
    """timeout ตามสเปก: ≥300 วินาที หรือ 60 วิ/นาทีสื่อ (≈ 1 เท่าความยาว) เลือกอันมาก
    ไม่รู้ความยาวสื่อ → เพดานกันลอย 7,200 วิ (ผู้ใช้ยกเลิกได้ตลอด)"""
    try:
        d = float(duration_sec or 0)
    except (TypeError, ValueError):
        d = 0.0
    if d <= 0:
        return 7200
    return max(300, int(d))


def draft_path_for(media_path):
    """<name>.draft.srt ข้างไฟล์ต้นฉบับ — ไม่เขียนทับอะไรที่มีอยู่"""
    stem = os.path.splitext(os.path.basename(media_path))[0]
    return os.path.join(os.path.dirname(os.path.abspath(media_path)), f"{stem}.draft.srt")
