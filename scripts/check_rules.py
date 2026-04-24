#!/usr/bin/env python3
"""Validate rule records against the planned enforcement-layer vocabulary."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import yaml

ROOT = Path(__file__).resolve().parent.parent
RULES_PATH = ROOT / "harness" / "rules.yaml"
REPORT_PATH = ROOT / "reports" / "rules-check.json"
REQUIRED_KEYS = ("id", "status", "scope", "rationale", "fix_hint", "enforcement_layer", "adr")
TOOL_NAME = "scripts/check_rules.rb"


@dataclass(frozen=True)
class RuleEntry:
    """Report projection for one rule after structural checks."""

    rule_id: object
    status: object
    enforcement_layer: object
    adr: object

    def to_report(self) -> dict[str, object]:
        """Return keys in the same insertion order as the Ruby report."""
        return {
            "id": self.rule_id,
            "status": self.status,
            "enforcement_layer": self.enforcement_layer,
            "adr": self.adr,
        }


def generated_timestamp() -> str:
    """Return the UTC timestamp format emitted by Ruby Time#iso8601."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_yaml_mapping(path: Path) -> dict[str, object]:
    """Load a YAML document expected to have a mapping root."""
    return cast("dict[str, object]", yaml.safe_load(path.read_text(encoding="utf-8")))


def fail_with(errors: list[str]) -> None:
    """Print validation errors before exiting with the validator failure code."""
    for error in errors:
        print(error, file=sys.stderr)
    raise SystemExit(1)


def as_mapping_list(value: object) -> list[dict[str, object]]:
    """Return YAML sequence entries that are known rule mappings in this template."""
    if not isinstance(value, list):
        return []
    return [cast("dict[str, object]", entry) for entry in value]


def as_string_list(value: object) -> list[str]:
    """Return YAML sequence entries that are known strings in this template."""
    if not isinstance(value, list):
        return []
    return [str(entry) for entry in value]


def validate_rules() -> tuple[dict[str, object], list[str], list[RuleEntry], list[str]]:
    """Validate rules.yaml and return the report ingredients."""
    rules_data = load_yaml_mapping(RULES_PATH)
    layers = as_string_list(rules_data.get("planned_enforcement_layers"))
    rules = as_mapping_list(rules_data.get("rules"))
    errors: list[str] = []
    entries: list[RuleEntry] = []

    for rule in rules:
        missing_keys = [key for key in REQUIRED_KEYS if key not in rule]
        rule_id = rule.get("id")
        if missing_keys:
            errors.append(f"{rule_id or '<unknown>'}: missing keys {', '.join(missing_keys)}")

        enforcement_layer = rule.get("enforcement_layer")
        if enforcement_layer and enforcement_layer not in layers:
            errors.append(f"{rule_id}: invalid enforcement_layer {enforcement_layer}")

        adr = rule.get("adr")
        if rule.get("status") == "active" and (adr is None or str(adr) == ""):
            errors.append(f"{rule_id}: active rules must reference an ADR")

        entries.append(
            RuleEntry(
                rule_id=rule_id,
                status=rule.get("status"),
                enforcement_layer=enforcement_layer,
                adr=adr,
            ),
        )

    return rules_data, layers, entries, errors


def write_report(
    rules_data: dict[str, object],
    layers: list[str],
    entries: list[RuleEntry],
) -> None:
    """Write the rules report with the legacy key order."""
    report_payload: dict[str, object] = {
        "generated_at": generated_timestamp(),
        "tool": TOOL_NAME,
        "rules_file": "harness/rules.yaml",
        "enforcement_state": rules_data.get("enforcement_state"),
        "planned_enforcement_layers": layers,
        "entries": [entry.to_report() for entry in entries],
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report_payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    """Run the rules validator and emit the report."""
    rules_data, layers, entries, errors = validate_rules()
    if errors:
        fail_with(errors)

    write_report(rules_data, layers, entries)
    print(f"Rules structure checks passed for {len(entries)} rule(s)")
    print(f"Wrote report {REPORT_PATH.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
