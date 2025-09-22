# Contributing to Project Aurum

## Table of Contents

1. [Welcome Contributors](#welcome-contributors)
2. [Code of Conduct](#code-of-conduct)
3. [Getting Started](#getting-started)
4. [Development Workflow](#development-workflow)
5. [Contribution Guidelines](#contribution-guidelines)
6. [Code Standards](#code-standards)
7. [Testing Requirements](#testing-requirements)
8. [Documentation Guidelines](#documentation-guidelines)
9. [Review Process](#review-process)
10. [Community & Communication](#community--communication)

## Welcome Contributors

Thank you for your interest in contributing to Project Aurum! We're building the next generation of quantitative trading systems for Indonesian and Southeast Asian markets, and we welcome contributions from developers, traders, researchers, and domain experts.

### Types of Contributions We Welcome

- 🐛 **Bug Reports & Fixes**: Help us improve system reliability
- ✨ **New Features**: Enhance platform capabilities
- 📚 **Documentation**: Improve guides, tutorials, and API docs
- 🔬 **Research**: Share trading strategies and market insights
- 🧪 **Testing**: Help us validate system performance
- 🌍 **Localization**: Translate content for regional markets
- 💡 **Ideas & Discussions**: Share feedback and suggestions

### Skill Areas We Need

- **Backend Development**: Python, FastAPI, PostgreSQL, Redis
- **Frontend Development**: React, TypeScript, Tailwind CSS
- **Machine Learning**: scikit-learn, XGBoost, feature engineering
- **DevOps**: Docker, Kubernetes, monitoring, CI/CD
- **Financial Markets**: Indonesian markets, quantitative trading
- **Data Science**: Market data analysis, backtesting, statistics
- **Security**: Authentication, authorization, penetration testing
- **Mobile Development**: React Native, iOS, Android

## Code of Conduct

### Our Pledge

We are committed to fostering an open, welcoming, and inclusive community. We pledge to make participation in Project Aurum a harassment-free experience for everyone, regardless of:

- Age, body size, disability, ethnicity, gender identity and expression
- Level of experience, education, socio-economic status
- Nationality, personal appearance, race, religion
- Sexual identity and orientation, or technology choices

### Our Standards

**Positive behaviors include:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Unacceptable behaviors include:**
- Harassment, trolling, or personal attacks
- Publishing private information without permission
- Inappropriate sexual attention or advances
- Spam, advertisements, or off-topic content
- Any conduct inappropriate in a professional setting

### Enforcement

Community leaders will fairly and consistently enforce this code of conduct. Anyone who violates these standards may be temporarily or permanently banned from the project.

**To report violations**: Email conduct@projectaurum.dev or contact project maintainers directly.

## Getting Started

### Prerequisites

Before contributing, ensure you have:

1. **Git** installed and configured
2. **Python 3.9+** for backend development
3. **Node.js 18+** for frontend development
4. **Docker & Docker Compose** for local development
5. **GitHub account** with SSH keys configured

### Fork and Clone

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone git@github.com:YOUR_USERNAME/project-aurum.git
   cd project-aurum
   ```

3. **Add upstream remote**:
   ```bash
   git remote add upstream git@github.com:project-aurum/project-aurum.git
   ```

4. **Verify remotes**:
   ```bash
   git remote -v
   # origin    git@github.com:YOUR_USERNAME/project-aurum.git (fetch)
   # origin    git@github.com:YOUR_USERNAME/project-aurum.git (push)
   # upstream  git@github.com:project-aurum/project-aurum.git (fetch)
   # upstream  git@github.com:project-aurum/project-aurum.git (push)
   ```

### Development Environment Setup

1. **Set up development environment**:
   ```bash
   # Copy environment configuration
   cp .env.example .env

   # Edit configuration for local development
   nano .env

   # Install dependencies
   make setup
   ```

2. **Start development services**:
   ```bash
   # Start background services (PostgreSQL, Redis)
   docker-compose up postgres redis -d

   # Start API server
   make start-api

   # In another terminal, start frontend
   make start-frontend
   ```

3. **Verify setup**:
   ```bash
   # Test API
   curl http://localhost:8000/health

   # Test frontend (should open in browser)
   # http://localhost:3000
   ```

### First Contribution

Start with a small contribution to familiarize yourself with the codebase:

1. **Good first issues**: Look for issues labeled `good-first-issue`
2. **Documentation improvements**: Fix typos, improve clarity
3. **Test coverage**: Add tests for existing functionality
4. **Bug fixes**: Start with simple, well-defined bugs

## Development Workflow

### Branch Strategy

We use **GitHub Flow** with the following conventions:

#### Branch Naming
- `feature/description` - New features
- `bugfix/issue-description` - Bug fixes
- `docs/topic` - Documentation updates
- `refactor/component` - Code refactoring
- `test/coverage-area` - Test improvements

#### Example Workflow

1. **Create feature branch**:
   ```bash
   git checkout main
   git pull upstream main
   git checkout -b feature/portfolio-rebalancing
   ```

2. **Make changes** and commit regularly:
   ```bash
   git add .
   git commit -m "feat(portfolio): add automatic rebalancing algorithm

   - Implement Kelly criterion position sizing
   - Add risk budget constraints
   - Include transaction cost optimization

   Closes #123"
   ```

3. **Keep branch updated**:
   ```bash
   git pull upstream main
   git rebase main  # Or merge if preferred
   ```

4. **Push and create PR**:
   ```bash
   git push origin feature/portfolio-rebalancing
   # Create Pull Request on GitHub
   ```

### Commit Message Convention

We follow **Conventional Commits** for clear, structured commit messages:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

#### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

#### Examples

```bash
# Simple feature
git commit -m "feat(api): add portfolio summary endpoint"

# Bug fix with details
git commit -m "fix(signals): correct confidence calculation

The confidence score was being calculated incorrectly when
sentiment data was missing. This fix adds proper fallback
handling and validation.

Fixes #456"

# Breaking change
git commit -m "feat(auth)!: implement JWT token refresh

BREAKING CHANGE: Authentication tokens now expire after 1 hour
and require refresh. Update client applications to handle token
refresh flow."
```

## Contribution Guidelines

### Before You Start

1. **Check existing issues**: Avoid duplicate work
2. **Discuss large changes**: Create an issue first for major features
3. **Read documentation**: Understand the codebase and architecture
4. **Follow coding standards**: Maintain consistency with existing code

### Types of Contributions

#### 🐛 Bug Reports

**Before reporting**:
- Search existing issues for duplicates
- Try to reproduce with minimal steps
- Test on latest version

**Include in report**:
- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Relevant logs or error messages

**Bug report template**:
```markdown
## Bug Description
Brief description of the issue

## Steps to Reproduce
1. Go to...
2. Click on...
3. See error

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: Ubuntu 20.04
- Python: 3.9.7
- Browser: Chrome 96.0
- Version: v1.0.0

## Additional Context
Any other relevant information
```

#### ✨ Feature Requests

**Before requesting**:
- Check if feature already exists
- Review roadmap for planned features
- Consider if it fits project scope

**Include in request**:
- Clear use case and motivation
- Detailed description of proposed feature
- Alternative solutions considered
- Willingness to implement

**Feature request template**:
```markdown
## Feature Description
Clear description of the proposed feature

## Problem Statement
What problem does this solve?

## Proposed Solution
Detailed description of how it should work

## Alternatives Considered
Other approaches you've thought about

## Additional Context
Any other relevant information

## Implementation
Are you willing to implement this feature?
- [ ] Yes, I can implement this
- [ ] I need help implementing this
- [ ] I'm just suggesting the idea
```

#### 📚 Documentation Contributions

Documentation is crucial for project success. We welcome:

- **API documentation improvements**
- **Tutorial and guide enhancements**
- **Code example additions**
- **Translation to Indonesian**
- **Video tutorial creation**

### Code Contributions

#### Feature Development Process

1. **Create issue** (for significant features)
2. **Get approval** from maintainers
3. **Create branch** from main
4. **Implement feature** with tests
5. **Update documentation**
6. **Submit pull request**
7. **Address review feedback**
8. **Merge when approved**

#### Pull Request Guidelines

**Title format**:
```
feat(scope): brief description of change
```

**Description should include**:
- What changes were made and why
- How to test the changes
- Link to related issues
- Screenshots for UI changes
- Breaking changes (if any)

**Pull request template**:
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Added new tests for this change

## Related Issues
Closes #123
Related to #456

## Screenshots (if applicable)
[Include screenshots for UI changes]

## Checklist
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
```

## Code Standards

### Python Code Standards

#### Style Guidelines
- **PEP 8** compliance enforced by `black` and `flake8`
- **Type hints** required for all public functions
- **Docstrings** required for all modules, classes, and public functions
- **Line length**: 88 characters (Black default)

#### Code Organization
```python
"""
Module docstring describing purpose and usage.

Example:
    from src.api.signals import SignalGenerator

    generator = SignalGenerator()
    signals = generator.generate_daily_signals()
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

import pandas as pd
import numpy as np
from pydantic import BaseModel

# Constants
DEFAULT_CONFIDENCE_THRESHOLD = 0.6
MAX_POSITION_SIZE = 0.05

# Configure logging
logger = logging.getLogger(__name__)


class SignalRequest(BaseModel):
    """Request model for signal generation."""

    symbols: Optional[List[str]] = None
    date: Optional[datetime] = None
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD


class SignalGenerator:
    """
    Generate trading signals using machine learning models.

    This class combines multiple ML models to generate buy/sell/hold
    signals for Indonesian stocks with appropriate risk management.

    Attributes:
        models: Dictionary of trained ML models
        last_update: Timestamp of last signal generation

    Example:
        >>> generator = SignalGenerator()
        >>> signals = generator.generate_signals(['BBCA', 'TLKM'])
        >>> print(f"Generated {len(signals)} signals")
    """

    def __init__(self, model_path: str) -> None:
        """
        Initialize signal generator.

        Args:
            model_path: Path to trained ML models

        Raises:
            FileNotFoundError: If model files don't exist
            ValueError: If models are invalid
        """
        self.models = self._load_models(model_path)
        self.last_update: Optional[datetime] = None

    def generate_signals(
        self,
        symbols: List[str],
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
    ) -> Dict[str, Dict[str, float]]:
        """
        Generate trading signals for given symbols.

        Args:
            symbols: List of stock symbols to analyze
            confidence_threshold: Minimum confidence for signal inclusion

        Returns:
            Dictionary mapping symbol to signal information:
            {
                'BBCA': {
                    'signal': 'BUY',
                    'strength': 0.85,
                    'confidence': 0.92
                }
            }

        Raises:
            ValueError: If symbols list is empty
            ModelError: If model prediction fails
        """
        if not symbols:
            raise ValueError("Symbols list cannot be empty")

        logger.info(f"Generating signals for {len(symbols)} symbols")

        signals = {}
        for symbol in symbols:
            try:
                signal_info = self._generate_single_signal(symbol)
                if signal_info['confidence'] >= confidence_threshold:
                    signals[symbol] = signal_info
            except Exception as e:
                logger.warning(f"Failed to generate signal for {symbol}: {e}")

        self.last_update = datetime.now()
        logger.info(f"Generated {len(signals)} signals")

        return signals
```

### TypeScript Code Standards

#### Style Guidelines
- **Prettier** formatting with default settings
- **ESLint** with strict TypeScript rules
- **Interface definitions** for all props and data structures
- **Functional components** with hooks preferred

#### Component Structure
```typescript
/**
 * Trading signal display component.
 *
 * Shows current trading signals with interactive filtering
 * and real-time updates via WebSocket connections.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';

import { useSignals } from '../hooks/useSignals';
import { SignalCard } from './SignalCard';
import { LoadingSpinner } from './ui/LoadingSpinner';
import { ErrorMessage } from './ui/ErrorMessage';

// Types
interface Signal {
  symbol: string;
  signal: 'BUY' | 'SELL' | 'HOLD';
  strength: number;
  confidence: number;
  reasoning: string[];
}

interface SignalDisplayProps {
  /** Maximum number of signals to display */
  maxSignals?: number;
  /** Filter by minimum confidence level */
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
  // State
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null);

  // Hooks
  const { signals, loading, error, refreshSignals } = useSignals();

  // Computed values
  const filteredSignals = useMemo(() => {
    if (!signals) return [];

    return signals
      .filter((signal) => signal.confidence >= minConfidence)
      .sort((a, b) => b.strength - a.strength)
      .slice(0, maxSignals);
  }, [signals, minConfidence, maxSignals]);

  // Event handlers
  const handleSignalClick = useCallback((signal: Signal) => {
    setSelectedSignal(signal);
    onSignalSelect?.(signal);
  }, [onSignalSelect]);

  const handleRefresh = useCallback(() => {
    refreshSignals();
  }, [refreshSignals]);

  // Effects
  useEffect(() => {
    // Auto-refresh every 5 minutes
    const interval = setInterval(refreshSignals, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [refreshSignals]);

  // Early returns
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
        onRetry={handleRefresh}
      />
    );
  }

  // Main render
  return (
    <div className={`signal-display ${className}`}>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">
          Trading Signals
        </h2>
        <button
          onClick={handleRefresh}
          className="btn btn-primary"
          type="button"
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
              onClick={handleSignalClick}
              isSelected={selectedSignal?.symbol === signal.symbol}
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

## Testing Requirements

### Test Coverage Requirements

- **Minimum coverage**: 80% for all new code
- **Critical paths**: 95% coverage for core trading logic
- **Integration tests**: Required for all API endpoints
- **End-to-end tests**: Required for critical user workflows

### Testing Strategy

#### Unit Tests
```python
# test_signal_generator.py
import pytest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np

from src.ml.signal_generator import SignalGenerator, SignalConfig
from src.ml.exceptions import ModelError


class TestSignalGenerator:
    """Test cases for SignalGenerator class."""

    @pytest.fixture
    def sample_config(self):
        """Create test configuration."""
        return SignalConfig(
            model_path="/tmp/test_model",
            confidence_threshold=0.6,
            max_positions=10
        )

    @pytest.fixture
    def mock_model(self):
        """Mock ML model for testing."""
        model = Mock()
        model.predict.return_value = np.array([0.8])
        return model

    @pytest.fixture
    def signal_generator(self, sample_config, mock_model):
        """Create signal generator with mocked dependencies."""
        with patch.object(SignalGenerator, '_load_models') as mock_load:
            mock_load.return_value = {'ensemble': mock_model}
            return SignalGenerator(sample_config)

    def test_generate_signals_success(self, signal_generator):
        """Test successful signal generation."""
        symbols = ['BBCA', 'TLKM']

        with patch.object(signal_generator, '_get_features') as mock_features:
            mock_features.return_value = np.array([[1, 2, 3]])

            signals = signal_generator.generate_signals(symbols)

            assert len(signals) == 2
            assert 'BBCA' in signals
            assert signals['BBCA']['confidence'] >= 0.6

    def test_generate_signals_empty_list(self, signal_generator):
        """Test error handling for empty symbol list."""
        with pytest.raises(ValueError, match="Symbols list cannot be empty"):
            signal_generator.generate_signals([])

    def test_generate_signals_model_error(self, signal_generator):
        """Test handling of model prediction errors."""
        symbols = ['BBCA']

        with patch.object(signal_generator, '_get_features') as mock_features:
            mock_features.side_effect = ModelError("Prediction failed")

            signals = signal_generator.generate_signals(symbols)

            # Should handle error gracefully and return empty dict
            assert len(signals) == 0


# Parameterized tests for different scenarios
@pytest.mark.parametrize("confidence,expected_count", [
    (0.5, 3),  # Lower threshold, more signals
    (0.7, 1),  # Higher threshold, fewer signals
    (0.9, 0),  # Very high threshold, no signals
])
def test_confidence_filtering(signal_generator, confidence, expected_count):
    """Test signal filtering by confidence level."""
    # Test implementation here
    pass
```

#### Integration Tests
```python
# test_api_integration.py
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.mark.asyncio
class TestSignalAPI:
    """Integration tests for signal API endpoints."""

    async def test_get_daily_signals_success(self, client: AsyncClient, auth_headers):
        """Test successful retrieval of daily signals."""
        response = await client.get("/signals/daily", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "signals" in data
        assert "generated_at" in data
        assert isinstance(data["signals"], list)

        # Validate signal structure
        if data["signals"]:
            signal = data["signals"][0]
            assert "symbol" in signal
            assert "signal" in signal
            assert "strength" in signal
            assert "confidence" in signal

    async def test_get_daily_signals_unauthorized(self, client: AsyncClient):
        """Test unauthorized access."""
        response = await client.get("/signals/daily")
        assert response.status_code == 401

    async def test_generate_signals_admin_only(self, client: AsyncClient, user_auth_headers):
        """Test that signal generation requires admin privileges."""
        response = await client.post("/signals/generate", headers=user_auth_headers)
        assert response.status_code == 403


@pytest.fixture
async def client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers."""
    token = create_access_token(data={"sub": test_user.username})
    return {"Authorization": f"Bearer {token}"}
```

#### Frontend Tests
```typescript
// SignalDisplay.test.tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { SignalDisplay } from '../SignalDisplay';
import { useSignals } from '../../hooks/useSignals';

// Mock the custom hook
jest.mock('../../hooks/useSignals');

const mockUseSignals = useSignals as jest.MockedFunction<typeof useSignals>;

const mockSignals = [
  {
    symbol: 'BBCA',
    signal: 'BUY' as const,
    strength: 0.85,
    confidence: 0.92,
    reasoning: ['Strong momentum', 'Good fundamentals']
  },
  {
    symbol: 'TLKM',
    signal: 'SELL' as const,
    strength: 0.65,
    confidence: 0.78,
    reasoning: ['Overvalued', 'Declining momentum']
  }
];

const renderWithQueryClient = (component: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  );
};

describe('SignalDisplay', () => {
  beforeEach(() => {
    mockUseSignals.mockReturnValue({
      signals: mockSignals,
      loading: false,
      error: null,
      refreshSignals: jest.fn()
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders signals correctly', () => {
    renderWithQueryClient(<SignalDisplay />);

    expect(screen.getByText('Trading Signals')).toBeInTheDocument();
    expect(screen.getByText('BBCA')).toBeInTheDocument();
    expect(screen.getByText('TLKM')).toBeInTheDocument();
  });

  it('filters signals by confidence', () => {
    renderWithQueryClient(<SignalDisplay minConfidence={0.8} />);

    expect(screen.getByText('BBCA')).toBeInTheDocument();
    expect(screen.queryByText('TLKM')).not.toBeInTheDocument();
  });

  it('calls onSignalSelect when signal is clicked', async () => {
    const user = userEvent.setup();
    const onSignalSelect = jest.fn();

    renderWithQueryClient(
      <SignalDisplay onSignalSelect={onSignalSelect} />
    );

    await user.click(screen.getByText('BBCA'));

    expect(onSignalSelect).toHaveBeenCalledWith(mockSignals[0]);
  });

  it('shows loading spinner when loading', () => {
    mockUseSignals.mockReturnValue({
      signals: [],
      loading: true,
      error: null,
      refreshSignals: jest.fn()
    });

    renderWithQueryClient(<SignalDisplay />);

    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('shows error message when error occurs', () => {
    const refreshSignals = jest.fn();
    mockUseSignals.mockReturnValue({
      signals: [],
      loading: false,
      error: 'Failed to fetch signals',
      refreshSignals
    });

    renderWithQueryClient(<SignalDisplay />);

    expect(screen.getByText('Failed to load signals')).toBeInTheDocument();

    const retryButton = screen.getByText('Retry');
    fireEvent.click(retryButton);

    expect(refreshSignals).toHaveBeenCalled();
  });
});
```

### Test Data and Fixtures

Create realistic test data that matches production scenarios:

```python
# tests/fixtures/market_data.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_sample_ohlcv_data(
    symbol: str = "BBCA",
    days: int = 252,
    start_price: float = 9500
) -> pd.DataFrame:
    """Create realistic OHLCV data for testing."""
    dates = pd.date_range(
        start=datetime.now() - timedelta(days=days),
        periods=days,
        freq='D'
    )

    # Generate realistic price movements
    returns = np.random.normal(0.0008, 0.02, days)  # ~20% annual volatility
    prices = [start_price]

    for ret in returns[1:]:
        new_price = prices[-1] * (1 + ret)
        prices.append(max(new_price, 50))  # Minimum price floor

    # Generate OHLC from close prices
    data = []
    for i, close in enumerate(prices):
        # Create realistic intraday range
        daily_range = abs(np.random.normal(0, 0.015)) * close
        high = close + np.random.uniform(0, daily_range)
        low = close - np.random.uniform(0, daily_range)
        open_price = low + np.random.uniform(0, high - low)

        volume = int(np.random.lognormal(15, 0.5))  # Realistic volume distribution

        data.append({
            'date': dates[i],
            'symbol': symbol,
            'open': round(open_price, 0),
            'high': round(high, 0),
            'low': round(low, 0),
            'close': round(close, 0),
            'volume': volume
        })

    return pd.DataFrame(data)
```

## Documentation Guidelines

### API Documentation

Use **OpenAPI/Swagger** specifications with detailed examples:

```python
from fastapi import FastAPI, Query
from pydantic import BaseModel, Field
from typing import List, Optional

class SignalResponse(BaseModel):
    """Trading signal response model."""

    symbol: str = Field(..., description="Stock symbol (e.g., BBCA)")
    signal: str = Field(..., description="Signal type: BUY, SELL, or HOLD")
    strength: float = Field(..., ge=-1, le=1, description="Signal strength from -1 to 1")
    confidence: float = Field(..., ge=0, le=1, description="Prediction confidence from 0 to 1")

    class Config:
        schema_extra = {
            "example": {
                "symbol": "BBCA",
                "signal": "BUY",
                "strength": 0.85,
                "confidence": 0.92
            }
        }

@app.get(
    "/signals/daily",
    response_model=List[SignalResponse],
    summary="Get daily trading signals",
    description="""
    Retrieve trading signals for the current or specified date.

    Signals are generated using ensemble machine learning models that analyze:
    - Technical indicators (momentum, trend, volatility)
    - Fundamental metrics (valuation, quality, growth)
    - Market sentiment (news, social media, analyst opinions)

    Only signals with confidence above the threshold are returned.
    """,
    responses={
        200: {
            "description": "Successful response with trading signals",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "symbol": "BBCA",
                            "signal": "BUY",
                            "strength": 0.85,
                            "confidence": 0.92
                        },
                        {
                            "symbol": "TLKM",
                            "signal": "SELL",
                            "strength": -0.62,
                            "confidence": 0.78
                        }
                    ]
                }
            }
        },
        401: {"description": "Authentication required"},
        429: {"description": "Rate limit exceeded"}
    }
)
async def get_daily_signals(
    date: Optional[str] = Query(
        None,
        description="Target date in YYYY-MM-DD format. Defaults to today.",
        example="2024-01-15"
    ),
    min_confidence: float = Query(
        0.6,
        ge=0,
        le=1,
        description="Minimum confidence threshold for signals",
        example=0.7
    )
):
    """Get daily trading signals endpoint."""
    # Implementation here
    pass
```

### Code Documentation

#### Python Docstrings (Google Style)
```python
def calculate_portfolio_risk(
    positions: Dict[str, float],
    covariance_matrix: np.ndarray,
    time_horizon: int = 252
) -> Dict[str, float]:
    """
    Calculate portfolio risk metrics using modern portfolio theory.

    This function computes various risk measures for a given portfolio
    using the provided covariance matrix and position weights.

    Args:
        positions: Dictionary mapping stock symbols to portfolio weights.
            Weights should sum to 1.0. Example: {'BBCA': 0.3, 'TLKM': 0.7}
        covariance_matrix: Numpy array containing the covariance matrix
            of stock returns. Must be symmetric and positive semi-definite.
        time_horizon: Number of trading days for annualization. Defaults
            to 252 (typical trading days per year).

    Returns:
        Dictionary containing calculated risk metrics:
        {
            'portfolio_variance': 0.0234,
            'portfolio_volatility': 0.153,
            'diversification_ratio': 0.72,
            'value_at_risk_95': -0.0245,
            'expected_shortfall_95': -0.0334
        }

    Raises:
        ValueError: If position weights don't sum to 1.0 or if covariance
            matrix dimensions don't match number of positions.
        LinAlgError: If covariance matrix is not positive semi-definite.

    Example:
        >>> positions = {'BBCA': 0.6, 'TLKM': 0.4}
        >>> cov_matrix = np.array([[0.04, 0.01], [0.01, 0.09]])
        >>> risk_metrics = calculate_portfolio_risk(positions, cov_matrix)
        >>> print(f"Portfolio volatility: {risk_metrics['portfolio_volatility']:.2%}")
        Portfolio volatility: 15.30%

    Note:
        This function assumes returns are normally distributed. For more
        accurate risk measures with non-normal returns, consider using
        Monte Carlo simulation or historical simulation methods.

    References:
        Markowitz, H. (1952). Portfolio Selection. The Journal of Finance,
        7(1), 77-91.
    """
    # Validate inputs
    if abs(sum(positions.values()) - 1.0) > 1e-6:
        raise ValueError("Position weights must sum to 1.0")

    # Implementation here
    pass
```

### User Documentation

#### Tutorial Style
```markdown
# Getting Started with Signal Generation

## Overview

Project Aurum generates trading signals using machine learning models trained on Indonesian market data. This tutorial will guide you through accessing and understanding these signals.

## Prerequisites

Before you begin, ensure you have:
- Active Project Aurum account
- API access token (see [Authentication Guide](auth.md))
- Basic understanding of Indonesian stock markets

## Step 1: Fetch Daily Signals

The simplest way to get trading signals is through the daily signals endpoint:

```python
import requests

# Your API token
token = "your-api-token-here"
headers = {"Authorization": f"Bearer {token}"}

# Fetch today's signals
response = requests.get(
    "https://api.projectaurum.com/signals/daily",
    headers=headers
)

signals = response.json()
print(f"Found {len(signals)} signals for today")
```

## Step 2: Understanding Signal Structure

Each signal contains the following information:

```json
{
  "symbol": "BBCA",
  "signal": "BUY",
  "strength": 0.85,
  "confidence": 0.92,
  "recommended_allocation": 0.04,
  "reasoning": [
    "Strong momentum breakout above 20-day MA",
    "P/E ratio attractive at 12.5x",
    "Positive analyst sentiment increase"
  ],
  "risk_metrics": {
    "volatility": 0.18,
    "beta": 0.95,
    "liquidity_score": 0.88
  }
}
```

### Signal Fields Explained

- **symbol**: Indonesian stock code (e.g., BBCA for Bank Central Asia)
- **signal**: Recommendation type (BUY, SELL, HOLD)
- **strength**: Signal strength from -1 (strong sell) to +1 (strong buy)
- **confidence**: Model confidence from 0 to 1
- **recommended_allocation**: Suggested portfolio allocation (0 to 1)
- **reasoning**: Human-readable explanation of the signal
- **risk_metrics**: Associated risk measures

## Step 3: Filtering Signals

You can filter signals based on your risk tolerance:

```python
# Only high-confidence signals
high_confidence_signals = [
    signal for signal in signals
    if signal['confidence'] >= 0.8
]

# Only buy signals with strong conviction
strong_buys = [
    signal for signal in signals
    if signal['signal'] == 'BUY' and signal['strength'] >= 0.7
]

# Filter by risk (low volatility stocks)
low_risk_signals = [
    signal for signal in signals
    if signal['risk_metrics']['volatility'] <= 0.15
]
```

## Step 4: Portfolio Integration

Integrate signals into your portfolio management:

```python
def calculate_position_sizes(signals, portfolio_value, max_single_position=0.05):
    """Calculate position sizes based on signals and portfolio constraints."""
    position_sizes = {}

    for signal in signals:
        if signal['signal'] == 'BUY':
            # Use recommended allocation, capped at maximum
            allocation = min(signal['recommended_allocation'], max_single_position)
            position_value = portfolio_value * allocation

            position_sizes[signal['symbol']] = {
                'value': position_value,
                'allocation': allocation,
                'confidence': signal['confidence']
            }

    return position_sizes

# Example usage
portfolio_value = 1_000_000_000  # 1 billion IDR
positions = calculate_position_sizes(strong_buys, portfolio_value)

for symbol, position in positions.items():
    print(f"{symbol}: IDR {position['value']:,.0f} ({position['allocation']:.1%})")
```

## Next Steps

- Learn about [Risk Management](risk-management.md)
- Explore [Portfolio Optimization](portfolio-optimization.md)
- Set up [Automated Alerts](alerts.md)
- Read about [Performance Analytics](analytics.md)

## Getting Help

If you need assistance:
- Check our [FAQ](faq.md)
- Join our [Discord community](https://discord.gg/projectaurum)
- Contact support at support@projectaurum.com
```

## Review Process

### Pull Request Review

#### Reviewer Guidelines

**What to review:**
- Code quality and adherence to standards
- Test coverage and quality
- Documentation completeness
- Performance implications
- Security considerations
- API design consistency

**Review checklist:**
- [ ] Code follows style guidelines
- [ ] Tests are comprehensive and pass
- [ ] Documentation is updated
- [ ] No breaking changes (or properly documented)
- [ ] Performance impact is acceptable
- [ ] Security implications are considered

#### Author Guidelines

**Before requesting review:**
- [ ] Self-review completed
- [ ] All tests pass locally
- [ ] Documentation updated
- [ ] Commits are clean and well-messaged
- [ ] CI/CD checks pass

**Responding to feedback:**
- Address all feedback promptly
- Ask for clarification if needed
- Make requested changes or explain why not
- Re-request review after changes

### Review Timeline

- **Initial review**: Within 48 hours
- **Follow-up reviews**: Within 24 hours
- **Expedited reviews**: Critical fixes within 4 hours

### Approval Requirements

- **Simple changes**: 1 approving review
- **Significant features**: 2 approving reviews
- **Breaking changes**: 2 approving reviews + maintainer approval
- **Security changes**: Security team review required

## Community & Communication

### Communication Channels

#### GitHub
- **Issues**: Bug reports, feature requests
- **Discussions**: Design discussions, Q&A
- **Pull Requests**: Code review and collaboration

#### Discord Server
- **#general**: General discussion
- **#development**: Development questions and help
- **#trading**: Trading strategy discussions
- **#announcements**: Project updates

#### Social Media
- **Twitter**: [@ProjectAurum](https://twitter.com/projectaurum)
- **LinkedIn**: [Project Aurum](https://linkedin.com/company/projectaurum)
- **Blog**: [blog.projectaurum.com](https://blog.projectaurum.com)

### Community Guidelines

#### Be Respectful
- Treat all community members with respect
- Provide constructive feedback
- Help newcomers get started
- Celebrate others' contributions

#### Be Helpful
- Answer questions when you can
- Share knowledge and resources
- Provide detailed bug reports
- Suggest improvements

#### Be Professional
- Keep discussions relevant to the project
- Avoid spam or self-promotion
- Respect intellectual property
- Follow the code of conduct

### Recognition

We recognize contributors through:

#### Contributor Spotlight
- Monthly feature of outstanding contributors
- Shared on social media and blog
- Special Discord role and badge

#### Contribution Metrics
- GitHub contributor stats
- Pull request leaderboards
- Issue resolution recognition

#### Special Recognition
- Annual contributor awards
- Conference speaking opportunities
- Project governance participation

### Getting Involved

#### For Developers
1. **Start small**: Pick up a "good first issue"
2. **Join discussions**: Participate in design conversations
3. **Share knowledge**: Write tutorials or blog posts
4. **Mentor others**: Help new contributors get started

#### For Traders
1. **Share strategies**: Contribute trading insights
2. **Test features**: Provide feedback on new functionality
3. **Report bugs**: Help improve system reliability
4. **Create content**: Share tutorials and case studies

#### For Researchers
1. **Academic collaboration**: Partner on research projects
2. **Paper contributions**: Co-author research publications
3. **Data insights**: Share market analysis and findings
4. **Conference presentations**: Present at academic conferences

---

## Thank You! 🙏

Thank you for considering contributing to Project Aurum. Your contributions help make quantitative trading more accessible and sophisticated for Indonesian markets. Together, we're building the future of algorithmic trading in Southeast Asia.

**Questions?** Don't hesitate to reach out:
- Email: contributors@projectaurum.dev
- Discord: Join our #development channel
- GitHub: Open a discussion

Happy coding! 🚀