#!/usr/bin/env python3
"""Run the program checks of a quality gate.

Usage:
    check_gate.py 1|2|3 --data DIR [--systems DIR] [--glossary DIR] [--answers FILE]

--data is required. Gate 1 also requires --answers. The script runs only the gates
whose helper scripts sit in its own folder: gate 2 needs bg_validate.py (skill
damapl-business-glossary), gate 3 needs map_build.py and gaps_build.py (skill
damapl-model-change). A gate whose scripts are missing exits with code 2.

Gate 1  second brain: sources have owner, date and classification; sample answers
        follow the answer contract.
Gate 2  glossary: no MUST findings; every term used by an approved concept link
        reaches at least the lowest tier of the active profile.
Gate 3  architecture: every approved concept link points to an Approved term; map
        and gaps build without errors.

Exit code 0 means all program checks passed, 1 means at least one failed, 2 means
the gate could not run. A passing gate is not a sign-off: a human records that in
gates/signoff-<n>.md. A failing gate is a prompt for a human decision, not an error
to hide. The program never writes a sign-off file.
Requires Python 3.10 or later and PyYAML.
"""

from __future__ import annotations

import argparse
import datetime
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
GATE_SCRIPTS = {
    "1": (),
    "2": ("bg_validate.py",),
    "3": ("map_build.py", "gaps_build.py"),
}
sys.path.insert(0, str(SCRIPTS))

import answer_contract  # noqa: E402
from arch_common import (NoteError, approved_links, current_systems,  # noqa: E402
                         load_glossary, load_systems, parse_frontmatter)

CLASSIFICATIONS = answer_contract.CLASSIFICATIONS

FAIL_PROMPT = (
    "A failing gate is a prompt for a human decision: decide who settles each finding "
    "(steward, architect), fix the source, or accept the risk in writing. "
    "Do not edit the check to make it pass."
)
DEMO_NOTE = (
    "This is the synthetic demo. It fails gate 3 on purpose: `device` is Under Review "
    "and `dose-event` is Draft, so the links that use them are not ready for approval."
)


class Report:
    """Collects check results and prints a per-check report."""

    def __init__(self, title: str):
        self.title = title
        self.results: list[tuple[str, bool, list[str]]] = []

    def add(self, name: str, problems: list[str]) -> None:
        self.results.append((name, not problems, problems))

    @property
    def passed(self) -> bool:
        return all(ok for _n, ok, _p in self.results)

    def render(self) -> str:
        lines = [self.title]
        for name, ok, problems in self.results:
            lines.append(f"  {'PASS' if ok else 'FAIL'}  {name}")
            lines.extend(f"          - {p}" for p in problems)
        failed = sum(1 for _n, ok, _p in self.results if not ok)
        lines.append(f"{len(self.results) - failed} passed, {failed} failed")
        return "\n".join(lines)


def _is_date(value) -> bool:
    if isinstance(value, datetime.date):
        return True
    try:
        datetime.date.fromisoformat(str(value))
        return True
    except ValueError:
        return False


def source_notes(systems: Path, data: Path) -> list[tuple[str, dict]]:
    """Source notes (type source in systems) plus every derived note and decision."""
    notes: list[tuple[str, dict]] = []
    for path in sorted(systems.glob("*.md")):
        fm = parse_frontmatter(path)
        if fm.get("type") == "source":
            notes.append((path.name, fm))
    for folder in ("notes", "decisions"):
        for path in sorted((data / folder).glob("*.md")):
            notes.append((f"{folder}/{path.name}", parse_frontmatter(path)))
    return notes


def metadata_problems(label: str, fm: dict) -> list[str]:
    problems = []
    if not str(fm.get("owner") or "").strip():
        problems.append(f"{label}: no owner")
    dates = [fm.get(k) for k in ("updated", "retrieved") if fm.get(k)]
    if not dates:
        problems.append(f"{label}: no date (updated or retrieved)")
    elif not all(_is_date(d) for d in dates):
        problems.append(f"{label}: date is not YYYY-MM-DD")
    if str(fm.get("confidentiality") or "") not in CLASSIFICATIONS:
        problems.append(f"{label}: confidentiality is not one of {', '.join(CLASSIFICATIONS)}")
    return problems


def gate_1(args) -> Report:
    report = Report("Gate 1: second brain")
    notes = source_notes(args.systems, args.data)
    problems = [p for label, fm in notes for p in metadata_problems(label, fm)]
    if not notes:
        problems.append("no source notes found")
    report.add(f"{len(notes)} source notes have owner, date and classification", problems)

    systems = load_systems(args.systems)
    known = {str(n["source_id"]) for n in systems if n.get("source_id")}
    classes = {str(n["source_id"]): str(n.get("confidentiality") or "public")
               for n in systems if n.get("source_id")}
    if not args.answers.is_file():
        report.add(f"sample answer follows the answer contract ({args.answers.name})",
                   [f"file not found: {args.answers}"])
    else:
        text = args.answers.read_text(encoding="utf-8")
        report.add(f"sample answer follows the answer contract ({args.answers.name})",
                   answer_contract.check_answer(text, known, classes))
    return report


def run_bg_validate(glossary: Path):
    from bg_validate import run  # noqa: E402  (business-glossary script, imported on demand)
    return run(str(glossary))


def gate_2(args) -> Report:
    report = Report("Gate 2: glossary")
    try:
        cfg, profile, terms, violations, tiers = run_bg_validate(args.glossary)
    except (SystemExit, OSError, ValueError) as error:
        report.add("bg_validate runs on the glossary", [f"could not run: {error}"])
        return report
    profile_name = profile.get("name", "unknown")
    must = [v for v in violations if v["level"] == "MUST"]
    report.add(
        f"bg_validate reports no MUST findings (profile {profile_name}, {len(terms)} terms)",
        [f"{v['rule']} {v['term']}: {v['message']}" for v in must],
    )

    tier_names = [t["name"] for t in profile.get("tiers") or []]
    lowest = tier_names[-1] if tier_names else None
    used = sorted({l["term"] for l in approved_links(current_systems(load_systems(args.systems)))})
    problems = []
    if lowest is None:
        problems.append(f"profile {profile_name} defines no tiers")
    for term_id in used:
        tier = tiers.get(term_id)
        if tier is None:
            problems.append(f"{term_id}: used by an approved link but not in the glossary")
        elif tier == "Below":
            problems.append(f"{term_id}: below the lowest tier ({lowest})")
    report.add(
        f"each of {len(used)} terms used by approved links reaches tier {lowest} or higher",
        problems,
    )
    return report


def run_script(script: str, *extra: str) -> list[str]:
    result = subprocess.run([sys.executable, str(SCRIPTS / script), *extra],
                            capture_output=True, text=True)
    if result.returncode == 0:
        return []
    return [(result.stderr or result.stdout).strip() or f"{script} exited {result.returncode}"]


def gate_3(args) -> Report:
    report = Report("Gate 3: architecture")
    links = approved_links(current_systems(load_systems(args.systems)))
    glossary = load_glossary(args.glossary)
    problems = []
    for link in links:
        term = glossary.get(link["term"])
        status = term.get("status") if term else None
        if status != "Approved":
            problems.append(
                f"{link['term']} in {link['system']}: "
                + ("not in the glossary" if term is None else f"term status is {status}, not Approved")
            )
    report.add(f"each of {len(links)} approved concepts: entries points to an Approved term",
               problems)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        report.add("map_build runs without errors", run_script(
            "map_build.py", "--systems", str(args.systems), "--out", str(out / "map.md")))
        report.add("gaps_build runs without errors", run_script(
            "gaps_build.py", "--systems", str(args.systems),
            "--glossary", str(args.glossary), "--out", str(out / "gaps.md")))
    return report


GATES = {"1": gate_1, "2": gate_2, "3": gate_3}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("gate", choices=sorted(GATES))
    parser.add_argument("--data", type=Path, required=True,
                        help="folder with systems/, notes/ and decisions/")
    parser.add_argument("--systems", type=Path, help="system notes (default: <data>/systems)")
    parser.add_argument("--glossary", type=Path, help="glossary repo (default: <data>/glossary)")
    parser.add_argument("--answers", type=Path, help="sample answer (required for gate 1)")
    args = parser.parse_args(argv)
    if args.gate == "1" and args.answers is None:
        parser.error("gate 1 requires --answers FILE")
    missing = [name for name in GATE_SCRIPTS[args.gate] if not (SCRIPTS / name).is_file()]
    if missing:
        print(f"error: gate {args.gate} needs {', '.join(missing)} next to check_gate.py; "
              f"this skill does not contain it. Run gate {args.gate} from the skill that does.",
              file=sys.stderr)
        return 2
    args.systems = args.systems or args.data / "systems"
    args.glossary = args.glossary or args.data / "glossary"
    for label, path in (("systems", args.systems), ("glossary", args.glossary)):
        if not path.is_dir():
            print(f"error: {label} directory not found: {path}", file=sys.stderr)
            return 2
    try:
        report = GATES[args.gate](args)
    except NoteError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(report.render())
    if report.passed:
        print(f"Gate {args.gate} program checks passed. The human sign-off is still "
              f"required: gates/signoff-{args.gate}.md, written by a person.")
        return 0
    print(FAIL_PROMPT)
    if args.systems.resolve().parts[-3:] == ("examples", "data", "systems") and args.gate == "3":
        print(DEMO_NOTE)
    return 1


if __name__ == "__main__":
    sys.exit(main())
