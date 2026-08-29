import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# A real personal path has a name and something after it. A page that states
# the rule writes the bare prefix, as in: No `/Users/` or `C:\`.
_PERSONAL_PATH = re.compile(r"/Users/[^/\s`'\"]+/|DevBox/[^\s`'\"]")
DOCS = ROOT / "docs"

_CHAT_PRODUCTS = re.compile(r"\b(ChatGPT|Claude|Grok)\b")
_CURSOR = re.compile(r"\bCursor\b")


class PagesInvestigationsTest(unittest.TestCase):
    def test_site_files_exist(self) -> None:
        required = (
            "_config.yml",
            "_layouts/default.html",
            "_includes/site.css",
            "_includes/nav.html",
            "index.md",
            "start.md",
            "scenarios.md",
            "api.md",
            "architecture.md",
            "skills.md",
            "demo.md",
            "local-editor.md",
            "ide-plugins.md",
            "cursor.md",
            "research-vibe-review.md",
            "investigations/index.md",
            "investigations/which-model.md",
            "investigations/everyday-laptop.md",
            "investigations/everyday-skills.md",
            "investigations/harness-comparison.md",
            "investigations/local-vs-cloud.md",
            "investigations/same-jobs.md",
            "investigations/what-to-improve.md",
            "investigations/small-llm-harness.md",
            "investigations/platform-engineering.md",
            "investigations/fine-tune-or-harness.md",
            "investigations/model-lanes.md",
            "investigations/hub-models.md",
        )
        missing = [name for name in required if not (DOCS / name).is_file()]
        self.assertEqual(missing, [])

    def test_skills_page_lists_every_kit_skill(self) -> None:
        page = (DOCS / "skills.md").read_text(encoding="utf-8")
        names = sorted(
            path.parent.name
            for path in (ROOT / "skills").glob("*/SKILL.md")
        )
        self.assertGreaterEqual(len(names), 14)
        missing = [name for name in names if f"`{name}`" not in page]
        self.assertEqual(missing, [])

    def test_seo_and_llm_discovery_files_exist(self) -> None:
        required = (
            "robots.md",
            "sitemap.md",
            "llms.md",
            "llms-full.md",
            "_includes/head-seo.html",
            "_includes/schema.html",
        )
        missing = [name for name in required if not (DOCS / name).is_file()]
        self.assertEqual(missing, [])
        llms = (DOCS / "llms.md").read_text(encoding="utf-8")
        self.assertIn("# python-vibe", llms)
        self.assertIn("permalink: /llms.txt", llms)
        self.assertIn("> ", llms)
        full = (DOCS / "llms-full.md").read_text(encoding="utf-8")
        self.assertIn("permalink: /llms-full.txt", full)
        self.assertIn("Do not call the project everyday-ready", full)
        robots = (DOCS / "robots.md").read_text(encoding="utf-8")
        self.assertIn("Allow: /", robots)
        self.assertIn("Sitemap:", robots)
        sitemap = (DOCS / "sitemap.md").read_text(encoding="utf-8")
        self.assertIn("urlset", sitemap)
        self.assertIn("/llms.txt", sitemap)
        layout = (DOCS / "_layouts" / "default.html").read_text(encoding="utf-8")
        self.assertIn("head-seo.html", layout)
        seo = (DOCS / "_includes" / "head-seo.html").read_text(encoding="utf-8")
        self.assertIn('rel="canonical"', seo)
        self.assertIn('rel="describedby"', seo)
        self.assertIn('type="text/markdown"', seo)
        self.assertIn("application/ld+json", (DOCS / "_includes" / "schema.html").read_text(encoding="utf-8"))
        self.assertIn("SoftwareSourceCode", (DOCS / "_includes" / "schema.html").read_text(encoding="utf-8"))
        self.assertIn("robots: noindex", (DOCS / "404.md").read_text(encoding="utf-8"))

    def test_layout_inlines_css_and_is_keyboard_usable(self) -> None:
        layout = (DOCS / "_layouts" / "default.html").read_text(encoding="utf-8")
        css = (DOCS / "_includes" / "site.css").read_text(encoding="utf-8")
        self.assertIn("{% include site.css %}", layout)
        self.assertNotIn('rel="stylesheet"', layout)
        self.assertIn('href="#main"', layout)
        self.assertIn('id="main"', layout)
        nav = (DOCS / "_includes" / "nav.html").read_text(encoding="utf-8")
        self.assertIn("aria-current", nav)
        labels = re.findall(r">([^<{]+)</a>", nav)
        labels = [item.strip() for item in labels if item.strip()]
        self.assertEqual(labels, list(dict.fromkeys(labels)), labels)
        self.assertEqual(labels.count("Demo"), 1)
        self.assertIn(":focus-visible", css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn("prefers-color-scheme: dark", css)
        self.assertIn("color-scheme: light dark", css)
        self.assertLess(len(css.encode("utf-8")), 9000)

    def test_no_personal_devbox_paths_in_pages(self) -> None:
        hits: list[str] = []
        for path in DOCS.rglob("*"):
            if not path.is_file() or path.suffix not in {".md", ".html", ".css", ".yml"}:
                continue
            text = path.read_text(encoding="utf-8")
            if _PERSONAL_PATH.search(text):
                hits.append(str(path.relative_to(ROOT)))
        self.assertEqual(hits, [])

    def test_public_copy_does_not_name_other_editors(self) -> None:
        hits: list[str] = []
        for path in DOCS.rglob("*"):
            if not path.is_file() or path.suffix not in {".md", ".html", ".css"}:
                continue
            rel = path.relative_to(DOCS)
            allow_cursor = rel.parts[0] != "investigations"
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if _CHAT_PRODUCTS.search(line):
                    hits.append(f"{path.relative_to(ROOT)}:{i}")
                elif _CURSOR.search(line) and not allow_cursor:
                    hits.append(f"{path.relative_to(ROOT)}:{i}")
        self.assertEqual(hits, [])


def _front_matter(path: Path) -> dict[str, str]:
    """The YAML block at the top of a Jekyll page, as plain key/value pairs."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, sep, value = line.partition(":")
        if sep and not key.startswith(" "):
            fields[key.strip()] = value.strip()
    return fields


def _site_pages() -> list[Path]:
    """Pages the site renders, excluding includes, layouts and raw files."""
    return sorted(
        path
        for path in DOCS.rglob("*.md")
        if "_includes" not in path.parts and "_layouts" not in path.parts
    )


class SiteFrontMatterTest(unittest.TestCase):
    """A page with no front matter publishes untitled and unlisted."""

    def test_every_page_has_front_matter(self) -> None:
        missing = [
            str(path.relative_to(ROOT))
            for path in _site_pages()
            if not _front_matter(path)
        ]
        self.assertEqual(missing, [])

    def test_every_rendered_page_has_a_title(self) -> None:
        missing = [
            str(path.relative_to(ROOT))
            for path in _site_pages()
            if _front_matter(path).get("layout") != "null"
            and not _front_matter(path).get("title")
        ]
        self.assertEqual(missing, [])

    def test_every_rendered_page_has_a_description(self) -> None:
        missing = [
            str(path.relative_to(ROOT))
            for path in _site_pages()
            if _front_matter(path).get("layout") != "null"
            and path.name not in {"404.md", "index.md"}
            and not _front_matter(path).get("description")
        ]
        self.assertEqual(missing, [])

    def test_every_rendered_page_is_listed_in_llms_txt(self) -> None:
        """llms.txt names every page, and names each one once.

        It is written by hand, so it drifts: a page added to the site and
        the sitemap was missing here, and one page was listed twice. The
        sitemap has had this check; this file had none.
        """
        text = (DOCS / "llms.md").read_text(encoding="utf-8")
        # Only the list entries. The prose above them names "/" as well.
        listing = "\n".join(
            line for line in text.splitlines() if line.startswith("- [")
        )
        missing, urls = [], []
        for path in _site_pages():
            fields = _front_matter(path)
            if fields.get("layout") == "null" or path.name == "404.md":
                continue
            rel = path.relative_to(DOCS)
            url = fields.get("permalink") or (
                "/" if rel.name == "index.md" and rel.parent == Path(".")
                else f"/{rel.parent.as_posix()}/".replace("/./", "/")
                if rel.name == "index.md"
                else f"/{rel.with_suffix('').as_posix()}/"
            )
            urls.append(url)
            if f"'{url}'" not in listing:
                missing.append(f"{rel} -> {url}")
        self.assertEqual(missing, [])
        listed = re.findall(r"^- \[([^\]]+)\]", listing, re.MULTILINE)
        self.assertEqual(listed, list(dict.fromkeys(listed)), "listed twice")
        for url in urls:
            self.assertEqual(listing.count(f"'{url}'"), 1, url)

    def test_every_rendered_page_is_in_the_sitemap(self) -> None:
        sitemap = (DOCS / "sitemap.xml").read_text(encoding="utf-8") if (
            DOCS / "sitemap.xml"
        ).is_file() else (DOCS / "sitemap.md").read_text(encoding="utf-8")
        unlisted = []
        for path in _site_pages():
            fields = _front_matter(path)
            if fields.get("layout") == "null" or path.name == "404.md":
                continue
            rel = path.relative_to(DOCS)
            url = fields.get("permalink") or (
                "/" if rel.name == "index.md" and rel.parent == Path(".")
                else f"/{rel.parent.as_posix()}/".replace("/./", "/")
                if rel.name == "index.md"
                else f"/{rel.with_suffix('').as_posix()}/"
            )
            if f"'{url}'" not in sitemap:
                unlisted.append(f"{rel} -> {url}")
        self.assertEqual(unlisted, [])



class CrossPlatformDocsTest(unittest.TestCase):
    """Pages that teach how to run the agent must work on every platform.

    `PYTHONPATH=src python3.13 ...` is not valid in cmd or PowerShell, and
    `pip install -r requirements.txt` pulls MLX, which does not install off
    Apple Silicon. A page that offers only those shuts Windows out.
    """

    RUN_PAGES = ("start.md", "api.md", "skills.md", "ide-plugins.md", "cursor.md")

    def test_each_page_shows_the_installed_command(self) -> None:
        missing = [
            name
            for name in self.RUN_PAGES
            if "python-vibe " not in (DOCS / name).read_text(encoding="utf-8")
        ]
        self.assertEqual(missing, [])

    def test_no_page_offers_the_mlx_requirements_as_the_way_in(self) -> None:
        offenders = [
            str(path.relative_to(ROOT))
            for path in DOCS.rglob("*.md")
            if "pip install -r requirements.txt" in path.read_text(encoding="utf-8")
        ]
        self.assertEqual(offenders, [])


class FirstRunOutputTest(unittest.TestCase):
    """`brief` is the first command a new user runs. It must read as English.

    `render_brief` is written for the model and ends in instructions such as
    "Action: done". Printing that to a person shows them the machine's
    prompt instead of an answer.
    """

    def _brief(self, project: Path) -> str:
        from harness.scan.project_brief import (
            classify_project,
            render_brief_for_person,
        )

        return render_brief_for_person(classify_project(project))

    def _sample(self, tmp: str) -> Path:
        root = Path(tmp)
        (root / "src").mkdir()
        (root / "src" / "app.py").write_text("def go() -> int:\n    return 1\n", encoding="utf-8")
        return root

    def test_it_says_how_big_the_project_is(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            text = self._brief(self._sample(tmp))
        self.assertIn("files", text)
        self.assertIn("src/app.py", text)

    def test_it_does_not_address_the_model(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            text = self._brief(self._sample(tmp))
        for phrase in ("Action:", "auto-read", "Mode:"):
            self.assertNotIn(phrase, text, f"{phrase!r} is written for the model")

    def test_a_large_project_says_what_to_do_about_it(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pkg").mkdir()
            for i in range(60):
                (root / "pkg" / f"m{i}.py").write_text("x = 1\n", encoding="utf-8")
            text = self._brief(root)
        self.assertIn("--scope", text)
        self.assertNotIn("Action:", text)

if __name__ == "__main__":
    unittest.main()
