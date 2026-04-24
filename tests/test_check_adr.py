from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]


def copy_script(tmp_path: Path, script_name: str) -> Path:
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    script_path = scripts_dir / script_name
    shutil.copy2(ROOT / "scripts" / script_name, script_path)
    script_path.chmod(0o755)
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


def adr_text(*, status: str = "accepted") -> str:
    return "\n".join(
        [
            "# Example ADR",
            "",
            f"Status: {status}",
            "",
            "## Context",
            "Context text.",
            "",
            "## Decision",
            "Decision text.",
            "",
            "## Consequences",
            "Consequence text.",
            "",
            "## Related Artifacts",
            "Artifact text.",
            "",
        ],
    )


def write_valid_adr_tree(root: Path) -> None:
    adr_dir = root / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "0000-adr-template.md").write_text(adr_text(status="template"), encoding="utf-8")
    (adr_dir / "0001-example.md").write_text(adr_text(), encoding="utf-8")
    (adr_dir / "decisions").mkdir()


def normalized_report(path: Path) -> dict[str, object]:
    report_payload = read_report(path)
    report_payload["generated_at"] = "<generated_at>"
    return report_payload


def test_check_adr_happy_path_writes_schema(tmp_path: Path) -> None:
    script_path = copy_script(tmp_path, "check_adr.py")
    write_valid_adr_tree(tmp_path)

    completed = run_script(script_path, tmp_path)

    assert completed.returncode == 0
    assert "ADR structure checks passed" in completed.stdout
    report_payload = read_report(tmp_path / "reports" / "adr-check.json")
    assert set(report_payload) == {"generated_at", "tool", "adr_directory", "entries"}
    entries = cast("list[object]", report_payload["entries"])
    assert len(entries) == 2


def test_check_adr_rejects_invalid_filename(tmp_path: Path) -> None:
    script_path = copy_script(tmp_path, "check_adr.py")
    write_valid_adr_tree(tmp_path)
    (tmp_path / "docs" / "adr" / "bad-name.md").write_text(adr_text(), encoding="utf-8")

    completed = run_script(script_path, tmp_path)

    assert completed.returncode == 1
    assert "docs/adr/bad-name.md: invalid ADR filename" in completed.stderr


def test_check_adr_rejects_missing_status_and_heading(tmp_path: Path) -> None:
    script_path = copy_script(tmp_path, "check_adr.py")
    write_valid_adr_tree(tmp_path)
    (tmp_path / "docs" / "adr" / "0002-broken.md").write_text(
        "# Broken\n\n## Context\n",
        encoding="utf-8",
    )

    completed = run_script(script_path, tmp_path)

    assert completed.returncode == 1
    assert "missing Status line" in completed.stderr
    assert "missing headings ## Decision, ## Consequences, ## Related Artifacts" in completed.stderr


def test_check_adr_skips_decision_log_artifact(tmp_path: Path) -> None:
    script_path = copy_script(tmp_path, "check_adr.py")
    write_valid_adr_tree(tmp_path)
    (tmp_path / "docs" / "adr" / "decision-log.md").write_text(
        "# ADR Decision Log\n",
        encoding="utf-8",
    )

    completed = run_script(script_path, tmp_path)

    assert completed.returncode == 0
    report_payload = read_report(tmp_path / "reports" / "adr-check.json")
    entries = cast("list[dict[str, object]]", report_payload["entries"])
    assert "docs/adr/decision-log.md" not in {entry["path"] for entry in entries}


def test_check_adr_matches_committed_report_modulo_generated_at() -> None:
    script_path = ROOT / "scripts" / "check_adr.py"
    committed_report_path = ROOT / "reports" / "adr-check.json"
    committed_report_text = committed_report_path.read_text(encoding="utf-8")
    committed_report = normalized_report(committed_report_path)

    try:
        completed = run_script(script_path, ROOT)
        generated_report = normalized_report(committed_report_path)
    finally:
        committed_report_path.write_text(committed_report_text, encoding="utf-8")

    assert completed.returncode == 0
    assert generated_report == committed_report
