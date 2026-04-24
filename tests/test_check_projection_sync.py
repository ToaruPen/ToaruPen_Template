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
    script_path = scripts_dir / "check_projection_sync.py"
    shutil.copy2(ROOT / "scripts" / "check_projection_sync.py", script_path)
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


def write_projection(root: Path, filename: str, projection_yaml: str) -> None:
    projections_dir = root / "harness" / "projections"
    projections_dir.mkdir(parents=True, exist_ok=True)
    (projections_dir / filename).write_text(projection_yaml, encoding="utf-8")


def normalized_report(path: Path) -> dict[str, object]:
    report_payload = read_report(path)
    report_payload["generated_at"] = "<generated_at>"
    for projection in cast("list[dict[str, object]]", report_payload["projections"]):
        projection["checked_at"] = "<checked_at>"
        projection["changes_since_last_report"] = "<changes_since_last_report>"
        for input_metadata in cast("dict[str, dict[str, object]]", projection["inputs"]).values():
            input_metadata["sha256"] = "<sha256>"
        output_metadata = cast("dict[str, object]", projection["output"])
        if "sha256" in output_metadata:
            output_metadata["sha256"] = "<sha256>"
        if "resolved_sha256" in output_metadata:
            output_metadata["resolved_sha256"] = "<sha256>"
    return report_payload


def test_check_projection_sync_happy_path_writes_schema(tmp_path: Path) -> None:
    script_path = copy_script(tmp_path)
    (tmp_path / "SOURCE.md").write_text("source\n", encoding="utf-8")
    (tmp_path / "TARGET.md").symlink_to("SOURCE.md")
    write_projection(
        tmp_path,
        "vendor.yaml",
        """\
target:
  vendor: fixture
  surface: TARGET.md
  output_path: TARGET.md
realization:
  mode: symlink
  canonical_source: SOURCE.md
inputs:
  - SOURCE.md
""",
    )

    completed = run_script(script_path, tmp_path)

    assert completed.returncode == 0
    assert "OK symlink TARGET.md -> SOURCE.md" in completed.stdout
    report_payload = read_report(tmp_path / "reports" / "projection-sync.json")
    assert set(report_payload) == {"generated_at", "tool", "projections"}
    projections = cast("list[object]", report_payload["projections"])
    assert len(projections) == 1


def test_check_projection_sync_reports_validation_failures(tmp_path: Path) -> None:
    script_path = copy_script(tmp_path)
    (tmp_path / "input.md").write_text("input\n", encoding="utf-8")
    (tmp_path / "regular.md").write_text("regular\n", encoding="utf-8")
    (tmp_path / "wrong.md").write_text("wrong\n", encoding="utf-8")
    (tmp_path / "emitted-link.md").symlink_to("input.md")
    (tmp_path / "bad-link.md").symlink_to("wrong.md")
    write_projection(
        tmp_path,
        "01-missing-output-path.yaml",
        "target: {}\nrealization:\n  mode: emitted\n",
    )
    write_projection(
        tmp_path,
        "02-missing-mode.yaml",
        "target:\n  output_path: regular.md\nrealization: {}\n",
    )
    write_projection(
        tmp_path,
        "03-missing-target.yaml",
        "target:\n  output_path: absent.md\nrealization:\n  mode: emitted\n",
    )
    write_projection(
        tmp_path,
        "04-missing-input.yaml",
        "target:\n"
        "  output_path: regular.md\n"
        "realization:\n"
        "  mode: emitted\n"
        "inputs:\n"
        "  - absent.md\n",
    )
    write_projection(
        tmp_path,
        "05-emitted-symlink.yaml",
        "target:\n  output_path: emitted-link.md\nrealization:\n  mode: emitted\n",
    )
    write_projection(
        tmp_path,
        "06-symlink-regular.yaml",
        "target:\n  output_path: regular.md\nrealization:\n  mode: symlink\n",
    )
    write_projection(
        tmp_path,
        "07-symlink-missing-source.yaml",
        "target:\n  output_path: bad-link.md\nrealization:\n  mode: symlink\n",
    )
    write_projection(
        tmp_path,
        "08-symlink-wrong-source.yaml",
        "target:\n"
        "  output_path: bad-link.md\n"
        "realization:\n"
        "  mode: symlink\n"
        "  canonical_source: input.md\n",
    )
    write_projection(
        tmp_path,
        "09-unsupported-mode.yaml",
        "target:\n  output_path: regular.md\nrealization:\n  mode: copied\n",
    )

    completed = run_script(script_path, tmp_path)

    assert completed.returncode == 1
    assert "missing target.output_path" in completed.stderr
    assert "missing realization.mode" in completed.stderr
    assert "target absent.md does not exist" in completed.stderr
    assert "missing input(s): absent.md" in completed.stderr
    assert "expected emitted-link.md to be a regular file" in completed.stderr
    assert "expected regular.md to be a symlink" in completed.stderr
    assert "symlink mode requires realization.canonical_source" in completed.stderr
    assert "bad-link.md resolves to wrong.md not input.md" in completed.stderr
    assert 'unsupported realization.mode "copied"' in completed.stderr


def test_check_projection_sync_matches_committed_report_modulo_timestamps() -> None:
    script_path = ROOT / "scripts" / "check_projection_sync.py"
    committed_report_path = ROOT / "reports" / "projection-sync.json"
    committed_report_text = committed_report_path.read_text(encoding="utf-8")
    committed_report = normalized_report(committed_report_path)

    try:
        completed = run_script(script_path, ROOT)
        generated_report = normalized_report(committed_report_path)
    finally:
        committed_report_path.write_text(committed_report_text, encoding="utf-8")

    assert completed.returncode == 0
    assert generated_report == committed_report
