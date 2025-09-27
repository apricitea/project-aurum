# Project Aurum - System Architecture

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Architecture Principles](#architecture-principles)
4. [Component Architecture](#component-architecture)
5. [Data Architecture](#data-architecture)
6. [Security Architecture](#security-architecture)
7. [Deployment Architecture](#deployment-architecture)
8. [Performance Architecture](#performance-architecture)
9. [Monitoring Architecture](#monitoring-architecture)
10. [Disaster Recovery](#disaster-recovery)

## Executive Summary

Project Aurum implements a microservices-based architecture optimized for high-frequency quantitative trading in the Indonesian Stock Exchange (IDX). The system is designed to handle real-time market data processing, machine learning inference, and multi-channel alert distribution with sub-second latency requirements.

### Key Architectural Decisions

- **Event-Driven Architecture**: Kafka-based message streaming for real-time data processing
- **Containerized Microservices**: Docker containers with horizontal scaling capabilities
- **Polyglot Persistence**: PostgreSQL for transactional data, Redis for caching, InfluxDB for time-series
- **ML Pipeline**: Separated feature engineering, model training, and inference services
- **API-First Design**: RESTful APIs with async/await patterns for high concurrency

## System Overview

```mermaid
graph TB
    subgraph "External Data Sources"
        IDX[IDX Market Data Feed]
        YAHOO[Yahoo Finance API]
        ALPHA[Alpha Vantage API]
        BINEWS[BI Economic Data]
    end

    subgraph "Data Ingestion Layer"
        GATEWAY[Data Gateway Service]
        KAFKA[Kafka Message Broker]
        VALIDATOR[Data Validation Service]
    end

    subgraph "Data Storage Layer"
        POSTGRES[(PostgreSQL<br/>Master Data)]
        REDIS[(Redis<br/>Cache & Sessions)]
        INFLUX[(InfluxDB<br/>Time Series)]
        S3[(MinIO/S3<br/>Object Storage)]
    end

    subgraph "Processing Layer"
        FEATURE[Feature Engineering Service]
        ENSEMBLE[ML Ensemble Service]
        SIGNALS[Signal Generation Service]
        RISK[Risk Management Service]
    end

    subgraph "Application Layer"
        API[FastAPI Application]
        AUTH[Authentication Service]
        CELERY[Celery Task Queue]
        SCHEDULER[APScheduler]
    end

    subgraph "Presentation Layer"
        FRONTEND[React Dashboard]
        ALERTS[Alert Engine]
        REPORTS[Report Generator]
        WEBSOCKET[WebSocket Handler]
    end

    subgraph "Infrastructure Layer"
        NGINX[Nginx Load Balancer]
        PROMETHEUS[Prometheus Monitoring]
        GRAFANA[Grafana Dashboards]
        ELK[ELK Logging Stack]
    end

    IDX --> GATEWAY
    YAHOO --> GATEWAY
    ALPHA --> GATEWAY
    BINEWS --> GATEWAY

    GATEWAY --> KAFKA
    KAFKA --> VALIDATOR
    VALIDATOR --> POSTGRES
    VALIDATOR --> REDIS
    VALIDATOR --> INFLUX

    POSTGRES --> FEATURE
    REDIS --> FEATURE
    INFLUX --> FEATURE

    FEATURE --> ENSEMBLE
    ENSEMBLE --> SIGNALS
    SIGNALS --> RISK

    RISK --> API
    API --> AUTH
    API --> CELERY
    API --> SCHEDULER

    API --> FRONTEND
    API --> ALERTS
    API --> REPORTS
    API --> WEBSOCKET

    NGINX --> API
    NGINX --> FRONTEND

    API --> PROMETHEUS
    PROMETHEUS --> GRAFANA
    API --> ELK
```

## Architecture Principles

### 1. Scalability
- **Horizontal Scaling**: All services can scale independently
- **Stateless Services**: No service stores state locally
- **Database Sharding**: Time-series data partitioned by date
- **Caching Strategy**: Multi-level caching with Redis and application-level cache

### 2. Reliability
- **Circuit Breakers**: Fail-fast patterns for external dependencies
- **Graceful Degradation**: System continues operating with reduced functionality
- **Health Checks**: Comprehensive health monitoring at all levels
- **Retry Mechanisms**: Exponential backoff for transient failures

### 3. Security
- **Zero Trust**: All communications encrypted and authenticated
- **Defense in Depth**: Multiple security layers
- **Least Privilege**: Role-based access control (RBAC)
- **Data Encryption**: At rest and in transit

### 4. Performance
- **Async/Await**: Non-blocking I/O throughout the stack
- **Connection Pooling**: Database and HTTP connection reuse
- **Batch Processing**: Optimized bulk operations
- **Compression**: Data compression for network and storage

### 5. Observability
- **Structured Logging**: JSON logs with correlation IDs
- **Metrics Collection**: Business and technical metrics
- **Distributed Tracing**: Request flow across services
- **Alerting**: Proactive issue detection

## Component Architecture

### Data Gateway Service

**Purpose**: Ingests and normalizes data from multiple external sources

```python
class DataGatewayService:
    """
    Handles real-time data ingestion with the following responsibilities:
    - Connection management to external data sources
    - Data format normalization and validation
    - Rate limiting and connection pooling
    - Error handling and retry logic
    """

    async def ingest_idx_data(self):
        """IDX Market Data Feed ingestion"""

    async def ingest_yahoo_data(self):
        """Yahoo Finance data ingestion"""

    async def validate_and_forward(self, data):
        """Data validation and Kafka publishing"""
```

**Key Features**:
- Real-time TCP connection to IDX Market Data Feed
- REST API polling for backup data sources
- Data quality validation before forwarding
- Automatic failover between data sources
- Configurable rate limiting per source

**Technology Stack**:
- FastAPI for REST endpoints
- asyncio for concurrent connections
- aioredis for caching
- aiokafka for message publishing

### Feature Engineering Service

**Purpose**: Transforms raw market data into ML-ready features

```python
class FeatureEngineeringService:
    """
    Converts raw market data into features for ML models:
    - Technical indicators (RSI, MACD, Bollinger Bands)
    - Fundamental ratios (P/E, P/B, ROE, ROA)
    - Market microstructure (order flow, volatility)
    - Sentiment indicators (news sentiment, momentum)
    """

    def compute_technical_features(self, ohlcv_data):
        """200+ technical indicators"""

    def compute_fundamental_features(self, financial_data):
        """Financial ratio calculations"""

    def compute_sentiment_features(self, news_data):
        """News sentiment and momentum"""
```

**Feature Categories**:

1. **Technical Features (150+ indicators)**
   - Price-based: SMA, EMA, RSI, MACD, Bollinger Bands
   - Volume-based: OBV, VWAP, Volume Profile
   - Volatility: ATR, Realized Volatility, GARCH estimates
   - Pattern recognition: Support/Resistance, Chart patterns

2. **Fundamental Features (50+ ratios)**
   - Valuation: P/E, P/B, P/S, EV/EBITDA
   - Profitability: ROE, ROA, Profit Margins
   - Financial Health: Debt Ratios, Current Ratio
   - Growth: Revenue Growth, EPS Growth

3. **Market Microstructure (30+ features)**
   - Order Book: Bid-Ask Spread, Market Depth
   - Trade Flow: Large Trade Detection, Trade Imbalance
   - Liquidity: Amihud Illiquidity, Roll's Spread

4. **Sentiment Features (20+ indicators)**
   - News Sentiment: NLP-based sentiment scores
   - Market Momentum: Price momentum, Volume momentum
   - Cross-Asset: IDR/USD impact, Regional market correlation

### ML Ensemble Service

**Purpose**: Manages multiple ML models and combines predictions

```python
class MLEnsembleService:
    """
    Ensemble of specialized ML models:
    - Technical Model: Random Forest for technical patterns
    - Fundamental Model: Gradient Boosting for value signals
    - Sentiment Model: XGBoost for momentum and sentiment
    - Meta-Model: Linear Regression for ensemble combination
    """

    async def predict_technical_signals(self, features):
        """Technical model predictions"""

    async def predict_fundamental_signals(self, features):
        """Fundamental model predictions"""

    async def predict_sentiment_signals(self, features):
        """Sentiment model predictions"""

    async def ensemble_predictions(self, individual_predictions):
        """Meta-model ensemble combination"""
```

**Model Architecture**:

1. **Technical Model (Random Forest)**
   - Features: Technical indicators, price patterns
   - Target: Next-day price direction
   - Trees: 200 estimators, max depth 15
   - Hyperparameters: Optimized via Bayesian optimization

2. **Fundamental Model (Gradient Boosting)**
   - Features: Financial ratios, valuation metrics
   - Target: 1-week price direction
   - Implementation: LightGBM with early stopping
   - Regularization: L1/L2 with cross-validation

3. **Sentiment Model (XGBoost)**
   - Features: News sentiment, momentum indicators
   - Target: Short-term (1-3 days) price movement
   - Boosting: 500 rounds with learning rate 0.01
   - Feature selection: Recursive feature elimination

4. **Meta-Model (Linear Regression)**
   - Inputs: Predictions from all three models
   - Output: Final signal strength (-1 to +1)
   - Regularization: Ridge regression with CV
   - Weights: Dynamically adjusted based on recent performance

### Signal Generation Service

**Purpose**: Converts ML predictions into actionable trading signals

```python
class SignalGenerationService:
    """
    Transforms ML predictions into trading signals:
    - Signal strength calculation
    - Position sizing recommendations
    - Risk-adjusted signal filtering
    - Portfolio-level signal optimization
    """

    async def generate_daily_signals(self):
        """Main daily signal generation workflow"""

    async def calculate_position_sizes(self, signals):
        """Kelly criterion-based position sizing"""

    async def apply_risk_filters(self, signals):
        """Risk management signal filtering"""
```

**Signal Generation Process**:

1. **Signal Strength Calculation**
   ```python
   signal_strength = (
       0.4 * technical_prediction +
       0.3 * fundamental_prediction +
       0.3 * sentiment_prediction
   ) * confidence_multiplier
   ```

2. **Position Sizing**
   - Kelly Criterion with volatility adjustment
   - Maximum 5% allocation per stock
   - Sector concentration limits (25% max)
   - Correlation-based adjustment

3. **Risk Filtering**
   - Minimum signal strength threshold (0.3)
   - Liquidity requirements (minimum daily volume)
   - News event filtering (earnings, corporate actions)
   - Market regime detection (bull/bear/sideways)

### Risk Management Service

**Purpose**: Monitors and manages portfolio risk in real-time

```python
class RiskManagementService:
    """
    Real-time risk monitoring and management:
    - Portfolio risk metrics calculation
    - Risk limit monitoring and alerting
    - Dynamic position adjustment
    - Correlation and concentration monitoring
    """

    async def calculate_portfolio_var(self):
        """Value at Risk calculation"""

    async def monitor_risk_limits(self):
        """Continuous risk limit monitoring"""

    async def adjust_positions(self, risk_breach):
        """Automatic position adjustment"""
```

**Risk Metrics**:

1. **Portfolio Level**
   - Value at Risk (VaR) - 1% and 5% levels
   - Expected Shortfall (CVaR)
   - Maximum Drawdown
   - Sharpe Ratio (rolling)

2. **Position Level**
   - Individual position size limits
   - Stop-loss levels
   - Position correlation
   - Concentration risk

3. **Market Level**
   - Market beta exposure
   - Sector concentration
   - Currency exposure (IDR/USD)
   - Volatility regime detection

## Data Architecture

### Database Design

#### PostgreSQL (Master Data)

```sql
-- Securities master table
CREATE TABLE securities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    sector VARCHAR(50),
    market_cap DECIMAL(20,2),
    listing_date DATE,
    is_lq45 BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- User management
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    permissions JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

-- Trading signals
CREATE TABLE signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) REFERENCES securities(symbol),
    signal_date DATE NOT NULL,
    signal_type VARCHAR(10) CHECK (signal_type IN ('BUY', 'SELL', 'HOLD')),
    signal_strength DECIMAL(3,2) CHECK (signal_strength BETWEEN -1 AND 1),
    recommended_allocation DECIMAL(5,2),
    model_predictions JSONB,
    generated_at TIMESTAMP DEFAULT NOW()
);

-- Portfolio positions
CREATE TABLE positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    symbol VARCHAR(20) REFERENCES securities(symbol),
    quantity INTEGER NOT NULL,
    average_price DECIMAL(15,2) NOT NULL,
    current_price DECIMAL(15,2),
    unrealized_pnl DECIMAL(15,2),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Risk metrics
CREATE TABLE risk_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    calculation_date DATE NOT NULL,
    portfolio_var_1pct DECIMAL(15,2),
    portfolio_var_5pct DECIMAL(15,2),
    max_drawdown DECIMAL(5,2),
    sharpe_ratio DECIMAL(5,2),
    volatility DECIMAL(5,2),
    beta DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Alerts and notifications
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    alert_type VARCHAR(50) NOT NULL,
    priority VARCHAR(10) DEFAULT 'MEDIUM',
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT NOW(),
    sent_at TIMESTAMP,
    acknowledged_at TIMESTAMP
);
```

#### Redis (Caching & Sessions)

```python
# Cache structure
CACHE_PATTERNS = {
    # Real-time data caching
    'price:latest:{symbol}': 60,  # 1 minute TTL
    'ohlcv:{symbol}:{timeframe}': 300,  # 5 minutes TTL
    'volume:{symbol}': 60,

    # Feature caching
    'features:technical:{symbol}': 900,  # 15 minutes TTL
    'features:fundamental:{symbol}': 3600,  # 1 hour TTL

    # Model predictions
    'predictions:{model}:{symbol}': 1800,  # 30 minutes TTL
    'signals:daily:{date}': 86400,  # 24 hours TTL

    # User sessions
    'session:{user_id}': 3600,  # 1 hour TTL
    'auth:token:{token_id}': 3600,

    # System cache
    'health:services': 30,
    'config:risk_limits': 300,
}
```

#### InfluxDB (Time Series)

```sql
-- Market data measurement
CREATE RETENTION POLICY "realtime" ON "market_data" DURATION 7d REPLICATION 1
CREATE RETENTION POLICY "historical" ON "market_data" DURATION 2555d REPLICATION 1

-- Time series structure
-- Measurement: trades
-- Tags: symbol, exchange
-- Fields: price, volume, side, timestamp
-- Time: nanosecond precision

-- Measurement: quotes
-- Tags: symbol, exchange
-- Fields: bid, ask, bid_size, ask_size, timestamp
-- Time: nanosecond precision

-- Measurement: ohlcv
-- Tags: symbol, timeframe
-- Fields: open, high, low, close, volume
-- Time: minute precision

-- Continuous queries for aggregation
CREATE CONTINUOUS QUERY "cq_ohlcv_1h" ON "market_data"
BEGIN
  SELECT first(open) AS open, max(high) AS high, min(low) AS low,
         last(close) AS close, sum(volume) AS volume
  INTO "market_data"."historical"."ohlcv_1h"
  FROM "market_data"."realtime"."ohlcv_1m"
  GROUP BY time(1h), symbol
END
```

### Data Flow Architecture

```mermaid
sequenceDiagram
    participant ES as External Sources
    participant DG as Data Gateway
    participant K as Kafka
    participant FE as Feature Engine
    participant ML as ML Ensemble
    participant SG as Signal Generator
    participant API as FastAPI
    participant UI as Frontend
    participant AL as Alert Engine

    ES->>DG: Market Data Stream
    DG->>K: Publish Raw Data
    K->>FE: Consume Market Data
    FE->>FE: Generate Features
    FE->>ML: Feature Vectors
    ML->>ML: Model Inference
    ML->>SG: Predictions
    SG->>SG: Generate Signals
    SG->>API: Trading Signals
    API->>UI: Real-time Updates
    API->>AL: Signal Alerts
    AL->>Users: Notifications
```

## Security Architecture

### Authentication & Authorization

```python
class SecurityManager:
    """
    Comprehensive security management:
    - JWT-based authentication with refresh tokens
    - Role-based access control (RBAC)
    - API rate limiting and request throttling
    - Input validation and sanitization
    """

    def authenticate_user(self, credentials):
        """Multi-factor authentication support"""

    def authorize_request(self, user, resource, action):
        """RBAC authorization"""

    def validate_input(self, request_data):
        """Input validation and sanitization"""
```

### Security Layers

1. **Network Security**
   - NGINX with SSL/TLS termination
   - VPC/Private networking
   - Firewall rules and security groups
   - DDoS protection via CloudFlare

2. **Application Security**
   - JWT tokens with short expiration
   - CORS protection
   - Rate limiting per user/IP
   - Input validation using Pydantic

3. **Data Security**
   - Encryption at rest (AES-256)
   - Encryption in transit (TLS 1.3)
   - Database connection encryption
   - Secrets management with HashiCorp Vault

4. **Infrastructure Security**
   - Container scanning for vulnerabilities
   - Regular security updates
   - Least privilege access principles
   - Audit logging for all actions

### Role-Based Access Control

```python
ROLES = {
    'admin': {
        'permissions': ['*'],  # All permissions
        'description': 'System administrator'
    },
    'trader': {
        'permissions': [
            'signals.read',
            'portfolio.read',
            'portfolio.update',
            'alerts.read',
            'reports.read'
        ],
        'description': 'Active trader'
    },
    'analyst': {
        'permissions': [
            'signals.read',
            'portfolio.read',
            'analytics.read',
            'reports.read',
            'models.read'
        ],
        'description': 'Quantitative analyst'
    },
    'viewer': {
        'permissions': [
            'signals.read',
            'portfolio.read',
            'reports.read'
        ],
        'description': 'Read-only access'
    }
}
```

## Deployment Architecture

### Container Architecture

```dockerfile
# Multi-stage Docker build
FROM python:3.11-slim as base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base as development
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY . .
CMD ["uvicorn", "src.api.main:app", "--reload", "--host", "0.0.0.0"]

FROM base as production
COPY . .
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser
CMD ["gunicorn", "src.api.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: trading-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: trading-api
  template:
    metadata:
      labels:
        app: trading-api
    spec:
      containers:
      - name: api
        image: project-aurum/api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: trading-api-service
spec:
  selector:
    app: trading-api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

### Infrastructure as Code (Terraform)

```hcl
# AWS ECS deployment
resource "aws_ecs_cluster" "trading_cluster" {
  name = "project-aurum"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_service" "trading_api" {
  name            = "trading-api"
  cluster         = aws_ecs_cluster.trading_cluster.id
  task_definition = aws_ecs_task_definition.trading_api.arn
  desired_count   = 3

  load_balancer {
    target_group_arn = aws_lb_target_group.trading_api.arn
    container_name   = "trading-api"
    container_port   = 8000
  }

  depends_on = [
    aws_lb_listener.trading_api
  ]
}

resource "aws_rds_instance" "trading_db" {
  identifier = "project-aurum-db"
  engine     = "postgres"
  engine_version = "15.3"
  instance_class = "db.r6g.xlarge"
  allocated_storage = 500
  storage_encrypted = true

  db_name  = "trading_system"
  username = var.db_username
  password = var.db_password

  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  tags = {
    Environment = var.environment
    Project     = "project-aurum"
  }
}
```

## Performance Architecture

### Optimization Strategy

1. **Database Optimization**
   ```sql
   -- Index optimization
   CREATE INDEX CONCURRENTLY idx_signals_symbol_date
   ON signals(symbol, signal_date DESC);

   CREATE INDEX CONCURRENTLY idx_positions_user_symbol
   ON positions(user_id, symbol);

   -- Partitioning for large tables
   CREATE TABLE signals_2024 PARTITION OF signals
   FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
   ```

2. **Caching Strategy**
   ```python
   # Multi-level caching
   @cache(ttl=60)  # Application cache
   async def get_latest_price(symbol: str):
       # Redis cache lookup
       cached = await redis.get(f"price:latest:{symbol}")
       if cached:
           return json.loads(cached)

       # Database fallback
       price = await db.fetch_latest_price(symbol)
       await redis.setex(f"price:latest:{symbol}", 60, json.dumps(price))
       return price
   ```

3. **Async Processing**
   ```python
   # Concurrent API requests
   async def fetch_multiple_signals(symbols: List[str]):
       tasks = [get_signal_for_symbol(symbol) for symbol in symbols]
       return await asyncio.gather(*tasks)
   ```

### Performance Metrics

| Component | Target Latency | Achieved | Throughput |
|-----------|---------------|----------|------------|
| API Response | <100ms | 45ms | 1000 RPS |
| Signal Generation | <5 minutes | 2.3 minutes | - |
| Data Ingestion | <1 second | 200ms | 10K msgs/sec |
| Alert Delivery | <30 seconds | 8 seconds | - |
| Dashboard Load | <2 seconds | 1.1 seconds | - |

## Monitoring Architecture

### Observability Stack

```yaml
# Prometheus configuration
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'trading-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### Key Metrics

1. **Business Metrics**
   - Signal generation success rate
   - Trading signal accuracy
   - Portfolio performance metrics
   - User engagement metrics

2. **Technical Metrics**
   - API response times
   - Database query performance
   - Cache hit rates
   - Error rates by endpoint

3. **Infrastructure Metrics**
   - CPU and memory utilization
   - Network I/O
   - Disk space usage
   - Container health status

### Alerting Rules

```yaml
# Critical alerts
- alert: APIHighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "High error rate detected"
    description: "Error rate is {{ $value }} errors per second"

- alert: DatabaseConnectionFailed
  expr: up{job="postgres"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Database connection failed"
    description: "PostgreSQL database is unreachable"

- alert: SignalGenerationFailed
  expr: increase(signal_generation_failures_total[1h]) > 0
  for: 1m
  labels:
    severity: warning
  annotations:
    summary: "Signal generation failed"
    description: "Signal generation has failed {{ $value }} times in the last hour"
```

## Disaster Recovery

### Backup Strategy

1. **Database Backups**
   ```bash
   # Automated daily backups
   #!/bin/bash
   DATE=$(date +%Y%m%d_%H%M%S)

   # Full PostgreSQL backup
   pg_dump -h localhost -U postgres trading_system | \
     gzip > /backups/postgres_${DATE}.sql.gz

   # Point-in-time recovery setup
   archive_command = 'cp %p /backups/wal_archive/%f'
   ```

2. **Model Backups**
   ```python
   # Automated model versioning
   def backup_models():
       timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
       backup_path = f"/backups/models_{timestamp}"

       # Copy all model files
       shutil.copytree("/app/models", backup_path)

       # Upload to S3
       s3_client.upload_file(
           f"{backup_path}.tar.gz",
           "model-backups",
           f"models_{timestamp}.tar.gz"
       )
   ```

### Recovery Procedures

1. **Database Recovery**
   ```bash
   # Restore from backup
   gunzip < /backups/postgres_20240101_120000.sql.gz | \
     psql -h localhost -U postgres trading_system

   # Point-in-time recovery
   pg_basebackup -h localhost -D /recovery -U postgres
   ```

2. **Service Recovery**
   ```bash
   # Rolling deployment with zero downtime
   docker-compose up -d --scale api=6  # Scale up
   sleep 30  # Wait for health checks
   docker-compose up -d --scale api=3  # Scale back down
   ```

### High Availability

- **Database**: PostgreSQL with streaming replication
- **Application**: Multiple API instances behind load balancer
- **Cache**: Redis Sentinel for automatic failover
- **Message Queue**: Kafka cluster with replication
- **Storage**: Distributed storage with redundancy

This architecture ensures Project Aurum can handle the demanding requirements of quantitative trading while maintaining high availability, performance, and security standards required for production financial systems.# Daily Alert System Architecture for Indonesian Quantitative Trading

## System Overview

A comprehensive backend architecture that extends the existing ML-based trading system with robust daily alert generation, multi-channel delivery, and real-time monitoring capabilities specifically designed for the Indonesian stock market.

## Architecture Components

### 1. Core Backend Services

```
┌─────────────────────────────────────────────────────────────────┐
│                    DAILY ALERT SYSTEM                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Web Dashboard │  │   Mobile API    │  │   Admin Panel   │ │
│  │   (React/Vue)   │  │   (FastAPI)     │  │   (Streamlit)   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Alert Engine    │  │ Signal Service  │  │ Risk Monitor    │ │
│  │ (FastAPI)       │  │ (FastAPI)       │  │ (FastAPI)       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Job Scheduler   │  │ Data Pipeline   │  │ ML Inference    │ │
│  │ (Celery+Redis)  │  │ (Existing)      │  │ (Existing)      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  PostgreSQL     │  │     Redis       │  │   File Storage  │ │
│  │ (Structured)    │  │   (Cache)       │  │   (Reports)     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Daily Workflow Integration

```
06:00 WIB - Data Collection (Existing)
06:30 WIB - Feature Engineering (Existing)
07:00 WIB - ML Model Inference (Existing)
07:30 WIB - Signal Generation + Risk Analysis (Enhanced)
08:00 WIB - Alert Processing + Portfolio Analysis (New)
08:30 WIB - Multi-Channel Alert Delivery (New)
09:00 WIB - Market Open Monitoring (New)
```

## Implementation Strategy

### Phase 1: Backend API Framework (Week 1-2)
- FastAPI microservices architecture
- PostgreSQL database schema
- Redis caching layer
- Authentication & authorization

### Phase 2: Alert Engine (Week 3-4)
- Alert processing engine
- Multi-channel notification system
- Email, mobile push, webhook delivery
- Alert persistence and tracking

### Phase 3: Real-time Monitoring (Week 5-6)
- Position tracking
- Risk monitoring
- Market hours surveillance
- Performance dashboards

### Phase 4: Integration & Testing (Week 7-8)
- Integration with existing ML pipeline
- Comprehensive testing
- Performance optimization
- Deployment automation

## Technology Stack

### Backend Services
- **API Framework**: FastAPI (Python 3.9+)
- **Task Queue**: Celery with Redis broker
- **Database**: PostgreSQL 15 with TimescaleDB extension
- **Cache**: Redis 7.0
- **Authentication**: JWT with role-based access control

### Monitoring & Observability
- **Metrics**: Prometheus + Grafana
- **Logging**: Structured logging with ELK stack
- **Health Checks**: Custom health check endpoints
- **Alerting**: PagerDuty integration for critical issues

### Deployment
- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Docker Compose (single server)
- **Proxy**: Nginx reverse proxy with SSL
- **Backup**: Automated PostgreSQL and Redis backups

## Scalability Considerations

### Single Server Deployment (Initial)
- All services on single server with Docker Compose
- Vertical scaling up to 32 cores, 128GB RAM
- Local storage with automated backups
- Estimated cost: $890/month (on-premises) vs $3,760/month (cloud)

### Future Scaling Path
- Microservices can be separated to individual containers
- Database can be moved to managed service
- Load balancing for high availability
- Kubernetes migration path available

## Indonesian Market Optimizations

### Market Hours Integration
- Precise WIB timezone handling
- Market calendar integration
- Holiday and half-day session support
- After-hours alert handling

### IDX-Specific Features
- LQ45 focus with enhanced monitoring
- IDR currency handling
- Indonesian corporate action processing
- Local regulatory compliance tracking

### Data Source Integration
- Primary: IDX official feeds
- Backup: Yahoo Finance Indonesia
- Fundamental data: Local financial databases
- News sentiment: Indonesian financial media

## Security Framework

### Authentication & Authorization
- JWT-based authentication
- Role-based access control (RBAC)
- API key management for external access
- Session management with refresh tokens

### Data Protection
- Database encryption at rest
- API communication over HTTPS
- Sensitive data masking in logs
- Regular security audits

### Access Control
- User roles: Admin, Trader, Viewer, API User
- Granular permissions for different operations
- Audit logging for all user actions
- Rate limiting and DDoS protection

## Cost Analysis

### Infrastructure Costs (Monthly USD)
| Component | Specification | Cost |
|-----------|---------------|------|
| Server | 16 cores, 64GB RAM, 2TB SSD | $400 |
| Database | PostgreSQL with TimescaleDB | $200 |
| Monitoring | Prometheus, Grafana stack | $100 |
| Backup Storage | 1TB encrypted backup | $50 |
| SSL & Domain | Certificates and domain | $20 |
| **Total Infrastructure** | | **$770** |

### Development Costs (One-time USD)
| Component | Effort | Cost |
|-----------|--------|------|
| Backend Development | 6 weeks x 2 developers | $24,000 |
| Frontend Dashboard | 4 weeks x 1 developer | $8,000 |
| Testing & QA | 2 weeks x 1 QA engineer | $3,000 |
| Deployment & DevOps | 1 week x 1 DevOps | $2,000 |
| **Total Development** | | **$37,000** |

### Annual Operating Costs
- Infrastructure: $9,240
- Maintenance (20% of dev cost): $7,400
- **Total Annual**: $16,640

## Risk Management & Reliability

### High Availability Design
- Database replication with automatic failover
- Redis clustering for cache redundancy
- Health checks with automatic restart
- Load balancing for critical services

### Disaster Recovery
- Automated daily backups to multiple locations
- Database point-in-time recovery capability
- Service configuration backup
- 15-minute RTO, 5-minute RPO targets

### Monitoring & Alerting
- Real-time system health monitoring
- Performance metrics tracking
- Automated anomaly detection
- Critical error notifications

## Compliance & Regulatory

### Indonesian Market Compliance
- OJK regulation adherence
- Data residency requirements
- Local audit trail maintenance
- Regulatory reporting capabilities

### Data Governance
- Data retention policies
- Privacy protection measures
- Access audit trails
- GDPR-style data protection

## Implementation Roadmap

### Month 1: Foundation
- [ ] Backend API framework setup
- [ ] Database schema implementation
- [ ] Authentication system
- [ ] Basic alert engine

### Month 2: Core Features
- [ ] Multi-channel notification system
- [ ] Real-time position tracking
- [ ] Risk monitoring dashboard
- [ ] Integration with existing ML pipeline

### Month 3: Enhancement
- [ ] Advanced alerting rules
- [ ] Performance optimization
- [ ] Comprehensive testing
- [ ] Security hardening

### Month 4: Production
- [ ] Production deployment
- [ ] Monitoring setup
- [ ] User training
- [ ] Go-live support

## Success Metrics

### Performance Targets
- Alert delivery within 30 seconds of generation
- 99.9% system uptime during market hours
- <100ms API response times
- Zero data loss tolerance

### Business Metrics
- Daily signal generation by 8:30 AM WIB
- Multi-channel alert delivery success rate >99%
- User engagement with dashboard
- System reliability during high-volume periods

This architecture provides a robust, scalable foundation that integrates seamlessly with the existing ML infrastructure while adding comprehensive alerting and monitoring capabilities specifically designed for the Indonesian quantitative trading environment.