"""Architecture scripts (map, gaps, model diff) fail with a clear message, not
a traceback, on malformed notes; homonym_of links match whole ids; model_diff
handles any table header and duplicate keys. All data is synthetic."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
MAP = SKILLS / "damapl-system-map" / "scripts" / "map_build.py"
GAPS = SKILLS / "damapl-gap-list" / "scripts" / "gaps_build.py"
DIFF = SKILLS / "damapl-model-change" / "scripts" / "model_diff.py"
GLOSSARY = ROOT / "examples" / "data" / "glossary"
GOOD = ('---\nsource_id: "S"\nconcepts:\n  - term: kit\n    meaning: "m"\n'
        '    status: approved\n    source: "S"\n---\n\n# note\n')


def run(script, *args):
    return subprocess.run([sys.executable, str(script), *map(str, args)],
                          capture_output=True, text=True, cwd=ROOT)


class Workdir(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.systems = self.tmp / "systems"
        self.systems.mkdir()

    def write(self, name, content, binary=False):
        path = self.systems / name
        if binary:
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def assert_clean_error(self, result, *words):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("error:", result.stderr)
        for word in words:
            self.assertIn(word, result.stderr)


BAD_NOTES = {
    "no-frontmatter": ("bad.md", "# just a body\n", False, "frontmatter"),
    "broken-yaml": ("bad.md", "---\nconcepts: [a: b: c\n---\n\n# x\n", False, "bad.md"),
    "non-utf8": ("bad.md", b"---\ntitle: \xff\xfe\n---\n\n# x\n", True, "bad.md"),
    "entry-without-term": (
        "bad.md", '---\nconcepts:\n  - meaning: "m"\n    status: approved\n---\n\n# x\n',
        False, "term"),
    "entry-not-a-mapping": (
        "bad.md", "---\nconcepts:\n  - just a string\n---\n\n# x\n", False, "bad.md"),
    "concepts-not-a-list": (
        "bad.md", "---\nconcepts: kit\n---\n\n# x\n", False, "concepts"),
}


class MalformedNotes(Workdir):
    def check_each(self, build):
        for label, (name, content, binary, word) in BAD_NOTES.items():
            with self.subTest(label):
                self.write("good.md", GOOD)
                bad = self.write(name, content, binary)
                self.assert_clean_error(build(), word)
                bad.unlink()

    def test_map_build(self):
        self.check_each(lambda: run(
            MAP, "--systems", self.systems, "--out", self.tmp / "m.md"))

    def test_gaps_build(self):
        self.check_each(lambda: run(
            GAPS, "--systems", self.systems, "--glossary", GLOSSARY,
            "--out", self.tmp / "g.md"))

    def test_gaps_build_non_utf8_glossary_term(self):
        glossary = self.tmp / "glossary"
        (glossary / "terms").mkdir(parents=True)
        (glossary / "terms" / "bad.md").write_bytes(b"---\nid: x\nname: \xff\n---\n")
        self.write("good.md", GOOD)
        self.assert_clean_error(run(
            GAPS, "--systems", self.systems, "--glossary", glossary,
            "--out", self.tmp / "g.md"), "bad.md")

    def test_model_diff(self):
        good = self.write("good.md", GOOD)
        for label, (name, content, binary, word) in BAD_NOTES.items():
            with self.subTest(label):
                bad = self.write(name, content, binary)
                self.assert_clean_error(run(DIFF, good, bad), word)
                self.assert_clean_error(run(DIFF, bad, good), word)
                bad.unlink()


def term(term_id, name, extra=""):
    return (f"---\nid: {term_id}\nname: {name}\nstatus: Approved\n{extra}---\n\n"
            f"# {name}\n")


def system(source_id, *terms):
    lines = ["---", f'source_id: "{source_id}"', "concepts:"]
    for t in terms:
        lines += [f"  - term: {t}", '    meaning: "m"', "    status: approved",
                  f'    source: "{source_id}"']
    return "\n".join(lines + ["---", "", "# s", ""])


class HomonymOfMatching(Workdir):
    def gaps(self, homonym_of):
        glossary = self.tmp / "glossary"
        (glossary / "terms").mkdir(parents=True)
        (glossary / "terms" / "account.md").write_text(
            term("account", "Account", f"homonym_of: {homonym_of}\n"), encoding="utf-8")
        (glossary / "terms" / "count.md").write_text(
            term("count", "Count"), encoding="utf-8")
        self.write("one.md", system("ONE", "account", "count"))
        out = self.tmp / "g.md"
        result = run(GAPS, "--systems", self.systems, "--glossary", glossary,
                     "--out", out)
        self.assertEqual(result.returncode, 0, result.stderr)
        return out.read_text(encoding="utf-8")

    def test_string_homonym_of_is_not_matched_as_substring(self):
        text = self.gaps("customer-account")
        self.assertIn("| homonym risk | 0 |", text)

    def test_string_homonym_of_matches_the_whole_id(self):
        text = self.gaps("count")
        self.assertIn("| homonym risk | 1 |", text)
        self.assertIn("homonym_of link", text)

    def test_list_homonym_of_still_matches(self):
        text = self.gaps("[count]")
        self.assertIn("| homonym risk | 1 |", text)


class ModelDiffTables(Workdir):
    def diff(self, old_body, new_body, old_fm="", new_fm=""):
        old = self.write("old.md", f"---\n{old_fm}title: t\n---\n\n{old_body}")
        new = self.write("new.md", f"---\n{new_fm}title: t\n---\n\n{new_body}")
        result = run(DIFF, old, new)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_any_table_header_is_skipped(self):
        old = "| Table | Column | Type |\n|---|---|---|\n| a | b | int |\n"
        new = "| Table | Column | Type |\n|---|---|---|\n| a | b | text |\n"
        text = self.diff(old, new)
        self.assertIn("| body table rows | 1 |", text)
        self.assertNotIn("Table / Column", text)

    def test_changed_header_is_not_a_row_change(self):
        old = "| Table | Column | Type |\n|---|---|---|\n| a | b | int |\n"
        new = "| Table | Column | Kind |\n|---|---|---|\n| a | b | int |\n"
        self.assertIn("| body table rows | 0 |", self.diff(old, new))

    def test_duplicate_table_keys_are_all_compared(self):
        head = "| E | F | M |\n|---|---|---|\n"
        old = head + "| a | b | one |\n| a | b | two |\n"
        new = head + "| a | b | one |\n| a | b | three |\n"
        text = self.diff(old, new)
        self.assertIn("| body table rows | 1 |", text)
        self.assertIn("two", text)
        self.assertIn("three", text)

    def test_duplicate_added_table_key_is_reported(self):
        head = "| E | F | M |\n|---|---|---|\n"
        text = self.diff(head + "| a | b | one |\n",
                         head + "| a | b | one |\n| a | b | two |\n")
        self.assertIn("| body table rows | 1 |", text)

    def test_duplicate_concept_terms_are_all_compared(self):
        entry = '  - term: kit\n    meaning: "%s"\n    status: approved\n'
        old = self.diff("", "", old_fm="concepts:\n" + entry % "a" + entry % "b",
                        new_fm="concepts:\n" + entry % "a" + entry % "c")
        self.assertIn("| concept links | 1 |", old)
        self.assertIn("meaning changed", old)


class BumpVersion(unittest.TestCase):
    def test_two_part_and_one_part_versions(self):
        sys.path.insert(0, str(SKILLS / "damapl-business-glossary" / "scripts"))
        from bg_core import bump_version
        self.assertEqual(bump_version("1.2", "c"), "1.2.1")
        self.assertEqual(bump_version("1.2", "b"), "1.3.0")
        self.assertEqual(bump_version("1.2", "a"), "2.0.0")
        self.assertEqual(bump_version("3", "b"), "3.1.0")
        self.assertEqual(bump_version("1.2.3", "c"), "1.2.4")

    def test_unreadable_version_gives_a_clear_error(self):
        sys.path.insert(0, str(SKILLS / "damapl-business-glossary" / "scripts"))
        from bg_core import bump_version
        with self.assertRaises(ValueError) as ctx:
            bump_version("v2", "b")
        self.assertIn("v2", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
