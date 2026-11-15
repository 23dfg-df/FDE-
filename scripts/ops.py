"""只管理本项目用户服务；备份恢复时保留回退副本。"""

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = "fde-capstone.service"


def run(*args):
    return subprocess.run(
        args, check=True, capture_output=True, text=True
    ).stdout.strip()


def hashes(directory):
    return {
        str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    }


def is_active():
    result = subprocess.run(
        ["systemctl", "--user", "is-active", SERVICE], capture_output=True, text=True
    )
    return result.returncode == 0 and result.stdout.strip() == "active"


def require_default_data():
    configured = Path(os.getenv("CAPSTONE_DATA", str(ROOT / "data"))).resolve()
    if configured != (ROOT / "data").resolve():
        raise ValueError(
            "运维脚本仅管理本项目默认 data 目录；"
            "自定义 CAPSTONE_DATA 请使用对应备份流程"
        )


def install():
    if any(x in str(ROOT) for x in ['"', "\n", "%"]):
        raise ValueError("部署目录包含 systemd 特殊字符")
    unit = Path.home() / ".config/systemd/user" / SERVICE
    unit.parent.mkdir(parents=True, exist_ok=True)
    directory = str(ROOT).replace("\\", "\\\\").replace(" ", "\\x20")
    unit.write_text(
        f'''[Unit]
Description=FDE Haystack knowledge lab
After=network.target

[Service]
Type=simple
WorkingDirectory={directory}
ExecStart=/bin/bash "{ROOT}/start.sh"
Restart=on-failure
RestartSec=5
KillMode=control-group
TimeoutStopSec=15

[Install]
WantedBy=default.target
''',
        "utf-8",
    )
    run("systemctl", "--user", "daemon-reload")
    run("systemctl", "--user", "enable", "--now", SERVICE)
    return {"service": SERVICE, "installed": True}


def backup():
    require_default_data()
    backup_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
    destination = ROOT / "backups" / backup_id
    was_active = is_active()
    if was_active:
        run("systemctl", "--user", "stop", SERVICE)
    try:
        shutil.copytree(
            ROOT / "data",
            destination / "data",
            ignore=shutil.ignore_patterns(
                "*.sqlite3", "*.sqlite3-wal", "*.sqlite3-shm"
            ),
        )
        database = ROOT / "data/history.sqlite3"
        if database.exists():
            with (
                sqlite3.connect(database) as source,
                sqlite3.connect(destination / "data/history.sqlite3") as target,
            ):
                source.backup(target)
        manifest = {
            "id": backup_id,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "files": hashes(destination),
        }
        (destination / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), "utf-8"
        )
    finally:
        if was_active:
            run("systemctl", "--user", "start", SERVICE)
    return manifest


def restore(backup_id):
    require_default_data()
    if not backup_id or Path(backup_id).name != backup_id or backup_id.startswith("."):
        raise ValueError("备份编号无效")
    source = ROOT / "backups" / backup_id
    manifest = json.loads((source / "manifest.json").read_text("utf-8"))
    if hashes(source) != manifest["files"]:
        raise ValueError("备份校验失败，未修改运行数据")
    safety = backup()
    staged = ROOT / "backups" / ("restore-staged-" + uuid.uuid4().hex)
    shutil.copytree(source / "data", staged)
    expected = {
        name.removeprefix("data/"): checksum
        for name, checksum in manifest["files"].items()
        if name.startswith("data/")
    }
    if hashes(staged) != expected:
        raise ValueError("恢复暂存文件校验失败，未修改运行数据")
    was_active = is_active()
    if was_active:
        run("systemctl", "--user", "stop", SERVICE)
    displaced = ROOT / "backups" / ("displaced-" + uuid.uuid4().hex)
    moved = False
    try:
        (ROOT / "data").rename(displaced)
        moved = True
        staged.rename(ROOT / "data")
    except Exception:
        if moved:
            if (ROOT / "data").exists():
                (ROOT / "data").rename(
                    ROOT / "backups" / ("failed-restore-" + uuid.uuid4().hex)
                )
            displaced.rename(ROOT / "data")
        raise
    finally:
        if was_active:
            run("systemctl", "--user", "start", SERVICE)
    return {
        "restored": backup_id,
        "safety_backup": safety["id"],
        "previous_data_retained": str(displaced),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["install", "status", "backup", "restore"])
    parser.add_argument("backup_id", nargs="?")
    args = parser.parse_args()
    if args.command == "install":
        result = install()
    elif args.command == "backup":
        result = backup()
    elif args.command == "restore":
        result = restore(args.backup_id)
    else:
        result = {
            "service": SERVICE,
            "status": run("systemctl", "--user", "is-active", SERVICE),
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
