# -*- coding: utf-8 -*-
"""tstudio_qa_bridge.py — สะพานเชื่อมตัวตรวจ QA (thai_qa.py จาก repo game-localization-qa)

ตามสัญญาใน docs/spec-qa-bridge.md (workspace "THub Studio"):
- เรียกผ่าน subprocess (loose coupling ไม่ import ข้าม repo)
- CSV มาตรฐาน TStudio: ID=1, Source=2, Translation=3 (1-based) → --source-col 2 --target-col 3
- Audit CSV: File, Location, Rule, Severity, AutoFixed, Before, After, Note
- Exit codes: 0 = สะอาด · 1 = มีคำเตือน · ≥2 = รันไม่สำเร็จ
"""
import os
import csv
import json
import subprocess
import sys

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox
)
from PyQt6.QtGui import QDesktopServices, QColor
from PyQt6.QtCore import QUrl, pyqtSignal

try:
    from tstudio_i18n import _
except ImportError:
    def _(key, **kw):
        return key


def _themed(mocha_hex):
    """สีตามธีมปัจจุบันจากตารางกลางของ tstudio_app (lazy — เลี่ยง circular import)"""
    try:
        from tstudio_app import themed_color
        return themed_color(mocha_hex)
    except Exception:
        return mocha_hex


def find_checker(cfg):
    """คืน path ของ thai_qa.py ถ้าตั้งค่าไว้ (qa_checker_path) และมีไฟล์จริง มิฉะนั้น None"""
    p = (cfg or {}).get("qa_checker_path", "")
    return p if p and os.path.isfile(p) else None


def _read_audit_rows(report_path):
    """อ่านตารางผลจาก audit CSV (Title Case keys ตรง schema ระยะแรก)"""
    rows = []
    try:
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8-sig", newline="") as f:
                rows = [r for r in csv.DictReader(f)]
    except Exception as e:
        print(f"QA bridge: อ่าน audit CSV ไม่ได้ — {e}")
    return rows


def _text_summary(proc):
    """สรุปแบบระยะแรก: หาบรรทัด 'รวม: ...' จาก stdout ของ checker เก่า"""
    out = (proc.stdout or "").strip()
    lines = [ln for ln in out.splitlines() if ln.strip()]
    summary = ""
    for ln in reversed(lines):
        if "รวม:" in ln or "รวม :" in ln:
            summary = ln
            break
    if not summary and lines:
        summary = lines[-1]
    if not summary:
        summary = (proc.stderr or "").strip()
    return summary


def _json_summary(auto_fixed, flagged):
    """สรุป dialog จากตัวเลข JSON ผ่าน i18n (ระยะสอง — ไม่ parse stdout แล้ว)"""
    try:
        return _("qa_summary_total", n=auto_fixed, m=flagged)
    except Exception:
        return f"รวม: แก้อัตโนมัติ {auto_fixed} จุด | แจ้งเตือนอีก {flagged} จุด"


def run_checker(checker_path, csv_path, report_path, fix=False):
    """รัน checker (dry-run default หรือ --fix) คืน (ok, rows, summary, autofix_count)

    ระยะสอง (docs/spec-qa-bridge.md): ใส่ --json แล้วใช้ JSON เป็นแหล่งความจริง —
    auto_fixed/flagged ตรง ๆ, สรุปสร้างจาก i18n, report path จาก JSON
    ถ้า checker เก่าไม่รู้จัก --json (ตายด้วย argparse exit ≥2 หรือ stdout ไม่ใช่ JSON)
    จะรันซ้ำครั้งเดียวแบบไม่มี --json แล้วใช้เส้นทาง text parse + audit CSV เดิม"""
    base_cmd = [
        sys.executable, checker_path, csv_path,
        "--csv", "--source-col", "2", "--target-col", "3",
        "--report", report_path, "--quiet",
    ]
    if fix:
        base_cmd.append("--fix")
    flags = 0x08000000 if os.name == "nt" else 0

    def _run(cmd):
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=600, creationflags=flags
        )

    try:
        proc = _run(base_cmd + ["--json"])
    except Exception as e:
        return False, [], str(e), 0

    data = None
    try:
        parsed = json.loads(proc.stdout or "")
        if isinstance(parsed, dict):
            data = parsed
    except (ValueError, TypeError):
        pass

    if data is not None:
        auto_fixed = int(data.get("auto_fixed") or 0)
        flagged = int(data.get("flagged") or 0)
        ok = proc.returncode in (0, 1)
        # ตารางผลยังอ่านจาก audit CSV (ตามข้อก. ของสเปก — เปลี่ยนน้อยที่สุด)
        rows = _read_audit_rows(data.get("report") or report_path)
        return ok, rows, _json_summary(auto_fixed, flagged), auto_fixed

    # checker เก่า (ไม่รู้จัก --json) หรือ stdout ไม่ใช่ JSON → รันซ้ำครั้งเดียวแบบไม่มี --json
    try:
        proc = _run(base_cmd)
    except Exception as e:
        return False, [], str(e), 0
    summary = _text_summary(proc)
    return proc.returncode in (0, 1), _read_audit_rows(report_path), summary, parse_autofix_count(summary)


def parse_autofix_count(summary_text):
    """ดึงจำนวน auto-fix ที่เป็นไปได้จากบรรทัดสรุป เช่น 'รวม: แก้อัตโนมัติ 12 จุด | ...'"""
    import re
    m = re.search(r"แก้อัตโนมัติ\s*(\d+)\s*จุด", summary_text or "")
    return int(m.group(1)) if m else 0


class QaResultDialog(QDialog):
    """หน้าต่างผล QA: สรุป + ตารางจาก audit + เปิดรายงานฉบับเต็ม + (ปุ่มแก้อัตโนมัติ)"""

    fix_requested = pyqtSignal()

    def __init__(self, rows, summary_text, report_path, parent=None, autofix_count=None):
        super().__init__(parent)
        self.setWindowTitle(_("qa_title"))
        self.resize(760, 480)
        self.report_path = report_path

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        self.lbl_summary = QLabel(summary_text or _("qa_no_issues"))
        self.lbl_summary.setObjectName("qaSummaryLabel")
        self.lbl_summary.setWordWrap(True)
        lay.addWidget(self.lbl_summary)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([_("qa_col_location"), _("qa_col_rule"), _("qa_col_severity"), _("qa_col_note")])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        lay.addWidget(self.table, 1)

        for r in rows:
            i = self.table.rowCount()
            self.table.insertRow(i)
            sev = (r.get("Severity") or "").strip().lower()
            items = [
                QTableWidgetItem(r.get("Location") or ""),
                QTableWidgetItem(r.get("Rule") or ""),
                QTableWidgetItem(r.get("Severity") or ""),
                QTableWidgetItem(r.get("Note") or ""),
            ]
            if sev == "error":
                items[2].setForeground(QColor(_themed("#f38ba8")))
            elif sev == "warning":
                items[2].setForeground(QColor(_themed("#f9e2af")))
            for col, it in enumerate(items):
                self.table.setItem(i, col, it)

        btn_row = QHBoxLayout()
        btn_report = QPushButton(_("qa_open_report"))
        btn_report.clicked.connect(self._open_report)
        btn_row.addWidget(btn_report)
        btn_row.addStretch(1)
        self.btn_close = QPushButton(_("qa_close"))
        self.btn_close.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_close)
        lay.addLayout(btn_row)

        # ปุ่มแก้อัตโนมัติ — จำนวนมาจาก JSON (ระยะสอง) หรือ parse จากสรุป (checker เก่า)
        autofix = autofix_count if autofix_count is not None else parse_autofix_count(summary_text)
        if autofix > 0:
            btn_fix = QPushButton(_("qa_autofix", n=autofix))
            btn_fix.setObjectName("btnSave")
            btn_fix.clicked.connect(self._request_fix)
            btn_row.insertWidget(0, btn_fix)

    def _open_report(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.report_path))

    def _request_fix(self):
        if QMessageBox.question(
            self, _("qa_autofix_confirm_title"),
            _("qa_autofix_confirm_msg"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes:
            self.fix_requested.emit()
            self.accept()
