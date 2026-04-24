#!/usr/bin/env python3
"""Validate projection realization targets and record input/output hashes."""

from __future__ import annotations

import hashlib
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
PROJECTIONS_DIR = ROOT / "harness" / "projections"
DEFAULT_REPORT_PATH = ROOT / "reports" / "projection-sync.json"
EMPTY_ARRAY_PATTERN = re.compile(r'^(?P<indent> *)"(?P<key>[^"]+)": \[\]$', re.MULTILINE)
TOOL_NAME = "scripts/check_projection_sync.rb"


@dataclass(frozen=True)
class ProjectionEntry:
    """Report row for one realized projection target."""

    projection: str
    target: dict[str, object]
    realization: dict[str, object]
    inputs: dict[str, object]
    output: dict[str, object]
    changes_since_last_report: list[str]
    checked_at: str

    def to_report(self) -> dict[str, object]:
        """Return keys in the same insertion order as the Ruby report."""
        return {
            "projection": self.projection,
            "target": self.target,
            "realization": self.realization,
            "inputs": self.inputs,
            "output": self.output,
            "changes_since_last_report": self.changes_since_last_report,
            "checked_at": self.checked_at,
        }


@dataclass(frozen=True)
class OutputCheck:
    """Validated output metadata plus the optional success line to print."""

    metadata: dict[str, object]
    checked_line: str | None


@dataclass(frozen=True)
class ProjectionOutputContext:
    """Fields needed to validate one projection output."""

    projection_path: Path
    output_path: object
    output: Path
    mode: object
    realization: dict[str, object]


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


def as_mapping(value: object) -> dict[str, object]:
    """Return a YAML/JSON mapping or an empty mapping for absent optional sections."""
    if not isinstance(value, dict):
        return {}
    return cast("dict[str, object]", value)


def as_string_list(value: object) -> list[str]:
    """Return YAML sequence entries that are known paths in this template."""
    if not isinstance(value, list):
        return []
    return [str(entry) for entry in value]


def sha256_for(path: Path) -> str:
    """Hash file bytes, following symlinks the same way Ruby Digest::SHA256.file does."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_to_root(path: Path) -> str:
    """Return a POSIX path relative to the repository root."""
    return path.relative_to(ROOT).as_posix()


def ruby_inspect(value: object) -> str:
    """Render the unsupported-mode value like Ruby String#inspect for error text."""
    if isinstance(value, str):
        return json.dumps(value)
    return str(value)


def fail_with(errors: list[str]) -> None:
    """Print validation errors before exiting with the validator failure code."""
    for error in errors:
        print(error, file=sys.stderr)
    raise SystemExit(1)


def previous_report_by_projection() -> dict[str, dict[str, object]]:
    """Index the existing report by projection path for change detection."""
    if DEFAULT_REPORT_PATH.exists():
        previous_report = as_mapping(
            json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8")),
        )
    else:
        previous_report = {"projections": []}

    indexed: dict[str, dict[str, object]] = {}
    projections = previous_report.get("projections")
    if not isinstance(projections, list):
        return indexed
    for projection in projections:
        projection_mapping = as_mapping(projection)
        projection_path = projection_mapping.get("projection")
        if isinstance(projection_path, str):
            indexed[projection_path] = projection_mapping
    return indexed


def input_hashes_for(
    input_paths: list[str],
    errors: list[str],
    projection_path: Path,
) -> dict[str, object] | None:
    """Return input metadata or append projection-specific missing-input errors."""
    input_hashes: dict[str, object] = {}
    missing_inputs: list[str] = []
    for input_path in input_paths:
        input_file = ROOT / input_path
        if not input_file.exists():
            missing_inputs.append(input_path)
            continue
        input_hashes[input_path] = {
            "sha256": sha256_for(input_file),
            "kind": "symlink" if input_file.is_symlink() else "file",
        }

    if missing_inputs:
        errors.append(f"{projection_path}: missing input(s): {', '.join(missing_inputs)}")
        return None
    return input_hashes


def changed_inputs_since_previous(
    input_hashes: dict[str, object],
    previous_projection: dict[str, object],
) -> list[str]:
    """Return input paths whose current hash differs from the previous report."""
    previous_inputs = as_mapping(previous_projection.get("inputs"))
    changed_inputs: list[str] = []
    for input_path, metadata in input_hashes.items():
        metadata_mapping = as_mapping(metadata)
        previous_hash = as_mapping(previous_inputs.get(input_path)).get("sha256")
        if previous_hash and previous_hash != metadata_mapping.get("sha256"):
            changed_inputs.append(input_path)
    return changed_inputs


def base_output_metadata(context: ProjectionOutputContext) -> dict[str, object]:
    """Return output metadata fields shared by all realization modes."""
    return {
        "path": context.output_path,
        "kind": "symlink" if context.output.is_symlink() else "file",
    }


def emitted_output_check(
    context: ProjectionOutputContext,
    errors: list[str],
) -> OutputCheck | None:
    """Validate an emitted projection target."""
    output_metadata = base_output_metadata(context)
    if context.output.is_symlink():
        errors.append(
            f"{context.projection_path}: expected {context.output_path} to be a regular file, "
            "but it is a symlink",
        )
        return None
    output_metadata["sha256"] = sha256_for(context.output)
    return OutputCheck(metadata=output_metadata, checked_line=f"OK emitted {context.output_path}")


def symlink_output_check(
    context: ProjectionOutputContext,
    errors: list[str],
) -> OutputCheck | None:
    """Validate a symlink projection target."""
    output_metadata = base_output_metadata(context)
    if not context.output.is_symlink():
        errors.append(f"{context.projection_path}: expected {context.output_path} to be a symlink")
        return None

    canonical_source = context.realization.get("canonical_source")
    if not canonical_source:
        errors.append(
            f"{context.projection_path}: symlink mode requires realization.canonical_source",
        )
        return None

    expected = (ROOT / str(canonical_source)).resolve(strict=True)
    actual = context.output.resolve(strict=True)
    if actual != expected:
        errors.append(
            f"{context.projection_path}: {context.output_path} resolves to "
            f"{relative_to_root(actual)} not {canonical_source}",
        )
        return None

    output_metadata["canonical_source"] = canonical_source
    output_metadata["resolved_path"] = relative_to_root(actual)
    output_metadata["resolved_sha256"] = sha256_for(actual)
    return OutputCheck(
        metadata=output_metadata,
        checked_line=f"OK symlink {context.output_path} -> {canonical_source}",
    )


def output_check_for(context: ProjectionOutputContext, errors: list[str]) -> OutputCheck | None:
    """Validate one projection output according to its realization mode."""
    output_metadata: dict[str, object] = {
        "path": context.output_path,
        "kind": "symlink" if context.output.is_symlink() else "file",
    }
    if context.mode == "emitted":
        return emitted_output_check(context, errors)
    if context.mode == "symlink":
        return symlink_output_check(context, errors)
    errors.append(
        f"{context.projection_path}: unsupported realization.mode {ruby_inspect(context.mode)}",
    )
    return OutputCheck(metadata=output_metadata, checked_line=None)


def projection_entries() -> tuple[list[str], list[ProjectionEntry]]:
    """Validate projection files and return checked messages plus report rows."""
    errors: list[str] = []
    checked: list[str] = []
    entries: list[ProjectionEntry] = []
    previous_by_projection = previous_report_by_projection()

    for projection_path in sorted(PROJECTIONS_DIR.glob("*.yaml")):
        projection_data = load_yaml_mapping(projection_path)
        target = as_mapping(projection_data.get("target"))
        realization = as_mapping(projection_data.get("realization"))
        output_path = target.get("output_path")
        mode = realization.get("mode")
        projection_name = relative_to_root(projection_path)

        if not output_path:
            errors.append(f"{projection_path}: missing target.output_path")
            continue
        if not mode:
            errors.append(f"{projection_path}: missing realization.mode")
            continue

        output = ROOT / str(output_path)
        if not output.exists() and not output.is_symlink():
            errors.append(f"{projection_path}: target {output_path} does not exist")
            continue

        input_hashes = input_hashes_for(
            as_string_list(projection_data.get("inputs")),
            errors,
            projection_path,
        )
        if input_hashes is None:
            continue

        output_check = output_check_for(
            ProjectionOutputContext(
                projection_path=projection_path,
                output_path=output_path,
                output=output,
                mode=mode,
                realization=realization,
            ),
            errors,
        )
        if output_check is None:
            continue
        if output_check.checked_line is not None:
            checked.append(output_check.checked_line)

        previous_projection = previous_by_projection.get(projection_name, {})
        entries.append(
            ProjectionEntry(
                projection=projection_name,
                target=target,
                realization=realization,
                inputs=input_hashes,
                output=output_check.metadata,
                changes_since_last_report=changed_inputs_since_previous(
                    input_hashes,
                    previous_projection,
                ),
                checked_at=generated_timestamp(),
            ),
        )

    if errors:
        fail_with(errors)
    return checked, entries


def write_report(entries: list[ProjectionEntry]) -> None:
    """Write the projection sync report with the legacy key order."""
    report_payload: dict[str, object] = {
        "generated_at": generated_timestamp(),
        "tool": TOOL_NAME,
        "projections": [entry.to_report() for entry in entries],
    }
    DEFAULT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_REPORT_PATH.write_text(ruby_pretty_json(report_payload), encoding="utf-8")


def main() -> None:
    """Run the projection sync validator and emit the report."""
    checked, entries = projection_entries()
    write_report(entries)
    for line in checked:
        print(line)
    print(f"Projection realization checks passed for {len(checked)} target(s)")
    print(f"Wrote report {relative_to_root(DEFAULT_REPORT_PATH)}")


if __name__ == "__main__":
    main()
