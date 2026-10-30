"""
Phase 21 — Benchmark Suite and CLI Integration Tests.

Validates:
  GET /api/ml/benchmark      — returns comparative metrics across paradigms
  scripts/benchmark_evaluation — executes multi-paradigm regression evaluations
  cli.py commands             — executes health and predict commands cleanly
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from scripts.benchmark_evaluation import run_benchmark


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_api_ml_benchmark_endpoint(client):
    """GET /api/ml/benchmark must return comparative evaluations for all 3 paradigms."""
    resp = await client.get("/api/ml/benchmark")
    assert resp.status_code == 200
    data = resp.json()

    assert "paradigms" in data
    paradigms = data["paradigms"]
    assert "heuristic_baseline" in paradigms
    assert "trained_ml_model" in paradigms
    assert "llm_as_a_judge" in paradigms

    # Validate trained model metrics
    ml_res = paradigms["trained_ml_model"]
    assert ml_res["r2_score"] >= 0.80
    assert ml_res["mae"] <= 0.15
    assert ml_res["mean_latency_ms"] >= 0.0
    assert ml_res["cost_per_1k_usd"] == 0.00


def test_benchmark_script_execution():
    """Direct execution of run_benchmark() must compute valid comparative report."""
    results = run_benchmark()
    assert "paradigms" in results
    assert "heuristic_baseline" in results["paradigms"]
    assert "trained_ml_model" in results["paradigms"]

    # Verify report files were generated
    from pathlib import Path
    benchmark_dir = Path(__file__).resolve().parent.parent / "data" / "benchmarks"
    assert (benchmark_dir / "model_benchmark_report.json").exists()
    assert (benchmark_dir / "benchmark_summary.md").exists()


def test_cli_health_and_predict(capsys):
    """CLI functions cmd_health and cmd_predict execute without unhandled exceptions."""
    import argparse
    from cli import cmd_health, cmd_predict

    # Test health
    cmd_health(argparse.Namespace())
    captured = capsys.readouterr()
    assert "Overall Status: HEALTHY" in captured.out

    # Test predict
    cmd_predict(argparse.Namespace(
        resume="Python developer with machine learning experience",
        job="Seeking Python developer with machine learning skills",
        skills="Python,Machine Learning"
    ))
    captured = capsys.readouterr()
    assert "ML COMPATIBILITY INFERENCE RESULT" in captured.out
    assert "Predicted Score:" in captured.out
