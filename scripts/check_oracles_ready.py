#!/usr/bin/env python3
"""Validate manifest quality-command readiness against the core oracle pack."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from re import Match
from typing import cast

import yaml

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "harness" / "manifest.yaml"
ORACLES_PATH = ROOT / "harness" / "oracles.yaml"
REPORT_PATH = ROOT / "reports" / "oracles-readiness.json"
CORE_CHECKS = ("format", "lint", "typecheck", "unit")
EMPTY_ARRAY_PATTERN = re.compile(r'^(?P<indent> *)"(?P<key>[^"]+)": \[\]$', re.MULTILINE)
TOOL_NAME = "scripts/check_oracles_ready.rb"


@dataclass(frozen=True)
class OracleEntry:
    """Report row joining an oracle check to its manifest command state."""

    check_id: object
    oracle_status: object
    blocked_on: object
    manifest_status: object
    manifest_command: object

    def to_report(self) -> dict[str, object]:
        """Return keys in the same insertion order as the Ruby report."""
        return {
            "check_id": self.check_id,
            "oracle_status": self.oracle_status,
            "blocked_on": self.blocked_on,
            "manifest_status": self.manifest_status,
            "manifest_command": self.manifest_command,
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


def load_yaml_mapping(path: Path) -> dict[str, object]:
    """Load a YAML document expected to have a mapping root."""
    return cast("dict[str, object]", yaml.safe_load(path.read_text(encoding="utf-8")))


def mapping_at(mapping: dict[str, object], *keys: str) -> dict[str, object]:
    """Return a nested YAML mapping or an empty mapping for absent optional sections."""
    current: object = mapping
    for key in keys:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    if not isinstance(current, dict):
        return {}
    return cast("dict[str, object]", current)


def value_at(mapping: dict[str, object], *keys: str) -> object:
    """Return a nested YAML value using Ruby dig-like nil behavior."""
    current: object = mapping
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def as_mapping_list(value: object) -> list[dict[str, object]]:
    """Return YAML sequence entries that are known mappings in this template."""
    if not isinstance(value, list):
        return []
    return [cast("dict[str, object]", entry) for entry in value]


def selected_core_checks(oracles: dict[str, object]) -> list[dict[str, object]]:
    """Return core-pack checks that participate in readiness validation."""
    packs = as_mapping_list(oracles.get("packs"))
    core_pack = next((pack for pack in packs if pack.get("id") == "core"), {})
    checks = as_mapping_list(core_pack.get("checks"))
    return [check for check in checks if check.get("id") in CORE_CHECKS]


def validate_oracles() -> tuple[dict[str, object], list[str]]:
    """Build the report and collect readiness failures."""
    manifest = load_yaml_mapping(MANIFEST_PATH)
    oracles = load_yaml_mapping(ORACLES_PATH)
    stack_status = value_at(manifest, "specialization_record", "stack_selection", "status")
    harness_status = value_at(manifest, "specialization_record", "harness_application", "status")
    quality_commands = mapping_at(
        manifest,
        "specialization_record",
        "harness_application",
        "quality_commands",
    )

    core_checks = selected_core_checks(oracles)
    errors: list[str] = []
    check_ids = [str(check.get("id")) for check in core_checks]
    missing_core_checks = [check_id for check_id in CORE_CHECKS if check_id not in check_ids]
    if missing_core_checks:
        errors.append(f"core oracle pack is missing checks: {', '.join(missing_core_checks)}")

    entries: list[OracleEntry] = []
    for check in core_checks:
        check_id = str(check.get("id"))
        manifest_entry = quality_commands.get(check_id)
        command_mapping = (
            cast("dict[str, object]", manifest_entry) if isinstance(manifest_entry, dict) else {}
        )
        command = command_mapping.get("command")
        status = command_mapping.get("status")

        if stack_status == "complete":
            if not command_mapping:
                errors.append(f"missing quality_commands entry for {check_id}")
            elif status is None or status == "":
                errors.append(f"quality_commands.{check_id}.status is missing")
            elif command is None or command == "TBD" or str(command).strip() == "":
                errors.append(f"quality_commands.{check_id}.command is not ready")
            elif harness_status == "complete" and status != "complete":
                errors.append(
                    f"quality_commands.{check_id} must be complete when "
                    "harness_application.status == complete",
                )

        entries.append(
            OracleEntry(
                check_id=check.get("id"),
                oracle_status=check.get("status"),
                blocked_on=check.get("blocked_on"),
                manifest_status=status,
                manifest_command=command,
            ),
        )

    report_payload: dict[str, object] = {
        "generated_at": generated_timestamp(),
        "tool": TOOL_NAME,
        "manifest": "harness/manifest.yaml",
        "oracles": "harness/oracles.yaml",
        "stack_selection_status": stack_status,
        "harness_application_status": harness_status,
        "entries": [entry.to_report() for entry in entries],
        "errors": errors,
    }
    return report_payload, errors


def report_and_exit(report_payload: dict[str, object], errors: list[str]) -> None:
    """Write the readiness report and mirror the Ruby success/failure messages."""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(ruby_pretty_json(report_payload), encoding="utf-8")
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(f"Wrote report {REPORT_PATH.relative_to(ROOT).as_posix()}")
        raise SystemExit(1)

    if report_payload["stack_selection_status"] == "complete":
        print("Oracle readiness checks passed")
    else:
        print("Oracle readiness checks deferred until stack selection is complete")
    print(f"Wrote report {REPORT_PATH.relative_to(ROOT).as_posix()}")


def main() -> None:
    """Run the oracle readiness validator and emit the report."""
    report_payload, errors = validate_oracles()
    report_and_exit(report_payload, errors)


if __name__ == "__main__":
    main()
