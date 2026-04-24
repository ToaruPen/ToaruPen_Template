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
    script_path = scripts_dir / "check_rules.py"
    shutil.copy2(ROOT / "scripts" / "check_rules.py", script_path)
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


def write_rules(root: Path, rules_yaml: str) -> None:
    harness_dir = root / "harness"
    harness_dir.mkdir()
    (harness_dir / "rules.yaml").write_text(rules_yaml, encoding="utf-8")


def normalized_report(path: Path) -> dict[str, object]:
    report_payload = read_report(path)
    report_payload["generated_at"] = "<generated_at>"
    return report_payload


def valid_rules_yaml() -> str:
    return """\
enforcement_state: metadata only
planned_enforcement_layers:
  - hook
  - ci
rules:
  - id: no-generated-core-merge
    status: proposed
    scope: template
    rationale: Keep generated code reviewed.
    fix_hint: Review the generated change.
    enforcement_layer: hook
    adr:
"""


def test_check_rules_happy_path_writes_schema(tmp_path: Path) -> None:
    script_path = copy_script(tmp_path)
    write_rules(tmp_path, valid_rules_yaml())

    completed = run_script(script_path, tmp_path)

    assert completed.returncode == 0
    assert "Rules structure checks passed" in completed.stdout
    report_payload = read_report(tmp_path / "reports" / "rules-check.json")
    assert set(report_payload) == {
        "generated_at",
        "tool",
        "rules_file",
        "enforcement_state",
        "planned_enforcement_layers",
        "entries",
    }


def test_check_rules_reports_missing_key_invalid_layer_and_active_without_adr(
    tmp_path: Path,
) -> None:
    script_path = copy_script(tmp_path)
    write_rules(
        tmp_path,
        """\
enforcement_state: metadata only
planned_enforcement_layers:
  - hook
rules:
  - id: missing-rationale
    status: proposed
    scope: template
    fix_hint: Add the missing field.
    enforcement_layer: hook
    adr:
  - id: bad-layer
    status: proposed
    scope: template
    rationale: Exercise invalid layer validation.
    fix_hint: Pick a planned layer.
    enforcement_layer: unknown
    adr:
  - id: active-no-adr
    status: active
    scope: template
    rationale: Active rules need provenance.
    fix_hint: Link an ADR.
    enforcement_layer: hook
    adr:
""",
    )

    completed = run_script(script_path, tmp_path)

    assert completed.returncode == 1
    assert "missing-rationale: missing keys rationale" in completed.stderr
    assert "bad-layer: invalid enforcement_layer unknown" in completed.stderr
    assert "active-no-adr: active rules must reference an ADR" in completed.stderr


def test_check_rules_matches_committed_report_modulo_generated_at() -> None:
    script_path = ROOT / "scripts" / "check_rules.py"
    committed_report_path = ROOT / "reports" / "rules-check.json"
    committed_report_text = committed_report_path.read_text(encoding="utf-8")
    committed_report = normalized_report(committed_report_path)

    try:
        completed = run_script(script_path, ROOT)
        generated_report = normalized_report(committed_report_path)
    finally:
        committed_report_path.write_text(committed_report_text, encoding="utf-8")

    assert completed.returncode == 0
    assert generated_report == committed_report
