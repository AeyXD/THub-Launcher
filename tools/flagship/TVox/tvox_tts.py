# -*- coding: utf-8 -*-
"""tvox_tts.py — AI TTS พากย์เสียงไทย (เฟส 1 ตาม spec-ai-dubbing.md)
Provider: edge-tts (subprocess CLI) · Audio processing: ffmpeg (atempo/ducking/loudnorm)
Pattern: bridge เดียวกับ tvox_stt.py / tstudio_thaiwrap.py — subprocess loose coupling
"""
import os
import subprocess
import sys
import tempfile

# venv ของ TStudio (แชร์กันอยู่แล้ว — edge-tts ติดตั้งที่นั่น)
_TSTUDIO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'TStudio'))
_EDGE_TTS_BIN = os.path.join(_TSTUDIO_DIR, '.venv', 'bin', 'edge-tts')

# เสียงที่รองรับ
VOICES = {
    "premwadee": "th-TH-PremwadeeNeural",
    "niwat":     "th-TH-NiwatNeural",
}
DEFAULT_VOICE = "th-TH-PremwadeeNeural"
RETRIES = 3
TIMEOUT = 30


def find_edge_tts():
    """คืน path ของ edge-tts binary ใน venv ของ TStudio"""
    if os.path.isfile(_EDGE_TTS_BIN) and os.access(_EDGE_TTS_BIN, os.X_OK):
        return _EDGE_TTS_BIN
    return None


def generate_tts(text, voice, out_wav, rate="+0%", ffmpeg_path=None):
    """สร้างเสียง TTS จากข้อความ → WAV 16kHz mono · คืน (ok, error_msg)

    subprocess: edge-tts CLI → MP3 (temp) → ffmpeg → WAV
    retry 3 ครั้ง · timeout 30 วิ/ประโยค · guard creationflags Windows
    """
    if not text or not text.strip():
        return False, "ข้อความว่าง"
    cli = find_edge_tts()
    if not cli:
        return False, "ไม่พบ edge-tts — ติดตั้งด้วย pip install edge-tts ใน venv ของ TStudio"

    tmpdir = tempfile.mkdtemp(prefix="tts_")
    mp3_out = os.path.join(tmpdir, "tts.mp3")

    for attempt in range(RETRIES):
        try:
            cmd = [cli, "--voice", voice, "--text", text.strip(), "--write-media", mp3_out]
            if rate and rate != "+0%":
                cmd.extend(["--rate", rate])
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=TIMEOUT,
                creationflags=0x08000000 if os.name == "nt" else 0
            )
            if proc.returncode == 0 and os.path.isfile(mp3_out) and os.path.getsize(mp3_out) > 100:
                break
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass
        if attempt < RETRIES - 1:
            import time
            time.sleep(1.5)
    else:
        return False, f"edge-tts ล้มเหลวหลัง {RETRIES} ครั้ง"

    # แปลง MP3 → WAV 16kHz mono
    ff = ffmpeg_path or _find_ffmpeg()
    if not ff:
        return False, "ไม่พบ ffmpeg — ต้องติดตั้ง (brew install ffmpeg)"

    try:
        subprocess.run(
            [ff, "-y", "-loglevel", "error", "-i", mp3_out,
             "-ar", "16000", "-ac", "1", out_wav],
            capture_output=True, timeout=15,
            creationflags=0x08000000 if os.name == "nt" else 0
        )
    except Exception as e:
        return False, f"ffmpeg แปลง WAV ไม่สำเร็จ: {e}"
    finally:
        try:
            os.remove(mp3_out)
            os.rmdir(tmpdir)
        except Exception:
            pass

    return os.path.isfile(out_wav), None if os.path.isfile(out_wav) else "WAV ไม่ถูกสร้าง"


def match_duration(wav_path, target_duration_sec, ffmpeg_path=None):
    """ยืด/บีบ WAV ให้พอดี duration ต้นฉบับ (±20% tolerance) · คืน path ใหม่"""
    ff = ffmpeg_path or _find_ffmpeg()
    if not ff or not os.path.isfile(wav_path):
        return wav_path

    # วัด duration ปัจจุบัน
    try:
        probe = subprocess.run(
            [ff, "-i", wav_path, "-f", "null", "-"],
            capture_output=True, text=True, timeout=10,
            creationflags=0x08000000 if os.name == "nt" else 0
        )
        import re
        m = re.search(r"time=(\d+):(\d+):(\d+\.?\d*)", proc_stderr(probe))
        if not m:
            return wav_path
        cur_dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    except Exception:
        return wav_path

    if cur_dur <= 0 or target_duration_sec <= 0:
        return wav_path

    ratio = cur_dur / target_duration_sec
    # atempo รับได้ 0.5–2.0 · ถ้าต่างเกิน 20% ค่อยปรับ
    if 0.8 <= ratio <= 1.2:
        return wav_path

    tempo = max(0.5, min(2.0, ratio))
    out = wav_path.replace(".wav", "_matched.wav")
    try:
        subprocess.run(
            [ff, "-y", "-loglevel", "error", "-i", wav_path,
             "-filter:a", f"atempo={tempo:.3f}", out],
            capture_output=True, timeout=15,
            creationflags=0x08000000 if os.name == "nt" else 0
        )
        if os.path.isfile(out) and os.path.getsize(out) > 100:
            return out
    except Exception:
        pass
    return wav_path


def mix_with_ducking(original_path, tts_wav, out_path, ffmpeg_path=None):
    """ผสมเสียงพากย์กับต้นฉบับ — ลดเสียงต้นฉบับลงตอนพากย์พูด (sidechaincompress) + normalize"""
    ff = ffmpeg_path or _find_ffmpeg()
    if not ff or not os.path.isfile(original_path) or not os.path.isfile(tts_wav):
        return False, "ไม่พบไฟล์เสียง"

    try:
        # sidechaincompress: tts_wav เป็น sidechain → ลดเสียงต้นฉบับ + loudnorm
        filter_complex = (
            f"[1:a]asplit=2[sc][mix];"
            f"[0:a][sc]sidechaincompress=threshold=0.03:ratio=8:attack=5:release=300[ducked];"
            f"[ducked][mix]amix=inputs=2:duration=longest,loudnorm=I=-16:TP=-1.5:LRA=11[out]"
        )
        subprocess.run(
            [ff, "-y", "-loglevel", "error",
             "-i", original_path, "-i", tts_wav,
             "-filter_complex", filter_complex,
             "-map", "[out]", "-ar", "44100", out_path],
            capture_output=True, timeout=120,
            creationflags=0x08000000 if os.name == "nt" else 0
        )
    except Exception as e:
        return False, f"ffmpeg mix ไม่สำเร็จ: {e}"

    return os.path.isfile(out_path), None if os.path.isfile(out_path) else "ไฟล์ผสมไม่ถูกสร้าง"


def _find_ffmpeg():
    """ค้นหา ffmpeg ใน PATH"""
    try:
        result = subprocess.run(["ffmpeg", "-version"],
                                capture_output=True, timeout=5,
                                creationflags=0x08000000 if os.name == "nt" else 0)
        if result.returncode == 0:
            return "ffmpeg"
    except Exception:
        pass
    return None


def proc_stderr(proc):
    """ffmpeg เขียน duration ไป stderr"""
    return proc.stderr or ""
