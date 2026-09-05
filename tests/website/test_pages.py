import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
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
            "tree.md",
            "skills.md",
            "demo.md",
            "live.md",
            "local-editor.md",
            "ide-plugins.md",
            "cursor.md",
            "vscode.md",
            "editor-demos.md",
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
            "investigations/first-run-four.md",
            "investigations/experiments.md",
            "investigations/held-out-exec-eval.md",
            "investigations/sample-and-run.md",
            "cite.md",
            "investigations/bench-record.md",
            "investigations/cloud-weights.md",
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
        self.assertEqual(labels.count("Live"), 1)
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

    def test_live_page_is_a_real_session(self) -> None:
        text = (DOCS / "live.md").read_text(encoding="utf-8")
        self.assertIn('$ python-vibe brief', text)
        self.assertIn('$ python-vibe ask "what does compute_total return?"', text)
        self.assertIn("subtotl → subtotal", text)
        self.assertIn("def total_lines(prices: list[int]) -> int:", text)
        self.assertIn("/media/live-demo.gif", text)
        self.assertIn("asciinema play docs/media/live-demo.cast", text)

    def test_live_recording_is_checked_in(self) -> None:
        gif = DOCS / "media" / "live-demo.gif"
        cast = DOCS / "media" / "live-demo.cast"
        self.assertTrue(gif.is_file(), gif)
        self.assertTrue(cast.is_file(), cast)
        self.assertLess(gif.stat().st_size, 800_000, "keep the GIF small enough to ship")
        body = cast.read_text(encoding="utf-8")
        self.assertNotIn("/Users/", body)
        self.assertNotIn("DevBox/", body)
        self.assertIn("python-vibe brief", body)
        self.assertIn("subtotl", body)
        self.assertIn("total_lines", body)

    def test_checkout_map_names_the_demo_and_the_helper(self) -> None:
        text = (DOCS / "tree.md").read_text(encoding="utf-8")
        self.assertIn("permalink: /tree/", text)
        self.assertIn("title: Folders", text)
        self.assertIn("demo/orders", text)
        self.assertIn("src/harness/", text)
        self.assertIn("Do not run `brief` on the", text)
        self.assertIn("source .venv/bin/activate", text)

    def test_home_is_a_short_map_in_plain_words(self) -> None:
        home = (DOCS / "index.md").read_text(encoding="utf-8")
        self.assertIn("| Command | What it does |", home)
        self.assertIn("| Page | What is on it |", home)
        self.assertIn("{{ '/api/' | relative_url }}", home)
        self.assertIn("{{ '/tree/' | relative_url }}", home)
        for name in ("index.md", "start.md", "tree.md"):
            text = (DOCS / name).read_text(encoding="utf-8").lower()
            self.assertNotIn("planted", text, name)
            self.assertNotIn("this checkout", text, name)
            self.assertNotIn("sidecar", text, name)
            self.assertNotIn("hosted ide", text, name)
        nav = (DOCS / "_includes" / "nav.html").read_text(encoding="utf-8")
        self.assertIn(">Commands<", nav)
        self.assertNotIn(">Using<", nav)
        self.assertNotIn(">Cite<", nav)

    def test_vscode_page_is_a_real_session(self) -> None:
        text = (DOCS / "vscode.md").read_text(encoding="utf-8")
        self.assertIn("/media/vscode-demo.gif", text)
        self.assertIn("asciinema play docs/media/vscode-demo.cast", text)
        self.assertIn("python scripts/measure/record_vscode.py", text)
        self.assertIn("python-vibe editors vscode", text)
        self.assertIn("Do not commit that path", text)
        self.assertNotIn("file has no personal path", text)
        self.assertIn('$ python-vibe ask "what does compute_total return?"', text)
        self.assertIn("subtotl → subtotal", text)

    def test_vscode_recording_is_checked_in(self) -> None:
        gif = DOCS / "media" / "vscode-demo.gif"
        cast = DOCS / "media" / "vscode-demo.cast"
        self.assertTrue(gif.is_file(), gif)
        self.assertTrue(cast.is_file(), cast)
        self.assertLess(gif.stat().st_size, 800_000, "keep the GIF small enough to ship")
        body = cast.read_text(encoding="utf-8")
        self.assertNotIn("/Users/", body)
        self.assertNotIn("DevBox/", body)
        self.assertIn("python-vibe editors vscode", body)
        self.assertIn("python-vibe brief", body)
        self.assertIn("compute_total", body)
        self.assertIn("subtotl", body)

    def test_cursor_page_is_a_real_session(self) -> None:
        text = (DOCS / "cursor.md").read_text(encoding="utf-8")
        self.assertIn("/media/cursor-demo.gif", text)
        self.assertIn("asciinema play docs/media/cursor-demo.cast", text)
        self.assertIn("python scripts/measure/record_cursor.py", text)
        self.assertIn("python-vibe editors cursor --allow-writes", text)
        self.assertIn('$ python-vibe ask "what does compute_total return?"', text)
        self.assertIn("subtotl → subtotal", text)

    def test_cursor_recording_is_checked_in(self) -> None:
        gif = DOCS / "media" / "cursor-demo.gif"
        cast = DOCS / "media" / "cursor-demo.cast"
        self.assertTrue(gif.is_file(), gif)
        self.assertTrue(cast.is_file(), cast)
        self.assertLess(gif.stat().st_size, 800_000, "keep the GIF small enough to ship")
        body = cast.read_text(encoding="utf-8")
        self.assertNotIn("/Users/", body)
        self.assertNotIn("DevBox/", body)
        self.assertIn("python-vibe editors cursor --allow-writes", body)
        self.assertIn("python-vibe brief", body)
        self.assertIn("compute_total", body)
        self.assertIn("subtotl", body)

    def test_daily_recording_is_checked_in(self) -> None:
        gif = DOCS / "media" / "daily-run.gif"
        cast = DOCS / "media" / "daily-run.cast"
        self.assertTrue(gif.is_file(), gif)
        self.assertTrue(cast.is_file(), cast)
        self.assertLess(gif.stat().st_size, 800_000, "keep the GIF small enough to ship")
        body = cast.read_text(encoding="utf-8")
        self.assertNotIn("/Users/", body)
        self.assertNotIn("DevBox/", body)
        self.assertIn("compute_total", body)
        self.assertIn("return sum(rows)", body)


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

    RUN_PAGES = (
        "start.md",
        "api.md",
        "skills.md",
        "ide-plugins.md",
        "cursor.md",
        "vscode.md",
    )

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

class NoCommercialPlanTest(unittest.TestCase):
    """This repository is personal public OSS. It holds no business plan.

    A control plane — per-customer API keys, a usage ledger, GPU metering,
    a platform fee — is a different job from a local write jail, and it
    carries customer secrets and money. It belongs in a private repository
    in the molecare org. A note about it was written into this tree and
    referenced from a published page, which put an unbuilt commercial
    plan on a personal open-source site.

    `--engine openai` stays: pointing the harness at a host you rent, with
    your own token, is a feature of the tool, not a business.
    """

    # Words that only appear when the commercial layer is being described.
    COMMERCIAL = (
        "control plane",
        "control-plane",
        "per-customer",
        "usage ledger",
        "platform fee",
        "invoice",
        "customer account",
    )
    # Real code that happens to use the word, and the guard's own text.
    ALLOWED = {"tests/test_pages.py"}

    def test_no_page_or_draft_describes_a_control_plane(self) -> None:
        offenders = []
        for path in sorted(ROOT.rglob("*.md")):
            rel = path.relative_to(ROOT).as_posix()
            if rel.startswith(".git/") or rel in self.ALLOWED:
                continue
            lowered = path.read_text(encoding="utf-8").lower()
            for word in self.COMMERCIAL:
                if word in lowered:
                    offenders.append(f"{rel}: {word}")
        self.assertEqual(
            offenders,
            [],
            f"commercial plan text in a public personal repo: {offenders}",
        )

    def test_billing_words_are_not_in_the_source(self) -> None:
        offenders = []
        for path in sorted((ROOT / "src").rglob("*.py")):
            lowered = path.read_text(encoding="utf-8").lower()
            for word in ("per-customer", "usage ledger", "platform fee"):
                if word in lowered:
                    offenders.append(f"{path.relative_to(ROOT)}: {word}")
        self.assertEqual(offenders, [], offenders)


class NoPersonalDraftsTest(unittest.TestCase):
    """Writing meant for somewhere else is not kept here.

    A `drafts/` directory was added to hold Medium articles, on the
    reasoning that version control would keep their numbers checkable.
    That was the wrong call: the articles are the author's own, they are
    not part of the tool, and a published page ended up pointing readers
    at a file that only makes sense before it is posted. They live
    outside this repository now.

    Measurements stay, in `docs/investigations/`. Those are the source
    the articles are written from, and they belong to the project.
    """

    def test_there_is_no_drafts_directory(self) -> None:
        self.assertFalse(
            (ROOT / "drafts").exists(),
            "drafts/ is the author's own writing; keep it outside the repo",
        )

    def test_no_file_is_a_draft_for_another_site(self) -> None:
        offenders = [
            path.relative_to(ROOT).as_posix()
            for path in sorted(ROOT.rglob("*.md"))
            if ".git/" not in path.as_posix()
            and path.name.lower().startswith("medium")
        ]
        self.assertEqual(offenders, [], offenders)

    def test_nothing_points_at_a_draft(self) -> None:
        offenders = []
        for path in sorted(ROOT.rglob("*.md")):
            rel = path.relative_to(ROOT).as_posix()
            if rel.startswith(".git/"):
                continue
            if "drafts/" in path.read_text(encoding="utf-8"):
                offenders.append(rel)
        self.assertEqual(offenders, [], offenders)


class DatedPagesSayTheDateTest(unittest.TestCase):
    """A published page cannot say "tonight" and mean anything later.

    Pages carried "Tonight's live run" and "as typed tonight". Read a
    week after the measurement they claim something that is not true,
    and the date is already in the front matter and the prose.
    """

    RELATIVE = ("tonight", "this evening", "this morning", "yesterday")

    def test_no_page_dates_itself_by_the_time_of_day(self) -> None:
        offenders = []
        for path in sorted(DOCS.rglob("*.md")):
            lowered = path.read_text(encoding="utf-8").lower()
            for word in self.RELATIVE:
                if word in lowered:
                    offenders.append(f"{path.relative_to(DOCS)}: {word}")
        self.assertEqual(offenders, [], offenders)


class PlainWordsTest(unittest.TestCase):
    """Say what a thing does, not what it is called in somebody's slang.

    "jail" came from chroot and had spread to sixty-odd places: the
    README, the repository description, half the investigation pages and
    several docstrings. A reader who has not met the term learns nothing
    from it. "write limit" says the same thing and needs no glossary.

    Add a word here when it turns out to need explaining.
    """

    JARGON = {
        "jail": "say what it limits, e.g. 'write limit'",
        "footgun": "say what goes wrong",
        "bikeshed": "say what the disagreement is about",
        "yak shav": "say what the detour was",
    }

    def _offenders(self, paths) -> list[str]:
        found = []
        for path in paths:
            rel = path.relative_to(ROOT).as_posix()
            if rel.startswith((".git/", "tests/test_pages.py")):
                continue
            lowered = path.read_text(encoding="utf-8").lower()
            for word, better in self.JARGON.items():
                if word in lowered:
                    found.append(f"{rel}: '{word}' — {better}")
        return found

    def test_pages_and_readme_use_plain_words(self) -> None:
        pages = sorted(DOCS.rglob("*.md")) + [ROOT / "README.md", ROOT / "CONTRIBUTING.md"]
        self.assertEqual(self._offenders(pages), [])

    def test_the_source_uses_plain_words_too(self) -> None:
        """Docstrings are read by whoever maintains this next."""
        self.assertEqual(self._offenders(sorted((ROOT / "src").rglob("*.py"))), [])



if __name__ == "__main__":
    unittest.main()
