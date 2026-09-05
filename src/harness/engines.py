"""Load a local generate() callable: MLX LoRA, MLX base, or Ollama."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from finetune.models import ModelSpec
from finetune.paths import PROJECT_ROOT

GenerateFn = Callable[[str], str]


def mlx_python_candidates() -> list[str]:
    home = Path.home()
    return [
        sys.executable,
        str(PROJECT_ROOT / ".venv" / "bin" / "python"),
        str(home / "DevBox/tracer-cloud/llm-finetunes/.venv/bin/python"),
        str(home / "DevBox/molecare/skincare-qa/.venv/bin/python"),
    ]


def has_mlx(exe: str) -> bool:
    if not Path(exe).is_file():
        return False
    probe = subprocess.run(
        [exe, "-c", "import mlx_lm"], capture_output=True, text=True
    )
    return probe.returncode == 0


def reexec_for_mlx() -> None:
    try:
        import mlx_lm  # noqa: F401
        return
    except ImportError:
        pass
    for exe in mlx_python_candidates():
        if exe == sys.executable:
            continue
        if has_mlx(exe):
            os.execv(exe, [exe, *sys.argv])
    sys.exit("mlx-lm missing. Use the Homebrew 3.13 venv or pass --engine ollama")


def any_mlx() -> bool:
    return any(has_mlx(path) for path in mlx_python_candidates())


def _attach_history(generate_once: GenerateFn, history: list[dict[str, str]]) -> GenerateFn:
    generate_once.history = history  # type: ignore[attr-defined]
    return generate_once


def stage_best_adapter(adapter_dir: Path) -> Path:
    from finetune.huggingface_store import BEST_ADAPTER

    ckpt = adapter_dir / BEST_ADAPTER
    if not ckpt.is_file():
        raise FileNotFoundError(f"no best checkpoint: {ckpt}")
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


def make_mlx(
    spec: ModelSpec,
    max_tokens: int,
    *,
    adapters: bool = True,
    temperature: float = 0.0,
    top_p: float = 0.8,
) -> tuple[str, GenerateFn]:
    reexec_for_mlx()
    from mlx_lm import generate, load

    from finetune.huggingface_store import BEST_ADAPTER, ensure_adapters

    adapter_path: str | None = None
    label = f"mlx-base:{spec.mlx_base}"
    if adapters:
        local = ensure_adapters(spec)
        staged = stage_best_adapter(local) if (local / BEST_ADAPTER).is_file() else local
        adapter_path = str(staged)
        label = f"mlx-lora:{Path(adapter_path).name}"
    model, tokenizer = load(spec.mlx_base, adapter_path=adapter_path)
    history: list[dict[str, str]] = []
    sampler = None
    if temperature > 0:
        from mlx_lm.sample_utils import make_sampler

        sampler = make_sampler(temp=temperature, top_p=top_p)

    def generate_once(prompt: str) -> str:
        messages = (
            [{"role": "system", "content": spec.system}]
            + history
            + [{"role": "user", "content": prompt}]
        )
        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        return generate(
            model,
            tokenizer,
            prompt=text,
            max_tokens=max_tokens,
            sampler=sampler,
        )

    return label, _attach_history(generate_once, history)


def make_ollama(
    spec: ModelSpec,
    *,
    temperature: float | None = None,
    top_p: float | None = None,
) -> tuple[str, GenerateFn]:
    from harness.ollama_generate import OllamaGenerate

    backend = OllamaGenerate(
        spec.ollama_base, spec.system, temperature=temperature, top_p=top_p
    )
    if not backend.healthy():
        sys.exit(f"ollama {backend.host} is down")
    history: list[dict[str, str]] = []

    def generate_once(prompt: str) -> str:
        return backend(prompt, history)

    return f"ollama:{spec.ollama_base}", _attach_history(generate_once, history)


HINT_SYSTEM = "You write one-line bug hints. No code. No fences."


def make_hint(model: str) -> GenerateFn | None:
    from harness.ollama_generate import OllamaGenerate

    backend = OllamaGenerate(model, HINT_SYSTEM, temperature=0.0)
    if not backend.healthy():
        return None

    def generate_once(prompt: str) -> str:
        return backend(prompt)

    return generate_once


def remember(generate_once: GenerateFn, prompt: str, draft: str) -> None:
    history = getattr(generate_once, "history", None)
    if history is None:
        return
    history.append({"role": "user", "content": prompt})
    history.append({"role": "assistant", "content": draft})
