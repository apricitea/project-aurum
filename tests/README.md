# Telegram Bot Tests - Quick Reference Guide

## Overview

Comprehensive unit test suite for the Indonesian Quantitative Trading System Telegram bot.

**Current Status:** 32/43 tests passing (74%)

## Quick Start

```bash
# Install dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock

# Run all tests
pytest tests/test_telegram_bot.py -v

# Run with coverage report
pytest tests/test_telegram_bot.py --cov=src.api --cov-report=html

# Open coverage report
# Windows: start htmlcov/index.html
# Mac/Linux: open htmlcov/index.html
```

## Test Organization

### Test Classes

1. **TestTelegramAuthentication** (8 tests)
   - Token generation and verification
   - Session management
   - Permission checks
   - Rate limiting

2. **TestCommandHandlers** (7 tests)
   - /start, /help, /ping commands
   - /signals, /portfolio, /risk commands
   - Authentication requirements

3. **TestTransactionHandlers** (7 tests)
   - /buy, /sell, /confirm, /cancel commands
   - Input validation
   - Two-step confirmation flow

4. **TestPreferencesHandlers** (5 tests)
   - /subscribe command (alert preferences)
   - /watchlist command (stock watchlist)
   - Signal filtering

5. **TestRateLimiting** (3 tests)
   - Request limits per command type
   - Rate limit enforcement
   - Limit configuration

6. **TestErrorHandling** (3 tests)
   - Database error handling
   - Internal error masking
   - Error logging

7. **TestTransactionManager** (4 tests)
   - Pending transaction creation
   - Transaction confirmation
   - Buy/sell execution
   - Confirmation code generation

8. **TestPreferenceManager** (3 tests)
   - Preference defaults
   - Watchlist management
   - Duplicate prevention

9. **TestBotIntegration** (2 tests)
   - Bot initialization
   - Health checks

## Running Specific Tests

```bash
# Run single test class
pytest tests/test_telegram_bot.py::TestRateLimiting -v

# Run single test
pytest tests/test_telegram_bot.py::TestTransactionHandlers::test_buy_validates_input_format -v

# Run all transaction tests
pytest tests/test_telegram_bot.py -k "transaction" -v

# Run all authentication tests
pytest tests/test_telegram_bot.py -k "auth" -v

# Stop on first failure
pytest tests/test_telegram_bot.py -x

# Show test collection only (don't run)
pytest tests/test_telegram_bot.py --collect-only
```

## Test Fixtures (in conftest.py)

### Mock Objects
- `mock_update` - Telegram Update object
- `mock_context` - Telegram Context object
- `mock_callback_query` - Inline button callbacks

### Mock Services
- `mock_db_manager` - Database operations
- `mock_redis` - Redis cache
- `mock_signal_service` - Trading signals
- `mock_alert_engine` - Alert notifications
- `mock_auth_manager` - Authentication
- `mock_transaction_manager` - Transactions
- `mock_preference_manager` - User preferences
- `mock_rate_limiter` - Rate limiting

### Mock Data
- `sample_signals` - Sample trading signals
- `sample_portfolio` - Sample portfolio data
- `authenticated_context` - Context with authenticated user

## Common Test Patterns

### Testing Async Functions

```python
@pytest.mark.asyncio
async def test_example(mock_update, mock_context):
    """Test async command handler"""
    # Arrange
    mock_context.args = ['BBCA']

    # Act
    await my_handler(mock_update, mock_context)

    # Assert
    mock_update.message.reply_text.assert_called_once()
```

### Testing Authentication Required

```python
@pytest.mark.asyncio
async def test_requires_auth(mock_update, mock_context, mock_auth_manager):
    """Test command requires authentication"""
    # Mock unauthenticated user
    mock_auth_manager.get_user_by_chat_id.return_value = None

    # Should reject with auth message
    # ...
```

### Testing Input Validation

```python
@pytest.mark.asyncio
async def test_validates_input(mock_update, authenticated_context):
    """Test command validates input"""
    # Arrange - invalid input
    authenticated_context.args = ['invalid']

    # Act
    await cmd_buy(mock_update, authenticated_context)

    # Assert error message
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "Invalid" in call_args or "format" in call_args.lower()
```

### Testing Error Handling

```python
@pytest.mark.asyncio
async def test_handles_errors(mock_update, authenticated_context, mock_signal_service):
    """Test graceful error handling"""
    # Arrange - mock service error
    mock_signal_service.get_daily_signals.side_effect = Exception("DB Error")

    # Act
    await handler(mock_update, authenticated_context)

    # Assert - generic error message (no internal details exposed)
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "error" in call_args.lower()
    assert "DB Error" not in call_args  # Don't expose internal errors
```

## Debugging Tests

### View Full Traceback

```bash
pytest tests/test_telegram_bot.py -v --tb=long
```

### Show Print Statements

```bash
pytest tests/test_telegram_bot.py -v -s
```

### Show Captured Logs

```bash
pytest tests/test_telegram_bot.py -v --log-cli-level=DEBUG
```

### Run with PDB on Failure

```bash
pytest tests/test_telegram_bot.py --pdb
```

## Known Issues & Fixes Needed

### 1. Database Context Manager Mocking
**Issue:** `'coroutine' object does not support the asynchronous context manager protocol`

**Fix:**
```python
# In conftest.py, update mock_db_manager
conn_mock = AsyncMock()
db.get_connection.return_value = conn_mock
db.get_connection.return_value.__aenter__ = AsyncMock(return_value=conn_mock)
db.get_connection.return_value.__aexit__ = AsyncMock(return_value=None)
```

### 2. Method Signature Mismatch
**Issue:** `cmd_signals() takes 2 positional arguments but 3 were given`

**Fix:**
```python
# Methods are bound to handlers instance, they expect (self, update, context)
# Tests should call like this:
await handlers.cmd_signals(mock_update, authenticated_context)
# NOT: await TelegramCommandHandlers.cmd_signals(handlers, mock_update, context)
```

### 3. Random Confirmation Code
**Issue:** Assertion fails because code is randomly generated

**Fix:**
```python
# Mock the private method
with patch.object(manager, '_generate_confirmation_code', return_value='ABC123'):
    result = await manager.create_pending_transaction(...)
    assert result['confirmation_code'] == 'ABC123'
```

## Coverage Goals

- **Current:** 9% overall, 12-17% for Telegram modules
- **Target:** 85% for Telegram modules
- **Critical paths:** 100% (auth, transactions)

## CI/CD Integration

```yaml
# Example GitHub Actions workflow
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: pytest tests/test_telegram_bot.py --cov=src.api --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## Adding New Tests

### 1. Create Test Class

```python
class TestNewFeature:
    """Test suite for new feature"""

    @pytest.mark.asyncio
    async def test_feature_works(self, mock_update, mock_context):
        """Test that feature works correctly"""
        # Arrange
        ...

        # Act
        ...

        # Assert
        ...
```

### 2. Use Existing Fixtures

Check `conftest.py` for available fixtures before creating new ones.

### 3. Follow Naming Convention

- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`
- Descriptive names: `test_<what>_<when>_<expected>`

### 4. Add Docstrings

```python
async def test_validates_stock_code(self):
    """Test that invalid stock codes are rejected with clear error message"""
```

## Best Practices

✅ **DO:**
- Use descriptive test names
- Test one thing per test
- Use fixtures for setup
- Mock external dependencies
- Test both success and failure paths
- Assert on observable behavior, not implementation
- Write tests before fixing bugs

❌ **DON'T:**
- Test implementation details
- Have tests depend on each other
- Use real databases/APIs in unit tests
- Hardcode test data inline
- Skip writing tests for "simple" code
- Leave commented-out test code

## Resources

- **Pytest Documentation:** https://docs.pytest.org/
- **Pytest-Asyncio:** https://pytest-asyncio.readthedocs.io/
- **Python Testing Best Practices:** https://docs.python-guide.org/writing/tests/
- **Mock Documentation:** https://docs.python.org/3/library/unittest.mock.html

## Support

For questions or issues with tests:
1. Check TEST_RESULTS.md for detailed test information
2. Review conftest.py for available fixtures
3. Check test_telegram_bot.py for usage examples
4. Run tests with `-v` flag for verbose output
