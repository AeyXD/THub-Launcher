# -*- coding: utf-8 -*-
"""open_utils — เปิดไฟล์/โฟลเดอร์ด้วยโปรแกรมปริยายของระบบ ข้ามทุก platform

os.startfile มีเฉพาะ Windows (เรียกบน macOS/Linux = AttributeError ทันที) —
ทุกจุดที่เคยใช้ให้เปลี่ยนมาใช้ open_path() นี้แทน
"""
import os
import subprocess
import sys


def open_path(path):
    """เปิด path (ไฟล์/โฟลเดอร์) ด้วยโปรแกรมปริยายของ OS · คืน True เมื่อสั่งเปิดสำเร็จ

    Windows: os.startfile · macOS: `open` · Linux: `xdg-open`
    path ไม่มีอยู่จริง → คืน False ทันที (ผู้เรียกแจ้งผู้ใช้เองตามบริบท)
    """
    path = os.path.abspath(str(path))
    if not os.path.exists(path):
        return False
    try:
        if sys.platform == "win32":
            os.startfile(path)  # Windows-only API
            return True
        if sys.platform == "darwin":
            subprocess.Popen(["open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        subprocess.Popen(["xdg-open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False
