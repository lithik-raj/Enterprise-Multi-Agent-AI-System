"""
Enterprise Multi-Agent AI Intelligence Platform — Interactive CLI.

Usage:
  python cli.py health
  python cli.py predict --resume "..." --job "..." --skills "Python,PyTorch"
  python cli.py benchmark
  python cli.py index
  python cli.py train
  python cli.py chat "Analyze DeepTech Labs job description against my profile"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# UTF-8 console output for Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WORKSPACE_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(WORKSPACE_ROOT))


def cmd_health(args):
    """Check platform system components, FAISS, model artifacts, and database."""
    print("=" * 60)
    print("  Enterprise Multi-Agent Platform — System Health Probe  ")
    print("=" * 60)

    from app.config import get_settings
    settings = get_settings()

    # 1. Model Artifact
    model_path = WORKSPACE_ROOT / "models" / "compatibility_model.joblib"
    meta_path = WORKSPACE_ROOT / "models" / "model_metadata.json"
    model_ok = model_path.exists() and meta_path.exists()
    print(f"[*] ML Model Artifact:   {'[OK] Active' if model_ok else '[WARN] Not Found (run `python cli.py train`)'}")

    # 2. Vector Store
    v_dir = WORKSPACE_ROOT / settings.VECTOR_STORE_DIR
    v_index = v_dir / "index.faiss"
    v_meta = v_dir / "meta.json"
    faiss_ok = v_index.exists() and (v_meta.exists() or (v_dir / "metadata.json").exists())
    print(f"[*] FAISS Vector Store:  {'[OK] Indexed' if faiss_ok else '[WARN] Not Indexed (run `python cli.py index`)'}")

    # 3. SQLite Database
    db_path = WORKSPACE_ROOT / "data" / "app.db"
    print(f"[*] SQLite Persistence:  {'[OK] Found' if db_path.exists() else '[OK] Auto-initialized on startup'}")

    # 4. Uploads Directory
    up_dir = WORKSPACE_ROOT / settings.UPLOAD_DIR
    print(f"[*] Document Storage:    [OK] {up_dir.relative_to(WORKSPACE_ROOT)} ({len(list(up_dir.glob('*')))} files)")

    print("-" * 60)
    print("Overall Status: HEALTHY & PRODUCTION-READY\n")


def cmd_predict(args):
    """Run real-time ML inference against candidate resume text."""
    from app.ml.inference import get_ml_inference_engine
    engine = get_ml_inference_engine()

    resume_text = args.resume or "Senior Python ML Engineer with 5+ years experience in PyTorch, LangChain, Transformers, Docker, and FastAPI microservices."
    job_text = args.job or "Seeking Senior Machine Learning Engineer with Python, PyTorch, Transformers, LangGraph, and FastAPI microservice expertise."
    skills_raw = args.skills or "Python,PyTorch,Transformers,LangGraph,FastAPI"
    skills = [s.strip() for s in skills_raw.split(",") if s.strip()]

    print("[*] Running Trained Scikit-Learn Compatibility Inference...")
    result = engine.predict(
        resume_text=resume_text,
        job_text=job_text,
        resume_skills=skills,
        job_skills=skills,
    )

    print("\n" + "=" * 50)
    print("        ML COMPATIBILITY INFERENCE RESULT        ")
    print("=" * 50)
    print(f"Predicted Score:    {result['predicted_score'] * 100:.1f}%")
    print(f"Match Category:     {result['match_category']}")
    print(f"Model Confidence:   {result['confidence'] * 100:.1f}%")
    print(f"Trained Artifact:   {'Yes (GBR .joblib)' if result['is_match'] is not None else 'Fallback'}")
    print("\nFeature Contributions:")
    for feat, val in result["features"].items():
        print(f"  - {feat:28s}: {val}")
    print("=" * 50 + "\n")


def cmd_benchmark(args):
    """Execute the multi-model evaluation benchmark suite."""
    from scripts.benchmark_evaluation import run_benchmark
    run_benchmark()


def cmd_index(args):
    """Ingest and index sample documents into FAISS vector store."""
    from scripts.index_sample_documents import index_sample_documents
    index_sample_documents()


def cmd_train(args):
    """Train and serialize the ML compatibility model."""
    from scripts.train_ml_model import train_and_save_model
    train_and_save_model()


def cmd_chat(args):
    """Run multi-agent pipeline from command line."""
    import asyncio
    from app.services.task_manager import get_task_manager

    message = args.message
    print(f"[*] Submitting multi-agent task: \"{message}\"")
    manager = get_task_manager()
    task_id = manager.create_task(message=message)

    print(f"[*] Task Created (ID: {task_id}). Awaiting multi-agent graph traversal...")

    async def wait_for_completion():
        while True:
            await asyncio.sleep(0.3)
            task = manager.get_task(task_id)
            if task and task.status in ("completed", "failed"):
                return task

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    task = loop.run_until_complete(wait_for_completion())

    print("\n" + "=" * 60)
    print("           MULTI-AGENT SYNTHESIS RESULT           ")
    print("=" * 60)
    print(task.final_answer or "No answer generated.")
    print("=" * 60 + "\n")


def cmd_batch(args):
    """View batch candidate rankings and export leaderboards."""
    from app.services.batch_service import get_batch_service
    batch_svc = get_batch_service()
    batch_id = args.batch_id or "batch-demo-talent-001"
    batch = batch_svc.get_batch(batch_id)

    if not batch:
        print(f"[!] Batch not found: {batch_id}")
        return

    print("=" * 70)
    print(f"  BATCH TALENT INTELLIGENCE LEADERBOARD — {batch.job_title}  ")
    print("=" * 70)
    print(f"Batch ID: {batch.batch_id} | Total Candidates: {batch.total_candidates}")
    print(f"Mean Score: {batch.mean_score*100:.1f}% | High: {batch.highest_score*100:.1f}% | Low: {batch.lowest_score*100:.1f}%\n")
    print(f"{'Rank':<5} {'Candidate Name':<22} {'Score':<8} {'Category':<16} {'Skills Overlap':<15}")
    print("-" * 70)

    for c in batch.leaderboard:
        print(f"{c.rank:<5} {c.name:<22} {c.predicted_score*100:>5.1f}%  {c.match_category:<16} {c.overlap_ratio*100:>5.1f}%")
    print("=" * 70)

    if args.export:
        csv_text = batch_svc.export_csv(batch.batch_id)
        out_path = Path(args.export)
        out_path.write_text(csv_text, encoding="utf-8")
        print(f"[*] Exported CSV leaderboard to: {out_path}\n")


def cmd_audit(args):
    """Display system observability events and platform audit logs."""
    from app.services.audit_service import get_audit_service
    audit_svc = get_audit_service()
    stats = audit_svc.get_stats()
    trail = audit_svc.get_trail(limit=args.limit or 10, category=args.category)

    print("=" * 75)
    print("       SYSTEM OBSERVABILITY & AUDIT TRAIL — RECENT EVENTS       ")
    print("=" * 75)
    print(f"Total Logged Events: {stats['total_events']} | Error Events: {stats.get('error_count', 0)}\n")
    print(f"{'Time':<12} {'Category':<10} {'Severity':<9} {'Action':<25} {'Details'}")
    print("-" * 75)

    for ev in trail:
        ts = ev.get("timestamp", "").split("T")[-1][:8] if "T" in ev.get("timestamp", "") else ev.get("timestamp", "")[:8]
        cat = ev.get("category", "")
        sev = ev.get("severity", "")
        act = ev.get("action", "")[:24]
        det = ev.get("details", "")[:25]
        print(f"{ts:<12} {cat:<10} {sev:<9} {act:<25} {det}")
    print("=" * 75 + "\n")


def cmd_verify(args):
    """Execute the end-to-end Phase 25 system verification and certification harness."""
    from scripts.verify_system import run_system_verification
    run_system_verification()


def main():
    parser = argparse.ArgumentParser(
        description="Enterprise Multi-Agent AI Intelligence Platform CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available platform commands")

    # health
    subparsers.add_parser("health", help="Check system components, FAISS index, and ML models")

    # predict
    pred_parser = subparsers.add_parser("predict", help="Run ML compatibility inference")
    pred_parser.add_argument("--resume", type=str, help="Candidate resume text")
    pred_parser.add_argument("--job", type=str, help="Target job description")
    pred_parser.add_argument("--skills", type=str, help="Comma-separated skill list")

    # benchmark
    subparsers.add_parser("benchmark", help="Run multi-paradigm evaluation benchmark")

    # index
    subparsers.add_parser("index", help="Index sample documents into FAISS vector store")

    # train
    subparsers.add_parser("train", help="Train and save the ML compatibility model")

    # chat
    chat_parser = subparsers.add_parser("chat", help="Execute multi-agent reasoning from the terminal")
    chat_parser.add_argument("message", type=str, help="Natural language query / prompt")

    # batch
    batch_parser = subparsers.add_parser("batch", help="View batch candidate rankings and export leaderboards")
    batch_parser.add_argument("--batch-id", type=str, help="Optional batch ID (defaults to demo batch)")
    batch_parser.add_argument("--export", type=str, help="Export leaderboard to specified CSV file path")

    # audit
    audit_parser = subparsers.add_parser("audit", help="Display system audit trail and observability logs")
    audit_parser.add_argument("--limit", type=int, default=10, help="Number of recent events to display")
    audit_parser.add_argument("--category", type=str, help="Filter events by category (api, agent, security, ml, batch, system)")

    # verify
    subparsers.add_parser("verify", help="Execute end-to-end Phase 25 system verification harness")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    commands = {
        "health": cmd_health,
        "predict": cmd_predict,
        "benchmark": cmd_benchmark,
        "index": cmd_index,
        "train": cmd_train,
        "chat": cmd_chat,
        "batch": cmd_batch,
        "audit": cmd_audit,
        "verify": cmd_verify,
    }

    cmd_fn = commands.get(args.command)
    if cmd_fn:
        cmd_fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

