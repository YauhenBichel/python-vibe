import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from finetune.huggingface_store import stage_adapter_bundle, write_card
from finetune.models import OFFICIAL_HF_REPO, SPECS, publish_hf_repo


class HuggingFaceStoreTest(unittest.TestCase):
    def test_official_download_repo_is_documented(self) -> None:
        self.assertEqual(OFFICIAL_HF_REPO, "YauhenBichel/python-vibe-0.5b")
        self.assertEqual(SPECS["python-vibe"].hf_repo, OFFICIAL_HF_REPO)
        self.assertEqual(list(SPECS), ["python-vibe"])

    def test_publish_uses_hf_user_not_official_account(self) -> None:
        import os

        spec = SPECS["python-vibe"]
        env = os.environ
        old_repo, old_user = env.get("HF_REPO"), env.get("HF_USER")
        env.pop("HF_REPO", None)
        env["HF_USER"] = "alice"
        try:
            self.assertEqual(publish_hf_repo(spec), "alice/python-vibe-0.5b")
        finally:
            env.pop("HF_USER", None)
            if old_user is not None:
                env["HF_USER"] = old_user
            if old_repo is not None:
                env["HF_REPO"] = old_repo

    def test_write_card(self) -> None:
        spec = SPECS["python-vibe"]
        with tempfile.TemporaryDirectory() as tmp:
            readme = write_card(spec, Path(tmp))
            text = readme.read_text(encoding="utf-8")
        self.assertIn("python-vibe-0.5b", text)
        self.assertIn("YauhenBichel/python-vibe-0.5b", text)
        self.assertIn("hf download YauhenBichel/python-vibe-0.5b", text)
        self.assertIn("github.com/YauhenBichel/py-harness", text)
        self.assertIn("formerly python-vibe", text)
        self.assertIn("py-harness brief", text)
        self.assertIn("## Experiments", text)
        self.assertIn("Not everyday-ready", text)
        self.assertIn("8 / 9", text)
        self.assertIn("0 / 54", text)

    def test_stage_adapter_bundle_drops_local_paths(self) -> None:
        spec = SPECS["python-vibe"]
        if not (spec.adapter_path / "adapter_config.json").is_file():
            self.skipTest("local adapters not on this machine")
        dest = stage_adapter_bundle(spec)
        cfg = json.loads((dest / "adapter_config.json").read_text(encoding="utf-8"))
        dumped = json.dumps(cfg)
        self.assertNotIn("/Users/", dumped)
        self.assertIn("lora_parameters", cfg)
        self.assertTrue((dest / "adapters.safetensors").is_file())
        self.assertTrue((dest / "README.md").is_file())


if __name__ == "__main__":
    unittest.main()
