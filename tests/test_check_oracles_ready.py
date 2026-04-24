from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]


def copy_script(tmp_path: Path) -> Path:
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    script_path = scripts_dir / "check_oracles_ready.py"
    shutil.copy2(ROOT / "scripts" / "check_oracles_ready.py", script_path)
    return script_path


def run_script(script_path: Path, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - Tests execute copied validators against fixtures.
        [sys.executable, script_path.as_posix()],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def read_report(path: Path) -> dict[str, object]:
    return cast("dict[str, object]", json.loads(path.read_text(encoding="utf-8")))


def write_harness_files(root: Path, *, manifest_yaml: str, oracles_yaml: str) -> None:
    harness_dir = root / "harness"
    harness_dir.mkdir()
    (harness_dir / "manifest.yaml").write_text(manifest_yaml, encoding="utf-8")
    (harness_dir / "oracles.yaml").write_text(oracles_yaml, encoding="utf-8")


def normalized_report(path: Path) -> dict[str, object]:
    report_payload = read_report(path)
    report_payload["generated_at"] = "<generated_at>"
    return report_payload


def core_oracles_yaml() -> str:
    return """\
packs:
  - id: core
    checks:
      - id: format
        status: planned
        blocked_on: stack
      - id: lint
        status: planned
        blocked_on: stack
      - id: typecheck
        status: planned
        blocked_on: stack
      - id: unit
        status: planned
        blocked_on: stack
"""


def pending_manifest_yaml() -> str:
    return """\
specialization_record:
  stack_selection:
    status: pending
  harness_application:
    status: pending
    quality_commands:
      format:
        status: pending
        command: TBD
      lint:
        status: pending
        command: TBD
      typecheck:
        status: pending
        command: TBD
      unit:
        status: pending
        command: TBD
"""


def test_check_oracles_ready_happy_path_writes_schema(tmp_path: Path) -> None:
    script_path = copy_script(tmp_path)
    write_harness_files(
        tmp_path,
        manifest_yaml=pending_manifest_yaml(),
        oracles_yaml=core_oracles_yaml(),
    )

    completed = run_script(script_path, tmp_path)

    assert completed.returncode == 0
    assert "deferred until stack selection is complete" in completed.stdout
    report_payload = read_report(tmp_path / "reports" / "oracles-readiness.json")
    assert set(report_payload) == {
        "generated_at",
        "tool",
        "manifest",
        "oracles",
        "stack_selection_status",
        "harness_application_status",
        "entries",
        "errors",
    }


def test_check_oracles_ready_reports_all_readiness_failures(tmp_path: Path) -> None:
    script_path = copy_script(tmp_path)
    write_harness_files(
        tmp_path,
        manifest_yaml="""\
specialization_record:
  stack_selection:
    status: complete
  harness_application:
    status: complete
    quality_commands:
      format:
        status: pending
        command: run-format
      lint:
        status:
        command: run-lint
      typecheck:
        status: pending
        command: TBD
""",
        oracles_yaml="""\
packs:
  - id: core
    checks:
      - id: format
        status: planned
        blocked_on: stack
      - id: lint
        status: planned
        blocked_on: stack
      - id: typecheck
        status: planned
        blocked_on: stack
""",
    )

    completed = run_script(script_path, tmp_path)

    assert completed.returncode == 1
    assert "core oracle pack is missing checks: unit" in completed.stderr
    assert "quality_commands.format must be complete" in completed.stderr
    assert "quality_commands.lint.status is missing" in completed.stderr
    assert "quality_commands.typecheck.command is not ready" in completed.stderr


def test_check_oracles_ready_reports_missing_quality_command_entry(tmp_path: Path) -> None:
    script_path = copy_script(tmp_path)
    write_harness_files(
        tmp_path,
        manifest_yaml="""\
specialization_record:
  stack_selection:
    status: complete
  harness_application:
    status: pending
    quality_commands: {}
""",
        oracles_yaml=core_oracles_yaml(),
    )

    completed = run_script(script_path, tmp_path)

    assert completed.returncode == 1
    assert "missing quality_commands entry for format" in completed.stderr


def test_check_oracles_ready_matches_committed_report_modulo_generated_at() -> None:
    script_path = ROOT / "scripts" / "check_oracles_ready.py"
    committed_report_path = ROOT / "reports" / "oracles-readiness.json"
    committed_report_text = committed_report_path.read_text(encoding="utf-8")
    committed_report = normalized_report(committed_report_path)

    try:
        completed = run_script(script_path, ROOT)
        generated_report = normalized_report(committed_report_path)
    finally:
        committed_report_path.write_text(committed_report_text, encoding="utf-8")

    assert completed.returncode == 0
    assert generated_report == committed_report
