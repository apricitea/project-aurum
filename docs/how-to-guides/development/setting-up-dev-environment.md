# Project Aurum - Development Guide

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Project Structure](#project-structure)
3. [Development Workflow](#development-workflow)
4. [Code Standards](#code-standards)
5. [Testing Framework](#testing-framework)
6. [Database Development](#database-development)
7. [API Development](#api-development)
8. [Frontend Development](#frontend-development)
9. [ML Model Development](#ml-model-development)
10. [Performance Optimization](#performance-optimization)
11. [Debugging & Profiling](#debugging--profiling)
12. [Contributing Guidelines](#contributing-guidelines)

## Development Environment Setup

### Prerequisites

#### System Requirements
- **Operating System**: Linux (Ubuntu 20.04+ recommended), macOS 10.15+, or Windows 10+ with WSL2
- **Memory**: 16GB RAM minimum, 32GB recommended
- **Storage**: 50GB available disk space
- **CPU**: 4+ cores, 8+ cores recommended for ML training

#### Required Software
```bash
# Core development tools
Python 3.9+
Node.js 18+
Docker 24.0+
Docker Compose v2
Git 2.30+
Make

# Database tools
PostgreSQL 15+
Redis 7+

# Optional but recommended
VS Code or PyCharm
Postman or Insomnia (API testing)
pgAdmin (database management)
```

### Local Development Setup

#### 1. Clone Repository
```bash
git clone https://github.com/your-org/project-aurum.git
cd project-aurum
```

#### 2. Python Environment Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install Python dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install
```

#### 3. Node.js Environment Setup
```bash
cd frontend
npm install
cd ..
```

#### 4. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit development configuration
nano .env
```

**Development Environment Variables:**
```bash
# Development Mode
ENVIRONMENT=development
DEBUG=true

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=trading_system_dev
DB_USER=postgres
DB_PASSWORD=dev_password

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Security (use weak keys for development)
JWT_SECRET_KEY=dev-secret-key-not-for-production

# API Configuration
API_PORT=8000
API_WORKERS=1
CORS_ORIGINS=["http://localhost:3000"]

# External APIs (use test/sandbox keys)
ALPHA_VANTAGE_API_KEY=demo
IDX_API_KEY=test

# Development Features
ENABLE_DEBUG_TOOLBAR=true
ENABLE_PROFILING=true
LOG_LEVEL=DEBUG
```

#### 5. Database Setup
```bash
# Start PostgreSQL (Docker)
docker run --name postgres-dev \
  -e POSTGRES_DB=trading_system_dev \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=dev_password \
  -p 5432:5432 \
  -d postgres:15

# Start Redis (Docker)
docker run --name redis-dev \
  -p 6379:6379 \
  -d redis:7-alpine

# Initialize database schema
alembic upgrade head

# Load development data
python scripts/load_dev_data.py
```

#### 6. Verification
```bash
# Test backend
python -m pytest tests/unit/ -v

# Test API endpoints
curl http://localhost:8000/health

# Test frontend (in frontend directory)
cd frontend
npm test
npm run dev  # Should start on http://localhost:3000
```

### Development Tools Configuration

#### VS Code Setup
```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "python.testing.pytestArgs": ["tests"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "[typescript]": {
        "editor.defaultFormatter": "esbenp.prettier-vscode"
    },
    "[typescriptreact]": {
        "editor.defaultFormatter": "esbenp.prettier-vscode"
    }
}
```

```json
// .vscode/extensions.json
{
    "recommendations": [
        "ms-python.python",
        "ms-python.flake8",
        "ms-python.mypy-type-checker",
        "bradlc.vscode-tailwindcss",
        "esbenp.prettier-vscode",
        "ms-vscode.vscode-typescript-next",
        "ms-vscode-remote.remote-containers",
        "ms-azuretools.vscode-docker"
    ]
}
```

#### Git Configuration
```bash
# Set up Git hooks
cp scripts/git-hooks/* .git/hooks/
chmod +x .git/hooks/*

# Configure Git for the project
git config core.autocrlf false
git config pull.rebase true
git config push.default simple
```

## Project Structure

### Directory Layout
```
project-aurum/
├── src/                          # Source code
│   ├── api/                      # FastAPI backend
│   │   ├── __init__.py
│   │   ├── main.py              # Application entry point
│   │   ├── auth.py              # Authentication logic
│   │   ├── database.py          # Database connection
│   │   ├── schemas.py           # Pydantic models
│   │   ├── config.py            # Configuration
│   │   ├── alert_engine.py      # Alert system
│   │   ├── signal_service.py    # Signal generation
│   │   ├── risk_monitor.py      # Risk management
│   │   └── scheduler.py         # Background tasks
│   ├── data_pipeline/           # Data processing
│   │   ├── __init__.py
│   │   ├── idx_data_gateway.py  # IDX data connection
│   │   ├── feature_engine.py    # Feature engineering
│   │   ├── data_validator.py    # Data quality
│   │   └── storage_manager.py   # Data storage
│   ├── ml/                      # Machine learning
│   │   ├── __init__.py
│   │   ├── models/              # ML models
│   │   ├── training/            # Training scripts
│   │   ├── inference/           # Inference engine
│   │   └── evaluation/          # Model evaluation
│   └── utils/                   # Utility functions
│       ├── __init__.py
│       ├── logging.py
│       ├── metrics.py
│       └── helpers.py
├── frontend/                    # React frontend
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── pages/              # Page components
│   │   ├── hooks/              # Custom hooks
│   │   ├── store/              # State management
│   │   ├── utils/              # Utility functions
│   │   ├── types/              # TypeScript types
│   │   └── styles/             # CSS/Tailwind
│   ├── public/                 # Static assets
│   ├── package.json
│   └── tsconfig.json
├── tests/                      # Test suites
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   ├── load/                   # Load tests
│   ├── e2e/                    # End-to-end tests
│   └── fixtures/               # Test data
├── scripts/                    # Utility scripts
│   ├── setup/                  # Setup scripts
│   ├── deployment/             # Deployment scripts
│   ├── data/                   # Data management
│   └── maintenance/            # Maintenance scripts
├── sql/                        # Database files
│   ├── migrations/             # Alembic migrations
│   ├── init/                   # Initial schema
│   └── seeds/                  # Seed data
├── docs/                       # Documentation
├── docker/                     # Docker configurations
├── monitoring/                 # Monitoring configs
├── pyproject.toml              # Python dependencies (uv project file)
├── uv.lock                     # Locked dependency versions (generate with `uv lock`)
├── pyproject.toml             # Python project config
├── docker-compose.yml         # Development environment
└── Makefile                   # Development commands
```

### Module Organization

#### Backend Modules
```python
# src/api/main.py - Main application entry point
from fastapi import FastAPI
from src.api import auth, database, alert_engine
from src.api.routers import signals, portfolio, alerts

app = FastAPI(
    title="Indonesian Quantitative Trading System",
    version="1.0.0"
)

# Include routers
app.include_router(signals.router, prefix="/signals")
app.include_router(portfolio.router, prefix="/portfolio")
app.include_router(alerts.router, prefix="/alerts")
```

#### Data Pipeline Modules
```python
# src/data_pipeline/feature_engine.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any
import pandas as pd

class FeatureEngine(ABC):
    """Abstract base class for feature engineering"""

    @abstractmethod
    def generate_features(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generate features from raw data"""
        pass

class TechnicalFeatureEngine(FeatureEngine):
    """Technical indicator feature generation"""

    def generate_features(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generate technical indicators"""
        # Implementation here
        pass
```

#### ML Module Structure
```python
# src/ml/models/base.py
from abc import ABC, abstractmethod
import numpy as np
from typing import Dict, Any

class BaseModel(ABC):
    """Base class for all ML models"""

    @abstractmethod
    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train the model"""
        pass

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Generate predictions"""
        pass

    @abstractmethod
    def save(self, path: str) -> None:
        """Save model to disk"""
        pass

    @abstractmethod
    def load(self, path: str) -> None:
        """Load model from disk"""
        pass
```

## Development Workflow

### Git Workflow

#### Branch Strategy
```
main
├── develop                    # Integration branch
├── feature/signal-generation  # Feature branches
├── feature/portfolio-ui
├── bugfix/auth-issue         # Bug fix branches
├── hotfix/critical-fix       # Hot fixes
└── release/v1.0.0           # Release branches
```

#### Branch Naming Convention
- **Feature branches**: `feature/short-description`
- **Bug fixes**: `bugfix/issue-description`
- **Hot fixes**: `hotfix/critical-issue`
- **Releases**: `release/version-number`

#### Commit Message Format
```
type(scope): short description

Longer description if necessary

- List changes
- Use bullet points
- Be specific

Closes #123
```

**Commit Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

#### Development Process
```bash
# 1. Create feature branch
git checkout develop
git pull origin develop
git checkout -b feature/new-signal-algorithm

# 2. Make changes and commit
git add .
git commit -m "feat(signals): add momentum-based signal algorithm

- Implement RSI momentum calculation
- Add volume confirmation logic
- Include backtesting validation

Closes #45"

# 3. Push and create PR
git push origin feature/new-signal-algorithm
# Create Pull Request on GitHub/GitLab

# 4. After review and approval
git checkout develop
git pull origin develop
git branch -d feature/new-signal-algorithm
```

### Development Commands

#### Makefile Targets
```makefile
# Development environment
.PHONY: setup install-dev start-dev stop-dev clean

setup:
	@echo "Setting up development environment..."
	python -m venv venv
	uv sync
	cd frontend && npm install

install-dev:
	uv sync
	cd frontend && npm install

start-dev:
	docker-compose -f docker-compose.dev.yml up -d
	@echo "Starting backend..."
	./venv/bin/uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000 &
	@echo "Starting frontend..."
	cd frontend && npm run dev &

stop-dev:
	docker-compose -f docker-compose.dev.yml down
	pkill -f uvicorn
	pkill -f "npm run dev"

# Code quality
.PHONY: format lint type-check test test-cov

format:
	./venv/bin/black src/ tests/
	./venv/bin/isort src/ tests/
	cd frontend && npm run format

lint:
	./venv/bin/flake8 src/ tests/
	./venv/bin/pylint src/
	cd frontend && npm run lint

type-check:
	./venv/bin/mypy src/
	cd frontend && npm run type-check

test:
	./venv/bin/pytest tests/unit/ -v
	cd frontend && npm test

test-cov:
	./venv/bin/pytest tests/ --cov=src --cov-report=html
	open htmlcov/index.html

# Database operations
.PHONY: db-migrate db-upgrade db-downgrade db-reset

db-migrate:
	./venv/bin/alembic revision --autogenerate -m "$(MESSAGE)"

db-upgrade:
	./venv/bin/alembic upgrade head

db-downgrade:
	./venv/bin/alembic downgrade -1

db-reset:
	docker-compose exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS trading_system_dev;"
	docker-compose exec postgres psql -U postgres -c "CREATE DATABASE trading_system_dev;"
	./venv/bin/alembic upgrade head
	./venv/bin/python scripts/load_dev_data.py

# Build and deployment
.PHONY: build build-dev build-prod

build-dev:
	docker build -t project-aurum:dev --target development .

build-prod:
	docker build -t project-aurum:prod --target production .
	cd frontend && npm run build

# Documentation
.PHONY: docs docs-serve

docs:
	./venv/bin/sphinx-build -b html docs/ docs/_build/

docs-serve:
	cd docs/_build && python -m http.server 8080
```

### Pre-commit Hooks

#### Configuration (.pre-commit-config.yaml)
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict

  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.0.0
    hooks:
      - id: prettier
        files: \.(ts|tsx|js|jsx|json|css|md)$
```

## Code Standards

### Python Code Standards

#### Style Guidelines
- **PEP 8** compliance with Black formatting
- **Line length**: 88 characters (Black default)
- **Import organization**: isort with Black profile
- **Type hints**: Required for all public functions
- **Docstrings**: Google style for all modules, classes, and functions

#### Example Python Code
```python
"""
Signal generation module for Indonesian quantitative trading.

This module provides classes and functions for generating trading signals
based on machine learning models and technical analysis.
"""

from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
import logging

import pandas as pd
import numpy as np
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SignalConfig(BaseModel):
    """Configuration for signal generation."""

    model_path: str
    confidence_threshold: float = 0.6
    max_positions: int = 20
    position_size_limit: float = 0.05


class SignalGenerator:
    """
    Generate trading signals using ML models and technical analysis.

    This class combines multiple models to generate buy/sell/hold signals
    for Indonesian stocks with appropriate risk management.

    Attributes:
        config: Signal generation configuration
        model: Trained ML model for predictions
        last_update: Timestamp of last signal generation
    """

    def __init__(self, config: SignalConfig) -> None:
        """
        Initialize signal generator.

        Args:
            config: Signal generation configuration

        Raises:
            ValueError: If model path is invalid
            FileNotFoundError: If model file doesn't exist
        """
        self.config = config
        self.model = self._load_model(config.model_path)
        self.last_update: Optional[datetime] = None

    def generate_signals(
        self,
        market_data: pd.DataFrame,
        symbols: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, Union[str, float]]]:
        """
        Generate trading signals for given symbols.

        Args:
            market_data: Market data for signal generation
            symbols: List of symbols to generate signals for.
                    If None, generates for all available symbols.

        Returns:
            Dictionary mapping symbol to signal information:
            {
                'BBCA': {
                    'signal': 'BUY',
                    'strength': 0.85,
                    'confidence': 0.92,
                    'recommended_size': 0.04
                }
            }

        Raises:
            ValueError: If market_data is empty or invalid
            ModelError: If model prediction fails
        """
        if market_data.empty:
            raise ValueError("Market data cannot be empty")

        if symbols is None:
            symbols = self._get_tradeable_symbols(market_data)

        signals = {}
        for symbol in symbols:
            try:
                signal_info = self._generate_single_signal(symbol, market_data)
                if signal_info["confidence"] >= self.config.confidence_threshold:
                    signals[symbol] = signal_info
            except Exception as e:
                logger.warning(f"Failed to generate signal for {symbol}: {e}")

        self.last_update = datetime.now()
        logger.info(f"Generated {len(signals)} signals for {len(symbols)} symbols")

        return signals

    def _load_model(self, model_path: str) -> object:
        """Load ML model from file."""
        # Implementation details
        pass

    def _get_tradeable_symbols(self, market_data: pd.DataFrame) -> List[str]:
        """Get list of tradeable symbols from market data."""
        # Implementation details
        pass

    def _generate_single_signal(
        self, symbol: str, market_data: pd.DataFrame
    ) -> Dict[str, Union[str, float]]:
        """Generate signal for single symbol."""
        # Implementation details
        pass
```

### TypeScript/React Code Standards

#### Style Guidelines
- **Prettier** formatting with default settings
- **ESLint** with TypeScript and React rules
- **Functional components** with hooks
- **TypeScript strict mode** enabled
- **Props interface** for all components

#### Example React Component
```typescript
/**
 * Signal display component for trading dashboard.
 *
 * Shows current trading signals with color-coded recommendations
 * and confidence indicators.
 */

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useSignals } from '../hooks/useSignals';
import { SignalCard } from './SignalCard';
import { LoadingSpinner } from './ui/LoadingSpinner';
import { ErrorMessage } from './ui/ErrorMessage';

interface Signal {
  symbol: string;
  signal: 'BUY' | 'SELL' | 'HOLD';
  strength: number;
  confidence: number;
  recommendedSize: number;
  reasoning: string[];
}

interface SignalDisplayProps {
  /** Maximum number of signals to display */
  maxSignals?: number;
  /** Filter signals by minimum confidence */
  minConfidence?: number;
  /** Callback when signal is selected */
  onSignalSelect?: (signal: Signal) => void;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Display trading signals in a responsive grid layout.
 */
export const SignalDisplay: React.FC<SignalDisplayProps> = ({
  maxSignals = 20,
  minConfidence = 0.6,
  onSignalSelect,
  className = '',
}) => {
  const { signals, loading, error, refreshSignals } = useSignals();
  const [filteredSignals, setFilteredSignals] = useState<Signal[]>([]);

  useEffect(() => {
    if (signals) {
      const filtered = signals
        .filter((signal) => signal.confidence >= minConfidence)
        .sort((a, b) => b.strength - a.strength)
        .slice(0, maxSignals);
      setFilteredSignals(filtered);
    }
  }, [signals, minConfidence, maxSignals]);

  const handleSignalClick = (signal: Signal): void => {
    onSignalSelect?.(signal);
  };

  const getSignalColor = (signal: Signal['signal']): string => {
    switch (signal) {
      case 'BUY':
        return 'text-green-600 bg-green-50';
      case 'SELL':
        return 'text-red-600 bg-red-50';
      case 'HOLD':
        return 'text-yellow-600 bg-yellow-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <ErrorMessage
        message="Failed to load signals"
        onRetry={refreshSignals}
      />
    );
  }

  return (
    <div className={`signal-display ${className}`}>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">
          Trading Signals
        </h2>
        <button
          onClick={refreshSignals}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Refresh
        </button>
      </div>

      <motion.div
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        {filteredSignals.map((signal, index) => (
          <motion.div
            key={signal.symbol}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: index * 0.1 }}
          >
            <SignalCard
              signal={signal}
              onClick={() => handleSignalClick(signal)}
              className={`cursor-pointer transition-transform hover:scale-105 ${getSignalColor(
                signal.signal
              )}`}
            />
          </motion.div>
        ))}
      </motion.div>

      {filteredSignals.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500">
            No signals found matching the current criteria.
          </p>
        </div>
      )}
    </div>
  );
};
```

### Database Standards

#### Migration Guidelines
```python
"""Add signal confidence tracking

Revision ID: abc123def456
Revises: def456ghi789
Create Date: 2024-01-15 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'abc123def456'
down_revision = 'def456ghi789'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add confidence tracking to signals table."""
    # Add confidence column
    op.add_column(
        'signals',
        sa.Column(
            'confidence',
            sa.Float,
            nullable=False,
            server_default='0.5'
        )
    )

    # Add index for confidence filtering
    op.create_index(
        'idx_signals_confidence',
        'signals',
        ['confidence'],
        postgresql_where=sa.text('confidence >= 0.6')
    )

    # Update existing records with default confidence
    op.execute(
        "UPDATE signals SET confidence = 0.7 WHERE signal_strength > 0.5"
    )


def downgrade() -> None:
    """Remove confidence tracking."""
    op.drop_index('idx_signals_confidence')
    op.drop_column('signals', 'confidence')
```

## Testing Framework

### Test Structure

#### Unit Tests
```python
"""
Unit tests for signal generation functionality.
"""

import pytest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
from datetime import datetime

from src.ml.models.signal_generator import SignalGenerator, SignalConfig
from src.ml.models.exceptions import ModelError


class TestSignalGenerator:
    """Test cases for SignalGenerator class."""

    @pytest.fixture
    def signal_config(self) -> SignalConfig:
        """Create test signal configuration."""
        return SignalConfig(
            model_path="/tmp/test_model.pkl",
            confidence_threshold=0.6,
            max_positions=10,
            position_size_limit=0.05
        )

    @pytest.fixture
    def market_data(self) -> pd.DataFrame:
        """Create test market data."""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        data = {
            'date': dates,
            'symbol': ['BBCA'] * 100,
            'close': np.random.uniform(9000, 10000, 100),
            'volume': np.random.uniform(1000000, 5000000, 100)
        }
        return pd.DataFrame(data)

    @pytest.fixture
    def signal_generator(self, signal_config: SignalConfig) -> SignalGenerator:
        """Create test signal generator."""
        with patch.object(SignalGenerator, '_load_model'):
            return SignalGenerator(signal_config)

    def test_init_with_valid_config(self, signal_config: SignalConfig):
        """Test initialization with valid configuration."""
        with patch.object(SignalGenerator, '_load_model') as mock_load:
            mock_load.return_value = Mock()

            generator = SignalGenerator(signal_config)

            assert generator.config == signal_config
            assert generator.last_update is None
            mock_load.assert_called_once_with(signal_config.model_path)

    def test_generate_signals_with_valid_data(
        self,
        signal_generator: SignalGenerator,
        market_data: pd.DataFrame
    ):
        """Test signal generation with valid market data."""
        # Mock model prediction
        with patch.object(signal_generator, '_generate_single_signal') as mock_signal:
            mock_signal.return_value = {
                'signal': 'BUY',
                'strength': 0.8,
                'confidence': 0.9,
                'recommended_size': 0.04
            }

            signals = signal_generator.generate_signals(market_data, ['BBCA'])

            assert len(signals) == 1
            assert 'BBCA' in signals
            assert signals['BBCA']['signal'] == 'BUY'
            assert signals['BBCA']['confidence'] >= signal_generator.config.confidence_threshold
            assert signal_generator.last_update is not None

    def test_generate_signals_with_empty_data(self, signal_generator: SignalGenerator):
        """Test signal generation with empty market data."""
        empty_data = pd.DataFrame()

        with pytest.raises(ValueError, match="Market data cannot be empty"):
            signal_generator.generate_signals(empty_data)

    def test_generate_signals_filters_low_confidence(
        self,
        signal_generator: SignalGenerator,
        market_data: pd.DataFrame
    ):
        """Test that low confidence signals are filtered out."""
        with patch.object(signal_generator, '_generate_single_signal') as mock_signal:
            mock_signal.return_value = {
                'signal': 'BUY',
                'strength': 0.8,
                'confidence': 0.4,  # Below threshold
                'recommended_size': 0.04
            }

            signals = signal_generator.generate_signals(market_data, ['BBCA'])

            assert len(signals) == 0

    def test_generate_signals_handles_model_error(
        self,
        signal_generator: SignalGenerator,
        market_data: pd.DataFrame
    ):
        """Test handling of model errors during signal generation."""
        with patch.object(signal_generator, '_generate_single_signal') as mock_signal:
            mock_signal.side_effect = ModelError("Model prediction failed")

            # Should not raise exception, but log warning and continue
            signals = signal_generator.generate_signals(market_data, ['BBCA'])

            assert len(signals) == 0


@pytest.mark.asyncio
class TestSignalAPI:
    """Integration tests for signal API endpoints."""

    async def test_get_daily_signals_success(self, client, auth_headers):
        """Test successful retrieval of daily signals."""
        response = await client.get("/signals/daily", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
        assert "generated_at" in data
        assert isinstance(data["signals"], list)

    async def test_get_daily_signals_unauthorized(self, client):
        """Test unauthorized access to signals endpoint."""
        response = await client.get("/signals/daily")

        assert response.status_code == 401

    async def test_generate_signals_trigger(self, client, admin_auth_headers):
        """Test manual signal generation trigger."""
        response = await client.post("/signals/generate", headers=admin_auth_headers)

        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "started"
```

#### Integration Tests
```python
"""
Integration tests for the complete signal generation pipeline.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
import pandas as pd

from src.api.main import app
from src.data_pipeline.feature_engine import TechnicalFeatureEngine
from src.ml.models.ensemble_model import EnsembleModel
from tests.fixtures.market_data import create_test_market_data


@pytest.mark.integration
class TestSignalPipeline:
    """Test complete signal generation pipeline."""

    @pytest.fixture(scope="class")
    async def setup_pipeline(self):
        """Setup test pipeline with real components."""
        # Create test database
        await self.create_test_database()

        # Load test market data
        market_data = create_test_market_data()
        await self.load_market_data(market_data)

        # Initialize feature engine
        feature_engine = TechnicalFeatureEngine()

        # Load pre-trained model
        model = EnsembleModel()
        await model.load("tests/fixtures/test_model.pkl")

        yield {
            "feature_engine": feature_engine,
            "model": model,
            "market_data": market_data
        }

        # Cleanup
        await self.cleanup_test_database()

    async def test_end_to_end_signal_generation(self, setup_pipeline):
        """Test complete signal generation flow."""
        components = setup_pipeline

        # 1. Feature engineering
        features = components["feature_engine"].generate_features(
            components["market_data"]
        )
        assert len(features) > 0

        # 2. Model prediction
        predictions = components["model"].predict(features)
        assert len(predictions) > 0

        # 3. Signal generation
        # This would test the complete pipeline
        pass

    async def test_signal_generation_performance(self, setup_pipeline):
        """Test signal generation performance benchmarks."""
        start_time = datetime.now()

        # Run signal generation
        # ... implementation

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Should complete within 2 minutes for LQ45 stocks
        assert duration < 120
```

#### Load Tests
```python
"""
Load tests for API endpoints.
"""

from locust import HttpUser, task, between
import json
import random


class TradingSystemUser(HttpUser):
    """Simulate trading system user behavior."""

    wait_time = between(1, 3)

    def on_start(self):
        """Login user before starting tasks."""
        response = self.client.post("/auth/login", json={
            "username": "test_user",
            "password": "test_password"
        })

        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}

    @task(3)
    def get_daily_signals(self):
        """Fetch daily signals - most common operation."""
        self.client.get("/signals/daily", headers=self.headers)

    @task(2)
    def get_portfolio_summary(self):
        """Get portfolio summary."""
        self.client.get("/portfolio/summary", headers=self.headers)

    @task(1)
    def get_risk_overview(self):
        """Get risk overview."""
        self.client.get("/risk/overview", headers=self.headers)

    @task(1)
    def get_market_status(self):
        """Get market status - lightweight operation."""
        self.client.get("/market/status")


class AdminUser(HttpUser):
    """Simulate admin user with different usage patterns."""

    wait_time = between(5, 10)

    def on_start(self):
        """Login as admin."""
        response = self.client.post("/auth/login", json={
            "username": "admin",
            "password": "admin_password"
        })

        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(1)
    def trigger_signal_generation(self):
        """Trigger manual signal generation - admin only."""
        self.client.post("/signals/generate", headers=self.headers)

    @task(2)
    def get_system_health(self):
        """Check system health."""
        self.client.get("/admin/system/health", headers=self.headers)
```

### Test Configuration

#### pytest.ini
```ini
[tool:pytest]
minversion = 6.0
addopts =
    -ra
    -q
    --strict-markers
    --strict-config
    --cov=src
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
testpaths = tests
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    load: marks tests as load tests
    e2e: marks tests as end-to-end tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

#### conftest.py
```python
"""
Shared test configuration and fixtures.
"""

import pytest
import asyncio
from typing import AsyncGenerator
import pandas as pd
from httpx import AsyncClient
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.database import get_db
from src.api.auth import create_access_token
from tests.fixtures.database import TestDatabase


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db():
    """Create test database."""
    db = TestDatabase()
    await db.create()
    yield db
    await db.destroy()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sync_client() -> TestClient:
    """Create synchronous test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Create authentication headers for testing."""
    token = create_access_token(data={"sub": "test_user"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers():
    """Create admin authentication headers."""
    token = create_access_token(data={"sub": "admin_user", "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_market_data():
    """Create sample market data for testing."""
    return pd.DataFrame({
        'symbol': ['BBCA', 'TLKM', 'ASII'] * 100,
        'date': pd.date_range('2024-01-01', periods=300, freq='D'),
        'close': [9500, 4200, 7800] * 100,
        'volume': [1000000, 2000000, 1500000] * 100
    })
```

This comprehensive development guide provides everything needed for developers to effectively contribute to Project Aurum, from environment setup to testing frameworks and code standards.
