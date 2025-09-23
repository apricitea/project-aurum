# Multi-stage Dockerfile for Indonesian Quantitative Trading Alert System

# Base stage with Python and system dependencies
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Development stage
FROM base as development

# Install development dependencies
RUN apt-get update && apt-get install -y \
    git \
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt requirements-dev.txt ./

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements-dev.txt

# Copy source code
COPY . .

# Create necessary directories
RUN mkdir -p logs data models reports backups && \
    chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 8000

# Default command for development
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base as production

# Copy requirements
COPY requirements.txt ./

# Install production dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install gunicorn

# Copy source code
COPY src/ ./src/
COPY main_pipeline.py feature_engineering.py model_ensemble.py signal_generator.py ./
COPY models/ ./models/

# Create necessary directories
RUN mkdir -p logs data reports backups && \
    chown -R appuser:appuser /app

# Health check script
COPY health_check.py ./
RUN chown appuser:appuser health_check.py

USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python health_check.py || exit 1

# Production command
CMD ["gunicorn", "src.api.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120", "--keep-alive", "2"]

# Testing stage
FROM development as testing

# Copy test files
COPY tests/ ./tests/
COPY pytest.ini ./

# Install test dependencies
RUN pip install pytest pytest-asyncio pytest-cov

# Default command for testing
CMD ["pytest", "tests/", "-v", "--cov=src"]

# Build stage for static analysis
FROM development as lint

# Install linting tools
RUN pip install black isort flake8 mypy bandit safety

# Run static analysis
CMD ["sh", "-c", "black --check src/ && isort --check-only src/ && flake8 src/ && mypy src/ && bandit -r src/ && safety check"]