"""Hugging Face GGUFs that are not in the Ollama library.

OpenCoder 8B and SWE-agent-LM 7B fit this laptop as Q4_K_M (~4.7 GB
each). They are not `ollama pull` tags. Download the GGUF, write a
Modelfile that only names the file, then `ollama create`. The harness
already sends the agent system prompt; do not bake it into the tag.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

Downloader = Callable[[str, str], Path]
Creator = Callable[[str, Path], None]


@dataclass(frozen=True)
class ImportSpec:
    key: str
    ollama_tag: str
    source: str
    gguf_repo: str
    filename: str
    default_quant: str
    about_gb: float
    license: str
    note: str


IMPORTS: dict[str, ImportSpec] = {
    "opencoder": ImportSpec(
        key="opencoder",
        ollama_tag="opencoder:8b",
        source="infly/OpenCoder-8B-Instruct",
        gguf_repo="bartowski/OpenCoder-8B-Instruct-GGUF",
        filename="OpenCoder-8B-Instruct-{quant}.gguf",
        default_quant="Q4_K_M",
        about_gb=4.7,
        license="INF",
        note="Code instruct. Not trained on python-vibe Action:.",
    ),
    "swe-agent-lm": ImportSpec(
        key="swe-agent-lm",
        ollama_tag="swe-agent-lm:7b",
        source="SWE-bench/SWE-agent-LM-7B",
        gguf_repo="mradermacher/SWE-agent-LM-7B-GGUF",
        filename="SWE-agent-LM-7B.{quant}.gguf",
        default_quant="Q4_K_M",
        about_gb=4.7,
        license="Apache-2.0",
        note="Qwen2.5-Coder-7B-Instruct plus 5k SWE-agent traces. Their tools, not Action:.",
    ),
}

LAPTOP_QUANT = "Q4_K_M"


def resolve(name: str) -> ImportSpec:
    try:
        return IMPORTS[name]
    except KeyError:
        known = ", ".join(sorted(IMPORTS))
        raise SystemExit(f"unknown import {name!r}: use {known}") from None


def names() -> list[str]:
    return sorted(IMPORTS)


def gguf_filename(spec: ImportSpec, quant: str | None = None) -> str:
    chosen = (quant or spec.default_quant).strip()
    if not chosen:
        raise SystemExit("quant is empty")
    return spec.filename.format(quant=chosen)


def write_modelfile(gguf: Path, dest: Path) -> Path:
    if not gguf.is_file():
        raise SystemExit(f"no GGUF: {gguf}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(f"FROM {gguf.resolve()}\n", encoding="utf-8")
    return dest


def _hf_download(repo_id: str, filename: str) -> Path:
    from huggingface_hub import hf_hub_download

    from finetune.huggingface_store import optional_token

    return Path(
        hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            token=optional_token(),
        )
    )


def download_gguf(
    spec: ImportSpec,
    *,
    quant: str | None = None,
    downloader: Downloader | None = None,
) -> Path:
    filename = gguf_filename(spec, quant)
    print(f"downloading https://huggingface.co/{spec.gguf_repo}/{filename}")
    fetch = downloader or _hf_download
    return fetch(spec.gguf_repo, filename)


def _ollama_create(tag: str, gguf: Path) -> None:
    ollama = shutil.which("ollama")
    if not ollama:
        raise SystemExit("ollama not on PATH")
    with tempfile.TemporaryDirectory() as tmp:
        dest = write_modelfile(gguf, Path(tmp) / "Modelfile")
        subprocess.check_call([ollama, "create", tag, "-f", str(dest)])


def import_one(
    name: str,
    *,
    quant: str | None = None,
    create: bool = True,
    downloader: Downloader | None = None,
    creator: Creator | None = None,
) -> tuple[ImportSpec, Path]:
    spec = resolve(name)
    gguf = download_gguf(spec, quant=quant, downloader=downloader)
    if create:
        make = creator or _ollama_create
        make(spec.ollama_tag, gguf)
    return spec, gguf


def import_many(
    keys: Sequence[str],
    *,
    quant: str | None = None,
    create: bool = True,
    downloader: Downloader | None = None,
    creator: Creator | None = None,
) -> list[tuple[ImportSpec, Path]]:
    return [
        import_one(
            key,
            quant=quant,
            create=create,
            downloader=downloader,
            creator=creator,
        )
        for key in keys
    ]
