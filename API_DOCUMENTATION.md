# Project Aurum - API Documentation

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Rate Limiting](#rate-limiting)
4. [Error Handling](#error-handling)
5. [Authentication Endpoints](#authentication-endpoints)
6. [Signal Management](#signal-management)
7. [Portfolio Management](#portfolio-management)
8. [Alert Management](#alert-management)
9. [Risk Management](#risk-management)
10. [Market Data](#market-data)
11. [Analytics & Reporting](#analytics--reporting)
12. [WebSocket Endpoints](#websocket-endpoints)
13. [Administrative Endpoints](#administrative-endpoints)
14. [Data Models](#data-models)
15. [SDK Examples](#sdk-examples)

## Overview

The Project Aurum API provides comprehensive access to quantitative trading signals, portfolio management, risk monitoring, and real-time market data for the Indonesian Stock Exchange (IDX). The API follows RESTful principles with JSON request/response format and supports real-time updates via WebSocket connections.

### Base URL
- **Production**: `https://api.projectaurum.com`
- **Staging**: `https://staging-api.projectaurum.com`
- **Development**: `http://localhost:8000`

### API Version
Current version: **v1**

All endpoints are prefixed with the base URL. Example:
```
GET https://api.projectaurum.com/health
```

### Content Type
All requests and responses use `application/json` content type unless otherwise specified.

## Authentication

The API uses JWT (JSON Web Token) authentication with Bearer token authorization.

### Authentication Flow

1. **Login** with username/password to receive access and refresh tokens
2. **Include** access token in `Authorization` header for all authenticated requests
3. **Refresh** access token using refresh token when expired

### Authorization Header Format
```http
Authorization: Bearer <access_token>
```

### Token Expiration
- **Access Token**: 1 hour
- **Refresh Token**: 7 days

## Rate Limiting

API requests are rate-limited to ensure fair usage and system stability.

### Default Limits
- **Authenticated users**: 1000 requests per hour
- **Unauthenticated requests**: 100 requests per hour
- **WebSocket connections**: 10 concurrent connections per user

### Rate Limit Headers
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

### Rate Limit Exceeded Response
```json
{
  "error": "Rate limit exceeded",
  "code": "RATE_LIMIT_EXCEEDED",
  "message": "You have exceeded the rate limit of 1000 requests per hour",
  "retry_after": 3600
}
```

## Error Handling

The API uses standard HTTP status codes and returns detailed error information in JSON format.

### Error Response Format
```json
{
  "error": "Error type",
  "code": "ERROR_CODE",
  "message": "Detailed error description",
  "details": {
    "field": "Additional error details"
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_abc123"
}
```

### Common HTTP Status Codes
- **200 OK**: Successful request
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid request parameters
- **401 Unauthorized**: Authentication required or invalid
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Validation errors
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error

## Authentication Endpoints

### POST /auth/login
Authenticate user and receive access tokens.

**Request Body:**
```json
{
  "username": "trader123",
  "password": "secure_password"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "user_123",
    "username": "trader123",
    "email": "trader@example.com",
    "role": "trader",
    "permissions": ["signals.read", "portfolio.read"]
  }
}
```

**Error Response (401 Unauthorized):**
```json
{
  "error": "Authentication failed",
  "code": "INVALID_CREDENTIALS",
  "message": "Invalid username or password"
}
```

### POST /auth/refresh
Refresh access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### GET /auth/me
Get current user profile information.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "id": "user_123",
  "username": "trader123",
  "email": "trader@example.com",
  "role": "trader",
  "permissions": ["signals.read", "portfolio.read", "portfolio.update"],
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-15T10:30:00Z",
  "preferences": {
    "timezone": "Asia/Jakarta",
    "language": "en",
    "notifications": {
      "email": true,
      "telegram": true,
      "sms": false
    }
  }
}
```

## Signal Management

### GET /signals/daily
Retrieve daily trading signals for all monitored stocks.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `date` (optional): Target date in YYYY-MM-DD format (default: today)
- `symbols` (optional): Comma-separated list of stock symbols
- `signal_type` (optional): Filter by signal type (BUY, SELL, HOLD)
- `min_strength` (optional): Minimum signal strength (0.0 to 1.0)

**Example Request:**
```http
GET /signals/daily?date=2024-01-15&symbols=BBCA,TLKM&min_strength=0.5
```

**Response (200 OK):**
```json
{
  "date": "2024-01-15",
  "generated_at": "2024-01-15T06:30:00Z",
  "total_signals": 25,
  "signals": [
    {
      "symbol": "BBCA",
      "company_name": "Bank Central Asia Tbk",
      "signal_type": "BUY",
      "signal_strength": 0.78,
      "recommended_allocation": 0.04,
      "current_price": 9750,
      "target_price": 10500,
      "stop_loss": 9200,
      "confidence": 0.82,
      "reasoning": {
        "technical_score": 0.85,
        "fundamental_score": 0.70,
        "sentiment_score": 0.80,
        "key_factors": [
          "Strong momentum breakout",
          "Attractive P/E ratio",
          "Positive analyst sentiment"
        ]
      },
      "risk_metrics": {
        "volatility": 0.15,
        "beta": 0.95,
        "liquidity_score": 0.90
      }
    }
  ],
  "portfolio_summary": {
    "total_allocation": 0.85,
    "cash_reserve": 0.15,
    "buy_signals": 8,
    "sell_signals": 3,
    "hold_signals": 14
  }
}
```

### POST /signals/generate
Manually trigger signal generation process.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Request Body (optional):**
```json
{
  "symbols": ["BBCA", "TLKM"],
  "force_regenerate": false,
  "notify_completion": true
}
```

**Response (202 Accepted):**
```json
{
  "task_id": "task_abc123",
  "status": "started",
  "message": "Signal generation started",
  "estimated_completion": "2024-01-15T06:35:00Z",
  "started_at": "2024-01-15T06:30:00Z"
}
```

### GET /signals/generation/{task_id}
Check signal generation task status.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "task_id": "task_abc123",
  "status": "completed",
  "progress": 100,
  "started_at": "2024-01-15T06:30:00Z",
  "completed_at": "2024-01-15T06:33:45Z",
  "result": {
    "signals_generated": 45,
    "signals_updated": 12,
    "errors": 0
  },
  "logs": [
    {
      "timestamp": "2024-01-15T06:30:05Z",
      "level": "INFO",
      "message": "Starting feature engineering for 45 symbols"
    },
    {
      "timestamp": "2024-01-15T06:32:10Z",
      "level": "INFO",
      "message": "ML model inference completed"
    }
  ]
}
```

### GET /signals/history
Retrieve historical signal performance.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `symbol` (optional): Stock symbol
- `start_date`: Start date (YYYY-MM-DD)
- `end_date`: End date (YYYY-MM-DD)
- `limit` (optional): Maximum results (default: 100)
- `offset` (optional): Pagination offset (default: 0)

**Response (200 OK):**
```json
{
  "total": 150,
  "limit": 100,
  "offset": 0,
  "signals": [
    {
      "signal_id": "sig_123",
      "symbol": "BBCA",
      "signal_date": "2024-01-10",
      "signal_type": "BUY",
      "signal_strength": 0.75,
      "entry_price": 9500,
      "exit_price": 9875,
      "holding_period": 3,
      "return_pct": 0.0395,
      "outcome": "profitable",
      "actual_allocation": 0.035
    }
  ],
  "performance_summary": {
    "total_signals": 150,
    "profitable_signals": 98,
    "win_rate": 0.653,
    "average_return": 0.0234,
    "total_return": 0.184,
    "sharpe_ratio": 1.45
  }
}
```

## Portfolio Management

### GET /portfolio/summary
Get current portfolio summary and performance metrics.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "portfolio_value": 1250000000,
  "cash_balance": 187500000,
  "invested_amount": 1062500000,
  "total_return": 0.125,
  "daily_pnl": 15750000,
  "daily_return": 0.0126,
  "positions_count": 18,
  "currency": "IDR",
  "last_updated": "2024-01-15T15:30:00Z",
  "performance_metrics": {
    "ytd_return": 0.089,
    "one_month_return": 0.034,
    "three_month_return": 0.067,
    "sharpe_ratio": 1.32,
    "max_drawdown": -0.045,
    "volatility": 0.142,
    "beta": 1.05
  },
  "sector_allocation": {
    "banking": 0.35,
    "telecommunications": 0.20,
    "consumer_goods": 0.25,
    "mining": 0.15,
    "cash": 0.05
  },
  "top_holdings": [
    {
      "symbol": "BBCA",
      "weight": 0.08,
      "value": 100000000
    }
  ]
}
```

### GET /portfolio/positions
Get current portfolio positions.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `symbol` (optional): Filter by stock symbol
- `status` (optional): Filter by position status (active, closed)

**Response (200 OK):**
```json
{
  "positions": [
    {
      "position_id": "pos_123",
      "symbol": "BBCA",
      "company_name": "Bank Central Asia Tbk",
      "quantity": 10000,
      "average_price": 9500,
      "current_price": 9750,
      "market_value": 97500000,
      "cost_basis": 95000000,
      "unrealized_pnl": 2500000,
      "unrealized_return": 0.026,
      "weight": 0.078,
      "sector": "banking",
      "last_signal": {
        "type": "HOLD",
        "date": "2024-01-15",
        "strength": 0.45
      },
      "risk_metrics": {
        "var_1day": -580000,
        "beta": 0.95,
        "volatility": 0.18
      },
      "entry_date": "2024-01-10T09:15:00Z",
      "last_updated": "2024-01-15T15:30:00Z"
    }
  ],
  "summary": {
    "total_positions": 18,
    "total_value": 1062500000,
    "total_pnl": 78125000,
    "total_return": 0.079
  }
}
```

### PUT /portfolio/positions/{symbol}
Update portfolio position for a specific stock.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "action": "buy",
  "quantity": 5000,
  "price": 9750,
  "notes": "Adding to existing position based on strong signal"
}
```

**Response (200 OK):**
```json
{
  "position_id": "pos_123",
  "symbol": "BBCA",
  "previous_quantity": 10000,
  "new_quantity": 15000,
  "previous_avg_price": 9500,
  "new_avg_price": 9625,
  "transaction": {
    "transaction_id": "txn_456",
    "action": "buy",
    "quantity": 5000,
    "price": 9750,
    "total_amount": 48750000,
    "fees": 48750,
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "updated_position": {
    "market_value": 144375000,
    "cost_basis": 144375000,
    "unrealized_pnl": 0,
    "weight": 0.115
  }
}
```

### GET /portfolio/transactions
Get transaction history.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `symbol` (optional): Filter by stock symbol
- `action` (optional): Filter by action (buy, sell)
- `start_date` (optional): Start date (YYYY-MM-DD)
- `end_date` (optional): End date (YYYY-MM-DD)
- `limit` (optional): Maximum results (default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Response (200 OK):**
```json
{
  "total": 125,
  "limit": 50,
  "offset": 0,
  "transactions": [
    {
      "transaction_id": "txn_456",
      "symbol": "BBCA",
      "action": "buy",
      "quantity": 5000,
      "price": 9750,
      "total_amount": 48750000,
      "fees": 48750,
      "timestamp": "2024-01-15T10:30:00Z",
      "order_type": "market",
      "execution_status": "filled",
      "signal_reference": "sig_789"
    }
  ]
}
```

## Alert Management

### GET /alerts
Retrieve user alerts with filtering and pagination.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `status` (optional): Filter by status (pending, sent, acknowledged, dismissed)
- `priority` (optional): Filter by priority (low, medium, high, critical)
- `alert_type` (optional): Filter by alert type
- `start_date` (optional): Start date filter
- `end_date` (optional): End date filter
- `limit` (optional): Maximum results (default: 100)
- `offset` (optional): Pagination offset (default: 0)

**Response (200 OK):**
```json
{
  "total": 45,
  "limit": 100,
  "offset": 0,
  "alerts": [
    {
      "alert_id": "alert_123",
      "alert_type": "trading_signal",
      "priority": "high",
      "title": "Strong BUY Signal - BBCA",
      "message": "BBCA has generated a strong BUY signal with 0.82 confidence. Recommended allocation: 4.5%",
      "status": "sent",
      "created_at": "2024-01-15T06:35:00Z",
      "sent_at": "2024-01-15T06:35:15Z",
      "acknowledged_at": null,
      "metadata": {
        "symbol": "BBCA",
        "signal_strength": 0.82,
        "signal_type": "BUY",
        "recommended_allocation": 0.045
      },
      "delivery_channels": ["email", "telegram"],
      "delivery_status": {
        "email": "delivered",
        "telegram": "delivered",
        "sms": "not_configured"
      }
    }
  ]
}
```

### POST /alerts
Create a new alert.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "alert_type": "risk_breach",
  "priority": "critical",
  "title": "Risk Limit Breach",
  "message": "Portfolio VaR has exceeded the 5% limit",
  "metadata": {
    "current_var": 0.067,
    "limit": 0.05,
    "breach_amount": 0.017
  },
  "delivery_channels": ["email", "telegram", "sms"]
}
```

**Response (201 Created):**
```json
{
  "alert_id": "alert_456",
  "status": "created",
  "message": "Alert created successfully",
  "estimated_delivery": "2024-01-15T10:31:00Z"
}
```

### PUT /alerts/{alert_id}/status
Update alert status (acknowledge, dismiss, etc.).

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "status": "acknowledged",
  "notes": "Position adjusted to reduce risk exposure"
}
```

**Response (200 OK):**
```json
{
  "alert_id": "alert_123",
  "previous_status": "sent",
  "new_status": "acknowledged",
  "acknowledged_at": "2024-01-15T10:45:00Z",
  "notes": "Position adjusted to reduce risk exposure"
}
```

## Risk Management

### GET /risk/overview
Get current portfolio risk overview.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "risk_summary": {
    "overall_risk_score": 6.5,
    "risk_level": "moderate",
    "last_calculated": "2024-01-15T15:30:00Z"
  },
  "var_metrics": {
    "var_1_day_1pct": -12500000,
    "var_1_day_5pct": -7850000,
    "expected_shortfall": -15750000,
    "confidence_level": 0.95
  },
  "exposure_metrics": {
    "gross_exposure": 1.05,
    "net_exposure": 0.85,
    "leverage": 1.05,
    "beta": 1.08
  },
  "concentration_risk": {
    "max_single_position": 0.08,
    "max_sector_exposure": 0.35,
    "top_5_concentration": 0.32,
    "herfindahl_index": 0.15
  },
  "liquidity_risk": {
    "avg_daily_volume_ratio": 0.02,
    "liquidity_score": 0.85,
    "estimated_liquidation_time": "2.3 days"
  },
  "correlation_risk": {
    "avg_correlation": 0.45,
    "max_correlation": 0.78,
    "diversification_ratio": 0.72
  }
}
```

### GET /risk/alerts
Get active risk alerts.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `active_only` (optional): Show only active alerts (default: true)
- `severity` (optional): Filter by severity (low, medium, high, critical)

**Response (200 OK):**
```json
{
  "active_alerts": [
    {
      "alert_id": "risk_alert_123",
      "risk_type": "concentration",
      "severity": "medium",
      "title": "High Sector Concentration",
      "description": "Banking sector exposure (38%) exceeds recommended limit (35%)",
      "current_value": 0.38,
      "threshold": 0.35,
      "breach_amount": 0.03,
      "triggered_at": "2024-01-15T14:20:00Z",
      "recommended_action": "Reduce banking sector positions by 3%",
      "affected_positions": ["BBCA", "BMRI", "BBNI"]
    }
  ],
  "risk_limits": {
    "max_position_size": 0.05,
    "max_sector_exposure": 0.35,
    "max_portfolio_var": 0.05,
    "min_liquidity_score": 0.70,
    "max_correlation": 0.80
  }
}
```

### PUT /risk/limits
Update risk limits (admin only).

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "max_position_size": 0.06,
  "max_sector_exposure": 0.40,
  "max_portfolio_var": 0.06,
  "effective_date": "2024-01-16"
}
```

**Response (200 OK):**
```json
{
  "message": "Risk limits updated successfully",
  "updated_limits": {
    "max_position_size": 0.06,
    "max_sector_exposure": 0.40,
    "max_portfolio_var": 0.06
  },
  "effective_date": "2024-01-16T00:00:00Z",
  "updated_by": "admin_user"
}
```

## Market Data

### GET /market/status
Get current market status.

**Response (200 OK):**
```json
{
  "market_status": {
    "is_open": true,
    "session_type": "regular",
    "current_time": "2024-01-15T14:30:00+07:00",
    "timezone": "Asia/Jakarta"
  },
  "trading_hours": {
    "market_open": "09:00:00",
    "market_close": "15:49:00",
    "pre_market_start": "08:45:00",
    "post_market_end": "16:15:00"
  },
  "next_session": {
    "next_open": "2024-01-16T09:00:00+07:00",
    "next_close": "2024-01-15T15:49:00+07:00"
  },
  "market_holidays": [
    {
      "date": "2024-01-01",
      "name": "New Year's Day"
    }
  ]
}
```

### GET /market/data/{symbol}
Get current market data for a specific stock.

**Path Parameters:**
- `symbol`: Stock symbol (e.g., BBCA)

**Query Parameters:**
- `include_historical` (optional): Include historical data (default: false)
- `period` (optional): Historical period (1d, 5d, 1m, 3m, 1y)

**Response (200 OK):**
```json
{
  "symbol": "BBCA",
  "company_name": "Bank Central Asia Tbk",
  "current_price": 9750,
  "price_change": 125,
  "price_change_pct": 0.0130,
  "volume": 15750000,
  "avg_volume": 25000000,
  "market_cap": 1156000000000,
  "last_updated": "2024-01-15T15:30:00Z",
  "day_range": {
    "low": 9600,
    "high": 9800
  },
  "52_week_range": {
    "low": 8200,
    "high": 10500
  },
  "fundamental_data": {
    "pe_ratio": 15.2,
    "pb_ratio": 2.1,
    "dividend_yield": 0.025,
    "roe": 0.148
  },
  "technical_indicators": {
    "rsi_14": 65.8,
    "sma_20": 9650,
    "sma_50": 9500,
    "bollinger_upper": 9850,
    "bollinger_lower": 9450
  }
}
```

## Analytics & Reporting

### GET /analytics/performance
Get portfolio performance analytics.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `period` (optional): Analysis period (1w, 1m, 3m, 6m, 1y, ytd)
- `benchmark` (optional): Benchmark symbol (default: JKSE)

**Response (200 OK):**
```json
{
  "period": "3m",
  "start_date": "2023-10-15",
  "end_date": "2024-01-15",
  "portfolio_performance": {
    "total_return": 0.067,
    "annualized_return": 0.268,
    "volatility": 0.142,
    "sharpe_ratio": 1.32,
    "max_drawdown": -0.045,
    "calmar_ratio": 5.96,
    "sortino_ratio": 1.89
  },
  "benchmark_performance": {
    "total_return": 0.034,
    "annualized_return": 0.136,
    "volatility": 0.125,
    "sharpe_ratio": 0.87
  },
  "risk_metrics": {
    "beta": 1.05,
    "alpha": 0.132,
    "information_ratio": 1.15,
    "tracking_error": 0.087,
    "correlation": 0.78
  },
  "attribution_analysis": {
    "stock_selection": 0.023,
    "sector_allocation": 0.010,
    "timing": 0.034
  }
}
```

### GET /reports/daily
Generate daily trading report.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `date` (optional): Report date (default: today)
- `format` (optional): Report format (json, pdf, csv)

**Response (200 OK):**
```json
{
  "report_date": "2024-01-15",
  "generated_at": "2024-01-15T16:00:00Z",
  "portfolio_snapshot": {
    "total_value": 1250000000,
    "daily_pnl": 15750000,
    "daily_return": 0.0126,
    "positions_count": 18
  },
  "trading_activity": {
    "trades_executed": 3,
    "total_volume": 48750000,
    "buy_orders": 2,
    "sell_orders": 1
  },
  "signal_summary": {
    "signals_generated": 45,
    "buy_signals": 8,
    "sell_signals": 3,
    "hold_signals": 34,
    "avg_signal_strength": 0.62
  },
  "risk_summary": {
    "portfolio_var": 0.035,
    "risk_score": 6.5,
    "risk_alerts": 1
  },
  "top_performers": [
    {
      "symbol": "TLKM",
      "return": 0.034,
      "contribution": 0.0045
    }
  ],
  "bottom_performers": [
    {
      "symbol": "INDF",
      "return": -0.021,
      "contribution": -0.0015
    }
  ]
}
```

## WebSocket Endpoints

### WebSocket /ws/alerts
Real-time alert notifications.

**Connection:**
```javascript
const ws = new WebSocket('wss://api.projectaurum.com/ws/alerts');
ws.onopen = function() {
    // Send authentication
    ws.send(JSON.stringify({
        type: 'auth',
        token: 'Bearer <access_token>'
    }));
};
```

**Message Types:**

**Authentication Message:**
```json
{
  "type": "auth",
  "token": "Bearer <access_token>"
}
```

**Alert Notification:**
```json
{
  "type": "alert",
  "data": {
    "alert_id": "alert_123",
    "alert_type": "trading_signal",
    "priority": "high",
    "title": "Strong BUY Signal - BBCA",
    "message": "BBCA has generated a strong BUY signal",
    "timestamp": "2024-01-15T06:35:00Z",
    "metadata": {
      "symbol": "BBCA",
      "signal_strength": 0.82
    }
  }
}
```

**Price Update:**
```json
{
  "type": "price_update",
  "data": {
    "symbol": "BBCA",
    "price": 9750,
    "change": 125,
    "change_pct": 0.0130,
    "volume": 15750000,
    "timestamp": "2024-01-15T15:30:00Z"
  }
}
```

### WebSocket /ws/portfolio
Real-time portfolio updates.

**Portfolio Update:**
```json
{
  "type": "portfolio_update",
  "data": {
    "portfolio_value": 1250000000,
    "daily_pnl": 15750000,
    "daily_return": 0.0126,
    "positions_updated": [
      {
        "symbol": "BBCA",
        "current_price": 9750,
        "unrealized_pnl": 2500000
      }
    ],
    "timestamp": "2024-01-15T15:30:00Z"
  }
}
```

## Administrative Endpoints

### GET /admin/users
Get user list (admin only).

**Headers:**
```http
Authorization: Bearer <admin_access_token>
```

**Response (200 OK):**
```json
{
  "total": 25,
  "users": [
    {
      "id": "user_123",
      "username": "trader123",
      "email": "trader@example.com",
      "role": "trader",
      "status": "active",
      "created_at": "2024-01-01T00:00:00Z",
      "last_login": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### GET /admin/system/health
Get detailed system health information (admin only).

**Response (200 OK):**
```json
{
  "overall_status": "healthy",
  "timestamp": "2024-01-15T16:00:00Z",
  "services": {
    "api": {
      "status": "healthy",
      "response_time": "45ms",
      "cpu_usage": 0.35,
      "memory_usage": 0.68
    },
    "database": {
      "status": "healthy",
      "connection_pool": "8/20",
      "query_avg_time": "12ms"
    },
    "redis": {
      "status": "healthy",
      "memory_usage": 0.42,
      "hit_rate": 0.94
    },
    "ml_service": {
      "status": "healthy",
      "last_training": "2024-01-14T06:00:00Z",
      "model_accuracy": 0.672
    }
  },
  "metrics": {
    "requests_per_minute": 450,
    "error_rate": 0.002,
    "active_users": 12,
    "data_feed_latency": "200ms"
  }
}
```

## Data Models

### User Model
```json
{
  "id": "string",
  "username": "string",
  "email": "string",
  "role": "admin|trader|analyst|viewer",
  "permissions": ["string"],
  "created_at": "datetime",
  "last_login": "datetime",
  "preferences": {
    "timezone": "string",
    "language": "string",
    "notifications": {
      "email": "boolean",
      "telegram": "boolean",
      "sms": "boolean"
    }
  }
}
```

### Signal Model
```json
{
  "signal_id": "string",
  "symbol": "string",
  "signal_date": "date",
  "signal_type": "BUY|SELL|HOLD",
  "signal_strength": "number (-1 to 1)",
  "recommended_allocation": "number (0 to 1)",
  "current_price": "number",
  "target_price": "number",
  "stop_loss": "number",
  "confidence": "number (0 to 1)",
  "reasoning": {
    "technical_score": "number",
    "fundamental_score": "number",
    "sentiment_score": "number",
    "key_factors": ["string"]
  },
  "generated_at": "datetime"
}
```

### Position Model
```json
{
  "position_id": "string",
  "symbol": "string",
  "quantity": "number",
  "average_price": "number",
  "current_price": "number",
  "market_value": "number",
  "cost_basis": "number",
  "unrealized_pnl": "number",
  "unrealized_return": "number",
  "weight": "number",
  "sector": "string",
  "entry_date": "datetime",
  "last_updated": "datetime"
}
```

## SDK Examples

### Python SDK Example

```python
import requests
from typing import Dict, List, Optional

class ProjectAurumAPI:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })

    def get_daily_signals(self, date: Optional[str] = None) -> Dict:
        """Get daily trading signals"""
        params = {'date': date} if date else {}
        response = self.session.get(f'{self.base_url}/signals/daily', params=params)
        response.raise_for_status()
        return response.json()

    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary"""
        response = self.session.get(f'{self.base_url}/portfolio/summary')
        response.raise_for_status()
        return response.json()

    def update_position(self, symbol: str, action: str, quantity: int, price: float) -> Dict:
        """Update portfolio position"""
        data = {
            'action': action,
            'quantity': quantity,
            'price': price
        }
        response = self.session.put(f'{self.base_url}/portfolio/positions/{symbol}', json=data)
        response.raise_for_status()
        return response.json()

# Usage example
api = ProjectAurumAPI('https://api.projectaurum.com', 'your_access_token')

# Get today's signals
signals = api.get_daily_signals()
print(f"Found {len(signals['signals'])} signals")

# Get portfolio summary
portfolio = api.get_portfolio_summary()
print(f"Portfolio value: IDR {portfolio['portfolio_value']:,}")

# Execute a trade
trade_result = api.update_position('BBCA', 'buy', 1000, 9750)
print(f"Trade executed: {trade_result['transaction']['transaction_id']}")
```

### JavaScript SDK Example

```javascript
class ProjectAurumAPI {
    constructor(baseURL, accessToken) {
        this.baseURL = baseURL;
        this.accessToken = accessToken;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: {
                'Authorization': `Bearer ${this.accessToken}`,
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        const response = await fetch(url, config);
        if (!response.ok) {
            throw new Error(`API request failed: ${response.statusText}`);
        }
        return response.json();
    }

    async getDailySignals(date = null) {
        const params = date ? `?date=${date}` : '';
        return this.request(`/signals/daily${params}`);
    }

    async getPortfolioSummary() {
        return this.request('/portfolio/summary');
    }

    async updatePosition(symbol, action, quantity, price) {
        return this.request(`/portfolio/positions/${symbol}`, {
            method: 'PUT',
            body: JSON.stringify({ action, quantity, price })
        });
    }

    // WebSocket connection for real-time updates
    connectWebSocket() {
        const ws = new WebSocket(`wss://api.projectaurum.com/ws/alerts`);

        ws.onopen = () => {
            ws.send(JSON.stringify({
                type: 'auth',
                token: `Bearer ${this.accessToken}`
            }));
        };

        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleRealtimeUpdate(message);
        };

        return ws;
    }

    handleRealtimeUpdate(message) {
        switch (message.type) {
            case 'alert':
                console.log('New alert:', message.data);
                break;
            case 'price_update':
                console.log('Price update:', message.data);
                break;
            case 'portfolio_update':
                console.log('Portfolio update:', message.data);
                break;
        }
    }
}

// Usage example
const api = new ProjectAurumAPI('https://api.projectaurum.com', 'your_access_token');

// Get signals and portfolio data
async function loadDashboard() {
    try {
        const [signals, portfolio] = await Promise.all([
            api.getDailySignals(),
            api.getPortfolioSummary()
        ]);

        console.log('Signals:', signals);
        console.log('Portfolio:', portfolio);

        // Connect to real-time updates
        const ws = api.connectWebSocket();
    } catch (error) {
        console.error('Failed to load dashboard:', error);
    }
}

loadDashboard();
```

This comprehensive API documentation provides developers with all the information needed to integrate with the Project Aurum quantitative trading system, including authentication, data retrieval, portfolio management, risk monitoring, and real-time updates.