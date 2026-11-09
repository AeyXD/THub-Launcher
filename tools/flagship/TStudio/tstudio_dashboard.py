# -*- coding: utf-8 -*-
"""TStudio Welcome Screen + Live Dashboard
หน้าแรก (Welcome) แสดงตอนยังไม่เปิดไฟล์ · แดชบอร์ดเป็น dock ที่อัปเดตสถิติการแปลแบบสด
"""
import os
from collections import Counter

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QFrame, QProgressBar, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

try:
    from tstudio_i18n import _
except ImportError:
    def _(key, **kw):
        return key

try:
    from tstudio_core import TStudioCore
except ImportError:
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Core')))
    from tstudio_core import TStudioCore


class _ActionCard(QFrame):
    """การ์ด quick action แบบคลิกได้ทั้งใบ"""

    def __init__(self, icon, title, desc, on_click, parent=None):
        super().__init__(parent)
        self.setObjectName("wsCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._on_click = on_click
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(4)
        lbl_t = QLabel(f"{icon}  {title}")
        lbl_t.setObjectName("wsCardTitle")
        lbl_d = QLabel(desc)
        lbl_d.setObjectName("wsCardDesc")
        lbl_d.setWordWrap(True)
        lay.addWidget(lbl_t)
        lay.addWidget(lbl_d)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._on_click:
            self._on_click()


class WelcomeScreen(QWidget):
    """หน้าแรก: hero + quick actions + ไฟล์ที่เปิดล่าสุด"""

    open_recent_requested = pyqtSignal(str)

    def __init__(self, studio, parent=None):
        super().__init__(parent)
        self.studio = studio

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll_body = QWidget()
        root = QVBoxLayout(scroll_body)
        root.setContentsMargins(48, 40, 48, 40)
        root.setSpacing(22)

        lbl_hero = QLabel("✦ TStudio")
        lbl_hero.setObjectName("wsHeroTitle")
        lbl_sub = QLabel(_("ws_hero_sub"))
        lbl_sub.setObjectName("wsHeroSub")
        root.addWidget(lbl_hero)
        root.addWidget(lbl_sub)

        grid = QGridLayout()
        grid.setSpacing(14)
        cards = [
            # การ์ดแรก = ทางเข้า Workflow Wizard (spec-workflow-wizard.md ระยะ 1) — พาทำทีละขั้น ①–⑥
            ("🧭", _("ws_card_wizard_title"), _("ws_card_wizard_desc"), studio.open_workflow_wizard),
            ("📂", _("ws_card_open_title"), _("ws_card_open_desc"), studio.new_project_from_file),
            ("🗂", _("ws_card_project_title"), _("ws_card_project_desc"), studio.open_project_dialog),
            ("🔀", _("ws_card_merge_title"), _("ws_card_merge_desc"), studio.open_merge_dialog),
            ("🧩", _("ws_card_plugin_title"), _("ws_card_plugin_desc"), studio.open_plugin_manager),
        ]
        for i, (icon, title, desc, fn) in enumerate(cards):
            grid.addWidget(_ActionCard(icon, title, desc, fn), i // 2, i % 2)
        root.addLayout(grid)

        lbl_recent = QLabel(_("ws_section_recent"))
        lbl_recent.setObjectName("wsSectionTitle")
        root.addWidget(lbl_recent)

        self.recent_container = QVBoxLayout()
        self.recent_container.setSpacing(2)
        root.addLayout(self.recent_container)
        root.addStretch(1)

        from PyQt6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(scroll_body)
        outer.addWidget(scroll)

        self.refresh_recent()

    def refresh_recent(self):
        while self.recent_container.count():
            item = self.recent_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        files = []
        try:
            cfg = TStudioCore.load_config()
            files = [f for f in cfg.get("recent_files", []) if os.path.exists(f)][:6]
        except Exception:
            pass

        if not files:
            empty = QLabel(_("ws_recent_empty"))
            empty.setObjectName("wsRecentEmpty")
            self.recent_container.addWidget(empty)
            return

        for path in files:
            btn = QPushButton(f"📄  {os.path.basename(path)}")
            btn.setObjectName("wsRecentItem")
            btn.setToolTip(path)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, p=path: self.open_recent_requested.emit(p))
            self.recent_container.addWidget(btn)


class _StatCard(QFrame):
    def __init__(self, label_key, parent=None):
        super().__init__(parent)
        self.setObjectName("dashCard")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(2)
        self.lbl_value = QLabel("0")
        self.lbl_value.setObjectName("dashValue")
        self.lbl_label = QLabel(_(label_key))
        self.lbl_label.setObjectName("dashLabel")
        lay.addWidget(self.lbl_value)
        lay.addWidget(self.lbl_label)


class DashboardPanel(QWidget):
    """แดชบอร์ดสถิติการแปล — อัปเดตสดจาก CsvTableModel"""

    def __init__(self, studio, parent=None):
        super().__init__(parent)
        self.studio = studio

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(14)

        self.lbl_percent = QLabel("0%")
        self.lbl_percent.setObjectName("dashPercent")
        self.lbl_detail = QLabel(_("dash_no_file"))
        self.lbl_detail.setObjectName("dashDetail")
        self.lbl_detail.setWordWrap(True)
        root.addWidget(self.lbl_percent)
        root.addWidget(self.lbl_detail)

        self.bar = QProgressBar()
        self.bar.setObjectName("dashBar")
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(10)
        root.addWidget(self.bar)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)
        self.card_total = _StatCard("dash_total")
        self.card_done = _StatCard("dash_translated")
        self.card_todo = _StatCard("dash_untranslated")
        cards_row.addWidget(self.card_total)
        cards_row.addWidget(self.card_done)
        cards_row.addWidget(self.card_todo)
        root.addLayout(cards_row)

        lbl_tags = QLabel(_("dash_tag_breakdown"))
        lbl_tags.setObjectName("wsSectionTitle")
        root.addWidget(lbl_tags)

        self.tag_container = QVBoxLayout()
        self.tag_container.setSpacing(6)
        root.addLayout(self.tag_container)
        root.addStretch(1)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(250)
        self._refresh_timer.timeout.connect(self.refresh)

        self.refresh()

    def throttled_refresh(self):
        self._refresh_timer.start()

    def refresh(self):
        data = getattr(self.studio, "model", None)._data if hasattr(self.studio, "model") else []
        total = len(data)
        done = sum(1 for r in data if str(r.get("trans", "")).strip())
        todo = total - done
        pct = (done / total * 100) if total else 0

        self.lbl_percent.setText(f"{pct:.0f}%")
        name = os.path.basename(self.studio.csv_path) if getattr(self.studio, "csv_path", "") else ""
        self.lbl_detail.setText(f"{name} — {done:,} / {total:,} {_('dash_rows')}" if total else _("dash_no_file"))
        self.bar.setValue(int(pct))
        self.card_total.lbl_value.setText(f"{total:,}")
        self.card_done.lbl_value.setText(f"{done:,}")
        self.card_todo.lbl_value.setText(f"{todo:,}")

        while self.tag_container.count():
            item = self.tag_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not total:
            return

        tags = Counter(r.get("tag", "") for r in data if r.get("tag", "").strip() and r["tag"] != "❓")
        for tag, count in tags.most_common(6):
            row = QHBoxLayout()
            row.setSpacing(8)
            lbl = QLabel(tag)
            lbl.setObjectName("dashTagLabel")
            lbl.setFixedWidth(86)
            bar = QProgressBar()
            bar.setObjectName("dashTagBar")
            bar.setRange(0, total)
            bar.setValue(count)
            bar.setTextVisible(False)
            bar.setFixedHeight(6)
            cnt = QLabel(f"{count:,}")
            cnt.setObjectName("dashTagCount")
            row.addWidget(lbl)
            row.addWidget(bar, 1)
            row.addWidget(cnt)
            holder = QWidget()
            holder.setLayout(row)
            self.tag_container.addWidget(holder)
