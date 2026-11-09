# -*- coding: utf-8 -*-
"""tvox_video_export.py — ทำวิดีโอพากย์ไทย (spec-workflow-wizard.md ระยะ 2-2)

พอร์ตจาก `make_videos_r1.sh` ของ hub (ทำมือและพิสูจน์แล้วในรอบที่ 1) เป็น Python:
  - `dub` = พากย์ล้วน (ตัดเสียงเดิม) + ฝังซับไทยเป็นแทร็ก (ถ้ามี SRT ที่ pack แล้ว)
  - `mix` = เสียงต้นฉบับ ducking + พากย์ (เทียบฟัง)
filter graph เหมือนที่ hub ใช้จริงทุกตัว:
  adelay → apad → amix normalize=0 → loudnorm(I=-16:TP=-1.5) → aresample 44100
  mix เพิ่ม sidechaincompress(threshold=.05 ratio=6 attack=25 release=350)
วิดีโอ `-c:v copy` เสมอ · เสียง aac 192k · ซับ mov_text language=tha

Pattern: QThread + QProgressDialog + ยกเลิกได้ (เดียวกับ _run_game_tool_with_progress)
· subprocess guard `creationflags` Windows · timing มาจาก ID `srt::n::start::end`
ด้วย regex เดียวกับ srt_packer.py ของ Game Tool Subtitles (ห้าม hardcode)
"""
import os
import re
import subprocess

from PyQt6.QtCore import Qt, QThread, QEventLoop, pyqtSignal
from PyQt6.QtWidgets import QProgressDialog

from tvox_i18n import _

# เดียวกับ _ID_RE ใน srt_packer.py (CustomParsers/GameTools/Subtitles) — แหล่งเวลาเดียวที่ใช้
SRT_ID_RE = re.compile(r'^srt::(\d+)::(\d+)::(\d+)$')


def parse_srt_id(row_id):
    """'srt::3::7444::9000' → (7444, 9000) ms · ไม่ใช่รูปแบบนี้ → None"""
    m = SRT_ID_RE.match(str(row_id or "").strip())
    return (int(m.group(2)), int(m.group(3))) if m else None


def wav_for_id(tts_dir, row_id):
    """หา WAV ของแถวใน tts_output/ — ชื่อตาม ID ใน CSV ({id}.wav ของ _start_tts_batch)
    รองรับชื่อแบบ r1 ของ hub (srt_1_0_3000.wav) เป็น fallback"""
    cand = [
        os.path.join(tts_dir, f"{row_id}.wav"),
        os.path.join(tts_dir, "srt_{}_{}_{}.wav".format(*SRT_ID_RE.match(row_id).groups()))
        if SRT_ID_RE.match(row_id) else "",
    ]
    for c in cand:
        if c and os.path.isfile(c):
            return c
    return None


def tts_dir_for(csv_path):
    """tts_output/ อยู่ข้าง CSV (เดียวกับ _start_tts_batch/_tts_wav_for_row)"""
    return os.path.join(os.path.dirname(os.path.abspath(csv_path or ".")), "tts_output")


def build_items(model_data, tts_dir):
    """[(start_ms, wav_path)] จาก model._data — เฉพาะแถว srt:: ที่มี WAV จริง เรียงตามเวลาเริ่ม"""
    items = []
    for row in model_data or []:
        span = parse_srt_id(row.get("id", ""))
        if not span:
            continue
        wav = wav_for_id(tts_dir, row.get("id", ""))
        if wav:
            items.append((span[0], wav))
    items.sort(key=lambda it: it[0])
    return items


def video_export_readiness(studio):
    """(พร้อมทำวิดีโอไหม, เหตุผล key) — ใช้ทั้งปุ่ม wizard และ dialog ของ TVox
    เงื่อนไขตามสเปก: มีวิดีโอเปิดใน player + CSV เป็นชุดซับ (ID srt::)"""
    player = getattr(studio, "player", None)
    if player is None or not getattr(player, "path", ""):
        return False, "vexp_need_video"
    rows = getattr(getattr(studio, "model", None), "_data", None) or []
    if not any(parse_srt_id(r.get("id", "")) for r in rows):
        return False, "vexp_need_srt_csv"
    return True, ""


def find_packed_srt(studio):
    """หา SRT ไทยที่ pack แล้ว: <video_stem>_TH.srt ข้างวิดีโอ → <csv_stem>_TH.srt ข้าง CSV"""
    player = getattr(studio, "player", None)
    vpath = getattr(player, "path", "") if player else ""
    cands = []
    if vpath:
        stem = os.path.splitext(vpath)[0]
        cands += [stem + "_TH.srt", os.path.join(os.path.dirname(vpath), os.path.basename(stem) + "_TH.srt")]
    csv_path = getattr(studio, "csv_path", "") or ""
    if csv_path:
        cands.append(os.path.splitext(csv_path)[0] + "_TH.srt")
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


def probe_duration_sec(ffmpeg_path, media_path):
    """ความยาวสื่อ (วินาที) ด้วย ffprobe ที่มาพร้อม build ของ ffmpeg — ใช้ตัดท้ายแบบ -t ของ hub"""
    ffprobe = os.path.join(os.path.dirname(os.path.abspath(ffmpeg_path)), "ffprobe")
    if not os.path.isfile(ffprobe):
        ffprobe = "ffprobe"
    try:
        r = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", media_path],
            capture_output=True, text=True, timeout=30,
            creationflags=0x08000000 if os.name == "nt" else 0)
        return float(r.stdout.strip())
    except Exception:
        return None


def build_ffmpeg_cmd(video_path, items, out_path, mode, srt_path=None, duration_sec=None):
    """ประกอบ argv ของ ffmpeg — filter graph ตาม make_videos_r1.sh ของ hub ทุกตัว

    items = [(start_ms, wav_path)] เรียงแล้ว · mode = 'dub' | 'mix'
    dub: ตัดเสียงเดิม + (ถ้ามี srt_path) ฝังเป็นแทร็ก mov_text language=tha
    mix: ต้นฉบับ ducking ผ่าน sidechaincompress (threshold .05 ratio 6 attack 25 release 350)
    """
    argv = ["-y", "-hide_banner", "-loglevel", "error", "-i", video_path]
    fparts, labels = [], []
    for i, (start_ms, wav) in enumerate(items, start=1):
        argv += ["-i", wav]
        fparts.append(
            f"[{i}:a]adelay={start_ms}|{start_ms},apad,"
            f"aformat=sample_rates=44100:channel_layouts=stereo[d{i}];")
        labels.append(f"[d{i}]")
    n = len(items)
    joined = "".join(labels)

    if mode == "dub":
        if srt_path:
            argv += ["-i", srt_path]
        argv += ["-filter_complex",
                 f"{''.join(fparts)}{joined}amix=inputs={n}:normalize=0,"
                 f"loudnorm=I=-16:TP=-1.5,aresample=44100[aout]",
                 "-map", "0:v", "-map", "[aout]"]
        if srt_path:
            argv += ["-map", f"{n + 1}:s",
                     "-c:s", "mov_text", "-metadata:s:s:0", "language=tha"]
    elif mode == "mix":
        argv += ["-filter_complex",
                 f"[0:a]aformat=sample_rates=44100:channel_layouts=stereo[orig];"
                 f"{''.join(fparts)}{joined}amix=inputs={n}:normalize=0,asplit=2[dubmix][dubkey];"
                 f"[orig][dubkey]sidechaincompress=threshold=0.05:ratio=6:attack=25:release=350[duck];"
                 f"[duck][dubmix]amix=inputs=2:duration=first:normalize=0,"
                 f"loudnorm=I=-16:TP=-1.5,aresample=44100[aout]",
                 "-map", "0:v", "-map", "[aout]"]
    else:
        raise ValueError(f"โหมดไม่รู้จัก: {mode}")

    argv += ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k"]
    if duration_sec:  # ตัดท้ายตามความยาววิดีโอ (แทน -t ที่ hub hardcode ไว้รอบ 1)
        argv += ["-t", f"{duration_sec:.3f}"]
    argv.append(out_path)
    return argv


class _ExportRunner(QThread):
    """รัน ffmpeg ในเธรด — done(ok, out_path|stderr_tail) · cancel() kill กระบวนการ"""
    done = pyqtSignal(bool, str)

    def __init__(self, argv, out_path):
        super().__init__()
        self._argv = argv
        self._out_path = out_path
        self._proc = None
        self._killed = False

    def run(self):
        try:
            self._proc = subprocess.Popen(
                self._argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=0x08000000 if os.name == "nt" else 0)
            _out, err = self._proc.communicate()
            ok = (not self._killed and self._proc.returncode == 0
                  and os.path.isfile(self._out_path))
            if ok:
                self.done.emit(True, self._out_path)
            else:
                tail = (err or b"").decode("utf-8", errors="ignore")[-600:]
                self.done.emit(False, tail or f"exit {self._proc.returncode}")
        except Exception as e:
            self.done.emit(False, str(e))

    def cancel(self):
        self._killed = True
        if self._proc and self._proc.poll() is None:
            self._proc.kill()


def output_path_for(video_path, mode):
    """<video_stem>_TH_dub.mp4 / _TH_mix.mp4 อยู่ข้างวิดีโอ (ตามชื่อไฟล์รอบ 1)"""
    stem = os.path.splitext(video_path)[0]
    return f"{stem}_TH_{mode}.mp4"


def export_dubbed_video(video_path, items, out_dir, mode, ffmpeg_path, parent=None,
                        srt_path=None, duration_sec=None):
    """สั่งทำวิดีโอพากย์ 1 โหมด — QThread + QProgressDialog (ยกเลิกได้) แล้ว block จนจบ

    คืน (ok, out_path | ข้อความ error) · out_dir ปล่อยว่าง = ข้างวิดีโอ
    """
    if not items:
        return False, "no items"
    if not ffmpeg_path or not os.path.isfile(ffmpeg_path):
        ffmpeg_path = "ffmpeg"
    if not duration_sec:
        duration_sec = probe_duration_sec(ffmpeg_path, video_path)

    out_path = (os.path.join(out_dir, os.path.basename(output_path_for(video_path, mode)))
                if out_dir else output_path_for(video_path, mode))

    argv = [ffmpeg_path] + build_ffmpeg_cmd(video_path, items, out_path, mode,
                                            srt_path=srt_path, duration_sec=duration_sec)

    runner = _ExportRunner(argv, out_path)
    loop = QEventLoop()
    result = {}

    def on_done(ok, msg):
        result["ok"], result["msg"] = ok, msg
        loop.quit()

    runner.done.connect(on_done)

    title = _("vexp_running_dub") if mode == "dub" else _("vexp_running_mix")
    prog = QProgressDialog(title, _("tts_cancel"), 0, 0, parent)
    prog.setWindowTitle(_("vexp_title"))
    prog.setWindowModality(Qt.WindowModality.WindowModal)
    prog.setMinimumDuration(300)
    prog.canceled.connect(lambda: (runner.cancel(), loop.quit()))
    runner.start()
    loop.exec()
    prog.cancel()
    prog.close()
    return result.get("ok", False), result.get("msg", "")
