# Project Aurum - Indonesian Stock Exchange Data Architecture

## Executive Summary

Project Aurum is a production-ready quantitative trading system designed specifically for the Indonesian Stock Exchange (IDX). This architecture handles 600+ securities with real-time data ingestion, historical storage, and machine learning capabilities while maintaining budget consciousness and high availability.

## 1. Data Source Strategy for Indonesian Market

### Primary Data Sources

#### 1.1 IDX Real-Time Data Feed
- **IDX Market Data Feed (MDF)**: Official real-time market data
  - Connection: Direct TCP/IP connection to IDX
  - Latency: <50ms from exchange
  - Coverage: All 600+ listed securities
  - Cost: ~USD 2,000-5,000/month for full feed
  - Data: Level 1 & Level 2 order book, trades, indices

#### 1.2 Alternative Data Providers
- **Bloomberg API**: Backup and reference data
  - Cost: ~USD 2,000/month per terminal
  - Coverage: IDX securities + global context
  - Usage: Corporate actions, fundamentals

- **Refinitiv (formerly Thomson Reuters)**: Secondary feed
  - Cost: ~USD 1,500/month
  - Usage: Cross-validation and backup

- **Yahoo Finance Indonesia**: Free backup source
  - Limitations: 15-minute delay, limited historical depth
  - Usage: Development and validation only

#### 1.3 Indonesian Market-Specific Sources
- **Bank Indonesia (BI)**: Economic indicators, currency rates
- **Badan Pusat Statistik (BPS)**: Economic statistics
- **OJK (Otoritas Jasa Keuangan)**: Regulatory data
- **IDX Website**: Corporate actions, announcements

### Data Source Reliability Strategy
```
Primary: IDX MDF (99.9% uptime target)
Secondary: Bloomberg/Refinitiv (failover within 5 seconds)
Tertiary: Yahoo Finance (development/validation)
```

## 2. Database Schema Design

### 2.1 PostgreSQL Schema (Master Data & Metadata)

#### Securities Master Table
```sql
CREATE TABLE securities (
    security_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(10) NOT NULL UNIQUE,
    isin_code VARCHAR(12) UNIQUE,
    company_name VARCHAR(255) NOT NULL,
    sector_code VARCHAR(10) REFERENCES sectors(code),
    subsector_code VARCHAR(10) REFERENCES subsectors(code),
    listing_date DATE NOT NULL,
    delisting_date DATE,
    market_type VARCHAR(20) CHECK (market_type IN ('REGULER', 'NEGOSIASI', 'TUNAI')),
    board_type VARCHAR(20) CHECK (board_type IN ('UTAMA', 'PENGEMBANGAN', 'AKSELERASI')),
    lot_size INTEGER DEFAULT 100,
    tick_size DECIMAL(10,2) NOT NULL,
    price_limits JSONB, -- {upper: 35, lower: -35, type: 'percentage'}
    status VARCHAR(20) DEFAULT 'ACTIVE',
    currency VARCHAR(3) DEFAULT 'IDR',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_securities_symbol ON securities(symbol);
CREATE INDEX idx_securities_sector ON securities(sector_code);
CREATE INDEX idx_securities_status ON securities(status);
```

#### Corporate Actions Table
```sql
CREATE TABLE corporate_actions (
    action_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    security_id UUID REFERENCES securities(security_id),
    action_type VARCHAR(50) NOT NULL, -- 'SPLIT', 'DIVIDEND', 'RIGHTS', 'BONUS'
    announcement_date DATE NOT NULL,
    ex_date DATE NOT NULL,
    record_date DATE,
    payment_date DATE,
    adjustment_factor DECIMAL(10,6), -- For splits/bonus issues
    dividend_amount DECIMAL(15,2), -- In IDR
    currency VARCHAR(3) DEFAULT 'IDR',
    details JSONB,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_corporate_actions_security ON corporate_actions(security_id);
CREATE INDEX idx_corporate_actions_ex_date ON corporate_actions(ex_date);
CREATE INDEX idx_corporate_actions_processed ON corporate_actions(processed);
```

#### Market Calendar Table
```sql
CREATE TABLE market_calendar (
    date DATE PRIMARY KEY,
    is_trading_day BOOLEAN NOT NULL,
    market_open TIME DEFAULT '09:00:00',
    market_close TIME DEFAULT '16:00:00',
    pre_market_open TIME DEFAULT '08:45:00',
    post_market_close TIME DEFAULT '16:15:00',
    session_type VARCHAR(20) DEFAULT 'FULL', -- 'FULL', 'HALF', 'CLOSED'
    holiday_name VARCHAR(255),
    timezone VARCHAR(50) DEFAULT 'Asia/Jakarta'
);
```

#### Sectors and Subsectors
```sql
CREATE TABLE sectors (
    code VARCHAR(10) PRIMARY KEY,
    name_id VARCHAR(255) NOT NULL,
    name_en VARCHAR(255) NOT NULL,
    description TEXT
);

CREATE TABLE subsectors (
    code VARCHAR(10) PRIMARY KEY,
    sector_code VARCHAR(10) REFERENCES sectors(code),
    name_id VARCHAR(255) NOT NULL,
    name_en VARCHAR(255) NOT NULL,
    description TEXT
);
```

### 2.2 InfluxDB Schema (Time-Series Data)

#### Real-Time Market Data
```sql
-- Measurement: market_data
-- Tags: symbol, data_type
-- Fields: price, volume, bid, ask, bid_size, ask_size
-- Time: timestamp (nanosecond precision)

CREATE RETENTION POLICY "realtime" ON "market_data" DURATION 7d REPLICATION 1 DEFAULT;
CREATE RETENTION POLICY "daily" ON "market_data" DURATION 365d REPLICATION 1;
CREATE RETENTION POLICY "historical" ON "market_data" DURATION INF REPLICATION 1;

-- Continuous Query for OHLCV aggregation
CREATE CONTINUOUS QUERY "cq_ohlcv_1m" ON "market_data"
BEGIN
  SELECT
    first(price) AS open,
    max(price) AS high,
    min(price) AS low,
    last(price) AS close,
    sum(volume) AS volume,
    count(price) AS trade_count
  INTO "ohlcv_1m"
  FROM "trades"
  GROUP BY time(1m), symbol
END;
```

#### Technical Indicators Storage
```sql
-- Measurement: technical_indicators
-- Tags: symbol, indicator_name, timeframe
-- Fields: value, signal
-- Time: timestamp

CREATE RETENTION POLICY "indicators_daily" ON "technical_indicators" DURATION 730d REPLICATION 1;
```

#### Order Book Data
```sql
-- Measurement: order_book
-- Tags: symbol, side (bid/ask)
-- Fields: price_level_1 through price_level_10, size_level_1 through size_level_10
-- Time: timestamp
```

## 3. Data Pipeline Architecture

### 3.1 Real-Time Ingestion Pipeline

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   IDX MDF       │    │   Data Gateway  │    │   Kafka Topics  │
│   (TCP/IP)      │───▶│   (FastAPI)     │───▶│   - raw_trades  │
│                 │    │                 │    │   - raw_quotes  │
└─────────────────┘    └─────────────────┘    │   - raw_orders  │
                                               └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   InfluxDB      │◀───│  Stream Processor│◀───│  Kafka Consumer │
│   (Time-Series) │    │  (Apache Flink) │    │   (Python)      │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 3.2 Data Gateway Implementation

```python
# data_gateway.py
from fastapi import FastAPI, WebSocket
import asyncio
import socket
import struct
from kafka import KafkaProducer
import json
from datetime import datetime
import pytz

class IDXDataGateway:
    def __init__(self):
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )
        self.jakarta_tz = pytz.timezone('Asia/Jakarta')

    async def connect_to_idx(self):
        """Connect to IDX Market Data Feed"""
        self.idx_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.idx_socket.connect(('idx_feed_host', 9999))  # IDX MDF connection

    async def parse_idx_message(self, raw_message: bytes):
        """Parse IDX binary message format"""
        # IDX-specific message parsing logic
        message_type = struct.unpack('B', raw_message[0:1])[0]

        if message_type == 1:  # Trade message
            return self.parse_trade_message(raw_message)
        elif message_type == 2:  # Quote message
            return self.parse_quote_message(raw_message)
        elif message_type == 3:  # Order book update
            return self.parse_orderbook_message(raw_message)

    def parse_trade_message(self, data: bytes):
        """Parse IDX trade message"""
        # Unpack binary trade data according to IDX specification
        timestamp, symbol, price, volume, side = struct.unpack('Q8sQQB', data[1:42])

        return {
            'message_type': 'trade',
            'timestamp': datetime.fromtimestamp(timestamp/1000000, self.jakarta_tz).isoformat(),
            'symbol': symbol.decode('utf-8').strip(),
            'price': price / 100,  # IDX prices in 1/100 IDR
            'volume': volume,
            'side': 'BUY' if side == 1 else 'SELL',
            'currency': 'IDR'
        }

    async def stream_data(self):
        """Main data streaming loop"""
        while True:
            try:
                raw_data = await self.idx_socket.recv(1024)
                if raw_data:
                    parsed_message = await self.parse_idx_message(raw_data)
                    if parsed_message:
                        # Send to appropriate Kafka topic
                        topic = f"raw_{parsed_message['message_type']}"
                        self.kafka_producer.send(
                            topic,
                            key=parsed_message['symbol'],
                            value=parsed_message
                        )
            except Exception as e:
                # Log error and attempt reconnection
                await self.handle_connection_error(e)
```

### 3.3 Stream Processing (Apache Flink)

```python
# flink_processor.py
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment
from pyflink.table.descriptors import Schema, Kafka, Json

def create_flink_pipeline():
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(4)

    t_env = StreamTableEnvironment.create(env)

    # Define source table (Kafka)
    t_env.execute_sql("""
        CREATE TABLE raw_trades (
            symbol STRING,
            price DOUBLE,
            volume BIGINT,
            trade_time TIMESTAMP(3),
            side STRING,
            WATERMARK FOR trade_time AS trade_time - INTERVAL '5' SECOND
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'raw_trades',
            'properties.bootstrap.servers' = 'localhost:9092',
            'properties.group.id' = 'flink_processor',
            'format' = 'json'
        )
    """)

    # Define sink table (InfluxDB)
    t_env.execute_sql("""
        CREATE TABLE processed_trades (
            symbol STRING,
            price DOUBLE,
            volume BIGINT,
            trade_time TIMESTAMP(3),
            side STRING,
            trade_value DOUBLE
        ) WITH (
            'connector' = 'influxdb',
            'url' = 'http://localhost:8086',
            'database' = 'market_data',
            'measurement' = 'trades'
        )
    """)

    # Process and enrich data
    t_env.execute_sql("""
        INSERT INTO processed_trades
        SELECT
            symbol,
            price,
            volume,
            trade_time,
            side,
            price * volume as trade_value
        FROM raw_trades
        WHERE price > 0 AND volume > 0
    """)
```

## 4. Data Quality Validation Framework

### 4.1 Real-Time Validation Rules

```python
# data_quality.py
from typing import Dict, List, Any
import pandas as pd
from datetime import datetime, time
import pytz

class IDXDataValidator:
    def __init__(self):
        self.jakarta_tz = pytz.timezone('Asia/Jakarta')
        self.market_open = time(9, 0)
        self.market_close = time(16, 0)

    def validate_trade_data(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """Validate individual trade message"""
        errors = []
        warnings = []

        # Price validation
        if trade['price'] <= 0:
            errors.append("Price must be positive")

        if trade['price'] > 1000000:  # 1M IDR per share seems unrealistic
            warnings.append("Unusually high price detected")

        # Volume validation
        if trade['volume'] <= 0:
            errors.append("Volume must be positive")

        if trade['volume'] % 100 != 0:  # IDX lot size is 100
            errors.append("Volume must be multiple of lot size (100)")

        # Market hours validation
        trade_time = datetime.fromisoformat(trade['timestamp']).time()
        if not (self.market_open <= trade_time <= self.market_close):
            warnings.append("Trade outside normal market hours")

        # Symbol validation
        if not self.is_valid_idx_symbol(trade['symbol']):
            errors.append("Invalid IDX symbol format")

        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'trade': trade if len(errors) == 0 else None
        }

    def validate_price_limits(self, symbol: str, price: float, prev_close: float) -> bool:
        """Validate against IDX price limits (35% auto rejection)"""
        upper_limit = prev_close * 1.35
        lower_limit = prev_close * 0.65

        return lower_limit <= price <= upper_limit

    def detect_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect statistical anomalies in price/volume data"""
        # Price spike detection
        df['price_zscore'] = (df['price'] - df['price'].rolling(20).mean()) / df['price'].rolling(20).std()
        df['volume_zscore'] = (df['volume'] - df['volume'].rolling(20).mean()) / df['volume'].rolling(20).std()

        # Flag potential anomalies
        df['price_anomaly'] = abs(df['price_zscore']) > 3
        df['volume_anomaly'] = abs(df['volume_zscore']) > 3

        return df

    def check_data_completeness(self, symbol: str, start_time: datetime, end_time: datetime) -> Dict:
        """Check for missing data gaps"""
        # Query expected vs actual data points
        # This would integrate with your database to check for gaps
        pass
```

### 4.2 Data Quality Monitoring Dashboard

```python
# quality_monitor.py
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta

def create_quality_dashboard():
    st.title("Project Aurum - Data Quality Monitor")

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Data Uptime", "99.94%", "0.02%")
    with col2:
        st.metric("Message Latency", "47ms", "-3ms")
    with col3:
        st.metric("Error Rate", "0.1%", "-0.05%")
    with col4:
        st.metric("Symbols Active", "623", "+2")

    # Data quality alerts
    st.subheader("Active Alerts")
    alerts = [
        {"symbol": "BBCA", "type": "Price Anomaly", "severity": "Medium", "time": "14:23:45"},
        {"symbol": "TLKM", "type": "Volume Spike", "severity": "Low", "time": "14:20:12"}
    ]

    for alert in alerts:
        st.warning(f"⚠️ {alert['symbol']}: {alert['type']} ({alert['severity']}) at {alert['time']}")
```

## 5. Backup and Disaster Recovery Strategy

### 5.1 Data Backup Strategy

#### PostgreSQL Backup
```bash
#!/bin/bash
# daily_pg_backup.sh

# Hot backup using pg_basebackup
pg_basebackup -h localhost -D /backup/postgresql/$(date +%Y%m%d) -U postgres -v -P -W -X stream

# WAL archiving for point-in-time recovery
archive_command = 'cp %p /backup/postgresql/wal_archive/%f'

# Logical backup for specific tables
pg_dump -h localhost -U postgres -t securities -t corporate_actions project_aurum > /backup/logical/$(date +%Y%m%d)_master_data.sql
```

#### InfluxDB Backup
```bash
#!/bin/bash
# influxdb_backup.sh

# Full backup
influxd backup -portable -database market_data /backup/influxdb/$(date +%Y%m%d)

# Incremental backup (last 24 hours)
influxd backup -portable -database market_data -start $(date -d '1 day ago' --iso-8601) /backup/influxdb/incremental/$(date +%Y%m%d)
```

### 5.2 High Availability Setup

#### PostgreSQL HA Configuration
```yaml
# postgresql.yml (Docker Compose)
version: '3.8'
services:
  postgres-primary:
    image: postgres:15
    environment:
      POSTGRES_DB: project_aurum
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_REPLICATION_USER: replicator
      POSTGRES_REPLICATION_PASSWORD: ${REPLICATION_PASSWORD}
    volumes:
      - ./postgresql.conf:/etc/postgresql/postgresql.conf
      - postgres_primary_data:/var/lib/postgresql/data
    command: postgres -c config_file=/etc/postgresql/postgresql.conf

  postgres-replica:
    image: postgres:15
    environment:
      PGUSER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      PGPASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_replica_data:/var/lib/postgresql/data
    command: |
      bash -c "
      until pg_basebackup -h postgres-primary -D /var/lib/postgresql/data -U replicator -v -P -W
      do
        echo 'Waiting for primary to connect...'
        sleep 1s
      done
      echo 'Backup done, starting replica...'
      chmod 0700 /var/lib/postgresql/data
      postgres"
    depends_on:
      - postgres-primary
```

#### InfluxDB Clustering
```yaml
# influxdb-cluster.yml
version: '3.8'
services:
  influxdb-1:
    image: influxdb:2.0
    environment:
      INFLUXDB_DB: market_data
      INFLUXDB_ADMIN_USER: admin
      INFLUXDB_ADMIN_PASSWORD: ${INFLUX_PASSWORD}
    volumes:
      - influxdb1_data:/var/lib/influxdb2

  influxdb-2:
    image: influxdb:2.0
    environment:
      INFLUXDB_DB: market_data
      INFLUXDB_ADMIN_USER: admin
      INFLUXDB_ADMIN_PASSWORD: ${INFLUX_PASSWORD}
    volumes:
      - influxdb2_data:/var/lib/influxdb2
```

### 5.3 Disaster Recovery Procedures

#### Recovery Time Objectives (RTO)
- **Critical Systems**: 15 minutes
- **Market Data Feed**: 5 minutes
- **Historical Data**: 2 hours
- **Analytics Platform**: 1 hour

#### Recovery Point Objectives (RPO)
- **Real-time Data**: 1 minute
- **Master Data**: 15 minutes
- **Analytical Data**: 1 hour

## 6. Performance Optimization Recommendations

### 6.1 Database Optimization

#### PostgreSQL Tuning
```sql
-- postgresql.conf optimizations
shared_buffers = 4GB                    # 25% of available RAM
work_mem = 256MB                        # For complex queries
maintenance_work_mem = 1GB              # For maintenance operations
effective_cache_size = 12GB             # 75% of available RAM
checkpoint_segments = 64                # For write-heavy workloads
wal_buffers = 16MB                      # WAL buffer size
random_page_cost = 1.1                  # For SSD storage

-- Query optimization
CREATE INDEX CONCURRENTLY idx_securities_symbol_status ON securities(symbol, status);
CREATE INDEX CONCURRENTLY idx_corp_actions_security_date ON corporate_actions(security_id, ex_date);

-- Partitioning for large tables
CREATE TABLE corporate_actions (
    action_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    security_id UUID REFERENCES securities(security_id),
    ex_date DATE NOT NULL,
    -- ... other columns
) PARTITION BY RANGE (ex_date);

CREATE TABLE corporate_actions_2024 PARTITION OF corporate_actions
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

#### InfluxDB Optimization
```sql
-- Retention policies for different data granularities
CREATE RETENTION POLICY "realtime" ON "market_data" DURATION 1d REPLICATION 1;
CREATE RETENTION POLICY "minute" ON "market_data" DURATION 30d REPLICATION 1;
CREATE RETENTION POLICY "hourly" ON "market_data" DURATION 365d REPLICATION 1;
CREATE RETENTION POLICY "daily" ON "market_data" DURATION 2555d REPLICATION 1; -- 7 years

-- Continuous queries for downsampling
CREATE CONTINUOUS QUERY "cq_downsample_1h" ON "market_data"
BEGIN
  SELECT mean(price) as price, sum(volume) as volume
  INTO "market_data"."hourly"."ohlcv"
  FROM "market_data"."minute"."ohlcv"
  GROUP BY time(1h), symbol
END;
```

### 6.2 Caching Strategy

#### Redis Configuration
```python
# redis_cache.py
import redis
import json
from typing import Dict, List, Optional
import pickle

class MarketDataCache:
    def __init__(self):
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True,
            max_connections=20
        )

    def cache_latest_prices(self, symbol: str, price_data: Dict):
        """Cache latest price data with 1-minute expiry"""
        key = f"price:latest:{symbol}"
        self.redis_client.setex(key, 60, json.dumps(price_data))

    def cache_ohlcv(self, symbol: str, timeframe: str, data: List[Dict]):
        """Cache OHLCV data with longer expiry"""
        key = f"ohlcv:{symbol}:{timeframe}"
        self.redis_client.setex(key, 300, json.dumps(data))  # 5 minutes

    def get_cached_data(self, key: str) -> Optional[Dict]:
        """Retrieve cached data"""
        data = self.redis_client.get(key)
        return json.loads(data) if data else None

    def cache_technical_indicators(self, symbol: str, indicators: Dict):
        """Cache computed technical indicators"""
        key = f"indicators:{symbol}"
        self.redis_client.setex(key, 300, pickle.dumps(indicators))
```

### 6.3 Query Optimization Patterns

```python
# optimized_queries.py
import asyncio
import asyncpg
from typing import List, Dict

class OptimizedQueries:
    def __init__(self, db_pool):
        self.pool = db_pool

    async def get_latest_prices_batch(self, symbols: List[str]) -> Dict[str, float]:
        """Optimized batch price retrieval"""
        query = """
        WITH latest_prices AS (
            SELECT DISTINCT ON (symbol)
                symbol, price, timestamp
            FROM market_data.trades
            WHERE symbol = ANY($1)
            ORDER BY symbol, timestamp DESC
        )
        SELECT symbol, price FROM latest_prices
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, symbols)
            return {row['symbol']: row['price'] for row in rows}

    async def get_ohlcv_optimized(self, symbol: str, start_date: str, end_date: str):
        """Memory-efficient OHLCV retrieval with streaming"""
        query = """
        SELECT
            date_trunc('minute', timestamp) as minute,
            first(price ORDER BY timestamp) as open,
            max(price) as high,
            min(price) as low,
            last(price ORDER BY timestamp) as close,
            sum(volume) as volume
        FROM market_data.trades
        WHERE symbol = $1
        AND timestamp BETWEEN $2 AND $3
        GROUP BY minute
        ORDER BY minute
        """

        async with self.pool.acquire() as conn:
            async for record in conn.cursor(query, symbol, start_date, end_date):
                yield dict(record)
```

## 7. Cost Estimation

### 7.1 Data Feed Costs (Monthly USD)

| Source | Cost | Coverage | SLA |
|--------|------|----------|-----|
| IDX MDF (Primary) | $3,500 | All IDX securities | 99.9% |
| Bloomberg Terminal | $2,000 | Global + IDX | 99.95% |
| Refinitiv Feed | $1,500 | IDX + Regional | 99.8% |
| **Total Data Feeds** | **$7,000** | | |

### 7.2 Infrastructure Costs (Monthly USD)

#### Cloud Infrastructure (AWS/GCP)
| Component | Specification | Monthly Cost |
|-----------|---------------|--------------|
| Database Server (PostgreSQL) | 16 vCPU, 64GB RAM, 2TB SSD | $800 |
| Time-Series Server (InfluxDB) | 8 vCPU, 32GB RAM, 4TB SSD | $600 |
| Application Servers (3x) | 4 vCPU, 16GB RAM each | $450 |
| Redis Cache | 4 vCPU, 16GB RAM | $200 |
| Kafka Cluster (3 nodes) | 2 vCPU, 8GB RAM each | $300 |
| Load Balancer | ALB with SSL | $50 |
| Data Transfer | 10TB/month | $900 |
| Backup Storage | 20TB S3 | $460 |
| **Total Infrastructure** | | **$3,760** |

#### On-Premises Alternative (Capital Cost)
| Component | Specification | One-time Cost |
|-----------|---------------|---------------|
| Database Server | Dell R750, 32 cores, 128GB RAM, 8TB NVMe | $15,000 |
| Time-Series Server | Dell R650, 16 cores, 64GB RAM, 16TB SSD | $12,000 |
| Network Equipment | Switches, Firewall, UPS | $5,000 |
| **Total Hardware** | | **$32,000** |
| **Monthly Equivalent** (3-year depreciation) | | **$890** |

### 7.3 Total Cost Summary (Monthly USD)

| Category | Cloud | On-Premises |
|----------|-------|-------------|
| Data Feeds | $7,000 | $7,000 |
| Infrastructure | $3,760 | $890 |
| Personnel (2 DevOps) | $8,000 | $8,000 |
| **Total Monthly** | **$18,760** | **$15,890** |
| **Annual Total** | **$225,120** | **$190,680** |

### 7.4 Cost Optimization Strategies

1. **Graduated Data Access**:
   - Free tier: Yahoo Finance (15-min delay)
   - Development: Reduced symbol set from paid feeds
   - Production: Full real-time feeds

2. **Infrastructure Scaling**:
   - Start with smaller instances and auto-scale
   - Use spot instances for non-critical batch processing
   - Implement data lifecycle policies (hot/warm/cold storage)

3. **Alternative Approaches**:
   - Web scraping IDX website (legal compliance required)
   - Partnership with local data vendors
   - Shared data feed costs with other firms

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-4)
- [ ] Set up PostgreSQL with master data schema
- [ ] Implement basic IDX data feed connection
- [ ] Create Kafka message bus
- [ ] Basic data validation framework

### Phase 2: Real-Time Processing (Weeks 5-8)
- [ ] Implement InfluxDB time-series storage
- [ ] Apache Flink stream processing
- [ ] Redis caching layer
- [ ] Data quality monitoring

### Phase 3: Analytics & ML (Weeks 9-12)
- [ ] Technical indicators computation
- [ ] ML model training pipeline
- [ ] Backtesting framework
- [ ] Performance monitoring

### Phase 4: Production Hardening (Weeks 13-16)
- [ ] High availability setup
- [ ] Disaster recovery implementation
- [ ] Security hardening
- [ ] Load testing and optimization

This architecture provides a robust, scalable foundation for Project Aurum that specifically addresses the unique characteristics of the Indonesian Stock Exchange while maintaining cost efficiency and high performance for quantitative trading operations.