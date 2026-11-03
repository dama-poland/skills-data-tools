"""Quality gates: the demo passes gates 1 and 2 and fails gate 3 on purpose."""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE_SKILL = {
    1: "damapl-second-brain-kickoff",
    2: "damapl-business-glossary",
    3: "damapl-model-change",
}
DATA = ROOT / "examples" / "data"
ANSWER = ROOT / "examples" / "expected" / "act-1-answer.md"


def script(skill):
    return ROOT / "skills" / skill / "scripts" / "check_gate.py"


def gate(number, *extra, skill=None, cwd=ROOT):
    """Run a gate from the skill that owns it, with the demo data unless overridden."""
    args = list(extra)
    if "--data" not in args:
        args += ["--data", str(DATA)]
    if number == 1 and "--answers" not in args:
        args += ["--answers", str(ANSWER)]
    return subprocess.run([sys.executable, str(script(skill or GATE_SKILL[number])), str(number), *args],
                          capture_output=True, text=True, cwd=cwd)


class GateTest(unittest.TestCase):
    def test_gate_1_passes_on_demo(self):
        self.assertEqual(gate(1).returncode, 0)

    def test_gate_2_passes_on_demo(self):
        self.assertEqual(gate(2).returncode, 0)

    def test_gate_3_fails_on_demo_for_the_unsettled_terms(self):
        result = gate(3)
        self.assertEqual(result.returncode, 1)
        self.assertIn("device in ctms", result.stdout)
        self.assertIn("dose-event in edc", result.stdout)
        self.assertIn("prompt for a human decision", result.stdout)
        self.assertNotIn("randomisation-number in", result.stdout)

    def test_gate_does_not_write_a_signoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            for number in (1, 2, 3):
                gate(number, cwd=tmp)
            self.assertEqual(list(Path(tmp).rglob("signoff-*.md")), [])
        self.assertEqual(list(ROOT.rglob("signoff-*.md")), [])

    def test_data_argument_is_required(self):
        result = subprocess.run([sys.executable, str(script(GATE_SKILL[3])), "3"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--data", result.stderr)

    def test_gate_1_requires_answers(self):
        result = subprocess.run([sys.executable, str(script(GATE_SKILL[1])), "1", "--data", str(DATA)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--answers", result.stderr)

    def test_gate_2_in_a_skill_without_bg_validate_exits_2(self):
        result = gate(2, skill="damapl-second-brain-kickoff")
        self.assertEqual(result.returncode, 2)
        self.assertIn("bg_validate.py", result.stderr)

    def test_gate_3_in_a_skill_without_map_scripts_exits_2(self):
        for skill in ("damapl-second-brain-kickoff", "damapl-business-glossary"):
            result = gate(3, skill=skill)
            self.assertEqual(result.returncode, 2, skill)
            self.assertIn("map_build.py", result.stderr)

    def test_gate_1_runs_from_every_skill_that_holds_the_script(self):
        for skill in ("damapl-business-glossary", "damapl-model-change"):
            self.assertEqual(gate(1, skill=skill).returncode, 0, skill)

    def test_gate_1_fails_without_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            shutil.copytree(DATA, data)
            ctms = data / "systems" / "ctms.md"
            ctms.write_text(ctms.read_text().replace('owner: "Synthetic demo maintainers"\n', ""))
            result = gate(1, "--data", str(data))
            self.assertEqual(result.returncode, 1)
            self.assertIn("ctms.md: no owner", result.stdout)

    def test_gate_1_fails_on_answer_without_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            answer = Path(tmp) / "answer.md"
            answer.write_text("## Answer\n\nYes.\n\n## Confidence\n\nHigh.\n")
            result = gate(1, "--answers", str(answer))
            self.assertEqual(result.returncode, 1)
            self.assertIn("missing part: Sources", result.stdout)

    def _demo_with_source(self, tmp, frontmatter):
        data = Path(tmp) / "data"
        shutil.copytree(DATA, data)
        (data / "sources").mkdir()
        (data / "sources" / "raw-model.md").write_text(
            "---\n" + frontmatter + "---\n\n# Raw model\n")
        return data

    def test_gate_1_checks_notes_in_sources_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = self._demo_with_source(tmp, 'title: "Raw model"\nretrieved: "2026-10-24"\n')
            result = gate(1, "--data", str(data))
            self.assertEqual(result.returncode, 1)
            self.assertIn("sources/raw-model.md: no owner", result.stdout)
            self.assertIn("sources/raw-model.md: confidentiality is not one of", result.stdout)

    def test_gate_1_passes_with_complete_note_in_sources_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = self._demo_with_source(
                tmp, 'title: "Raw model"\nowner: "Synthetic demo maintainers"\n'
                     'retrieved: "2026-10-24"\nconfidentiality: "public"\n')
            self.assertEqual(gate(1, "--data", str(data)).returncode, 0)

    def test_gate_1_knows_source_ids_declared_in_sources_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = self._demo_with_source(
                tmp, 'title: "Raw model"\nsource_id: "RAW-MODEL-v1"\n'
                     'owner: "Synthetic demo maintainers"\n'
                     'retrieved: "2026-10-24"\nconfidentiality: "public"\n')
            answer = Path(tmp) / "answer.md"
            answer.write_text(ANSWER.read_text().replace(
                "## Confidence", "- `sources/raw-model.md`, `RAW-MODEL-v1`, retrieved 2026-10-24.\n\n## Confidence").replace(
                "retrieved 2026-10-24.\n\n- `sources/raw-model.md`", "retrieved 2026-10-24.\n- `sources/raw-model.md`"))
            result = gate(1, "--data", str(data), "--answers", str(answer))
            self.assertEqual(result.returncode, 0, result.stdout)

    def _answer_citing_raw_model(self, tmp):
        answer = Path(tmp) / "answer.md"
        answer.write_text(ANSWER.read_text().replace(
            "retrieved 2026-10-24.\n\n## Confidence",
            "retrieved 2026-10-24.\n- `sources/raw-model.md`, `RAW-MODEL-v1`, "
            "retrieved 2026-10-24.\n\n## Confidence"))
        return answer

    def test_gate_1_treats_source_without_classification_as_internal(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = self._demo_with_source(
                tmp, 'title: "Raw model"\nsource_id: "RAW-MODEL-v1"\n'
                     'owner: "Synthetic demo maintainers"\n'
                     'retrieved: "2026-10-24"\n')
            answer = self._answer_citing_raw_model(tmp)
            result = gate(1, "--data", str(data), "--answers", str(answer))
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("Classification is lower than the highest classification",
                          result.stdout)
            answer.write_text(answer.read_text().replace(
                "## Classification\n\nPublic.", "## Classification\n\nInternal."))
            result = gate(1, "--data", str(data), "--answers", str(answer))
            self.assertNotIn("Classification is lower", result.stdout)

    def test_gate_1_treats_source_with_unknown_classification_as_restricted(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = self._demo_with_source(
                tmp, 'title: "Raw model"\nsource_id: "RAW-MODEL-v1"\n'
                     'owner: "Synthetic demo maintainers"\n'
                     'retrieved: "2026-10-24"\nconfidentiality: "secret-ish"\n')
            answer = self._answer_citing_raw_model(tmp)
            answer.write_text(answer.read_text().replace(
                "## Classification\n\nPublic.", "## Classification\n\nInternal."))
            result = gate(1, "--data", str(data), "--answers", str(answer))
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("Classification is lower than the highest classification",
                          result.stdout)

    def test_gate_3_passes_when_terms_are_approved(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            shutil.copytree(DATA, data)
            for name in ("device", "dose-event"):
                path = data / "glossary" / "terms" / f"{name}.md"
                text = path.read_text()
                for old in ("status: Under Review", "status: Draft"):
                    text = text.replace(old, "status: Approved", 1)
                path.write_text(text)
            self.assertEqual(gate(3, "--data", str(data)).returncode, 0)


if __name__ == "__main__":
    unittest.main()
