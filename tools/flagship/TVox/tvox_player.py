# -*- coding: utf-8 -*-
"""tvox_player.py — Video player abstraction (backend pattern)

Backends:
  - MpvBackend      (python-mpv)     — หลักบน Windows/Linux (embed ใน Qt ผ่าน wid=)
  - QtPlayerBackend (QMediaPlayer)   — หลักบน macOS + fallback ทุกแพลตฟอร์ม

เหตุผล: python-mpv 1.x + libmpv 2.x SIGSEGV บน macOS ตอน constructor (signal จับไม่ได้)
จึงแยก player ออกจาก UI เป็น interface บาง ๆ — เมื่อ python-mpv แก้บั๊ก macOS
แก้ pick_backend() บรรทัดเดียว แล้ว mpv กลับมาเป็น backend หลักบน macOS ได้ทันที

Qt 6.5+ ใช้ FFmpeg backend บนทุกแพลตฟอร์ม → รองรับฟอร์แมตกว้าง (mp4/mkv/webm/avi/wav)
"""
import os
import sys

# ให้ mpv หา libmpv-2.dll ในโฟลเดอร์ TVox ได้ (Windows) — ต้อง set ก่อน import mpv
os.environ["PATH"] = os.path.dirname(os.path.abspath(__file__)) + os.pathsep + os.environ.get("PATH", "")

# ── Probe backends ตอน import (ถูก ๆ ไม่สร้าง instance) ──────────────────────

# macOS: ห้าม import mpv เด็ดขาด — SIGSEGV ใน constructor จับด้วย try/except ไม่ได้
MPV_DISABLED_ON_MACOS = sys.platform == 'darwin'

MPV_IMPORT_ERROR = None
_mpv_mod = None
if not MPV_DISABLED_ON_MACOS:
    try:
        import mpv as _mpv_mod
    except Exception as e:
        MPV_IMPORT_ERROR = str(e)
else:
    MPV_IMPORT_ERROR = ('Video player (mpv) disabled on macOS — known SIGSEGV '
                        'in python-mpv 1.x + libmpv 2.x')

QT_MEDIA_OK = False
try:
    from PyQt6.QtCore import Qt, QUrl
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PyQt6.QtMultimediaWidgets import QVideoWidget
    QT_MEDIA_OK = True
except Exception:
    pass


class PlayerBackend:
    """Interface ร่วม — TVox คุยกับ player ผ่านหน้านี้เท่านั้น

    Properties:
      position (float|None)  — วินาทีปัจจุบัน · set = seek absolute
      duration (float|None)  — ความยาววินาที (None = ยังไม่โหลด)
      path     (str|None)    — ไฟล์ที่โหลดอยู่
      paused   (bool)        · set ได้
      speed    (float)       · set ได้
    Methods:
      load(path, start_paused=False) · toggle_pause() · seek_relative(sec) · shutdown()
    """
    name = 'base'


class MpvBackend(PlayerBackend):
    """python-mpv — embed ใน Qt widget ผ่าน wid= (Windows/Linux)"""

    name = 'mpv'

    def __init__(self, host_widget=None):
        if _mpv_mod is None:
            raise RuntimeError(MPV_IMPORT_ERROR or 'mpv not importable')
        # osc=False เพราะเรามี UI คุมเอง · keep_open=True ค้างหน้าจอไว้ตอนจบไฟล์
        if host_widget is not None:
            self._mpv = _mpv_mod.MPV(wid=int(host_widget.winId()), osc=False,
                                      input_default_bindings=True,
                                      input_vo_keyboard=True, keep_open=True)
        else:
            self._mpv = _mpv_mod.MPV(osc=False, input_default_bindings=True,
                                     input_vo_keyboard=True, keep_open=True)

    @property
    def position(self):
        try:
            return self._mpv.time_pos
        except Exception:
            return None

    @position.setter
    def position(self, sec):
        self._mpv.time_pos = sec

    @property
    def duration(self):
        try:
            return getattr(self._mpv, 'duration', None)
        except Exception:
            return None

    @property
    def path(self):
        try:
            return getattr(self._mpv, 'path', None)
        except Exception:
            return None

    @property
    def paused(self):
        return bool(self._mpv.pause)

    @paused.setter
    def paused(self, val):
        self._mpv.pause = bool(val)

    @property
    def speed(self):
        return float(getattr(self._mpv, 'speed', 1.0) or 1.0)

    @speed.setter
    def speed(self, val):
        self._mpv.speed = val

    def load(self, path, start_paused=False):
        self._mpv.play(path)
        if start_paused:
            self._mpv.pause = True

    def toggle_pause(self):
        self._mpv.pause = not self._mpv.pause

    def seek_relative(self, sec):
        self._mpv.seek(sec, reference='relative')

    def shutdown(self):
        try:
            self._mpv.terminate()
        except Exception:
            pass


class QtPlayerBackend(PlayerBackend):
    """QMediaPlayer + QVideoWidget (Qt 6.5+ FFmpeg backend) — macOS หลัก / fallback"""

    name = 'qt'

    def __init__(self, parent=None):
        if not QT_MEDIA_OK:
            raise RuntimeError('PyQt6 QtMultimedia not available')
        self.video_widget = QVideoWidget(parent)
        self.video_widget.setMinimumSize(2, 2)
        self._media = QMediaPlayer(parent)
        self._audio = QAudioOutput(parent)
        self._media.setVideoOutput(self.video_widget)
        self._media.setAudioOutput(self._audio)
        self._current_path = None

    # --- properties (หน่วยวินาที ภายนอก · ms ภายใน) ---

    @property
    def position(self):
        if not self._current_path or self._media.duration() <= 0:
            return None
        return self._media.position() / 1000.0

    @position.setter
    def position(self, sec):
        self._media.setPosition(max(0, int(sec * 1000)))

    @property
    def duration(self):
        d = self._media.duration()
        return d / 1000.0 if d > 0 else None

    @property
    def path(self):
        return self._current_path

    @property
    def paused(self):
        return self._media.playbackState() == QMediaPlayer.PlaybackState.PausedState

    @paused.setter
    def paused(self, val):
        if val:
            self._media.pause()
        else:
            self._media.play()

    @property
    def speed(self):
        return float(self._media.playbackRate() or 1.0)

    @speed.setter
    def speed(self, val):
        self._media.setPlaybackRate(float(val))

    def load(self, path, start_paused=False):
        self._current_path = path
        self._media.setSource(QUrl.fromLocalFile(path))
        # pause() ต่อจาก setSource: Qt จะโหลด media เข้าสู่ paused state ให้เอง
        if start_paused:
            self._media.pause()
        else:
            self._media.play()

    def toggle_pause(self):
        if self._media.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._media.pause()
        else:
            self._media.play()

    def seek_relative(self, sec):
        self._media.setPosition(max(0, self._media.position() + int(sec * 1000)))

    def shutdown(self):
        try:
            self._media.stop()
        except Exception:
            pass
        # widget/audio output เป็นลูกของ parent — Qt จัดการ cleanup เอง


# ── Factory ──────────────────────────────────────────────────────────────────

def pick_backend():
    """เลือก backend ตามแพลตฟอร์ม:
    macOS → qt (mpv SIGSEGV) · อื่น ๆ → mpv ถ้า import ได้ · fallback → qt เสมอ
    เมื่อ python-mpv แก้บั๊ก macOS แล้ว ลบ branch แรกออก mpv กลับมาเป็นหลักบน macOS"""
    if MPV_DISABLED_ON_MACOS:
        return 'qt' if QT_MEDIA_OK else None
    if _mpv_mod is not None:
        return 'mpv'
    return 'qt' if QT_MEDIA_OK else None


def create_player(host_widget=None, parent=None):
    """สร้าง backend ตามแพลตฟอร์ม · คืน (backend|None, error_msg|None)

    host_widget: QWidget สำหรับ embed วิดีโอ (mpv ใช้ winId · qt มี video_widget ของตัวเอง)
    parent: QObject parent (Qt ownership สำหรับ backend ฝั่ง Qt)
    mpv init พัง (เช่น dll หาย) → fallback เป็น Qt อัตโนมัติ พร้อม error ให้ UI แจ้ง
    """
    choice = pick_backend()
    if choice == 'mpv':
        try:
            return MpvBackend(host_widget=host_widget), None
        except Exception as e:
            if QT_MEDIA_OK:
                return QtPlayerBackend(parent=parent), f'mpv-init-failed: {e}'
            return None, str(e)
    if choice == 'qt':
        return QtPlayerBackend(parent=parent), None
    return None, (MPV_IMPORT_ERROR or 'no video backend available '
                                      '(mpv missing · QtMultimedia missing)')
