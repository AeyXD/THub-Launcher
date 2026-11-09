# -*- coding: utf-8 -*-
"""Workflow Wizard — ตัวช่วยทำงานเป็นขั้นตอน ①–⑥ (spec-workflow-wizard.md ระยะ 1 MVP)

หลักการ: wizard เป็น **ชั้น orchestration** — เรียก method เดิมของ TranslationStudio
(open_draft_in_table, open_stt_dialog, open_game_tool_extract, retranslate_batch,
run_qa_check, deploy_to_game, open_tts_dialog) ไม่ rewrite logic แปล/QA/TTS เด็ดขาด

- QDockWidget แนวตั้งแคบ จอดซ้าย · ย่อได้ · ไม่ทับตาราง
- TVox ได้ใช้อัตโนมัติเพราะสืบทอด TranslationStudio (method TVox แทนที่ตามปกติ)
- ทุกขั้นบอก 3 อย่าง: กำลังทำอะไร · สถานะ (○ ● ✓ ↷) · ปุ่มกดต่อไปคืออะไร
- ตรวจสถานะอัตโนมัติ: เปิด CSV ที่แปลครบ → ขั้น ②③④ ✓ ให้เอง
- จำขั้นล่าสุด + ไฟล์งานเดิมใน config runtime (wizard_state — ห้าม commit)
- สีทั้งหมดผ่าน objectName + stylesheet กลาง (ไม่มี inline สี)
"""
import os

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame, QFileDialog,
)

from tstudio_i18n import _

CONFIG_KEY = "wizard_state"

# glyph สถานะขั้น: ยังไม่ทำ / กำลังทำ / เสร็จ / ข้าม
_GLYPH_TODO, _GLYPH_CURRENT, _GLYPH_DONE, _GLYPH_SKIP = "○", "●", "✓", "↷"


class WorkflowWizard(QDockWidget):
    """Stepper 6 ขั้น: ① เลือกงาน ② นำเข้า ③ ตรวจต้นฉบับ ④ แปล AI ⑤ ตรวจ QA ⑥ เสร็จงาน"""

    def __init__(self, studio, parent=None):
        super().__init__(_("wz_dock_title"), parent or studio)
        self.setObjectName("wizard_dock")
        self.studio = studio
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable)

        # state รันไทม์ (persist ลง config ผ่าน _save_state)
        self.mode = None          # 'video' | 'game'
        self.step = 1             # 1–6
        self.done = set()         # เลขขั้นที่เสร็จ
        self.skipped = set()      # เลขขั้นที่ถูกข้าม
        self._collapsed = False
        # csv ของงานรอบก่อนที่ "เริ่มงานใหม่" แล้วให้ลืม — auto-detect ไม่นับไฟล์นี้
        # จนกว่าผู้ใช้จะนำเข้าไฟล์ใหม่ผ่านปุ่มของขั้น ② (ปุ่มนำเข้าทุกตัวเคลียร์ค่านี้)
        self._stale_csv = ""
        # ระยะ 2-3: จำนวนจุด QA รอบล่าสุด (memory + wizard_state)
        self._qa_issues = 0

        root = QWidget()
        root.setObjectName("wzRoot")
        root.setMinimumWidth(240)
        root.setMaximumWidth(330)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(6)

        # ── หัว wizard: strip สรุปหน้างาน (ระยะ 2-3) + บอกกำลังทำอะไร ──
        head = QFrame()
        head.setObjectName("wzHeader")
        head_lay = QVBoxLayout(head)
        head_lay.setContentsMargins(8, 6, 8, 6)
        head_lay.setSpacing(2)
        self.lbl_summary = QLabel("")  # "n แถว · แปลแล้ว x · QA y จุด · โหมด"
        self.lbl_summary.setObjectName("wzSummary")
        self.lbl_summary.setWordWrap(True)
        self.lbl_head = QLabel(_("wz_header_title"))
        self.lbl_head.setObjectName("wzHeaderTitle")
        self.lbl_head.setWordWrap(True)
        self.lbl_sub = QLabel("")
        self.lbl_sub.setObjectName("wzHeaderSub")
        self.lbl_sub.setWordWrap(True)
        head_lay.addWidget(self.lbl_summary)
        head_lay.addWidget(self.lbl_head)
        head_lay.addWidget(self.lbl_sub)
        lay.addWidget(head)

        # ── Stepper: รายชื่อ 6 ขั้น + glyph สถานะ — คลิกแถวเพื่อกระโดดขั้นได้ ──
        self.step_rows = []
        steps_frame = QFrame()
        steps_frame.setObjectName("wzSteps")
        steps_lay = QVBoxLayout(steps_frame)
        steps_lay.setContentsMargins(8, 6, 8, 6)
        steps_lay.setSpacing(3)
        for i in range(1, 7):
            row = QPushButton()
            row.setObjectName("wzStepRow")
            row.setCursor(Qt.CursorShape.PointingHandCursor)
            row.setFlat(True)
            row.setToolTip(_("wz_step_row_tooltip"))
            row.clicked.connect(lambda _c=False, n=i: self.goto(n))
            steps_lay.addWidget(row)
            self.step_rows.append(row)
        lay.addWidget(steps_frame)

        # ── เนื้อหาขั้นปัจจุบัน ──
        self.pages = QStackedWidget()
        self.pages.setObjectName("wzPages")
        for builder in (self._page1, self._page2, self._page3,
                        self._page4, self._page5, self._page6):
            self.pages.addWidget(self._wrap_page(builder()))
        lay.addWidget(self.pages, 1)

        # ── ปุ่มรวมล่าง: ข้ามขั้นนี้ + ย่อ wizard ──
        bottom = QHBoxLayout()
        bottom.setSpacing(6)
        self.btn_skip = QPushButton(_("wz_skip"))
        self.btn_skip.setObjectName("wzBtnSkip")
        self.btn_skip.clicked.connect(self.skip_current)
        self.btn_collapse = QPushButton(_("wz_collapse"))
        self.btn_collapse.setObjectName("wzBtnCollapse")
        self.btn_collapse.clicked.connect(self.toggle_collapse)
        bottom.addWidget(self.btn_skip, 1)
        bottom.addWidget(self.btn_collapse)
        lay.addLayout(bottom)

        self.setWidget(root)

        # restore ขั้นล่าสุดจาก config (ปิด/เปิดใหม่ → จำงานเดิม)
        self._restore_state()

        # ตรวจสถานะอัตโนมัติ (นำเข้าแล้ว? แปลครบ?) — ทุก 1.2 วิ
        self._timer = QTimer(self)
        self._timer.setInterval(1200)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._refresh()

    # ─────────────────────────────────────────────────────────────
    # UI helpers
    # ─────────────────────────────────────────────────────────────

    def _wrap_page(self, inner):
        """หน้าขั้น: การ์ดที่ซ่อน/แสดงได้ตอนย่อ wizard"""
        card = QFrame()
        card.setObjectName("wzPage")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(6)
        lay.addWidget(inner)
        return card

    def _new_page(self):
        page = QWidget()
        page_lay = QVBoxLayout(page)
        page_lay.setContentsMargins(0, 0, 0, 0)
        page_lay.setSpacing(6)
        return page, page_lay

    def _big_btn(self, text, on_click, primary=False):
        btn = QPushButton(text)
        btn.setObjectName("wzBigBtn")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if primary:
            btn.setProperty("class", "btn-primary")
        btn.clicked.connect(on_click)
        return btn

    def _hint(self, key, **kw):
        lbl = QLabel(_(key, **kw))
        lbl.setObjectName("wzHint")
        lbl.setWordWrap(True)
        return lbl

    # ─────────────────────────────────────────────────────────────
    # หน้า 6 ขั้น (orchestration — เรียก method เดิมเท่านั้น)
    # ─────────────────────────────────────────────────────────────

    def _page1(self):
        """① เลือกงาน — แยกเส้นทางวิดีโอ/เสียง vs ไฟล์เกม"""
        page, lay = self._new_page()
        lay.addWidget(self._hint("wz_s1_q"))
        lay.addWidget(self._big_btn(_("wz_s1_video"), lambda: self._set_mode("video"), primary=True))
        lay.addWidget(self._big_btn(_("wz_s1_game"), lambda: self._set_mode("game")))
        self.lbl_s1_prev = self._hint("wz_s1_resume")
        self.lbl_s1_prev.hide()
        lay.addWidget(self.lbl_s1_prev)
        self.btn_s1_resume = QPushButton("")
        self.btn_s1_resume.setObjectName("wzBigBtn")
        self.btn_s1_resume.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_s1_resume.clicked.connect(self._open_saved_csv)
        self.btn_s1_resume.hide()
        lay.addWidget(self.btn_s1_resume)
        # ทางออกกลางทาง: ล้างงานเดิมทั้งหมดแล้วเริ่มรอบใหม่ (มีทั้งหน้า ① และ ⑥)
        lay.addWidget(self._big_btn(_("wz_s6_restart"), self.reset))
        lay.addStretch(1)
        return page

    def _page2(self):
        """② นำเข้า — วิดีโอ: ถอดเสียง/เลือก SRT · เกม: Game Tool extract"""
        page, lay = self._new_page()

        self.frm_s2_video = QFrame()
        v_lay = QVBoxLayout(self.frm_s2_video)
        v_lay.setContentsMargins(0, 0, 0, 0)
        v_lay.setSpacing(6)
        v_lay.addWidget(self._hint("wz_s2_video_hint"))
        self.btn_s2_stt = self._big_btn(_("wz_s2_stt"), self._do_stt, primary=True)
        v_lay.addWidget(self.btn_s2_stt)
        self.lbl_s2_stt_note = self._hint("wz_s2_stt_only_tvox")
        v_lay.addWidget(self.lbl_s2_stt_note)
        self.btn_s2_srt = self._big_btn(_("wz_s2_pick_srt"), self._pick_srt)
        v_lay.addWidget(self.btn_s2_srt)
        lay.addWidget(self.frm_s2_video)

        self.frm_s2_game = QFrame()
        g_lay = QVBoxLayout(self.frm_s2_game)
        g_lay.setContentsMargins(0, 0, 0, 0)
        g_lay.setSpacing(6)
        g_lay.addWidget(self._hint("wz_s2_game_hint"))
        g_lay.addWidget(self._big_btn(_("wz_s2_game_btn"), self._do_game_extract, primary=True))
        lay.addWidget(self.frm_s2_game)

        self.lbl_s2_status = self._hint("wz_s2_wait")
        lay.addWidget(self.lbl_s2_status)
        lay.addStretch(1)
        return page

    def _page3(self):
        """③ ตรวจต้นฉบับ — ชวนคลิกแถวแก้ในตาราง แล้วยืนยันใช้ร่าง"""
        page, lay = self._new_page()
        self.lbl_s3_summary = self._hint("wz_s3_summary", n=0)
        lay.addWidget(self.lbl_s3_summary)
        self.lbl_s3_video = self._hint("wz_s3_video_hint")
        lay.addWidget(self.lbl_s3_video)
        lay.addWidget(self._big_btn(_("wz_s3_confirm"), self._confirm_draft, primary=True))
        lay.addStretch(1)
        return page

    def _page4(self):
        """④ แปล AI — โชว์โมเดล + เปลี่ยนได้ + แปลทั้งหมด + progress n/N"""
        page, lay = self._new_page()
        self.lbl_s4_model = self._hint("wz_s4_model", model="-")
        lay.addWidget(self.lbl_s4_model)
        lay.addWidget(self._big_btn(_("wz_s4_change"), self._change_model))
        lay.addWidget(self._big_btn(_("wz_s4_translate_all"), self._translate_all, primary=True))
        self.lbl_s4_progress = self._hint("wz_s4_progress", done=0, total=0)
        lay.addWidget(self.lbl_s4_progress)
        lay.addStretch(1)
        return page

    def _page5(self):
        """⑤ ตรวจ QA — ปุ่มตรวจเลย + แก้อัตโนมัติ (dialog เดิมของ run_qa_check)"""
        page, lay = self._new_page()
        lay.addWidget(self._hint("wz_s5_hint"))
        lay.addWidget(self._big_btn(_("wz_s5_run"), self._run_qa, primary=True))
        lay.addWidget(self._big_btn(_("wz_s5_autofix"), self._run_qa_fix))
        self.lbl_s5_status = self._hint("wz_s5_wait")
        lay.addWidget(self.lbl_s5_status)
        lay.addStretch(1)
        return page

    def _page6(self):
        """⑥ เสร็จงาน — วิดีโอ: พากย์ AI/ทำวิดีโอพากย์/ส่งออกซับ · เกม: Pack กลับเข้าเกม"""
        page, lay = self._new_page()
        self.btn_s6_tts = self._big_btn(_("wz_s6_video_tts"), self._do_tts, primary=True)
        lay.addWidget(self.btn_s6_tts)
        self.lbl_s6_tts_note = self._hint("wz_s6_tts_only_tvox")
        lay.addWidget(self.lbl_s6_tts_note)
        # ระยะ 2-2: ทำวิดีโอพากย์ (พอร์ต make_videos_r1.sh ของ hub) — TVox เท่านั้น
        self.btn_s6_video = self._big_btn(_("wz_s6_make_video"), self._make_video, primary=True)
        lay.addWidget(self.btn_s6_video)
        self.lbl_s6_video_note = self._hint("wz_s6_video_only_tvox")
        lay.addWidget(self.lbl_s6_video_note)
        self.btn_s6_srt = self._big_btn(_("wz_s6_export_srt"), self._deploy)
        lay.addWidget(self.btn_s6_srt)
        self.btn_s6_pack = self._big_btn(_("wz_s6_pack"), self._deploy, primary=True)
        lay.addWidget(self.btn_s6_pack)
        lay.addWidget(self._hint("wz_s6_done_hint"))
        lay.addWidget(self._big_btn(_("wz_s6_restart"), self.reset))
        lay.addStretch(1)
        return page

    # ─────────────────────────────────────────────────────────────
    # Actions — ทุกอย่างเรียก method เดิมของ studio
    # ─────────────────────────────────────────────────────────────

    def _set_mode(self, mode):
        self.mode = mode
        self.done.add(1)
        self.goto(2)

    def _do_stt(self):
        """ถอดเสียงผ่าน dialog เดิมของ TVox — เสร็จแล้วเปิดร่างในตารางอัตโนมัติ"""
        stt = getattr(self.studio, "open_stt_dialog", None)
        if not callable(stt):
            return
        self._stale_csv = ""  # นำเข้าไฟล์ใหม่ — เลิกลืมงานก่อนหน้า
        self.studio._stt_auto_open_draft = True
        stt()

    def _pick_srt(self):
        path, _sel = QFileDialog.getOpenFileName(
            self.studio, _("wz_s2_pick_srt"), "", _("wz_srt_filter"))
        if path:
            self._stale_csv = ""  # นำเข้าไฟล์ใหม่ — เลิกลืมงานก่อนหน้า
            self.studio.open_draft_in_table(path)

    def _do_game_extract(self):
        self._stale_csv = ""  # นำเข้าไฟล์ใหม่ — เลิกลืมงานก่อนหน้า
        self.studio.open_game_tool_extract()

    def _open_saved_csv(self):
        """เปิดไฟล์งานเดิมจาก wizard_state (resume หลังปิด/เปิดแอปใหม่)"""
        csv = self._saved_csv()
        if csv and os.path.exists(csv):
            self._stale_csv = ""  # กลับมาทำงานนี้ต่อ — นับสถานะตามปกติ
            self.studio.csv_path = csv
            self.studio._load_csv()
            self._refresh()

    def _confirm_draft(self):
        self.done.add(3)
        self.goto(4)

    def _change_model(self):
        self.studio.open_settings()

    def _translate_all(self):
        """เลือกทุกแถวแล้วเข้า engine แปลเดิม — กล่องโต้ตอบ TRun/CAT ของแอปเดิมเด้งตามปกติ"""
        table = getattr(self.studio, "table", None)
        if table is not None:
            table.selectAll()
        self.studio.retranslate_batch()

    def _run_qa(self):
        self.studio.run_qa_check()
        self._collect_qa_issues()  # ระยะ 2-3: จำจำนวนจุดรอบล่าสุดไว้บนหัว wizard
        self.done.add(5)
        self._save_state()
        self.goto(6)

    def _collect_qa_issues(self):
        """นับจุดจาก qa_audit.csv ที่ checker เขียนไว้ข้าง CSV (ผลรอบล่าสุด)"""
        csv_path = getattr(self.studio, "csv_path", "") or ""
        report = os.path.join(os.path.dirname(os.path.abspath(csv_path)), "qa_audit.csv")
        n = 0
        try:
            if os.path.isfile(report):
                with open(report, "r", encoding="utf-8", errors="replace") as f:
                    lines = [ln for ln in f.read().splitlines() if ln.strip()]
                n = max(0, len(lines) - 1)  # ตัด header
        except Exception:
            n = 0
        self._qa_issues = n

    def _run_qa_fix(self):
        self.studio.run_qa_check(fix=True)

    def _do_tts(self):
        tts = getattr(self.studio, "open_tts_dialog", None)
        if callable(tts):
            tts()

    def _make_video(self):
        """🎬 ทำวิดีโอพากย์ (ระยะ 2-2) — dialog ของ TVox (dub/mix + ฝังซับ)"""
        fn = getattr(self.studio, "open_video_export_dialog", None)
        if callable(fn):
            fn()

    def _deploy(self):
        """เส้นทาง Ctrl+D เดิม: QA gate → Thai Wrap → Pack กลับ (SRT/ไฟล์เกม)"""
        self.studio.deploy_to_game()

    # ─────────────────────────────────────────────────────────────
    # สถานะ / การเดินขั้น
    # ─────────────────────────────────────────────────────────────

    def goto(self, step):
        self.step = max(1, min(6, step))
        self.pages.setCurrentIndex(self.step - 1)
        self._refresh()
        self._save_state()

    def skip_current(self):
        if self.step >= 2:
            self.skipped.add(self.step)
            self.goto(self.step + 1)

    def reset(self):
        """เริ่มงานใหม่จริง — ล้างขั้น/สถานะทั้งหมด และ "ลืม" งานเดิมที่ยังเปิดในตาราง
        (ตารางเดิมไม่ถูกลบ — นำเข้าไฟล์ใหม่ในขั้น ② แล้วแทนที่ตาม flow เดิม)"""
        self.mode = None
        self.step = 1
        self.done = set()
        self.skipped = set()
        self._stale_csv = getattr(self.studio, "csv_path", "") or ""
        self.goto(1)
        if hasattr(self.studio, "show_welcome"):
            self.studio.show_welcome()

    def toggle_collapse(self):
        """ย่อ wizard = เหลือแค่หัว + stepper (เนื้อหาขั้นซ่อน)"""
        self._collapsed = not self._collapsed
        self.pages.setVisible(not self._collapsed)
        self.btn_skip.setVisible(not self._collapsed)
        self.btn_collapse.setText(_("wz_expand") if self._collapsed else _("wz_collapse"))

    def _studio_rows(self):
        model = getattr(self.studio, "model", None)
        data = getattr(model, "_data", None) if model else None
        return data or []

    def _imported(self):
        csv_path = getattr(self.studio, "csv_path", "")
        if not csv_path or not os.path.exists(csv_path) or not self._studio_rows():
            return False
        if csv_path == self._stale_csv:
            return False  # งานรอบก่อนที่ "เริ่มงานใหม่" แล้ว — ไม่นับ จนกว่าจะนำเข้าไฟล์ใหม่
        return True

    def _translated_counts(self):
        rows = self._studio_rows()
        total = len(rows)
        done_n = sum(1 for it in rows if (it.get("trans") or "").strip())
        return done_n, total

    def _tick(self):
        self._refresh(auto=True)

    def _refresh(self, auto=False):
        """อัปเดต glyph ทุกขั้น + เนื้อหาหน้า และตรวจ auto-advance (เปิด CSV แปลครบ → ②③④ ✓)"""
        imported = self._imported()
        done_n, total = self._translated_counts()
        all_translated = imported and total > 0 and done_n == total
        if imported:
            self.done.add(2)
        if all_translated:
            self.done.add(3)
            self.done.add(4)

        # auto-advance: ขั้นปัจจุบันเสร็จเองแล้ว → เสนอขั้นถัดไปทันที
        if auto and imported:
            if self.step == 2:
                self.goto(3)
                return
            if self.step == 4 and all_translated:
                self.goto(5)
                return

        # stepper rows: glyph สถานะ + ชื่อขั้น (คลิกกระโดดขั้นได้)
        for i, row in enumerate(self.step_rows, start=1):
            if i in self.done:
                glyph = _GLYPH_DONE
            elif i in self.skipped:
                glyph = _GLYPH_SKIP
            elif i == self.step:
                glyph = _GLYPH_CURRENT
            else:
                glyph = _GLYPH_TODO
            row.setText(f"{glyph} {i}. {_(f'wz_step{i}_name')}")
            row.setProperty("cur", i == self.step)
            row.style().unpolish(row)
            row.style().polish(row)

        # หัว wizard: กำลังทำอะไร
        step_name = _(f"wz_step{self.step}_name")
        self.lbl_head.setText(f"{self.step}/6 · {step_name}")

        # แต่งหน้าตาม mode + สถานะ
        is_video = self.mode == "video"
        self.frm_s2_video.setVisible(is_video)
        self.frm_s2_game.setVisible(self.mode == "game")
        has_stt = callable(getattr(self.studio, "open_stt_dialog", None))
        self.btn_s2_stt.setEnabled(has_stt)
        self.lbl_s2_stt_note.setVisible(is_video and not has_stt)
        self.lbl_s3_video.setVisible(is_video)
        self.btn_s6_tts.setVisible(is_video)
        self.lbl_s6_tts_note.setVisible(is_video and not callable(getattr(self.studio, "open_tts_dialog", None)))
        # ระยะ 2-2: ปุ่มทำวิดีโอพากย์ — TVox เท่านั้น + ต้องพร้อม (วิดีโอเปิด + CSV เป็นชุดซับ)
        has_vexp = callable(getattr(self.studio, "open_video_export_dialog", None))
        self.btn_s6_video.setVisible(is_video)
        self.lbl_s6_video_note.setVisible(is_video and not has_vexp)
        vexp_ready, vexp_reason = (False, "")
        if has_vexp:
            try:
                vexp_ready, vexp_reason = self.studio.can_make_dub_video()
            except Exception:
                vexp_ready, vexp_reason = False, ""
        self.btn_s6_video.setEnabled(vexp_ready)
        self.btn_s6_video.setToolTip(_(vexp_reason) if (has_vexp and not vexp_ready and vexp_reason) else "")
        self.btn_s6_srt.setVisible(is_video)
        self.btn_s6_pack.setVisible(not is_video)
        mode_label = _("wz_mode_video") if is_video else _("wz_mode_game") if self.mode else _("wz_mode_none")
        self.lbl_sub.setText(mode_label)
        # ระยะ 2-3: strip สรุปหน้างานบนหัว wizard (มองเห็นตลอด ไม่ต้องเข้าขั้น ③④)
        if total > 0:
            self.lbl_summary.setText(_("wz_summary", n=total, done=done_n,
                                       qa=getattr(self, "_qa_issues", 0), mode=mode_label))
            self.lbl_summary.show()
        else:
            self.lbl_summary.hide()

        # ข้อความสถานะรายหน้า
        if imported:
            csv_path = getattr(self.studio, "csv_path", "")
            self.lbl_s2_status.setText(_("wz_s2_loaded", file=os.path.basename(csv_path), n=total))
        else:
            self.lbl_s2_status.setText(_("wz_s2_wait"))
        self.lbl_s3_summary.setText(_("wz_s3_summary", n=total))
        try:
            from tstudio_core import TStudioCore
            cfg = TStudioCore.load_config()
            model_name = cfg.get("model", "-") or "-"
            provider = cfg.get("provider", "")
        except Exception:
            model_name, provider = "-", ""
        self.lbl_s4_model.setText(_("wz_s4_model", model=f"{provider} · {model_name}" if provider else model_name))
        self.lbl_s4_progress.setText(_("wz_s4_progress", done=done_n, total=total))
        self.lbl_s5_status.setText(_("wz_s4_progress", done=done_n, total=total))

        # resume งานเดิมบนขั้น ①
        saved = self._saved_csv()
        if saved and os.path.exists(saved) and not imported:
            self.lbl_s1_prev.show()
            self.btn_s1_resume.setText(_("wz_s1_resume_btn", file=os.path.basename(saved)))
            self.btn_s1_resume.show()
        else:
            self.lbl_s1_prev.hide()
            self.btn_s1_resume.hide()

        self.btn_skip.setEnabled(self.step >= 2 and self.step <= 5)

    # ─────────────────────────────────────────────────────────────
    # Persistence (config runtime — ห้าม commit)
    # ─────────────────────────────────────────────────────────────

    def _saved_csv(self):
        try:
            from tstudio_core import TStudioCore
            state = TStudioCore.load_config().get(CONFIG_KEY, {}) or {}
            return state.get("csv", "") or ""
        except Exception:
            return ""

    def _save_state(self):
        try:
            from tstudio_core import TStudioCore
            cfg = TStudioCore.load_config()
            cfg[CONFIG_KEY] = {
                "mode": self.mode,
                "step": self.step,
                "current_step": self.step,  # ระยะ 2-1: ฟิลด์ตามสเปก (mirror ของ step — บันทึกทุก goto())
                # จำไฟล์งานเฉพาะตอนมีงานค้าง — "เริ่มงานใหม่" แล้วไม่เสนอ resume ไฟล์เก่า
                "csv": (getattr(self.studio, "csv_path", "") or "") if (self.mode or self.step > 1) else "",
                "qa_issues": getattr(self, "_qa_issues", 0),
            }
            TStudioCore.save_config(cfg)
        except Exception as e:
            print(f"Wizard: บันทึกสถานะไม่ได้ — {e}")

    def _restore_state(self):
        try:
            from tstudio_core import TStudioCore
            state = TStudioCore.load_config().get(CONFIG_KEY, {}) or {}
            self.mode = state.get("mode") if state.get("mode") in ("video", "game") else None
            step = state.get("current_step") or state.get("step", 1)
            self.step = max(1, min(6, int(step))) if step else 1
            self._qa_issues = int(state.get("qa_issues", 0) or 0)
            self.pages.setCurrentIndex(self.step - 1)
        except Exception:
            pass

    def resume_saved_job(self):
        """ระยะ 2-1: การ์ด ▶️ ทำงานต่อ — เปิด wizard + โหลด CSV เดิม + กลับขั้นที่ค้าง ในคลิกเดียว"""
        try:
            from tstudio_core import TStudioCore
            state = TStudioCore.load_config().get(CONFIG_KEY, {}) or {}
        except Exception:
            return False
        csv_path = state.get("csv", "") or ""
        step = state.get("current_step") or state.get("step") or 1
        if not csv_path or not os.path.exists(csv_path):
            return False
        self.show()
        self.raise_()
        self._stale_csv = ""  # กลับมาทำงานนี้ต่อ — นับสถานะตามปกติ
        self.studio.csv_path = csv_path
        self.studio._load_csv()
        self.goto(max(1, min(6, int(step))))
        return True
