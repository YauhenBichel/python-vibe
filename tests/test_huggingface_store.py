import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from finetune.huggingface_store import (
    BEST_ADAPTER,
    ensure_adapters,
    stage_adapter_bundle,
    write_card,
)
from finetune.models import HF_USER, SPECS, ModelSpec
from finetune.systems import PYTHON_VIBE_SYSTEM


def _spec(root: Path) -> ModelSpec:
    return ModelSpec(
        name="python-vibe",
        mlx_base="mlx-community/Qwen2.5-Coder-0.5B-Instruct-4bit",
        ollama_base="qwen2.5-coder:0.5b",
        hf_repo="YauhenBichel/python-vibe-0.5b",
        system=PYTHON_VIBE_SYSTEM,
        adapter_path=root / "adapters" / "python-vibe",
        fused_path=root / "fused" / "python-vibe",
        ram_mb=400,
    )


class HuggingFaceStoreTest(unittest.TestCase):
    def test_repo_lives_under_yauhenbichel(self) -> None:
        self.assertEqual(HF_USER, "YauhenBichel")
        self.assertEqual(SPECS["python-vibe"].hf_repo, "YauhenBichel/python-vibe-0.5b")
        self.assertEqual(list(SPECS), ["python-vibe"])

    def test_write_card(self) -> None:
        spec = SPECS["python-vibe"]
        with tempfile.TemporaryDirectory() as tmp:
            readme = write_card(spec, Path(tmp))
            text = readme.read_text(encoding="utf-8")
        self.assertIn("python-vibe-0.5b", text)
        self.assertIn("YauhenBichel/python-vibe-0.5b", text)

    def test_stage_prefers_step_100_and_slims_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spec = _spec(Path(tmp))
            spec.adapter_path.mkdir(parents=True)
            (spec.adapter_path / BEST_ADAPTER).write_bytes(b"best")
            (spec.adapter_path / "adapters.safetensors").write_bytes(b"latest")
            (spec.adapter_path / "adapter_config.json").write_text(
                json.dumps(
                    {
                        "fine_tune_type": "lora",
                        "num_layers": 12,
                        "lora_parameters": {"rank": 8},
                        "adapter_path": "/private/tmp/do-not-upload",
                    }
                ),
                encoding="utf-8",
            )
            dest = stage_adapter_bundle(spec)
            self.assertEqual((dest / "adapters.safetensors").read_bytes(), b"best")
            slim = json.loads((dest / "adapter_config.json").read_text(encoding="utf-8"))
            self.assertEqual(set(slim), {"fine_tune_type", "num_layers", "lora_parameters"})
            self.assertTrue((dest / "README.md").is_file())

    def test_ensure_adapters_uses_local_weights(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spec = _spec(Path(tmp))
            spec.adapter_path.mkdir(parents=True)
            (spec.adapter_path / "adapters.safetensors").write_bytes(b"local")
            self.assertEqual(ensure_adapters(spec), spec.adapter_path)


if __name__ == "__main__":
    unittest.main()
