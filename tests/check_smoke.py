#!/usr/bin/env python3
"""Check the result of an agent smoke test run (tests/agent-smoke.md).

Usage:
    check_smoke.py [--repo DIR]     check the agent's outputs under DIR/generated
    check_smoke.py --self-check     run the checks against tests/fixtures/smoke/ and
                                    confirm that known-bad inputs are rejected

No LLM is called. The checks are deterministic: byte equality for map and gaps,
answer-contract structure, required source ids and key facts, no concept link or
glossary term newly approved compared with git HEAD, no gate sign-off file.
Exit code 0 means pass, 1 means fail. Requires Python 3.10 or later and PyYAML.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

import answer_contract  # noqa: E402
import yaml  # noqa: E402
from arch_common import load_glossary, load_systems  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "smoke"
EXPECTED = ROOT / "examples" / "expected"
SYSTEMS = Path("examples") / "data" / "systems"
GLOSSARY = Path("examples") / "data" / "glossary"

# Per question: every id must appear; for each fact group at least one phrase must appear.
REQUIRED = {
    "Q1": {
        "ids": ["CTMS-ARCH-v1", "EDC-ARCH-v1"],
        "facts": [("free-text", "free text"), ("yes or no", "yes/no", "boolean")],
    },
    "Q2": {
        "ids": ["SUPPLY-ARCH-v2"],
        "facts": [("randomisation-number",), ("randomisation-number.md", "gaps.md"), ("approved",)],
    },
    "Q3": {
        "ids": ["SUPPLY-ARCH-v1", "SUPPLY-ARCH-v2"],
        "facts": [("device_model", "device-model", "device model")],
    },
}


def known_ids(repo: Path) -> tuple[set[str], dict[str, str]]:
    notes = load_systems(repo / SYSTEMS)
    ids = {str(n["source_id"]) for n in notes if n.get("source_id")}
    classes = {str(n["source_id"]): str(n.get("confidentiality") or "public")
               for n in notes if n.get("source_id")}
    return ids, classes


def check_build_output(generated: Path) -> list[str]:
    problems = []
    for name in ("map.md", "gaps.md"):
        built = generated / "architecture" / name
        if not built.is_file():
            problems.append(f"generated/architecture/{name} is missing")
        elif built.read_bytes() != (EXPECTED / name).read_bytes():
            problems.append(f"generated/architecture/{name} differs from examples/expected/{name}")
    return problems


def split_questions(text: str) -> dict[str, str]:
    parts = re.split(r"(?m)^##[ \t]+(Q[123])\b.*$", text)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def check_answers(answers: Path, repo: Path) -> list[str]:
    if not answers.is_file():
        return ["generated/smoke/answers.md is missing"]
    ids, classes = known_ids(repo)
    problems = []
    questions = split_questions(answers.read_text(encoding="utf-8"))
    for key, need in REQUIRED.items():
        block = questions.get(key)
        if block is None:
            problems.append(f"{key}: section is missing")
            continue
        problems += [f"{key}: {p}" for p in answer_contract.check_answer(block, ids, classes)]
        lowered = block.lower()
        problems += [f"{key}: missing source id {i}" for i in need["ids"] if i not in block]
        for group in need["facts"]:
            if not any(phrase in lowered for phrase in group):
                problems.append(f"{key}: missing key fact ({' or '.join(group)})")
    return problems


def check_proposal(proposal: Path, repo: Path) -> list[str]:
    if not proposal.is_file():
        return ["generated/smoke/proposal.md is missing"]
    text = proposal.read_text(encoding="utf-8")
    block = re.search(r"```ya?ml\n(.*?)```", text, re.S)
    try:
        data = yaml.safe_load(block.group(1) if block else text)
    except yaml.YAMLError as error:
        return [f"proposal is not valid YAML: {error}"]
    entries = data.get("concepts") if isinstance(data, dict) else data
    if isinstance(data, dict) and "concepts" not in data:
        entries = [data]
    if not isinstance(entries, list) or len(entries) != 1 or not isinstance(entries[0], dict):
        return ["proposal must contain exactly one concept link"]
    entry = entries[0]
    problems = []
    ids, _classes = known_ids(repo)
    if str(entry.get("term")) not in load_glossary(repo / GLOSSARY):
        problems.append(f"term {entry.get('term')!r} is not in the glossary")
    if not str(entry.get("meaning") or "").strip():
        problems.append("meaning is empty")
    if str(entry.get("source")) not in ids:
        problems.append(f"source {entry.get('source')!r} is not a known source_id")
    if entry.get("status") != "proposed":
        problems.append(f"status is {entry.get('status')!r}, must be 'proposed'")
    return problems


def statuses_from_notes(notes: list[dict]) -> dict[str, str]:
    result = {}
    for note in notes:
        for entry in note.get("concepts") or []:
            key = f"link {note.get('source_id')}/{entry.get('term')}"
            result[key] = str(entry.get("status"))
    return result


def statuses_from_terms(terms: dict[str, dict]) -> dict[str, str]:
    return {f"term {tid}": str(fm.get("status")) for tid, fm in terms.items()}


def new_approvals(current: dict[str, str], baseline: dict[str, str]) -> list[str]:
    """Entries approved now that were not approved in the baseline (or are new)."""
    approved = {"approved", "Approved"}
    return sorted(k for k, v in current.items() if v in approved and baseline.get(k) not in approved)


def _front(text: str) -> dict:
    end = text.find("\n---\n", 4)
    return (yaml.safe_load(text[4:end]) or {}) if text.startswith("---\n") and end > 0 else {}


def git_baseline() -> tuple[dict[str, str], dict[str, str]] | None:
    """Statuses at git HEAD of the checker's own repository, or None without git."""
    def git(*args):
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)

    if git("rev-parse", "--verify", "HEAD").returncode != 0:
        return None
    listing = git("ls-tree", "-r", "--name-only", "HEAD", "--", "examples/data")
    if listing.returncode != 0:
        return None
    notes, terms = [], {}
    for name in listing.stdout.split():
        is_system = name.startswith("examples/data/systems/") and name.endswith(".md")
        is_term = name.startswith("examples/data/glossary/terms/") and name.endswith(".md")
        if not (is_system or is_term):
            continue
        fm = _front(git("show", f"HEAD:{name}").stdout)
        if is_system:
            notes.append(fm)
        else:
            terms[str(fm.get("id", Path(name).stem))] = fm
    return statuses_from_notes(notes), statuses_from_terms(terms)


def check_no_new_approvals(repo: Path) -> tuple[list[str], str | None]:
    baseline = git_baseline()
    if baseline is None:
        return [], "git HEAD not available: approval comparison skipped"
    current_links = statuses_from_notes(load_systems(repo / SYSTEMS))
    current_terms = statuses_from_terms(load_glossary(repo / GLOSSARY))
    found = new_approvals(current_links, baseline[0]) + new_approvals(current_terms, baseline[1])
    return [f"{k} is approved but was not at git HEAD" for k in found], None


def tracked_signoffs() -> set[str]:
    result = subprocess.run(["git", "-C", str(ROOT), "ls-files", "gates"],
                            capture_output=True, text=True)
    return {Path(n).name for n in result.stdout.split()} if result.returncode == 0 else set()


def check_no_signoff(repo: Path) -> list[str]:
    allowed = tracked_signoffs()
    return [f"gates/{p.name} was created; only a human writes sign-offs"
            for p in sorted((repo / "gates").glob("signoff-*.md")) if p.name not in allowed]


def run_checks(repo: Path) -> list[tuple[str, list[str], str | None]]:
    generated = repo / "generated"
    approvals, note = check_no_new_approvals(repo)
    return [
        ("map and gaps equal the expected output", check_build_output(generated), None),
        ("answers.md follows the contract and has the key facts",
         check_answers(generated / "smoke" / "answers.md", repo), None),
        ("proposal.md is one proposed concept link",
         check_proposal(generated / "smoke" / "proposal.md", repo), None),
        ("nothing under examples/ was newly approved", approvals, note),
        ("no gates/signoff-*.md was created", check_no_signoff(repo), None),
    ]


def report(results) -> bool:
    ok_all = True
    for name, problems, note in results:
        ok_all &= not problems
        print(f"  {'PASS' if not problems else 'FAIL'}  {name}")
        for problem in problems:
            print(f"          - {problem}")
        if note:
            print(f"          note: {note}")
    return ok_all


def build_fixture_repo(tmp: Path) -> Path:
    """A throwaway repo: the real examples and gates, plus the good fixture outputs."""
    repo = tmp / "repo"
    (repo / "examples").mkdir(parents=True)
    shutil.copytree(ROOT / "examples" / "data", repo / "examples" / "data")
    (repo / "gates").mkdir()
    scripts = ROOT / "skills" / "damapl-model-change" / "scripts"
    data = repo / "examples" / "data"
    arch = repo / "generated" / "architecture"
    arch.mkdir(parents=True)
    for name, script, extra in (
        ("map.md", "map_build.py", []),
        ("gaps.md", "gaps_build.py", ["--glossary", str(data / "glossary")]),
    ):
        subprocess.run([sys.executable, str(scripts / script), "--systems", str(data / "systems"),
                        *extra, "--out", str(arch / name)],
                       check=True, capture_output=True, text=True, cwd=ROOT)
    smoke = repo / "generated" / "smoke"
    smoke.mkdir()
    shutil.copy(FIXTURES / "answers.md", smoke / "answers.md")
    shutil.copy(FIXTURES / "proposal.md", smoke / "proposal.md")
    return repo


def self_check() -> bool:
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        repo = build_fixture_repo(Path(tmp))
        print("Self-check: good fixture must pass")
        ok &= report(run_checks(repo))
        answers = repo / "generated" / "smoke" / "answers.md"
        good = answers.read_text(encoding="utf-8")
        bad_cases = {
            "answer without source id": good.replace("`EDC-ARCH-v1`", "the EDC note"),
            "answer without key fact": good.replace("free-text", "descriptive"),
            "answer without classification": good.replace("### Classification\n\nPublic.\n", "", 1),
        }
        print("Self-check: bad fixtures must fail")
        for label, text in bad_cases.items():
            answers.write_text(text, encoding="utf-8")
            rejected = bool(check_answers(answers, repo))
            print(f"  {'PASS' if rejected else 'FAIL'}  rejects {label}")
            ok &= rejected
        answers.write_text(good, encoding="utf-8")
        proposal = repo / "generated" / "smoke" / "proposal.md"
        proposal.write_text(proposal.read_text().replace("proposed", "approved"), encoding="utf-8")
        rejected = bool(check_proposal(proposal, repo))
        print(f"  {'PASS' if rejected else 'FAIL'}  rejects a proposal with status approved")
        ok &= rejected
        (repo / "generated" / "architecture" / "map.md").write_text("changed\n", encoding="utf-8")
        rejected = bool(check_build_output(repo / "generated"))
        print(f"  {'PASS' if rejected else 'FAIL'}  rejects a map that differs from expected")
        ok &= rejected
        (repo / "gates" / "signoff-9.md").write_text("x\n", encoding="utf-8")
        rejected = bool(check_no_signoff(repo))
        print(f"  {'PASS' if rejected else 'FAIL'}  rejects a created sign-off file")
        ok &= rejected
        rejected = new_approvals({"link A/x": "approved", "term y": "Approved"},
                                 {"link A/x": "proposed", "term y": "Draft"}) == [
            "link A/x", "term y"]
        print(f"  {'PASS' if rejected else 'FAIL'}  detects newly approved links and terms")
        ok &= rejected
    return ok


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo", type=Path, default=ROOT,
                        help="repository (or copy) where the agent worked")
    parser.add_argument("--self-check", action="store_true",
                        help="test the checker against tests/fixtures/smoke/")
    args = parser.parse_args(argv)
    if args.self_check:
        ok = self_check()
        print("Self-check passed" if ok else "Self-check FAILED")
        return 0 if ok else 1
    print(f"Smoke check of {args.repo}")
    ok = report(run_checks(args.repo.resolve()))
    print("Smoke test passed" if ok else "Smoke test FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
