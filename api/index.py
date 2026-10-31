"""
Vercel Serverless Function Entrypoint for Enterprise Multi-Agent AI Platform.
Exposes the FastAPI application as `app` for Vercel's Python runtime.
"""

from __future__ import annotations

import os
import sys

# Ensure repository root is on sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Set serverless environment defaults
os.environ.setdefault("ENVIRONMENT", "production")
os.environ.setdefault("NO_BROWSER", "1")
os.environ.setdefault("VERCEL", "1")
os.environ.setdefault("DISABLE_SPACY", "1")
os.environ.setdefault("DISABLE_TORCH", "1")

from app.main import app  # noqa: E402, F401
