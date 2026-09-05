import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from finetune.hf_ollama import (
    IMPORTS,
    LAPTOP_QUANT,
    gguf_filename,
    import_one,
    names,
    resolve,
    write_modelfile,
)


class HfOllamaImportTest(unittest.TestCase):
    def test_catalog_is_the_two_hf_only_laptop_tags(self) -> None:
        self.assertEqual(names(), ["opencoder", "swe-agent-lm"])
        open_coder = IMPORTS["opencoder"]
        swe = IMPORTS["swe-agent-lm"]
        self.assertEqual(open_coder.ollama_tag, "opencoder:8b")
        self.assertEqual(swe.ollama_tag, "swe-agent-lm:7b")
        self.assertEqual(open_coder.source, "infly/OpenCoder-8B-Instruct")
        self.assertEqual(swe.source, "SWE-bench/SWE-agent-LM-7B")
        self.assertEqual(open_coder.default_quant, LAPTOP_QUANT)
        self.assertEqual(swe.default_quant, LAPTOP_QUANT)
        self.assertLessEqual(open_coder.about_gb, 6)
        self.assertLessEqual(swe.about_gb, 6)

    def test_gguf_filenames_match_the_hub_repos(self) -> None:
        self.assertEqual(
            gguf_filename(IMPORTS["opencoder"]),
            "OpenCoder-8B-Instruct-Q4_K_M.gguf",
        )
        self.assertEqual(
            gguf_filename(IMPORTS["swe-agent-lm"]),
            "SWE-agent-LM-7B.Q4_K_M.gguf",
        )
        self.assertEqual(
            gguf_filename(IMPORTS["opencoder"], "Q5_K_M"),
            "OpenCoder-8B-Instruct-Q5_K_M.gguf",
        )

    def test_unknown_name_lists_the_catalog(self) -> None:
        with self.assertRaises(SystemExit) as caught:
            resolve("starcoder2")
        self.assertIn("opencoder", str(caught.exception))
        self.assertIn("swe-agent-lm", str(caught.exception))

    def test_modelfile_is_from_gguf_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gguf = Path(tmp) / "model.gguf"
            gguf.write_bytes(b"GGUF")
            dest = Path(tmp) / "Modelfile"
            write_modelfile(gguf, dest)
            text = dest.read_text(encoding="utf-8")
        self.assertEqual(text, f"FROM {gguf.resolve()}\n")
        self.assertNotIn("SYSTEM", text)

    def test_import_downloads_then_creates_the_ollama_tag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gguf = Path(tmp) / "OpenCoder-8B-Instruct-Q4_K_M.gguf"
            gguf.write_bytes(b"GGUF")
            seen: list[tuple[str, Path]] = []

            def fake_download(repo_id: str, filename: str) -> Path:
                self.assertEqual(repo_id, "bartowski/OpenCoder-8B-Instruct-GGUF")
                self.assertEqual(filename, gguf.name)
                return gguf

            def fake_create(tag: str, path: Path) -> None:
                seen.append((tag, path))

            spec, path = import_one(
                "opencoder",
                downloader=fake_download,
                creator=fake_create,
            )
        self.assertEqual(spec.ollama_tag, "opencoder:8b")
        self.assertEqual(path, gguf)
        self.assertEqual(seen, [("opencoder:8b", gguf)])

    def test_no_create_skips_ollama(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gguf = Path(tmp) / "SWE-agent-LM-7B.Q4_K_M.gguf"
            gguf.write_bytes(b"GGUF")

            def fake_download(repo_id: str, filename: str) -> Path:
                self.assertEqual(repo_id, "mradermacher/SWE-agent-LM-7B-GGUF")
                return gguf

            spec, path = import_one(
                "swe-agent-lm",
                create=False,
                downloader=fake_download,
                creator=lambda tag, gguf_path: self.fail("create ran"),
            )
        self.assertEqual(spec.ollama_tag, "swe-agent-lm:7b")
        self.assertEqual(path, gguf)


if __name__ == "__main__":
    unittest.main()
