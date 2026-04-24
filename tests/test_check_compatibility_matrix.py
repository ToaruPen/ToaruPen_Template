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
    script_path = scripts_dir / "check_compatibility_matrix.py"
    shutil.copy2(ROOT / "scripts" / "check_compatibility_matrix.py", script_path)
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


def write_matrix(root: Path, matrix_yaml: str) -> None:
    harness_dir = root / "harness"
    harness_dir.mkdir()
    (harness_dir / "compatibility-matrix.yaml").write_text(matrix_yaml, encoding="utf-8")


def normalized_report(path: Path) -> dict[str, object]:
    report_payload = read_report(path)
    report_payload["generated_at"] = "<generated_at>"
    return report_payload


def minimal_matrix_yaml() -> str:
    return """\
status: draft
coverage: partial
matrix_scope: Fixture scope.
missing_policy: Missing entries are unreviewed.
kernel_vocabulary:
  - plans
  - hooks
vendors:
  vendor-b:
    support:
      plans:
        status: native
  vendor-a:
    support:
      hooks:
        status: emulated
"""


def test_check_compatibility_matrix_happy_path_writes_schema(tmp_path: Path) -> None:
    script_path = copy_script(tmp_path)
    write_matrix(tmp_path, minimal_matrix_yaml())

    completed = run_script(script_path, tmp_path)

    assert completed.returncode == 0
    assert "coverage summary generated for 2 vendor(s)" in completed.stdout
    report_payload = read_report(tmp_path / "reports" / "compatibility-matrix.json")
    assert set(report_payload) == {
        "generated_at",
        "tool",
        "matrix",
        "matrix_status",
        "matrix_coverage",
        "matrix_scope",
        "missing_policy",
        "totals",
        "vendors",
    }
    vendors = cast("list[dict[str, object]]", report_payload["vendors"])
    assert [vendor["vendor"] for vendor in vendors] == ["vendor-a", "vendor-b"]


def test_check_compatibility_matrix_handles_empty_vocabulary(tmp_path: Path) -> None:
    script_path = copy_script(tmp_path)
    write_matrix(
        tmp_path,
        """\
status: draft
coverage: partial
matrix_scope: Fixture scope.
missing_policy: Missing entries are unreviewed.
kernel_vocabulary: []
vendors:
  vendor-a:
    support: {}
""",
    )

    completed = run_script(script_path, tmp_path)

    assert completed.returncode == 0
    report_payload = read_report(tmp_path / "reports" / "compatibility-matrix.json")
    totals = cast("dict[str, object]", report_payload["totals"])
    assert totals["reviewed_coverage_percent"] == 0.0


def test_check_compatibility_matrix_matches_committed_report_modulo_generated_at() -> None:
    script_path = ROOT / "scripts" / "check_compatibility_matrix.py"
    committed_report_path = ROOT / "reports" / "compatibility-matrix.json"
    committed_report_text = committed_report_path.read_text(encoding="utf-8")
    committed_report = normalized_report(committed_report_path)

    try:
        completed = run_script(script_path, ROOT)
        generated_report = normalized_report(committed_report_path)
    finally:
        committed_report_path.write_text(committed_report_text, encoding="utf-8")

    assert completed.returncode == 0
    assert generated_report == committed_report
