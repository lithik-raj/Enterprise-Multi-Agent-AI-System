"""
scripts/train_ml_model.py

CLI command to trigger training of the ML Resume-Job Compatibility Model.
Usage:
    python scripts/train_ml_model.py
"""

import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add workspace root to sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from app.ml.train import train_and_save_model

if __name__ == "__main__":
    print("[*] Training Resume-Job Compatibility Model on curated dataset...")
    pipeline, metrics = train_and_save_model()
    print("\n[+] Training Complete!")
    print(f"Dataset Size:           {metrics.samples_count} labeled pairs")
    print(f"Model R^2 Score:        {metrics.r2_score}")
    print(f"Mean Absolute Error:    {metrics.mean_absolute_error}")
    print(f"Classification Acc:     {metrics.classification_accuracy * 100:.1f}%")
    print(f"F1 Score:               {metrics.f1_score}")
    print("\nFeature Importances:")
    for feat, imp in metrics.feature_importances.items():
        print(f"  - {feat:28s}: {imp:.4f}")
    print(f"\nArtifact saved to: models/compatibility_model.joblib")
    print(f"Metadata saved to: models/model_metadata.json")
