FROM python:3.11-slim

LABEL maintainer="Enterprise Multi-Agent AI Intelligence Platform"
LABEL description="Production-grade multi-agent AI platform with LangGraph, RAG, NLP, and HITL"

WORKDIR /app

# Ensure standard unbuffered logging and prevent bytecode caching in container
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0


# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy language model
RUN python -m spacy download en_core_web_sm

# Copy application code
COPY . .

# Create required runtime directories
RUN mkdir -p data/vector_store uploads

# Expose the API port
EXPOSE 8000

# Health check using the platform's /api/health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the production server
CMD ["python", "run.py"]
