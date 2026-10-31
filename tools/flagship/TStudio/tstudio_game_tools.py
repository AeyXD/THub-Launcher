# -*- coding: utf-8 -*-
"""tstudio_game_tools.py — runtime สำหรับ Game Tools (spec: docs/spec-game-tools.md Phase C)

Game Tool คือ unpacker/packer รายเกมจาก TFormat-Plugins (Game_Extractors/) ที่ติดตั้งผ่าน
Plugin Manager ลง CustomParsers/GameTools/<Game>/ — ทุกอย่างขับด้วย manifest tool.json
(THL ไม่ hardcode ชื่อเกม/คำสรัฐ) · subprocess loose coupling แบบเดียวกับ QA bridge ·
offline-friendly: เกมที่ติดตั้งแล้วใช้งานได้โดยไม่ต้องมีเน็ต
"""
import json
import os
import subprocess
import sys

import file_converter

GAMETOOLS_DIR = os.path.join(file_converter.CUSTOM_PARSERS_DIR, "GameTools")

# GitHub source เดียวกับ plugin ทั่วไป (fork AeyXD/TFormat-Plugins)
GAMETOOLS_API_BASE = "https://api.github.com/repos/AeyXD/TFormat-Plugins/contents/Game_Extractors"

TOOL_TIMEOUT = 300  # วินาที — unpack/pack ปกติเสร็จในวินาทีเดียว ตั้งกันงานไฟล์ใหญ่พิเศษ


def installed_tools():
    """คืน {game_name: manifest} ของ Game Tools ที่ติดตั้งอยู่ในเครื่อง (อ่าน tool.json)"""
    tools = {}
    if not os.path.isdir(GAMETOOLS_DIR):
        return tools
    for game in sorted(os.listdir(GAMETOOLS_DIR)):
        mf = os.path.join(GAMETOOLS_DIR, game, "tool.json")
        if os.path.isfile(mf):
            try:
                with open(mf, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                if data.get("game") and data.get("unpack_cmd"):
                    tools[data["game"]] = data
            except Exception as e:
                print(f"GameTools: อ่าน {mf} ไม่ได้ — {e}")
    return tools


def tool_dir(manifest):
    return os.path.join(GAMETOOLS_DIR, manifest.get("game", ""))


def tool_for_file(path):
    """หา Game Tool ที่รองรับนามสกุลของไฟล์นี้ (ใช้ตอนเสนอ Pack กลับจาก origin_file)"""
    ext = os.path.splitext(path or "")[1].lower()
    for manifest in installed_tools().values():
        if ext in [e.lower() for e in manifest.get("file_extensions", [])]:
            return manifest
    return None


def build_cmd(cmd_template, manifest, mapping):
    """เติม sys.executable + path สคริปต์ + placeholder ให้เป็น argv เต็ม
    cmd_template รูปแบบตาม tool.json: ["Boltgun_unpacker.py", "{input}", "{output_csv}"]"""
    if not cmd_template:
        return None
    argv = [sys.executable, os.path.join(tool_dir(manifest), cmd_template[0])]
    for arg in cmd_template[1:]:
        for key, val in mapping.items():
            arg = arg.replace("{" + key + "}", val)
        argv.append(arg)
    return argv


def run_tool(cmd_template, manifest, mapping, timeout=TOOL_TIMEOUT):
    """รัน Game Tool ผ่าน subprocess (guard Windows ตามกฎเหล็กข้อ 3)
    คืน (ok, combined_output) — exit 0 = สำเร็จตาม contract ของ Phase A"""
    argv = build_cmd(cmd_template, manifest, mapping)
    if argv is None:
        return False, "tool.json ไม่มีคำสั่งสำหรับขั้นตอนนี้"
    script = argv[1]
    if not os.path.isfile(script):
        return False, f"ไม่พบสคริปต์ Game Tool: {script}"
    try:
        proc = subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout,
            creationflags=0x08000000 if os.name == "nt" else 0
        )
    except subprocess.TimeoutExpired:
        return False, f"หมดเวลา {timeout} วินาที"
    except Exception as e:
        return False, str(e)
    out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    return proc.returncode == 0, out


def unpack(manifest, input_path, output_csv):
    """แตกไฟล์เกม → CSV กลาง (ID, Source, Translation, AI_Reference)"""
    return run_tool(manifest.get("unpack_cmd"), manifest,
                    {"input": input_path, "output_csv": output_csv})


def pack(manifest, original_path, csv_path, output_path):
    """pack CSV กลับเป็นไฟล์เกม (manifest ที่ pack_cmd = null จะคืน not ok)"""
    if not manifest.get("pack_cmd"):
        return False, "เกมนี้รองรับเฉพาะการแตกไฟล์ (ไม่มี pack_cmd)"
    return run_tool(manifest.get("pack_cmd"), manifest,
                    {"original": original_path, "csv": csv_path, "output": output_path})


def default_extract_csv_path(input_path):
    """ตำแหน่ง CSV ที่สร้างจากการแตกไฟล์ — อยู่ข้างไฟล์ต้นทาง ไม่ทับไฟล์เดิม"""
    stem = os.path.splitext(os.path.basename(input_path))[0]
    return os.path.join(os.path.dirname(os.path.abspath(input_path)), f"{stem}_extracted.csv")
