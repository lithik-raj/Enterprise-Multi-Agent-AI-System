"""
Phase 25 — End-to-End System Verification & Certification Tests.

Covers:
  - scripts/verify_system.py execution and 100% check pass rate
  - data/system_verification_report.json schema and persistence
  - cli.py Phase 25 commands: batch, audit, and verify
"""

import argparse
import json
from pathlib import Path
import pytest

from scripts.verify_system import run_system_verification
from cli import cmd_batch, cmd_audit, cmd_verify

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


def test_system_verification_harness():
    """Verify that all 12 platform subsystem checks pass with 100% success."""
    report = run_system_verification()

    assert report is not None
    assert report["total_checks"] == 12
    assert report["passed"] == 12
    assert report["failed"] == 0
    assert (report["passed"] / report["total_checks"]) == 1.0

    # Verify report JSON artifact was written to disk
    report_file = WORKSPACE_ROOT / "data" / "system_verification_report.json"
    assert report_file.exists(), "system_verification_report.json must be persisted"

    with open(report_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["passed"] == 12
    assert len(data["checks"]) == 12
    for check in data["checks"]:
        assert check["status"] == "passed"
        assert "latency_ms" in check


def test_cli_batch_command(capsys):
    """Verify CLI batch command outputs formatted candidate leaderboard."""
    cmd_batch(argparse.Namespace(batch_id="batch-demo-talent-001", export=None))
    captured = capsys.readouterr()
    assert "BATCH TALENT INTELLIGENCE LEADERBOARD" in captured.out
    assert "Dr. Sarah Lin" in captured.out
    assert "Alex Vance" in captured.out
    assert "Mean Score:" in captured.out


def test_cli_batch_export_csv(capsys, tmp_path):
    """Verify CLI batch command exports valid CSV table to file."""
    csv_target = tmp_path / "leaderboard_export.csv"
    cmd_batch(argparse.Namespace(batch_id="batch-demo-talent-001", export=str(csv_target)))
    captured = capsys.readouterr()
    assert "Exported CSV leaderboard to:" in captured.out
    assert csv_target.exists()
    content = csv_target.read_text(encoding="utf-8")
    assert "Rank,Candidate Name" in content
    assert "Dr. Sarah Lin" in content


def test_cli_audit_command(capsys):
    """Verify CLI audit command displays logged observability events."""
    cmd_audit(argparse.Namespace(limit=5, category=None))
    captured = capsys.readouterr()
    assert "SYSTEM OBSERVABILITY & AUDIT TRAIL" in captured.out
    assert "Total Logged Events:" in captured.out


def test_cli_verify_command(capsys):
    """Verify CLI verify command runs the Phase 25 verification suite."""
    cmd_verify(argparse.Namespace())
    captured = capsys.readouterr()
    assert "PHASE 25 E2E VERIFICATION SUITE" in captured.out
    assert "12/12 Checks Passed (100.0%)" in captured.out
