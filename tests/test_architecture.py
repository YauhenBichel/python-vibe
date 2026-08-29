"""The layer rule, enforced. A refactor that rots fails here first.

`src/harness/` is ordered bottom-up. A module may import a layer strictly
below it and never one above or beside it, so the import graph stays a
DAG and every layer can be read on its own.
"""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "src" / "harness"

# Lower number = deeper. A layer may only import strictly lower layers.
DEPTH = {
    # `paths` and `task` are the bottom: they import nothing of their own.
    "paths": 0,
    "task": 0,
    "model": 1,
    # `ship` sits above `scan` because reading a ticket means locating what
    # it names in the project.
    "ship": 3,
    "guard": 1,
    "scan": 2,
    "skillkit": 3,
    "act": 4,
    "locate": 5,
    "observe": 6,
    "agent": 7,
    "server": 8,
    "mcp_stdio": 8,
    "editor_kit": 1,
    "cli": 9,
    "__main__": 10,
}


def _layer(rel: Path) -> str:
    """Package name for a subpackage module, else the module's own stem."""
    return rel.parts[0] if len(rel.parts) > 1 else rel.stem


def _edges() -> set[tuple[str, str, str]]:
    found: set[tuple[str, str, str]] = set()
    for path in sorted(HARNESS.rglob("*.py")):
        rel = path.relative_to(HARNESS)
        if rel == Path("__init__.py"):
            continue
        source = _layer(rel)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if not node.module or not node.module.startswith("harness."):
                continue
            target = node.module.split(".", 1)[1].split(".")[0]
            if target != source:
                found.add((source, target, str(rel)))
    return found


class LayerRuleTest(unittest.TestCase):
    def test_every_layer_is_known(self) -> None:
        layers = {_layer(p.relative_to(HARNESS)) for p in HARNESS.rglob("*.py")}
        layers.discard("__init__")
        unknown = sorted(layers - set(DEPTH))
        self.assertEqual(
            unknown,
            [],
            f"new layer(s) {unknown}: give them a depth in DEPTH, or move them",
        )

    def test_imports_only_point_downwards(self) -> None:
        upward = [
            f"{where}: {source} -> {target}"
            for source, target, where in sorted(_edges())
            if DEPTH[target] >= DEPTH[source]
        ]
        self.assertEqual(upward, [], "layer rule broken")

    def test_no_import_cycles(self) -> None:
        graph: dict[str, set[str]] = {}
        for source, target, _where in _edges():
            graph.setdefault(source, set()).add(target)
        state: dict[str, int] = {}

        def walk(node: str, trail: list[str]) -> list[str] | None:
            state[node] = 1
            for nxt in sorted(graph.get(node, ())):
                if state.get(nxt) == 1:
                    return trail + [node, nxt]
                if state.get(nxt, 0) == 0:
                    found = walk(nxt, trail + [node])
                    if found:
                        return found
            state[node] = 2
            return None

        for node in sorted(graph):
            if state.get(node, 0) == 0:
                self.assertIsNone(walk(node, []), "import cycle between layers")

    def test_no_module_counts_its_own_depth(self) -> None:
        """`parents[N]` breaks the moment a module moves into a layer."""
        offenders = [
            str(path.relative_to(HARNESS))
            for path in sorted(HARNESS.rglob("*.py"))
            if "parents[" in path.read_text(encoding="utf-8")
            and path.name != "paths.py"
        ]
        self.assertEqual(offenders, [], "use harness.paths instead of parents[N]")

    def test_the_guard_layer_cannot_write(self) -> None:
        """The safety boundary must not import a layer that touches files."""
        writers = {"act", "locate"}
        leaks = [
            f"{where}: guard -> {target}"
            for source, target, where in sorted(_edges())
            if source == "guard" and target in writers
        ]
        self.assertEqual(leaks, [])


class TempDirectoryTest(unittest.TestCase):
    """A test must not create files inside the checkout.

    AGENTS.md asks for `tempfile.TemporaryDirectory`. Passing `dir=ROOT`
    puts the directory in the repository instead of the system temp area,
    so a crashed run leaves it behind, where the suite's own scans of the
    project will then find it.
    """

    TESTS = Path(__file__).resolve().parent

    def test_no_test_creates_a_temporary_directory_in_the_repo(self) -> None:
        offenders: list[str] = []
        for path in sorted(self.TESTS.glob("test_*.py")):
            for number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1
            ):
                stripped = line.strip()
                if "TemporaryDirectory(" not in stripped:
                    continue
                if "dir=" in stripped and "dir=tmp" not in stripped:
                    offenders.append(f"{path.name}:{number}: {stripped}")
        self.assertEqual(offenders, [], "use the system temp area")


class SuiteRunsWholeFilesTest(unittest.TestCase):
    """Every test in a file must run when that file is run on its own.

    `unittest.main()` executes where it sits, so a class defined below
    it is never collected. Ten files had it mid-file; test_autofix.py
    ran 11 of its 36 tests that way. CI uses discovery, so all of them
    were green while more than half of one file did nothing. Iterating
    on a single file is the normal way to work, and it was the way that
    lied.
    """

    def test_no_test_class_is_defined_after_unittest_main(self) -> None:
        stragglers = []
        for path in sorted((ROOT / "tests").glob("test_*.py")):
            lines = path.read_text(encoding="utf-8").splitlines()
            start = next(
                (i for i, line in enumerate(lines)
                 if line.startswith('if __name__ == "__main__"')),
                None,
            )
            if start is None:
                continue
            after = [
                line for line in lines[start + 1:]
                if line.startswith("class ") or line.startswith("def test")
            ]
            if after:
                stragglers.append(f"{path.name}: {after[0]}")
        self.assertEqual(stragglers, [])

    def test_running_a_file_directly_collects_what_discovery_does(self) -> None:
        import unittest.loader

        loader = unittest.defaultTestLoader
        for path in sorted((ROOT / "tests").glob("test_*.py")):
            with self.subTest(file=path.name):
                found = loader.discover(str(ROOT / "tests"), pattern=path.name)
                self.assertGreater(found.countTestCases(), 0, path.name)
if __name__ == "__main__":
    unittest.main()
