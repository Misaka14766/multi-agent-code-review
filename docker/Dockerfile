FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for tree-sitter and semgrep
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY config/ ./config/
COPY src/ ./src/
COPY prompts/ ./prompts/
COPY static/ ./static/
COPY knowledge_data/ ./knowledge_data/
COPY pyproject.toml .

# Expose API port
EXPOSE 8000

# Run the FastAPI server
CMD ["python", "-m", "uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
