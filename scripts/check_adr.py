#!/usr/bin/env python3
"""Validate ADR filenames, required headings, and accepted-record presence."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from re import Match

ROOT = Path(__file__).resolve().parent.parent
ADR_DIR = ROOT / "docs" / "adr"
REPORT_PATH = ROOT / "reports" / "adr-check.json"
DECISION_LOG_NAME = "decision-log.md"
ADR_PATTERN = re.compile(r"^\d{4}-[a-z0-9-]+\.md$")
REQUIRED_HEADINGS = (
    "## Context",
    "## Decision",
    "## Consequences",
    "## Related Artifacts",
)
EMPTY_ARRAY_PATTERN = re.compile(r'^(?P<indent> *)"(?P<key>[^"]+)": \[\]$', re.MULTILINE)
TOOL_NAME = "scripts/check_adr.py"


@dataclass(frozen=True)
class AdrEntry:
    """Report row for one ADR file after structural validation."""

    path: str
    status: str | None
    missing_headings: list[str]

    def to_report(self) -> dict[str, object]:
        """Return keys in the same insertion order as the Ruby report."""
        return {
            "path": self.path,
            "status": self.status,
            "missing_headings": self.missing_headings,
        }


def generated_timestamp() -> str:
    """Return the UTC timestamp format emitted by Ruby Time#iso8601."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def expand_empty_array(match: Match[str]) -> str:
    """Match Ruby JSON.pretty_generate formatting for empty array values."""
    indent = match.group("indent")
    key = match.group("key")
    return f'{indent}"{key}": [\n\n{indent}]'


def ruby_pretty_json(report_payload: dict[str, object]) -> str:
    """Serialize reports with Ruby-compatible empty-array whitespace."""
    json_text = json.dumps(report_payload, indent=2)
    return EMPTY_ARRAY_PATTERN.sub(expand_empty_array, json_text) + "\n"


def fail_with(errors: list[str]) -> None:
    """Print validation errors before exiting with the validator failure code."""
    for error in errors:
        print(error, file=sys.stderr)
    raise SystemExit(1)


def validate_adr_files() -> list[AdrEntry]:
    """Validate ADR files and return report entries when no failures block output."""
    if not ADR_DIR.is_dir():
        fail_with(["docs/adr directory does not exist"])

    errors: list[str] = []
    entries: list[AdrEntry] = []
    template_present = False
    accepted_present = False

    adr_files = sorted(
        candidate
        for candidate in ADR_DIR.iterdir()
        if candidate.is_file() and candidate.name != DECISION_LOG_NAME
    )
    for path in adr_files:
        basename = path.name
        relative_path = path.relative_to(ROOT).as_posix()
        if ADR_PATTERN.fullmatch(basename) is None:
            errors.append(f"{relative_path}: invalid ADR filename")
            continue

        text = path.read_text(encoding="utf-8")
        status_line = next(
            (line for line in text.splitlines() if line.startswith("Status: ")),
            None,
        )
        if status_line is None:
            errors.append(f"{relative_path}: missing Status line")

        missing_headings = [heading for heading in REQUIRED_HEADINGS if heading not in text]
        if missing_headings:
            errors.append(f"{relative_path}: missing headings {', '.join(missing_headings)}")

        status = status_line.removeprefix("Status: ").strip() if status_line is not None else None
        template_present = template_present or basename == "0000-adr-template.md"
        accepted_present = accepted_present or (
            basename != "0000-adr-template.md" and status is not None and status != "template"
        )

        entries.append(
            AdrEntry(
                path=relative_path,
                status=status,
                missing_headings=missing_headings,
            ),
        )

    if not template_present:
        errors.append("docs/adr/0000-adr-template.md is missing")
    if not accepted_present:
        errors.append("At least one non-template ADR is required")

    if errors:
        fail_with(errors)

    return entries


def write_report(entries: list[AdrEntry]) -> None:
    """Write the ADR report with the legacy key order."""
    report_payload: dict[str, object] = {
        "generated_at": generated_timestamp(),
        "tool": TOOL_NAME,
        "adr_directory": "docs/adr",
        "entries": [entry.to_report() for entry in entries],
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(ruby_pretty_json(report_payload), encoding="utf-8")


def main() -> None:
    """Run the ADR validator and emit the report."""
    entries = validate_adr_files()
    write_report(entries)
    print(f"ADR structure checks passed for {len(entries)} file(s)")
    print(f"Wrote report {REPORT_PATH.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
