"""Load MLX LoRA or Ollama once; reuse for a batch of prompts."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from finetune.huggingface_store import BEST_ADAPTER, ensure_adapters
from finetune.models import SPECS
from finetune.paths import PROJECT_ROOT
from harness.paths import venv_python


def mlx_pythons() -> list[str]:
    extra = os.environ.get("MLX_PYTHON", "")
    return [
        sys.executable,
        str(venv_python(PROJECT_ROOT / ".venv")),
        *([extra] if extra else []),
    ]


def has_mlx(exe: str) -> bool:
    if not Path(exe).is_file():
        return False
    probe = subprocess.run([exe, "-c", "import mlx_lm"], capture_output=True)
    return probe.returncode == 0


def reexec_for_mlx() -> None:
    try:
        import mlx_lm  # noqa: F401
        return
    except ImportError:
        pass
    for exe in mlx_pythons():
        if exe == sys.executable:
            continue
        if has_mlx(exe):
            os.execv(exe, [exe, *sys.argv])
    sys.exit("mlx-lm missing. Use the Homebrew 3.13 venv or pass --engine ollama")


def _stage_best(adapter_dir: Path) -> Path:
    ckpt = adapter_dir / BEST_ADAPTER
    if not ckpt.is_file():
        sys.exit(f"no best checkpoint: {ckpt}")
    staging = adapter_dir.parent / "python-vibe-100"
    staging.mkdir(parents=True, exist_ok=True)
    dest = staging / "adapters.safetensors"
    cfg = staging / "adapter_config.json"
    src_cfg = adapter_dir / "adapter_config.json"
    if dest.exists() or dest.is_symlink():
        dest.unlink()
    dest.symlink_to(ckpt.resolve())
    if src_cfg.is_file():
        if cfg.exists() or cfg.is_symlink():
            cfg.unlink()
        cfg.symlink_to(src_cfg.resolve())
    return staging


def make_generate(
    engine: str,
    max_tokens: int,
    *,
    model: str | None = None,
    system: str | None = None,
    memory=None,
    adapters: bool = True,
) -> tuple[str, Callable[[str], str]]:
    """A label and a function that answers one prompt.

    `memory` is whatever the harness is using to remember the run. It
    only has to answer `messages(prompt)`. Nothing here decides what is
    remembered or forgotten: that belongs to the harness, and this
    package does not import it.
    """
    if engine == "auto":
        engine = "mlx" if any(has_mlx(p) for p in mlx_pythons()) else "ollama"
    if engine == "mlx":
        return _mlx_generate(
            max_tokens, system=system, memory=memory, adapters=adapters
        )
    if engine == "openai":
        return _openai_generate(
            max_tokens, model=model, system=system, memory=memory
        )
    if engine != "ollama":
        sys.exit(f"unknown engine {engine!r}: use ollama, mlx, or openai")
    return _ollama_generate(model=model, system=system, memory=memory)


def _mlx_generate(
    max_tokens: int,
    *,
    system: str | None = None,
    memory=None,
    adapters: bool = True,
) -> tuple[str, Callable[[str], str]]:
    reexec_for_mlx()
    from mlx_lm import generate, load

    spec = SPECS["python-vibe"]
    adapter_path: str | None = None
    label = f"mlx-base:{spec.mlx_base}"
    if adapters:
        local = ensure_adapters(spec)
        adapter = _stage_best(local) if (local / BEST_ADAPTER).is_file() else local
        adapter_path = str(adapter)
        label = f"mlx-lora:{adapter.name}"
    model, tokenizer = load(spec.mlx_base, adapter_path=adapter_path)

    def generate_once(prompt: str) -> str:
        text = tokenizer.apply_chat_template(
            memory.messages(prompt), tokenize=False, add_generation_prompt=True
        )
        return generate(model, tokenizer, prompt=text, max_tokens=max_tokens)

    generate_once.memory = memory  # type: ignore[attr-defined]
    return label, generate_once


def _openai_generate(
    max_tokens: int,
    *,
    model: str | None = None,
    system: str | None = None,
    memory=None,
) -> tuple[str, Callable[[str], str]]:
    from harness.model.openai_generate import OpenAIGenerate

    spec = SPECS["python-vibe"]
    name = model or spec.ollama_base
    try:
        backend = OpenAIGenerate(
            name, system or spec.system, max_tokens=max_tokens
        )
    except ValueError as exc:
        sys.exit(str(exc))
    def generate_once(prompt: str) -> str:
        return backend.send(memory.messages(prompt))

    generate_once.memory = memory  # type: ignore[attr-defined]
    return f"openai:{name}", generate_once


def _ollama_generate(
    *, model: str | None = None, system: str | None = None, memory=None
) -> tuple[str, Callable[[str], str]]:
    from harness.model.ollama_generate import OllamaGenerate

    spec = SPECS["python-vibe"]
    name = model or spec.ollama_base
    backend = OllamaGenerate(name, system or spec.system)
    if not backend.healthy():
        sys.exit(f"ollama {backend.host} is down")
    def generate_once(prompt: str) -> str:
        return backend.send(memory.messages(prompt))

    generate_once.memory = memory  # type: ignore[attr-defined]
    return f"ollama:{name}", generate_once
