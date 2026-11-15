"""Package the reviewed learning sources and a standalone HTML, without private data."""
from __future__ import annotations
import argparse
import hashlib
import json
import zipfile
from pathlib import Path
import build

PATTERNS = ["README.md", "PROGRESS.md", "AUTHORING.md", "build.py", "package.py", "content/*.json", "web/*", "labs/*.py", "labs/*.md", "tests/*.py", "tests/*.cjs", "templates/*.md", "docs/*.md", "evidence/*-checks.json", "evidence/validation.json"]


def package(destination):
    root = Path(__file__).resolve().parent
    stats = build.build(root / "dist/index.html", root / "docs")
    files = sorted({p for pattern in PATTERNS for p in root.glob(pattern) if p.is_file() and not p.is_symlink()})
    manifest = {"scope": "original_learning_content_and_cpu_labs", "version": build.VERSION,
                "files": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
                "excluded": ["personal learning records", "credentials", "runtime environments", "model weights", "browser screenshots"]}
    manifest["files"]["FDE完整学习知识库.html"] = stats["html_sha256"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files: archive.write(path, "FDE-learning/" + str(path.relative_to(root)))
        archive.write(root / "dist/index.html", "FDE-learning/FDE完整学习知识库.html")
        archive.writestr("FDE-learning/MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None: raise ValueError("ZIP integrity check failed")
    return {"file": str(destination), "files": len(files) + 2, "bytes": destination.stat().st_size,
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(), "content": stats}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(package(args.output), ensure_ascii=False, indent=2))
