"""下载固定版本的腾讯混元权重，并记录文件校验；不启动 GPU。"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("HF_ENDPOINT", "https://huggingface.co")
os.environ["HF_HUB_OFFLINE"] = "0"
os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "120"

from huggingface_hub import HfApi, snapshot_download  # noqa: E402

REPOSITORY = "tencent/Hunyuan-1.8B-Instruct"
REVISION = "de940610ab5d45b4fedbd37e08444d0dc502837c"
ROOT = Path(__file__).resolve().parents[1]
DESTINATION = Path(os.getenv("FDE_MODEL_PATH", str(ROOT.parent / "models/Hunyuan-1.8B-Instruct")))


def main():
    info = HfApi().model_info(REPOSITORY, revision=REVISION, files_metadata=True)
    if info.sha != REVISION:
        raise RuntimeError("模型版本与固定提交不一致")
    snapshot_download(
        REPOSITORY,
        revision=REVISION,
        local_dir=DESTINATION,
        allow_patterns=["*.json", "*.safetensors", "LICENSE*", "Notice*", "README*"],
        max_workers=2,
    )
    files = []
    for item in info.siblings:
        path = DESTINATION / item.rfilename
        if not path.is_file():
            continue
        with path.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        expected = item.lfs.sha256 if item.lfs else None
        if expected and digest != expected:
            raise RuntimeError(f"文件 SHA256 不符：{path.name}")
        files.append(
            {
                "file": path.name,
                "bytes": path.stat().st_size,
                "sha256": digest,
                "upstream_lfs_sha256": expected,
            }
        )
    report = {
        "model": REPOSITORY,
        "revision": REVISION,
        "endpoint": os.environ["HF_ENDPOINT"],
        "path": str(DESTINATION),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }
    destination = ROOT / "evidence/hunyuan-migration/model-manifest.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
