import sys
import os

# TV-C5: sys.path MUST be set up before any local imports
flagship_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(flagship_dir, 'Core'))
sys.path.append(os.path.join(flagship_dir, 'TStudio'))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tvox_i18n import _

import csv
import shutil
import time
from tvox_recorder import TVoxRecorder

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSplitter, QFileDialog, QMessageBox,
    QSlider, QLabel, QComboBox, QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

# Prepend TVox dir to PATH so libmpv-2.dll is found automatically
os.environ["PATH"] = os.path.dirname(os.path.abspath(__file__)) + os.pathsep + os.environ["PATH"]

# macOS: python-mpv 1.x + libmpv 2.x SIGSEGV at mpv_set_option — ปิดชั่วคาว (video player ใช้ไม่ได้ แต่ STT/TTS/แปล AI ใช้ได้ครบ)
import platform as _platform
try:
    import mpv
    MPV_AVAILABLE = _platform.system() != 'Darwin'
    MPV_ERROR = '' if MPV_AVAILABLE else 'Video player (mpv) disabled on macOS — known SIGSEGV in python-mpv 1.x + libmpv 2.x. STT/TTS/AI translate work normally.'
except OSError as e:
    MPV_AVAILABLE = False
    MPV_ERROR = str(e)
except Exception as e:
    MPV_AVAILABLE = False
    MPV_ERROR = str(e)

# Import TranslationStudio to inherit all its AI/Glossary/Table features!
try:
    from tstudio_app import TranslationStudio
    HAS_TSTUDIO = True
except ImportError as e:
    HAS_TSTUDIO = False
    print(f"Failed to import TStudio: {e}")

if HAS_TSTUDIO:
    class TVoxApp(TranslationStudio):
        # TV-C4: Signals to safely route MPV callbacks to Qt UI thread
        time_pos_updated = pyqtSignal(float)
        duration_updated = pyqtSignal(float)
        def __init__(self, project_path=None):
            super().__init__(project_path=project_path)
            self.setWindowTitle(_("window_title"))
            self.setGeometry(100, 100, 1400, 900)

            # Window & Taskbar Icon
            from PyQt6.QtGui import QIcon
            tvox_ico = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "TVox.ico"))
            if not os.path.exists(tvox_ico):
                tvox_ico = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "TVox.png"))
            if os.path.exists(tvox_ico):
                self.setWindowIcon(QIcon(tvox_ico))

            # --- Internal State ---
            self.is_user_seeking = False
            self.mark_a = None
            self.mark_b = None
            self.loop_active = False

            # 1. TStudio is now fully dock-based, no central widget to detach
            
            # 2. Create DockWidget for Video
            from PyQt6.QtWidgets import QDockWidget, QMainWindow
            self.video_dock = QDockWidget(_("dock_video_player"), self)
            self.video_dock.setAllowedAreas(Qt.DockWidgetArea.TopDockWidgetArea | Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
            self.video_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetFloatable | QDockWidget.DockWidgetFeature.DockWidgetMovable)
            self.setDockOptions(self.dockOptions() | QMainWindow.DockOption.AllowNestedDocks)

            # --- DUBBING STUDIO DOCK ---
            self.dubbing_dock = QDockWidget("🎙️ Dubbing Studio", self)
            self.dubbing_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
            self.dubbing_container = QWidget()
            self.dubbing_layout = QVBoxLayout(self.dubbing_container)
            
            # Progress bar
            self.lbl_dub_progress = QLabel("Project Progress: 0%")
            self.dubbing_layout.addWidget(self.lbl_dub_progress)
            self.dub_progress = QProgressBar()
            self.dubbing_layout.addWidget(self.dub_progress)
            
            # Action Buttons
            self.dub_btn_layout = QHBoxLayout()
            self.btn_play_original = QPushButton("▶️ Play Original")
            self.btn_record = QPushButton("🎙️ Record")
            self.btn_stop = QPushButton("⏹️ Stop")
            self.btn_inject = QPushButton("📦 Inject to Game")
            self.btn_stop.setEnabled(False)
            
            self.dub_btn_layout.addWidget(self.btn_play_original)
            self.dub_btn_layout.addWidget(self.btn_record)
            self.dub_btn_layout.addWidget(self.btn_stop)
            self.dub_btn_layout.addWidget(self.btn_inject)
            self.dubbing_layout.addLayout(self.dub_btn_layout)
            
            # Dubbing Table
            self.dub_table = QTableWidget()
            self.dub_table.setColumnCount(5)
            self.dub_table.setHorizontalHeaderLabels(["ID", "Status", "Duration", "Original", "Dubbed"])
            self.dub_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            self.dub_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.dub_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
            self.dub_table.setAcceptDrops(True)
            self.dub_table.viewport().installEventFilter(self)
            self.dubbing_layout.addWidget(self.dub_table)
            
            self.dubbing_dock.setWidget(self.dubbing_container)
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dubbing_dock)
            
            # Initialize Recorder
            self.recorder = TVoxRecorder()
            self.current_dub_id = None
            
            # Connect signals
            self.btn_play_original.clicked.connect(self.play_original_audio)
            self.btn_record.clicked.connect(self.start_dub_recording)
            self.btn_stop.clicked.connect(self.stop_dub_recording)
            self.btn_inject.clicked.connect(self.inject_dubbed_audio)
            self.dub_table.itemSelectionChanged.connect(self.on_dub_table_selection)
            
            # Load Dubbing Data
            QTimer.singleShot(500, self.load_dubbing_tracking)
            
            # 4. Build Video Player
            self.video_container = QWidget()
            self.video_container.setStyleSheet("background-color: black;")
            self.video_layout = QVBoxLayout(self.video_container)
            self.video_layout.setContentsMargins(0,0,0,0)
            self.video_layout.setSpacing(0)
            
            self.video_widget = QWidget()
            self.video_widget.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors)
            self.video_widget.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
            self.video_widget.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
            self.video_widget.installEventFilter(self)
            self.video_layout.addWidget(self.video_widget, stretch=1)
            
            # --- Subtitle Overlay ---
            self.lbl_subtitle = QLabel(self.video_container)
            self.lbl_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lbl_subtitle.setWordWrap(True)
            self.lbl_subtitle.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 32px;
                    font-weight: bold;
                    background-color: transparent;
                    /* Basic shadow effect */
                    text-shadow: 2px 2px 4px #000000;
                }
            """)
            # Create a simple drop shadow effect
            from PyQt6.QtWidgets import QGraphicsDropShadowEffect
            shadow = QGraphicsDropShadowEffect(self.lbl_subtitle)
            shadow.setBlurRadius(8)
            shadow.setColor(Qt.GlobalColor.black)
            shadow.setOffset(2, 2)
            self.lbl_subtitle.setGraphicsEffect(shadow)
            self.lbl_subtitle.setText("") # Start empty
            self.lbl_subtitle.hide()

            # --- Timeline & Controls Panel (Compact Mode) ---
            self.panel_widget = QWidget()
            self.panel_widget.setStyleSheet("background-color: #1e1e2e;")
            panel_layout = QHBoxLayout(self.panel_widget)
            panel_layout.setContentsMargins(5, 5, 5, 5)
            panel_layout.setSpacing(5)

            # Playback Controls
            self.btn_open_video = QPushButton("\U0001f4c2")
            self.btn_open_video.setToolTip(_("tooltip_open_video"))
            self.btn_open_video.clicked.connect(self.open_video)
            self.btn_open_video.setStyleSheet("background: transparent; font-family: 'Segoe UI Symbol', 'Segoe UI Emoji', sans-serif; font-size: 16px; border: none;")
            
            self.btn_seek_m1 = QPushButton("-1s")
            self.btn_seek_m1.setToolTip(_("tooltip_seek_m1"))
            self.btn_seek_m1.clicked.connect(lambda: self.seek_relative(-1.0))
            self.btn_seek_m1.setStyleSheet("background: transparent; color: #a6adc8; border: none;")
            
            self.btn_seek_m01 = QPushButton("-.1s")
            self.btn_seek_m01.setToolTip(_("tooltip_seek_m01"))
            self.btn_seek_m01.clicked.connect(lambda: self.seek_relative(-0.1))
            self.btn_seek_m01.setStyleSheet("background: transparent; color: #a6adc8; border: none;")
            
            self.btn_play_pause = QPushButton("\u25b6")
            self.btn_play_pause.setToolTip(_("tooltip_play_pause"))
            self.btn_play_pause.clicked.connect(self.toggle_play)
            self.btn_play_pause.setStyleSheet("background: transparent; color: #a6e3a1; font-family: 'Segoe UI Symbol', 'Segoe UI Emoji', sans-serif; font-weight: bold; font-size: 18px; border: none;")
            
            self.btn_seek_p01 = QPushButton("+.1s")
            self.btn_seek_p01.setToolTip(_("tooltip_seek_p01"))
            self.btn_seek_p01.clicked.connect(lambda: self.seek_relative(0.1))
            self.btn_seek_p01.setStyleSheet("background: transparent; color: #a6adc8; border: none;")
            
            self.btn_seek_p1 = QPushButton("+1s")
            self.btn_seek_p1.setToolTip(_("tooltip_seek_p1"))
            self.btn_seek_p1.clicked.connect(lambda: self.seek_relative(1.0))
            self.btn_seek_p1.setStyleSheet("background: transparent; color: #a6adc8; border: none;")
            
            self.cbo_speed = QComboBox()
            self.cbo_speed.addItems(["0.5x", "0.75x", "1.0x", "1.25x", "1.5x"])
            self.cbo_speed.setCurrentText("1.0x")
            self.cbo_speed.currentTextChanged.connect(self.change_speed)
            self.cbo_speed.setStyleSheet("background: transparent; color: #a6adc8; border: none;")
            
            panel_layout.addWidget(self.btn_open_video)
            panel_layout.addWidget(self.btn_seek_m1)
            panel_layout.addWidget(self.btn_seek_m01)
            panel_layout.addWidget(self.btn_play_pause)
            panel_layout.addWidget(self.btn_seek_p01)
            panel_layout.addWidget(self.btn_seek_p1)
            panel_layout.addWidget(self.cbo_speed)
            
            # Waveform
            from tvox_waveform import WaveformWidget, AudioExtractorWorker
            from ffmpeg_utils import ensure_ffmpeg
            
            self.lbl_time_curr = QLabel(_("time_default"))
            self.lbl_time_curr.setStyleSheet("color: #a6adc8; font-family: monospace; font-size: 11px;")
            
            self.waveform = WaveformWidget()
            self.waveform.seek_requested.connect(self.on_waveform_seek)
            self.waveform.installEventFilter(self)
            
            self.lbl_time_total = QLabel(_("time_default"))
            self.lbl_time_total.setStyleSheet("color: #a6adc8; font-family: monospace; font-size: 11px;")
            
            panel_layout.addWidget(self.lbl_time_curr)
            panel_layout.addWidget(self.waveform, stretch=1)
            panel_layout.addWidget(self.lbl_time_total)
            
            # Loop Controls
            self.btn_mark_a = QPushButton(_("btn_mark_a"))
            self.btn_mark_a.setToolTip(_("tooltip_mark_a"))
            self.btn_mark_a.clicked.connect(self.set_mark_a)
            self.btn_mark_a.setStyleSheet("background: transparent; border: 1px solid #cba6f7; color: #cba6f7; font-weight: bold; padding: 2px 6px; border-radius: 4px;")
            
            self.btn_mark_b = QPushButton(_("btn_mark_b"))
            self.btn_mark_b.setToolTip(_("tooltip_mark_b"))
            self.btn_mark_b.clicked.connect(self.set_mark_b)
            self.btn_mark_b.setStyleSheet("background: transparent; border: 1px solid #f38ba8; color: #f38ba8; font-weight: bold; padding: 2px 6px; border-radius: 4px;")
            
            self.btn_loop = QPushButton("\U0001f501")
            self.btn_loop.setToolTip(_("tooltip_loop"))
            self.btn_loop.clicked.connect(self.toggle_loop)
            self.btn_loop.setStyleSheet("background: #45475a; color: #cdd6f4; font-weight: bold; padding: 4px; border-radius: 4px;")
            
            panel_layout.addWidget(self.btn_mark_a)
            panel_layout.addWidget(self.btn_mark_b)
            panel_layout.addWidget(self.btn_loop)

            # Whisper ถอดเสียงเป็นซับร่าง (spec-vox-whisper.md Phase S2) — ผ่าน thaistt CLI
            self.btn_stt = QPushButton("\U0001f9ec")
            self.btn_stt.setToolTip(_("stt_btn_tooltip"))
            self.btn_stt.setStyleSheet("background: transparent; color: #89b4fa; font-size: 15px; border: none; padding: 2px;")
            self.btn_stt.clicked.connect(self.open_stt_dialog)
            panel_layout.addWidget(self.btn_stt)
            self.refresh_stt_btn_state()

            # AI TTS พากย์อัตโนมัติ (spec-ai-dubbing.md เฟส 1)
            self.btn_tts = QPushButton("🎙️")
            self.btn_tts.setToolTip(_("tts_btn_tooltip"))
            self.btn_tts.setStyleSheet("background: transparent; color: #f5c2e7; font-size: 15px; border: none; padding: 2px;")
            self.btn_tts.clicked.connect(self.open_tts_dialog)
            panel_layout.addWidget(self.btn_tts)

            self.video_layout.addWidget(self.panel_widget)
            
            self.video_dock.setWidget(self.video_container)

            # 5. Add Dock Widget to Top
            self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self.video_dock)
            
            # Ensure it has a reasonable starting size
            self.video_container.setMinimumHeight(300)
            # Try to force the dock to take half the height initially (window is 900 tall)
            self.resizeDocks([self.video_dock], [450], Qt.Orientation.Vertical)

            # 6. Initialize MPV and Timer
            self.player = None
            self.init_mpv()

            # TV-C4: Connect signals to UI slot methods
            self.time_pos_updated.connect(self._on_time_pos_ui)
            self.duration_updated.connect(self._on_duration_ui)

            self.update_timer = QTimer(self)
            self.update_timer.setInterval(30) # ~33fps updates
            self.update_timer.timeout.connect(self.update_ui_from_mpv)
            self.update_timer.start()

            # 7. Hook into TStudio's table row selection
            self.table.selectionModel().currentChanged.connect(self.on_tvox_row_selected)

            # 8. Context menu เล่นเสียง TTS รายแถว (คลิกขวา)
            self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.table.customContextMenuRequested.connect(self._on_table_context_menu)
            self._tts_play_proc = None
            self._tts_playing_row = -1

            # Set initial title with profile
            # TV-W4: Pass the actual profile name into the format string
            active = getattr(self, '_profiles_data', {}).get("active_preset", "Default")
            self.setWindowTitle(_("window_title_profile").format(active=active))
            
            # Override TStudio's large minimum size to allow DockWidget to expand
            self.setMinimumSize(1000, 600)
            
            # Focus video widget by default so Spacebar works immediately
            self.video_widget.setFocus()
            
            # 8. Check Requirements on Startup
            QTimer.singleShot(500, self.check_requirements)

        def check_requirements(self):
            if not MPV_AVAILABLE:
                if sys.platform == "darwin":
                    # macOS: ปิด mpv ชั่วคราว (SIGSEGV) — แจ้งแบบ info ไม่ต้อง dll
                    QMessageBox.information(self, _("dlg_mpv_missing_title"), _("tvox_mpv_macos_info"))
                else:
                    msg = f"MPV Engine ไม่พร้อมใช้งาน!\n\nโปรดดาวน์โหลดไฟล์ libmpv-2.dll และนำมาวางไว้ที่:\n{os.path.dirname(__file__)}\n\nรายละเอียด Error:\n{MPV_ERROR}"
                    QMessageBox.warning(self, _("dlg_mpv_missing_title"), msg)

        def on_profile_changed(self, text):
            super().on_profile_changed(text)
            self.setWindowTitle(f"TVox - FMV Modding Studio [{text}]")

        def init_mpv(self):
            if not MPV_AVAILABLE:
                return

            try:
                # macOS: wid= ส่ง NSView pointer ที่ libmpv ไม่รองรับ → SIGSEGV
                # แก่โดยไม่ embed ใน Qt widget บน macOS (mpv เปิดหน้าต่างของตัวเองแทน)
                if sys.platform == 'darwin':
                    self.player = mpv.MPV(osc=False, input_default_bindings=True, input_vo_keyboard=True, keep_open=True)
                else:
                    # osc=False because we built our own UI now!
                    self.player = mpv.MPV(wid=int(self.video_widget.winId()), osc=False, input_default_bindings=True, input_vo_keyboard=True, keep_open=True)
            except Exception as e:
                QMessageBox.critical(self, _("dlg_mpv_init_error_title"), _("dlg_mpv_init_error_msg"))

        # --- MPV UI UPDATE LOGIC ---
        def resizeEvent(self, event):
            super().resizeEvent(event)
            if hasattr(self, 'lbl_subtitle'):
                # Position subtitle at bottom center of video_container
                w = self.video_container.width()
                h = self.video_container.height()
                lbl_w = w - 40 # 20px padding on each side
                lbl_h = 100 # ample height for 2-3 lines
                self.lbl_subtitle.setGeometry(20, h - lbl_h - 20, lbl_w, lbl_h)

        def eventFilter(self, obj, event):
            # Handle Drag & Drop on dub_table
            if hasattr(self, 'dub_table') and obj == self.dub_table.viewport():
                if event.type() == event.Type.DragEnter:
                    if event.mimeData().hasUrls():
                        event.acceptProposedAction()
                        return True
                elif event.type() == event.Type.Drop:
                    urls = event.mimeData().urls()
                    if urls and urls[0].isLocalFile():
                        filepath = urls[0].toLocalFile()
                        if filepath.lower().endswith('.wav'):
                            # Find which row was dropped on
                            pos = event.position().toPoint()
                            item = self.dub_table.itemAt(pos)
                            if item:
                                row = item.row()
                                audio_id = self.dub_table.item(row, 0).text()
                                self.handle_dropped_wav(audio_id, filepath)
                        event.acceptProposedAction()
                        return True
                        
            if event.type() == event.Type.KeyPress:
                is_target = (obj == self.video_widget) or (hasattr(self, 'waveform') and obj == self.waveform)
                if is_target and event.key() == Qt.Key.Key_Space:
                    self.toggle_play()
                    return True
            return super().eventFilter(obj, event)

        def format_time(self, seconds):
            if seconds is None: return _("time_default")
            m = int(seconds // 60)
            s = int(seconds % 60)
            ms = int((seconds % 1) * 1000)
            return f"{m:02d}:{s:02d}.{ms:03d}"

        def _on_time_pos_ui(self, pos):
            """TV-C4: Slot called via pyqtSignal to safely update time UI."""
            self.lbl_time_curr.setText(self.format_time(pos))

        def _on_duration_ui(self, dur):
            """TV-C4: Slot called via pyqtSignal to safely update duration UI."""
            self.lbl_time_total.setText(self.format_time(dur))

        def update_ui_from_mpv(self):
            # TV-C3: Wrap entire body in try-except — player may be destroyed
            try:
                if not self.player or not hasattr(self.player, 'time_pos') or self.player.time_pos is None:
                    return

                pos = self.player.time_pos

                # TV-W1: Guard duration access
                duration = getattr(self.player, 'duration', None)
                if duration is None:
                    return
                dur = duration if duration > 0 else 1.0

                # TV-C4: Emit signals instead of touching UI directly
                self.time_pos_updated.emit(pos)
                self.duration_updated.emit(dur)

                # Update Waveform
                if not getattr(self.waveform, 'is_dragging', False):
                    self.waveform.update_position(pos, dur)

                # Subtitle Sync
                if hasattr(self, 'lbl_subtitle') and hasattr(self, 'subtitle_timing'):
                    active_text = ""
                    active_row_id = None
                    for timing in self.subtitle_timing:
                        if timing["start"] <= pos <= timing["end"]:
                            active_row_id = timing["row_id"]
                            break

                    if active_row_id is not None and hasattr(self, 'model'):
                        # Find the text in the table model by matching row_id to col 0
                        # For performance, could cache row index, but this is fast enough for small sets
                        for row in self.model._data:
                            if str(row[0]) == active_row_id:
                                # Use Translation (col 3) if available, else Source (col 2)
                                active_text = row[3] if len(row) > 3 and str(row[3]).strip() else row[2]
                                break

                    if active_text:
                        if self.lbl_subtitle.text() != active_text:
                            self.lbl_subtitle.setText(active_text)
                        if self.lbl_subtitle.isHidden():
                            self.lbl_subtitle.show()
                            self.lbl_subtitle.raise_()
                    else:
                        if not self.lbl_subtitle.isHidden():
                            self.lbl_subtitle.hide()

                # Handle A-B Looping
                if self.loop_active and self.mark_a is not None and self.mark_b is not None:
                    if self.mark_a < self.mark_b:
                        if pos >= self.mark_b:
                            if not getattr(self, 'is_loop_seeking', False):
                                try:
                                    self.is_loop_seeking = True
                                    self.player.time_pos = self.mark_a
                                except Exception:
                                    pass
                        elif pos < self.mark_b - 0.2:
                            self.is_loop_seeking = False

            except Exception:
                pass  # TV-C3: player may be destroyed during shutdown

        # --- UI ACTIONS ---
        def on_waveform_seek(self, target_sec):
            if self.player:
                self.lbl_time_curr.setText(self.format_time(target_sec))
                try:
                    self.player.time_pos = target_sec
                except Exception as e:
                    print(f"Seek error: {e}")

        def _load_csv(self):
            # Let TStudio logic load the self.csv_path into self.model._data
            super()._load_csv()
            
            # Parse subtitle timings
            self.subtitle_timing = []
            if hasattr(self, 'csv_path') and self.csv_path:
                try:
                    import json, os
                    base_dir = os.path.dirname(self.csv_path)
                    json_path = os.path.join(base_dir, f"{os.path.basename(self.csv_path).replace('.csv', '')}_meta.json")
                    if os.path.exists(json_path):
                        with open(json_path, 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                            for row_id, data in meta.get("original_data", {}).items():
                                ts_str = data.get("timestamp", "")
                                if "-->" in ts_str:
                                    parts = ts_str.split("-->")
                                    if len(parts) == 2:
                                        start_str = parts[0].strip().replace(',', '.')
                                        end_str = parts[1].strip().replace(',', '.')
                                        
                                        def parse_time(t_str):
                                            t_parts = t_str.split(':')
                                            if len(t_parts) == 3:
                                                h, m, s = t_parts
                                                return int(h)*3600 + int(m)*60 + float(s)
                                            return 0.0
                                            
                                        start_sec = parse_time(start_str)
                                        end_sec = parse_time(end_str)
                                        self.subtitle_timing.append({
                                            "row_id": str(row_id),
                                            "start": start_sec,
                                            "end": end_sec
                                        })
                except Exception as e:
                    print(f"Failed to load subtitle timing metadata: {e}")

        # ─────────── Whisper ถอดเสียงเป็นซับ (spec-vox-whisper.md Phase S2) ───────────

        def refresh_stt_btn_state(self):
            """ปุ่ม STT เปิดก็ต่อเมื่อตั้ง stt_cli_path — ไม่ตั้ง → disabled + tooltip แนะนำ"""
            from tstudio_core import TStudioCore
            from tvox_stt import find_stt_cli
            try:
                cli = find_stt_cli(TStudioCore.load_config())
            except Exception:
                cli = None
            self.btn_stt.setEnabled(cli is not None)
            self.btn_stt.setToolTip(_("stt_btn_tooltip") if cli else _("stt_btn_disabled_tooltip"))

        def changeEvent(self, event):
            """รีเฟรชสถานะปุ่ม STT ทุกครั้งที่หน้าต่างกลับมา active (เช่นปิด Settings แล้ว)"""
            super().changeEvent(event)
            if event.type() == event.Type.WindowActivate and hasattr(self, "btn_stt"):
                self.refresh_stt_btn_state()

        # ─────────── AI TTS พากย์อัตโนมัติ (spec-ai-dubbing.md เฟส 1) ───────────

        def open_tts_dialog(self):
            from PyQt6.QtWidgets import QDialog, QFormLayout, QComboBox, QDialogButtonBox
            from tstudio_core import TStudioCore
            from tvox_tts import VOICES, DEFAULT_VOICE

            cfg = TStudioCore.load_config()
            dlg = QDialog(self)
            dlg.setWindowTitle(_("tts_dialog_title"))
            form = QFormLayout(dlg)

            # เลือกเสียง
            self.cbo_tts_voice = QComboBox()
            voice_labels = {"premwadee": _("tts_voice_premwadee"), "niwat": _("tts_voice_niwat")}
            for vid, vcode in VOICES.items():
                self.cbo_tts_voice.addItem(voice_labels.get(vid, vid), vcode)
            cur_voice = cfg.get("tts_voice", DEFAULT_VOICE)
            for i in range(self.cbo_tts_voice.count()):
                if self.cbo_tts_voice.itemData(i) == cur_voice:
                    self.cbo_tts_voice.setCurrentIndex(i)
                    break
            form.addRow(_("tts_voice_label"), self.cbo_tts_voice)

            # ความเร็วพูด
            self.cbo_tts_rate = QComboBox()
            self.cbo_tts_rate.addItems(["+0%", "-10%", "-20%", "+10%", "+20%"])
            self.cbo_tts_rate.setCurrentText(cfg.get("tts_rate", "+0%"))
            form.addRow(_("tts_rate_label"), self.cbo_tts_rate)

            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            buttons.accepted.connect(dlg.accept)
            buttons.rejected.connect(dlg.reject)
            form.addRow(buttons)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return

            voice = self.cbo_tts_voice.currentData()
            rate = self.cbo_tts_rate.currentText()
            self._start_tts_batch(voice, rate)

        def _start_tts_batch(self, voice, rate):
            """พากย์ทุกแถวที่มีคำแปล → WAV รายแถว → ไฟล์ผสม"""
            from PyQt6.QtWidgets import QProgressDialog, QMessageBox
            from tvox_tts import generate_tts, find_edge_tts, mix_with_ducking
            from tstudio_core import TStudioCore
            from ffmpeg_utils import get_ffmpeg_path

            cli = find_edge_tts()
            if not cli:
                QMessageBox.warning(self, _("tts_dialog_title"), _("tts_need_install"))
                return

            rows = [(i, r) for i, r in enumerate(self.model._data) if (r.get("trans") or "").strip()]
            if not rows:
                QMessageBox.information(self, _("tts_dialog_title"), _("tts_no_translations"))
                return

            ff = get_ffmpeg_path()
            if not ff:
                QMessageBox.warning(self, _("tts_dialog_title"), _("tts_need_ffmpeg"))
                return

            # บันทึก settings
            try:
                cfg = TStudioCore.load_config()
                cfg["tts_voice"] = voice
                cfg["tts_rate"] = rate
                TStudioCore.save_config(cfg)
            except Exception:
                pass

            out_dir = os.path.join(os.path.dirname(getattr(self, 'csv_path', '.') or '.'), "tts_output")
            os.makedirs(out_dir, exist_ok=True)

            prog = QProgressDialog(_("tts_generating", n=0, total=len(rows)), _("tts_cancel"), 0, len(rows), self)
            prog.setWindowTitle(_("tts_dialog_title"))
            prog.setMinimumDuration(200)
            prog.setWindowModality(Qt.WindowModality.WindowModal)
            self._tts_cancelled = False

            success = 0
            wav_files = []
            for idx, (row_i, row) in enumerate(rows):
                if self._tts_cancelled:
                    break
                app.processEvents()
                text = row.get("trans", "").strip()
                row_id = row.get("id", f"row_{row_i}")
                wav_path = os.path.join(out_dir, f"{row_id}.wav")
                prog.setLabelText(_("tts_generating_row", n=idx + 1, total=len(rows), text=text[:40]))
                prog.setValue(idx)

                ok, err = generate_tts(text, voice, wav_path, rate=rate, ffmpeg_path=ff)
                if ok:
                    success += 1
                    wav_files.append((row_i, wav_path))
                else:
                    print(f"TTS row {row_id}: {err}")

            prog.setValue(len(rows))
            prog.close()

            if self._tts_cancelled:
                QMessageBox.information(self, _("tts_dialog_title"), _("tts_cancelled"))
                return
            if success == 0:
                QMessageBox.warning(self, _("tts_dialog_title"), _("tts_all_failed"))
                return

            # ผสมไฟล์และเปิดใน player ถ้ามีไฟล์ต้นฉบับเปิดอยู่
            has_original = False
            try:
                has_original = bool(self.player and getattr(self.player, 'path', None))
            except Exception:
                pass

            if has_original and wav_files:
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                try:
                    first_wav = wav_files[0][1]
                    mix_out = os.path.join(out_dir, "_preview_mix.wav")
                    ok_mix, err_mix = mix_with_ducking(
                        getattr(self.player, 'path', ''), first_wav, mix_out, ff)
                    QApplication.restoreOverrideCursor()
                    if ok_mix:
                        self.player.loadfile(mix_out)
                except Exception:
                    QApplication.restoreOverrideCursor()

            self.statusBar().showMessage(
                _("tts_done_status", n=success, total=len(rows), dir=os.path.basename(out_dir)), 6000)
            QMessageBox.information(
                self, _("tts_dialog_title"),
                _("tts_done_msg", n=success, total=len(rows)) + "\n\n" + _("tts_output_dir", dir=out_dir))

        # ─────────── เล่นเสียง TTS รายแถว (context menu คลิกขวา) ───────────

        def _tts_wav_for_row(self, source_row):
            """หาไฟล์ WAV ของแถวจาก tts_output/ — ชื่อตาม ID ใน CSV"""
            if not hasattr(self, 'csv_path') or not self.csv_path:
                return None
            out_dir = os.path.join(os.path.dirname(os.path.abspath(self.csv_path)), "tts_output")
            row = self.model._data[source_row] if 0 <= source_row < len(self.model._data) else None
            if not row:
                return None
            row_id = row.get("id", f"row_{source_row}")
            wav = os.path.join(out_dir, f"{row_id}.wav")
            return wav if os.path.isfile(wav) else None

        def _on_table_context_menu(self, pos):
            from PyQt6.QtWidgets import QMenu
            index = self.table.indexAt(pos)
            if not index.isValid():
                return
            source_idx = self.proxy.mapToSource(index)
            row = source_idx.row()

            menu = QMenu(self)
            wav = self._tts_wav_for_row(row)
            if wav:
                if self._tts_playing_row == row and self._tts_play_proc:
                    act = menu.addAction(_("tts_stop_row"))
                    act.triggered.connect(lambda: self._stop_tts_play())
                else:
                    act = menu.addAction(_("tts_play_row"))
                    act.triggered.connect(lambda: self._play_tts_row(row, wav))
            else:
                act = menu.addAction(_("tts_no_wav"))
                act.setEnabled(False)
            menu.exec(self.table.viewport().mapToGlobal(pos))

        def _play_tts_row(self, row, wav_path):
            """เล่น WAV ของแถว + highlight แถวในตาราง"""
            self._stop_tts_play()

            import subprocess
            try:
                if sys.platform == "darwin":
                    self._tts_play_proc = subprocess.Popen(
                        ["afplay", wav_path],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    self._tts_play_proc = subprocess.Popen(
                        ["start", "/b", wav_path], shell=True,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                return

            self._tts_playing_row = row
            # highlight แถวที่กำลังเล่น
            proxy_idx = self.proxy.mapFromSource(self.model.index(row, 0))
            if proxy_idx.isValid():
                self.table.selectRow(proxy_idx.row())

            # เมื่อเล่นจบ → เคลียร์สถานะ
            from PyQt6.QtCore import QTimer
            def _on_done():
                if self._tts_play_proc and self._tts_play_proc.poll() is None:
                    QTimer.singleShot(200, _on_done)
                    return
                self._tts_play_proc = None
                self._tts_playing_row = -1
            QTimer.singleShot(500, _on_done)

        def _stop_tts_play(self):
            """หยุดเล่นเสียง"""
            if self._tts_play_proc:
                try:
                    self._tts_play_proc.terminate()
                    self._tts_play_proc.wait(2)
                except Exception:
                    pass
                self._tts_play_proc = None
            self._tts_playing_row = -1

        def open_stt_dialog(self):
            from PyQt6.QtWidgets import QDialog, QFormLayout, QComboBox, QDialogButtonBox
            from tstudio_core import TStudioCore
            from tvox_stt import find_stt_cli, ab_range, LANGS, MEDIA_EXTS

            cli = find_stt_cli(TStudioCore.load_config())
            if not cli:
                QMessageBox.information(self, _("stt_need_setup_title"), _("stt_need_setup_msg"))
                return

            dlg = QDialog(self)
            dlg.setWindowTitle(_("stt_dialog_title"))
            form = QFormLayout(dlg)

            # แหล่ง: ไฟล์ที่เปิดอยู่ในเครื่องเล่น หรือเลือกไฟล์ใหม่
            playing = None
            try:
                playing = self.player.path if (self.player and getattr(self.player, "path", None)) else None
            except Exception:
                playing = None
            self.cbo_stt_source = QComboBox()
            if playing:
                self.cbo_stt_source.addItem(_("stt_source_current", name=os.path.basename(playing)), playing)
            self.cbo_stt_source.addItem(_("stt_source_pick"), "__pick__")
            if not playing:
                self.cbo_stt_source.setCurrentIndex(len(self.cbo_stt_source) - 1)
            form.addRow(_("stt_source"), self.cbo_stt_source)

            # ช่วงเวลา: ทั้งไฟล์ หรือ A–B ตามตำแหน่งเครื่องเล่นที่ mark ไว้
            self.cbo_stt_range = QComboBox()
            self.cbo_stt_range.addItem(_("stt_range_full"), None)
            rab = ab_range(self.mark_a, self.mark_b)
            if rab:
                self.cbo_stt_range.addItem(_("stt_range_ab", a=self.format_time(self.mark_a), b=self.format_time(self.mark_b)), rab)
            form.addRow(_("stt_range"), self.cbo_stt_range)

            self.cbo_stt_lang = QComboBox()
            self.cbo_stt_lang.addItems(list(LANGS))
            form.addRow(_("stt_lang"), self.cbo_stt_lang)

            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            buttons.accepted.connect(dlg.accept)
            buttons.rejected.connect(dlg.reject)
            form.addRow(buttons)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return

            media = self.cbo_stt_source.currentData()
            if media == "__pick__":
                flt = _("stt_media_filter", exts=" ".join("*" + e for e in MEDIA_EXTS))
                media, _sel = QFileDialog.getOpenFileName(self, _("stt_source_pick"), "", flt)
            if not media or media == "__pick__":
                return

            out_srt = __import__("tvox_stt").draft_path_for(media)
            if os.path.exists(out_srt):
                reply = QMessageBox.question(self, _("stt_dialog_title"),
                                             _("stt_overwrite_confirm", file=os.path.basename(out_srt)),
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply != QMessageBox.StandardButton.Yes:
                    return

            duration = None
            try:
                if playing and os.path.abspath(media) == os.path.abspath(playing):
                    duration = getattr(self.player, "duration", None)
            except Exception:
                duration = None
            self._start_thaistt(media, self.cbo_stt_lang.currentText(),
                                self.cbo_stt_range.currentData(), duration)

        def _start_thaistt(self, media, lang, range_ab, duration):
            """รัน thaistt ผ่าน QProcess + QProgressDialog (ยกเลิกได้ + timeout + progress จาก stderr)"""
            from PyQt6.QtWidgets import QProgressDialog
            from PyQt6.QtCore import QProcess, QTimer
            from tstudio_core import TStudioCore
            from tvox_stt import find_stt_cli, build_cmd, timeout_for, PROGRESS_RE

            cli = find_stt_cli(TStudioCore.load_config())
            if not cli:
                QMessageBox.information(self, _("stt_need_setup_title"), _("stt_need_setup_msg"))
                return
            self._stt_out_srt = __import__("tvox_stt").draft_path_for(media)
            self._stt_cancelled = False

            prog = QProgressDialog(_("stt_running", file=os.path.basename(media)), _("stt_cancel_btn"), 0, 100, self)
            prog.setWindowTitle(_("stt_dialog_title"))
            prog.setMinimumDuration(200)
            prog.setWindowModality(Qt.WindowModality.WindowModal)

            self._stt_proc = QProcess(self)
            self._stt_proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

            self._stt_tail = []

            def on_ready():
                while self._stt_proc.canReadLine():
                    line = bytes(self._stt_proc.readLine()).decode("utf-8", errors="ignore").strip()
                    if line:
                        # เก็บท้าย 6 บรรทัดไว้โชว์ตอนพัง (บรรทัดที่อ่านไปแล้ว QProcess คืนไม่ได้)
                        self._stt_tail = (self._stt_tail + [line])[-6:]
                    m = PROGRESS_RE.search(line)
                    if m:
                        prog.setLabelText(_("stt_running_pct", pct=m.group(1), file=os.path.basename(media)))
                        prog.setValue(min(99, int(m.group(1))))

            def on_done(exit_code):
                self._stt_kill_timer.stop()
                prog.reset()
                prog.close()
                self._on_stt_finished(exit_code)

            def on_cancel():
                self._stt_cancelled = True
                if self._stt_proc.state() != QProcess.ProcessState.NotRunning:
                    self._stt_proc.kill()

            def on_error(err):
                # โปรแกรมเริ่มไม่ได้ (path หาย ฯลฯ) — QProcess จะไม่ยิง finished ต้องปิด dialog เอง
                if err != type(self._stt_proc).ProcessError.Crashed and self._stt_proc.state() == type(self._stt_proc).ProcessState.NotRunning:
                    self._stt_kill_timer.stop()
                    prog.reset()
                    prog.close()
                    self._on_stt_finished(-1)

            self._stt_proc.readyReadStandardOutput.connect(on_ready)
            self._stt_proc.finished.connect(on_done)
            self._stt_proc.errorOccurred.connect(on_error)
            prog.canceled.connect(on_cancel)

            self._stt_kill_timer = QTimer(self)
            self._stt_kill_timer.setSingleShot(True)
            self._stt_kill_timer.timeout.connect(on_cancel)
            self._stt_kill_timer.start(timeout_for(duration) * 1000)

            argv = build_cmd(cli, media, lang, self._stt_out_srt, range_ab)
            prog.setValue(0)
            self._stt_proc.start(argv[0], argv[1:])

        def _cancel_stt(self):
            """ยกเลิกจากภายนอก (ใช้ในการทดสอบ/ปิดโปรแกรม)"""
            if getattr(self, "_stt_proc", None) and self._stt_proc.state() != type(self._stt_proc).ProcessState.NotRunning:
                self._stt_cancelled = True
                self._stt_proc.kill()

        def _on_stt_finished(self, exit_code):
            from PyQt6.QtGui import QDesktopServices
            from PyQt6.QtCore import QUrl
            out_srt = getattr(self, "_stt_out_srt", "")

            if getattr(self, "_stt_cancelled", False) or not (exit_code == 0 and out_srt and os.path.isfile(out_srt)):
                tail = "\n".join(getattr(self, "_stt_tail", []) or [])[-500:]
                msg = _("stt_timeout_msg") if getattr(self, "_stt_cancelled", False) else _("stt_failed_msg", code=exit_code)
                QMessageBox.warning(self, _("stt_dialog_title"), msg + ("\n\n" + tail if tail else ""))
                return

            box = QMessageBox(self)
            box.setWindowTitle(_("stt_done_title"))
            box.setIcon(QMessageBox.Icon.Information)
            box.setText(_("stt_done_msg", file=os.path.basename(out_srt)) + "\n\n" + _("stt_workflow_warning"))
            btn_table = box.addButton(_("stt_open_in_table"), QMessageBox.ButtonRole.YesRole)
            btn_srt = box.addButton(_("stt_open_srt"), QMessageBox.ButtonRole.ActionRole)
            box.addButton(QMessageBox.StandardButton.Close)
            box.exec()
            if box.clickedButton() is btn_table:
                self.open_draft_in_table(out_srt)
            elif box.clickedButton() is btn_srt:
                QDesktopServices.openUrl(QUrl.fromLocalFile(out_srt))

        def open_draft_in_table(self, srt_path):
            """SRT ร่าง → ตาราง TStudio ผ่าน Game Tool Subtitles (CSV กลาง + origin_file อัตโนมัติ)"""
            import tstudio_game_tools as gt
            from tstudio_core import TStudioCore

            manifest = gt.installed_tools().get("Subtitles")
            if not manifest:
                QMessageBox.information(self, _("stt_dialog_title"), _("stt_need_subtitles_tool"))
                return
            csv_out = os.path.splitext(srt_path)[0] + ".csv"
            ok, out = self._run_game_tool_with_progress(
                lambda: gt.unpack(manifest, srt_path, csv_out), _("stt_unpacking"))
            if not ok:
                QMessageBox.critical(self, _("stt_dialog_title"), _("stt_failed_msg", code=out[:300]))
                return
            try:
                cfg = TStudioCore.load_config()
                cfg["origin_file"] = srt_path
                TStudioCore.save_config(cfg)
            except Exception as e:
                print(f"STT: บันทึก origin_file ไม่ได้ — {e}")
            self.csv_path = csv_out
            self._load_csv()
            self.statusBar().showMessage(_("stt_opened_status", csv=os.path.basename(csv_out), n=len(self.model._data)), 6000)

        def open_video(self):
            if not self.player: return
            file_path, _ext = QFileDialog.getOpenFileName(self, _("fdlg_open_video_title"), "", "Video Files (*.mp4 *.mkv *.avi *.webm *.mov *.bundle)")
            if file_path:
                try:
                    from tbundle_manager import TBundleManager
                    if TBundleManager.is_unity_bundle(file_path):
                        out_dir = os.path.join(os.path.dirname(file_path), "_tvox_cache")
                        
                        def do_work():
                            return TBundleManager.extract_video(file_path, out_dir)
                            
                        def on_result(extracted_video):
                            if extracted_video:
                                self.player.play(extracted_video)
                                self.player.pause = True
                                self.btn_play_pause.setText("\u25b6")
                                
                        from tstudio_ui_shared import ApiWorker
                        from PyQt6.QtCore import QThreadPool
                        worker = ApiWorker(do_work)
                        worker.signals.finished.connect(on_result)
                        QThreadPool.globalInstance().start(worker)
                        return
                except Exception as e:
                    print(f"Bundle extract error: {e}")

                self.player.play(file_path)
                
                # Default to paused state
                self.player.pause = True
                self.btn_play_pause.setText("\u25b6")
                
                # Refocus to video widget so spacebar works immediately
                self.video_widget.setFocus()
                
                self.mark_a = None
                self.mark_b = None
                self.btn_mark_a.setText(_("btn_mark_a"))
                self.btn_mark_b.setText(_("btn_mark_b"))
                
                # Check for FFmpeg and start extracting audio
                from ffmpeg_utils import ensure_ffmpeg
                from tvox_waveform import AudioExtractorWorker
                ffmpeg_path = ensure_ffmpeg(self)
                if ffmpeg_path:
                    if hasattr(self, 'audio_worker') and self.audio_worker.isRunning():
                        self.audio_worker.is_cancelled = True
                        self.audio_worker.wait()
                    
                    self.audio_worker = AudioExtractorWorker(ffmpeg_path, file_path)
                    self.audio_worker.finished.connect(self.waveform.set_audio_data)
                    self.audio_worker.error.connect(lambda msg: print(f"Audio Extractor Error: {msg}"))
                    self.audio_worker.start()

        def toggle_play(self):
            if not self.player: return
            self.player.pause = not self.player.pause

        def seek_relative(self, seconds):
            # TV-W2: Guard against seeking when no file is loaded
            try:
                if not self.player or not getattr(self.player, 'path', None):
                    return
            except Exception:
                return
            self.player.seek(seconds, reference="relative")

        def change_speed(self, text):
            if not self.player: return
            try:
                speed = float(text.replace("x", ""))
                self.player.speed = speed
            except ValueError:
                pass

        def set_mark_a(self):
            if not self.player or self.player.time_pos is None: return
            self.mark_a = self.player.time_pos
            self.btn_mark_a.setText(f"A: {self.format_time(self.mark_a)}")

        def set_mark_b(self):
            if not self.player or self.player.time_pos is None: return
            self.mark_b = self.player.time_pos
            self.btn_mark_b.setText(f"B: {self.format_time(self.mark_b)}")

        def toggle_loop(self):
            self.loop_active = not self.loop_active
            if self.loop_active:
                self.btn_loop.setText("🔁")
                self.btn_loop.setStyleSheet("background: #a6e3a1; color: #1e1e2e; font-weight: bold; padding: 4px; border-radius: 4px;")
                # If we turn on loop but missed a mark, maybe auto set it?
                if self.mark_a is not None and self.mark_b is None:
                    # TV-W1: Guard player.duration
                    duration = getattr(self.player, 'duration', None) if self.player else None
                    if duration:
                        self.mark_b = duration
            else:
                self.btn_loop.setText("🔁")
                self.btn_loop.setStyleSheet("background: #45475a; color: #cdd6f4; font-weight: bold; padding: 4px; border-radius: 4px;")
                # TV-C2: Reset loop-seeking flag when loop is disabled
                self.is_loop_seeking = False

        def on_tvox_row_selected(self, current, previous):
            # This is called *after* TStudio's own on_row_selected
            if not current.isValid(): return
            source_idx = self.proxy.mapToSource(current)
            row = source_idx.row()
            item = self.model._data[row]
            # Future feature: jump to start time of dialogue
            pass


        def load_dubbing_tracking(self):
            if not self.project_path: return
            base_dir = os.path.dirname(self.project_path)
            dub_csv = os.path.join(base_dir, "dubbing_tracking.csv")
            if not os.path.exists(dub_csv):
                return
            
            self.dub_table.setRowCount(0)
            self.dub_data = []
            recorded_count = 0
            total_count = 0
            
            with open(dub_csv, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.dub_data.append(row)
                    total_count += 1
                    if row.get('status') in ['RECORDED', 'APPROVED']:
                        recorded_count += 1
                        
            self.dub_table.setRowCount(total_count)
            for i, row in enumerate(self.dub_data):
                self.dub_table.setItem(i, 0, QTableWidgetItem(row.get('audio_id', '')))
                self.dub_table.setItem(i, 1, QTableWidgetItem(row.get('status', '')))
                self.dub_table.setItem(i, 2, QTableWidgetItem(row.get('duration_sec', '')))
                self.dub_table.setItem(i, 3, QTableWidgetItem(row.get('original_path', '')))
                self.dub_table.setItem(i, 4, QTableWidgetItem(row.get('dubbed_file_path', '')))
                
            if total_count > 0:
                pct = int((recorded_count / total_count) * 100)
                self.dub_progress.setValue(pct)
                self.lbl_dub_progress.setText(f"Project Progress: {pct}% ({recorded_count}/{total_count})")
                
        def on_dub_table_selection(self):
            selected = self.dub_table.selectedItems()
            if not selected:
                self.current_dub_id = None
                return
            row = selected[0].row()
            self.current_dub_id = self.dub_table.item(row, 0).text()
            
            # Sync with main table if possible
            # We can find the row in self.model._data with this ID and select it
            for i, item in enumerate(self.model._data):
                if item.get('id') == self.current_dub_id:
                    idx = self.proxy.mapFromSource(self.model.index(i, 0))
                    self.table.selectRow(idx.row())
                    break

        def play_original_audio(self):
            if not self.current_dub_id: return
            base_dir = os.path.dirname(self.project_path) if self.project_path else os.getcwd()
            original_path = os.path.join(base_dir, "original_audio", f"{self.current_dub_id}.wav")
            if os.path.exists(original_path):
                self.player.loadfile(original_path)
            else:
                QMessageBox.warning(self, "Not Found", f"Original audio not found:\n{original_path}")
                
        def handle_dropped_wav(self, audio_id, filepath):
            base_dir = os.path.dirname(self.project_path) if self.project_path else os.getcwd()
            output_dir = os.path.join(base_dir, "dubbed_audio")
            os.makedirs(output_dir, exist_ok=True)
            out_file = os.path.join(output_dir, f"{audio_id}.wav")
            shutil.copy2(filepath, out_file)
            
            # Duration Validation
            duration = self.recorder.get_wav_duration(out_file)
            orig_duration = 0.0
            for row in self.dub_data:
                if row.get('audio_id') == audio_id:
                    try:
                        orig_duration = float(row.get('duration_sec', 0))
                    except: pass
                    break
                    
            if orig_duration > 0 and duration > orig_duration + 1.5:
                QMessageBox.warning(self, "Duration Warning", f"Dropped audio ({duration:.2f}s) is significantly longer than original ({orig_duration:.2f}s).")
            else:
                QMessageBox.information(self, "Success", f"Audio imported successfully! ({duration:.2f}s)")
                
            self.update_dubbing_status(audio_id, "RECORDED", out_file)
            
        def start_dub_recording(self):
            if not self.current_dub_id:
                QMessageBox.warning(self, "Error", "Please select an audio row to dub.")
                return
            self.btn_record.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.recorder.start_recording()
            
        def stop_dub_recording(self):
            self.btn_record.setEnabled(True)
            self.btn_stop.setEnabled(False)
            base_dir = os.path.dirname(self.project_path) if self.project_path else os.getcwd()
            output_dir = os.path.join(base_dir, "dubbed_audio")
            os.makedirs(output_dir, exist_ok=True)
            out_file = os.path.join(output_dir, f"{self.current_dub_id}.wav")
            
            duration = self.recorder.stop_recording(out_file)
            
            # Validation
            orig_duration = 0.0
            for row in self.dub_data:
                if row.get('audio_id') == self.current_dub_id:
                    try:
                        orig_duration = float(row.get('duration_sec', 0))
                    except: pass
                    break
                    
            if orig_duration > 0 and duration > orig_duration + 1.5:
                QMessageBox.warning(self, "Duration Warning", f"Your recording ({duration:.2f}s) is significantly longer than the original ({orig_duration:.2f}s). This might cause cut-offs in game.")
            else:
                QMessageBox.information(self, "Success", f"Recorded successfully! ({duration:.2f}s)")
                
            # Update status in CSV and table
            self.update_dubbing_status(self.current_dub_id, "RECORDED", out_file)
            
        def update_dubbing_status(self, audio_id, new_status, file_path):
            if not self.project_path: return
            base_dir = os.path.dirname(self.project_path)
            dub_csv = os.path.join(base_dir, "dubbing_tracking.csv")
            if not os.path.exists(dub_csv): return
            
            # Update memory
            for i, row in enumerate(self.dub_data):
                if row.get('audio_id') == audio_id:
                    row['status'] = new_status
                    row['dubbed_file_path'] = file_path
                    self.dub_table.setItem(i, 1, QTableWidgetItem(new_status))
                    self.dub_table.setItem(i, 4, QTableWidgetItem(file_path))
                    break
                    
            # Write to CSV
            keys = self.dub_data[0].keys() if self.dub_data else []
            with open(dub_csv, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(self.dub_data)
                
            self.load_dubbing_tracking() # Refresh progress
            
        def inject_dubbed_audio(self):
            base_dir = os.path.dirname(self.project_path) if self.project_path else os.getcwd()
            script = os.path.join(base_dir, "inject_dubbed_audio.py")
            if not os.path.exists(script):
                QMessageBox.warning(self, "Not Found", f"Injection script not found at:\n{script}")
                return
            
            QMessageBox.information(self, "Inject", "Injection process started in background. Check terminal for logs.")
            import subprocess
            subprocess.Popen(["python", script], cwd=os.path.dirname(script))

        def closeEvent(self, event):
            """TV-C1: Clean shutdown — stop timers and terminate MPV player."""
            # Stop UI update timer
            if hasattr(self, 'update_timer') and self.update_timer:
                self.update_timer.stop()
            # Stop any waveform-related timers
            if hasattr(self, 'waveform_timer') and self.waveform_timer:
                self.waveform_timer.stop()
            # Terminate MPV player gracefully
            if hasattr(self, 'player') and self.player:
                try:
                    self.player.terminate()
                except Exception:
                    pass
            event.accept()

else:
    from PyQt6.QtWidgets import QMainWindow
    class TVoxApp(QMainWindow):
        def __init__(self, project_path=None):
            super().__init__()
            self.setWindowTitle(_("window_title_error"))
            QMessageBox.critical(self, _("dlg_tstudio_missing_title"), _("dlg_tstudio_missing_msg"))

def main():
    import argparse
    from tstudio_core import TStudioCore
    parser = argparse.ArgumentParser()
    parser.add_argument("project", nargs="?", type=str, help="Path to the THub project workspace", default=None)
    parser.add_argument("--standalone", action="store_true", help="Run standalone legacy TVox window")
    args, unknown = parser.parse_known_args()
    
    TStudioCore.set_project_path(args.project)

    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('flagship.tvox.dubbing.1.0')
        except Exception:
            pass

    app = QApplication(sys.argv)
    from PyQt6.QtGui import QFont, QIcon
    tvox_ico = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "TVox.ico"))
    if not os.path.exists(tvox_ico):
        tvox_ico = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "TVox.png"))
    if os.path.exists(tvox_ico):
        app.setWindowIcon(QIcon(tvox_ico))

    f = app.font()
    f.setFamily("Segoe UI")
    app.setFont(f)
    
    window = TVoxApp(project_path=args.project)
            
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
