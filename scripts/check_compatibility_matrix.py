#!/usr/bin/env python3
"""Generate reviewed-coverage totals for the vendor compatibility matrix."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import yaml

ROOT = Path(__file__).resolve().parent.parent
MATRIX_PATH = ROOT / "harness" / "compatibility-matrix.yaml"
REPORT_PATH = ROOT / "reports" / "compatibility-matrix.json"
PERCENT_SCALE = 100
PERCENT_DIGITS = 2
TOOL_NAME = "scripts/check_compatibility_matrix.py"


@dataclass(frozen=True)
class VendorEntry:
    """Report row summarizing one vendor's reviewed capability cells."""

    vendor: str
    reviewed_capabilities: int
    total_capabilities: int
    reviewed_coverage_percent: float
    status_counts: dict[str, int]
    unreviewed_capabilities: list[str]

    def to_report(self) -> dict[str, object]:
        """Return keys in the same insertion order as the Ruby report."""
        return {
            "vendor": self.vendor,
            "reviewed_capabilities": self.reviewed_capabilities,
            "total_capabilities": self.total_capabilities,
            "reviewed_coverage_percent": self.reviewed_coverage_percent,
            "status_counts": self.status_counts,
            "unreviewed_capabilities": self.unreviewed_capabilities,
        }


def generated_timestamp() -> str:
    """Return the UTC timestamp format emitted by Ruby Time#iso8601."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_yaml_mapping(path: Path) -> dict[str, object]:
    """Load a YAML document expected to have a mapping root."""
    return cast("dict[str, object]", yaml.safe_load(path.read_text(encoding="utf-8")))


def as_string_list(value: object) -> list[str]:
    """Return YAML sequence entries that are known strings in this template."""
    if not isinstance(value, list):
        return []
    return [str(entry) for entry in value]


def as_mapping(value: object) -> dict[str, object]:
    """Return a YAML mapping or an empty mapping for absent optional sections."""
    if not isinstance(value, dict):
        return {}
    return cast("dict[str, object]", value)


def percentage(part: int, whole: int) -> float:
    """Return Ruby-compatible coverage percentage for report values."""
    if whole == 0:
        return 0.0
    return round((part / whole) * PERCENT_SCALE, PERCENT_DIGITS)


def vendor_entries(matrix: dict[str, object]) -> list[VendorEntry]:
    """Build sorted vendor report entries from the matrix document."""
    vocabulary = as_string_list(matrix.get("kernel_vocabulary"))
    vendors = as_mapping(matrix.get("vendors"))
    entries: list[VendorEntry] = []

    for vendor_name, vendor_value in sorted(vendors.items()):
        vendor_data = as_mapping(vendor_value)
        support = as_mapping(vendor_data.get("support"))
        missing = [capability for capability in vocabulary if capability not in support]
        status_counter: Counter[str] = Counter()
        for support_value in support.values():
            support_entry = as_mapping(support_value)
            status_counter[str(support_entry["status"])] += 1

        reviewed = len(support)
        entries.append(
            VendorEntry(
                vendor=vendor_name,
                reviewed_capabilities=reviewed,
                total_capabilities=len(vocabulary),
                reviewed_coverage_percent=percentage(reviewed, len(vocabulary)),
                status_counts=dict(sorted(status_counter.items())),
                unreviewed_capabilities=sorted(missing),
            ),
        )

    return entries


def totals_for(entries: list[VendorEntry], vocabulary_size: int) -> dict[str, object]:
    """Return aggregate matrix coverage totals with legacy key order."""
    reviewed_cells = sum(entry.reviewed_capabilities for entry in entries)
    possible_cells = len(entries) * vocabulary_size
    totals: dict[str, object] = {
        "vendors": len(entries),
        "capability_vocabulary_size": vocabulary_size,
        "reviewed_cells": reviewed_cells,
        "possible_cells": possible_cells,
    }
    totals["reviewed_coverage_percent"] = percentage(reviewed_cells, possible_cells)
    return totals


def write_report(matrix: dict[str, object], entries: list[VendorEntry]) -> None:
    """Write the compatibility report with the legacy key order."""
    vocabulary = as_string_list(matrix.get("kernel_vocabulary"))
    report_payload: dict[str, object] = {
        "generated_at": generated_timestamp(),
        "tool": TOOL_NAME,
        "matrix": MATRIX_PATH.relative_to(ROOT).as_posix(),
        "matrix_status": matrix.get("status"),
        "matrix_coverage": matrix.get("coverage"),
        "matrix_scope": matrix.get("matrix_scope"),
        "missing_policy": matrix.get("missing_policy"),
        "totals": totals_for(entries, len(vocabulary)),
        "vendors": [entry.to_report() for entry in entries],
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report_payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    """Run the compatibility matrix summarizer and emit the report."""
    matrix = load_yaml_mapping(MATRIX_PATH)
    entries = vendor_entries(matrix)
    write_report(matrix, entries)
    print(f"Compatibility matrix coverage summary generated for {len(entries)} vendor(s)")
    print(f"Wrote report {REPORT_PATH.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
