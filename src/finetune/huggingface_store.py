"""Save fused weights and adapters on https://huggingface.co/YauhenBichel."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from finetune.models import HF_USER, ModelSpec
from finetune.paths import PROJECT_ROOT

CARDS = PROJECT_ROOT / "cards"
BEST_ADAPTER = "0000100_adapters.safetensors"
_HUB_CONFIG_KEYS = ("fine_tune_type", "num_layers", "lora_parameters")


def require_token() -> str:
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if token:
        return token
    try:
        from huggingface_hub import get_token

        token = get_token()
    except Exception:
        token = None
    if not token:
        raise SystemExit(
            "No Hugging Face token. Run `huggingface-cli login` or export HF_TOKEN. "
            f"Uploads go to https://huggingface.co/{HF_USER}"
        )
    return token


def write_card(spec: ModelSpec, dest: Path) -> Path:
    src = CARDS / f"{spec.name}.md"
    if not src.is_file():
        raise FileNotFoundError(src)
    dest.mkdir(parents=True, exist_ok=True)
    readme = dest / "README.md"
    readme.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return readme


def push_folder(spec: ModelSpec, folder: Path, *, private: bool, token: str) -> str:
    if not folder.is_dir() or not any(folder.iterdir()):
        raise FileNotFoundError(f"nothing to upload in {folder}")
    from huggingface_hub import HfApi

    write_card(spec, folder)
    api = HfApi(token=token)
    api.create_repo(spec.hf_repo, repo_type="model", private=private, exist_ok=True)
    api.upload_folder(
        folder_path=str(folder),
        repo_id=spec.hf_repo,
        repo_type="model",
        commit_message=f"save {spec.name} ({folder.name})",
    )
    return f"https://huggingface.co/{spec.hf_repo}"


def optional_token() -> str | None:
    try:
        return require_token()
    except SystemExit:
        return None


def _weights_file(adapter_dir: Path) -> Path | None:
    best = adapter_dir / BEST_ADAPTER
    latest = adapter_dir / "adapters.safetensors"
    if best.is_file():
        return best
    if latest.is_file():
        return latest
    return None


def stage_adapter_bundle(spec: ModelSpec) -> Path:
    """Copy the best checkpoint + a path-free config into a folder safe to upload."""
    src = spec.adapter_path
    weights = _weights_file(src)
    if weights is None:
        raise FileNotFoundError(f"no adapters in {src}")
    dest = spec.adapter_path.parent / f"{spec.name}-hub"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    shutil.copy2(weights, dest / "adapters.safetensors")
    cfg_path = src / "adapter_config.json"
    raw = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.is_file() else {}
    slim = {key: raw[key] for key in _HUB_CONFIG_KEYS if key in raw}
    (dest / "adapter_config.json").write_text(
        json.dumps(slim, indent=2) + "\n", encoding="utf-8"
    )
    write_card(spec, dest)
    return dest


def pull_folder(spec: ModelSpec, dest: Path, *, token: str | None) -> Path:
    from huggingface_hub import snapshot_download

    dest.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=spec.hf_repo,
        local_dir=str(dest),
        token=token,
    )
    return dest


def ensure_adapters(spec: ModelSpec) -> Path:
    """Local adapters if present; otherwise download the public Hub repo."""
    if _weights_file(spec.adapter_path) is not None:
        return spec.adapter_path
    print(f"downloading https://huggingface.co/{spec.hf_repo} → {spec.adapter_path}")
    return pull_folder(spec, spec.adapter_path, token=optional_token())
