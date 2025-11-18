# Project Aurum - Troubleshooting Guide

## Table of Contents

1. [Common Issues](#common-issues)
2. [Installation Problems](#installation-problems)
3. [Database Issues](#database-issues)
4. [API & Backend Issues](#api--backend-issues)
5. [Frontend Issues](#frontend-issues)
6. [ML Model Issues](#ml-model-issues)
7. [Performance Problems](#performance-problems)
8. [Data Feed Issues](#data-feed-issues)
9. [Deployment Issues](#deployment-issues)
10. [Monitoring & Debugging](#monitoring--debugging)

## Common Issues

### System Won't Start

#### Issue: Docker containers fail to start
**Symptoms:**
```bash
ERROR: Service 'postgres' failed to build
ERROR: for postgres  Cannot start service postgres: driver failed
```

**Solutions:**
1. **Check Docker daemon:**
   ```bash
   # Linux/macOS
   sudo systemctl status docker
   sudo systemctl start docker

   # Windows
   # Start Docker Desktop application
   ```

2. **Clean Docker environment:**
   ```bash
   docker system prune -a
   docker volume prune
   docker-compose down -v
   docker-compose up --build
   ```

3. **Check port conflicts:**
   ```bash
   # Check if ports are in use
   netstat -tulpn | grep 5432  # PostgreSQL
   netstat -tulpn | grep 6379  # Redis
   netstat -tulpn | grep 8000  # API
   netstat -tulpn | grep 3000  # Frontend

   # Kill processes using ports
   sudo kill -9 $(sudo lsof -t -i:5432)
   ```

#### Issue: Environment variables not loaded
**Symptoms:**
- Configuration errors on startup
- Database connection failures
- Missing API keys

**Solutions:**
1. **Verify .env file:**
   ```bash
   # Check if .env exists and has correct format
   ls -la .env
   cat .env | grep -v "^#" | grep "="

   # Copy from template if missing
   cp .env.example .env
   ```

2. **Check environment variable syntax:**
   ```bash
   # Incorrect (spaces around =)
   DB_PASSWORD = mypassword

   # Correct (no spaces)
   DB_PASSWORD=mypassword
   ```

3. **Validate required variables:**
   ```python
   # Check in Python
   import os
   required_vars = ['DB_PASSWORD', 'JWT_SECRET_KEY', 'REDIS_HOST']
   missing = [var for var in required_vars if not os.getenv(var)]
   if missing:
       print(f"Missing environment variables: {missing}")
   ```

### Authentication Issues

#### Issue: JWT token errors
**Symptoms:**
```json
{
  "error": "Invalid token",
  "code": "TOKEN_INVALID"
}
```

**Solutions:**
1. **Check token expiration:**
   ```bash
   # Decode JWT token (using jwt.io or python-jwt)
   python -c "
   import jwt
   token = 'your_token_here'
   decoded = jwt.decode(token, options={'verify_signature': False})
   print(decoded)
   "
   ```

2. **Regenerate tokens:**
   ```bash
   # Login again to get fresh token
   curl -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "your_username", "password": "your_password"}'
   ```

3. **Check JWT secret key:**
   ```python
   # Ensure JWT_SECRET_KEY is consistent
   import os
   secret = os.getenv('JWT_SECRET_KEY')
   if not secret or len(secret) < 32:
       print("JWT secret key is missing or too short")
   ```

## Installation Problems

### Python Environment Issues

#### Issue: Package installation failures
**Symptoms:**
```bash
ERROR: Could not install packages due to an EnvironmentError
ModuleNotFoundError: No module named 'xyz'
```

**Solutions:**
1. **Verify Python version:**
   ```bash
   python --version  # Should be 3.9+
   which python

   # If using wrong version
   python3.9 -m venv venv
   source venv/bin/activate
   ```

2. **Refresh tooling and resolve dependency drift:**
   ```bash
   uv pip install --upgrade pip setuptools wheel
   uv sync --refresh
   ```

3. **Handle dependency conflicts:**
   ```bash
   # Recreate environment
   rm -rf .venv
   uv venv
   uv sync

   # Install pinned versions when required
   uv pip install pandas==1.5.3 numpy==1.24.3
   ```

4. **Platform-specific issues:**
   ```bash
   # macOS with M1/M2 chips
   export ARCHFLAGS="-arch arm64"
   uv pip install --force-reinstall .

   # Windows with Visual Studio Build Tools
   uv pip install --only-binary=all .
   ```

### Node.js Environment Issues

#### Issue: npm install failures
**Symptoms:**
```bash
npm ERR! code ERESOLVE
npm ERR! ERESOLVE unable to resolve dependency tree
```

**Solutions:**
1. **Clear npm cache:**
   ```bash
   npm cache clean --force
   rm -rf node_modules package-lock.json
   npm install
   ```

2. **Use specific Node.js version:**
   ```bash
   # Using nvm
   nvm install 18
   nvm use 18
   npm install

   # Or specify engine in package.json
   "engines": {
     "node": ">=18.0.0",
     "npm": ">=8.0.0"
   }
   ```

3. **Resolve dependency conflicts:**
   ```bash
   # Force resolution
   npm install --legacy-peer-deps

   # Or update package.json with resolutions
   "overrides": {
     "some-package": "^2.0.0"
   }
   ```

## Database Issues

### PostgreSQL Connection Problems

#### Issue: Database connection refused
**Symptoms:**
```
psycopg2.OperationalError: could not connect to server: Connection refused
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) connection refused
```

**Solutions:**
1. **Check PostgreSQL service:**
   ```bash
   # Check if PostgreSQL is running
   docker ps | grep postgres

   # Start PostgreSQL container
   docker-compose up postgres -d

   # Check logs
   docker-compose logs postgres
   ```

2. **Verify connection parameters:**
   ```python
   import psycopg2
   try:
       conn = psycopg2.connect(
           host="localhost",
           port=5432,
           database="trading_system",
           user="postgres",
           password="your_password"
       )
       print("Connection successful")
   except Exception as e:
       print(f"Connection failed: {e}")
   ```

3. **Test with psql:**
   ```bash
   # Test connection directly
   psql -h localhost -p 5432 -U postgres -d trading_system

   # If connection works but app doesn't, check network
   docker network ls
   docker network inspect project-aurum_trading_network
   ```

#### Issue: Database schema errors
**Symptoms:**
```
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
```

**Solutions:**
1. **Run database migrations:**
   ```bash
   # Check migration status
   alembic current
   alembic history --verbose

   # Run migrations
   alembic upgrade head

   # If migrations fail, reset database
   make db-reset
   ```

2. **Check database schema:**
   ```sql
   -- Connect to database and check tables
   \dt
   \d signals  -- Describe signals table

   -- Check for missing columns
   SELECT column_name, data_type
   FROM information_schema.columns
   WHERE table_name = 'signals';
   ```

3. **Manual schema fix:**
   ```sql
   -- Create missing table
   CREATE TABLE IF NOT EXISTS signals (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       symbol VARCHAR(20) NOT NULL,
       signal_date DATE NOT NULL,
       signal_type VARCHAR(10) NOT NULL,
       created_at TIMESTAMP DEFAULT NOW()
   );
   ```

### Redis Connection Issues

#### Issue: Redis connection timeout
**Symptoms:**
```
redis.exceptions.TimeoutError: Timeout reading from socket
redis.exceptions.ConnectionError: Error connecting to Redis
```

**Solutions:**
1. **Check Redis service:**
   ```bash
   # Test Redis connection
   docker exec -it redis-container redis-cli ping

   # Check Redis logs
   docker-compose logs redis

   # Restart Redis
   docker-compose restart redis
   ```

2. **Test Redis operations:**
   ```python
   import redis
   try:
       r = redis.Redis(host='localhost', port=6379, db=0, socket_timeout=5)
       r.ping()
       print("Redis connection successful")

       # Test basic operations
       r.set('test_key', 'test_value')
       value = r.get('test_key')
       print(f"Retrieved value: {value}")
   except Exception as e:
       print(f"Redis error: {e}")
   ```

3. **Adjust Redis configuration:**
   ```bash
   # Check Redis memory usage
   docker exec redis-container redis-cli info memory

   # Increase memory limit if needed
   docker exec redis-container redis-cli config set maxmemory 1gb
   ```

## API & Backend Issues

### FastAPI Server Problems

#### Issue: Server won't start or crashes
**Symptoms:**
```bash
ImportError: No module named 'src'
AttributeError: module 'src.api.main' has no attribute 'app'
```

**Solutions:**
1. **Check Python path:**
   ```bash
   # Ensure project root is in Python path
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"

   # Or install package in development mode
   uv pip install --editable .
   ```

2. **Verify imports:**
   ```python
   # Test imports manually
   python -c "from src.api.main import app; print('Import successful')"

   # Check for circular imports
   python -c "import src.api.main"
   ```

3. **Start with debug mode:**
   ```bash
   # Start with detailed error output
   uvicorn src.api.main:app --reload --log-level debug --host 0.0.0.0

   # Check for configuration issues
   python -c "
   from src.api.config import settings
   print(settings.dict())
   "
   ```

#### Issue: API endpoint errors
**Symptoms:**
```json
{
  "detail": "Internal Server Error"
}
```

**Solutions:**
1. **Check API logs:**
   ```bash
   # View API logs
   docker-compose logs api

   # Follow logs in real-time
   docker-compose logs -f api

   # Check specific error patterns
   docker-compose logs api | grep ERROR
   ```

2. **Test endpoint directly:**
   ```bash
   # Test health endpoint
   curl -v http://localhost:8000/health

   # Test with authentication
   curl -H "Authorization: Bearer your_token" http://localhost:8000/signals/daily

   # Test with invalid data
   curl -X POST http://localhost:8000/signals/generate \
     -H "Content-Type: application/json" \
     -d '{"invalid": "data"}'
   ```

3. **Debug with Python:**
   ```python
   import requests
   import logging

   # Enable debug logging
   logging.basicConfig(level=logging.DEBUG)

   # Test API call
   try:
       response = requests.get('http://localhost:8000/health')
       print(f"Status: {response.status_code}")
       print(f"Response: {response.text}")
   except Exception as e:
       print(f"Request failed: {e}")
   ```

### Background Task Issues

#### Issue: Celery workers not processing tasks
**Symptoms:**
- Tasks stuck in PENDING state
- No signal generation happening
- Background tasks timing out

**Solutions:**
1. **Check Celery worker status:**
   ```bash
   # Check worker logs
   docker-compose logs celery_worker

   # Check if workers are active
   docker-compose exec celery_worker celery -A src.api.main:celery_app inspect active

   # Check task queue
   docker-compose exec celery_worker celery -A src.api.main:celery_app inspect reserved
   ```

2. **Restart Celery workers:**
   ```bash
   # Restart workers
   docker-compose restart celery_worker celery_beat

   # Scale workers if needed
   docker-compose up --scale celery_worker=3
   ```

3. **Monitor task execution:**
   ```python
   from celery import Celery

   app = Celery('project-aurum')

   # Check worker status
   inspect = app.control.inspect()
   print("Active workers:", inspect.active_queues())
   print("Reserved tasks:", inspect.reserved())
   print("Worker stats:", inspect.stats())
   ```

## Frontend Issues

### React Development Server Problems

#### Issue: Frontend won't start
**Symptoms:**
```bash
Error: Cannot find module 'react-scripts'
Module not found: Can't resolve 'src/components/Dashboard'
```

**Solutions:**
1. **Reinstall dependencies:**
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   npm start
   ```

2. **Check Node.js version:**
   ```bash
   node --version  # Should be 18+
   npm --version   # Should be 8+

   # Update if needed
   nvm install 18
   nvm use 18
   ```

3. **Fix module resolution:**
   ```bash
   # Clear cache
   npm start -- --reset-cache

   # Or delete cache manually
   rm -rf node_modules/.cache
   ```

#### Issue: TypeScript compilation errors
**Symptoms:**
```bash
TypeScript error in src/components/Dashboard.tsx(25,10):
Property 'signals' does not exist on type 'Props'
```

**Solutions:**
1. **Check TypeScript configuration:**
   ```json
   // tsconfig.json
   {
     "compilerOptions": {
       "strict": true,
       "noImplicitAny": true,
       "skipLibCheck": true
     }
   }
   ```

2. **Fix type definitions:**
   ```typescript
   // Define proper interfaces
   interface Props {
     signals: Signal[];
     onSignalSelect: (signal: Signal) => void;
   }

   interface Signal {
     symbol: string;
     signal: 'BUY' | 'SELL' | 'HOLD';
     strength: number;
   }
   ```

3. **Update type dependencies:**
   ```bash
   npm install --save-dev @types/react @types/node
   npm run type-check
   ```

### Build and Bundle Issues

#### Issue: Production build failures
**Symptoms:**
```bash
FATAL ERROR: Ineffective mark-compacts near heap limit
Module not found: Error: Can't resolve './config'
```

**Solutions:**
1. **Increase memory limit:**
   ```bash
   # Increase Node.js memory
   export NODE_OPTIONS="--max-old-space-size=4096"
   npm run build

   # Or in package.json
   "scripts": {
     "build": "NODE_OPTIONS=--max-old-space-size=4096 react-scripts build"
   }
   ```

2. **Check bundle size:**
   ```bash
   # Analyze bundle
   npm install --save-dev webpack-bundle-analyzer
   npx webpack-bundle-analyzer build/static/js/*.js

   # Optimize imports
   import { Button } from '@mui/material/Button'  # Specific import
   // instead of
   import { Button } from '@mui/material'         # Entire library
   ```

3. **Fix missing dependencies:**
   ```bash
   # Check for missing dependencies
   npm ls
   npm audit fix

   # Install missing peer dependencies
   npm install --save-dev @types/react-router-dom
   ```

## ML Model Issues

### Model Training Problems

#### Issue: Training data errors
**Symptoms:**
```python
ValueError: Input contains NaN, infinity or a value too large
sklearn.exceptions.DataConversionWarning: A column-vector y was passed
```

**Solutions:**
1. **Check data quality:**
   ```python
   import pandas as pd
   import numpy as np

   # Check for NaN values
   print("NaN count:", df.isnull().sum())

   # Check for infinite values
   print("Infinite values:", np.isinf(df.select_dtypes(include=[np.number])).sum())

   # Check data types
   print("Data types:", df.dtypes)

   # Clean data
   df = df.dropna()
   df = df.replace([np.inf, -np.inf], np.nan).dropna()
   ```

2. **Validate feature dimensions:**
   ```python
   # Check feature matrix shape
   print(f"X shape: {X.shape}")
   print(f"y shape: {y.shape}")

   # Ensure consistent samples
   assert X.shape[0] == y.shape[0], "Sample count mismatch"

   # Reshape target if needed
   if y.ndim > 1 and y.shape[1] == 1:
       y = y.ravel()
   ```

3. **Debug model training:**
   ```python
   from sklearn.model_selection import train_test_split
   from sklearn.preprocessing import StandardScaler

   # Split data
   X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

   # Scale features
   scaler = StandardScaler()
   X_train_scaled = scaler.fit_transform(X_train)
   X_test_scaled = scaler.transform(X_test)

   # Train with error handling
   try:
       model.fit(X_train_scaled, y_train)
       print("Training successful")
   except Exception as e:
       print(f"Training failed: {e}")
   ```

#### Issue: Model prediction errors
**Symptoms:**
```python
ValueError: X has 45 features, but model was trained with 50 features
pickle.UnpicklingError: could not find MARK
```

**Solutions:**
1. **Check feature consistency:**
   ```python
   # Save feature names during training
   import joblib

   # During training
   feature_names = ['feature1', 'feature2', ...]
   joblib.dump({'model': model, 'features': feature_names}, 'model.pkl')

   # During prediction
   saved_data = joblib.load('model.pkl')
   model = saved_data['model']
   expected_features = saved_data['features']

   # Validate features
   if list(X.columns) != expected_features:
       print(f"Feature mismatch: expected {expected_features}, got {list(X.columns)}")
   ```

2. **Handle model loading errors:**
   ```python
   import joblib
   import pickle

   try:
       # Try joblib first
       model = joblib.load('model.pkl')
   except Exception as e:
       print(f"Joblib loading failed: {e}")
       try:
           # Fallback to pickle
           with open('model.pkl', 'rb') as f:
               model = pickle.load(f)
       except Exception as e2:
           print(f"Pickle loading also failed: {e2}")
   ```

3. **Model version compatibility:**
   ```python
   # Check library versions
   import sklearn
   import xgboost
   print(f"Scikit-learn version: {sklearn.__version__}")
   print(f"XGBoost version: {xgboost.__version__}")

   # Save with version info
   model_info = {
       'model': model,
       'sklearn_version': sklearn.__version__,
       'xgboost_version': xgboost.__version__,
       'created_at': datetime.now()
   }
   joblib.dump(model_info, 'model_with_version.pkl')
   ```

## Performance Problems

### Slow API Response Times

#### Issue: API endpoints taking too long
**Symptoms:**
- Response times > 5 seconds
- Timeout errors
- High server load

**Solutions:**
1. **Profile API endpoints:**
   ```python
   import time
   from functools import wraps

   def profile_endpoint(func):
       @wraps(func)
       async def wrapper(*args, **kwargs):
           start_time = time.time()
           result = await func(*args, **kwargs)
           end_time = time.time()
           print(f"{func.__name__} took {end_time - start_time:.2f} seconds")
           return result
       return wrapper

   @profile_endpoint
   async def get_daily_signals():
       # Endpoint implementation
       pass
   ```

2. **Optimize database queries:**
   ```python
   # Use query profiling
   import logging
   logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

   # Add indexes for frequent queries
   CREATE INDEX idx_signals_date_symbol ON signals(signal_date, symbol);
   CREATE INDEX idx_positions_user_symbol ON positions(user_id, symbol);

   # Use eager loading to avoid N+1 queries
   signals = session.query(Signal).options(
       joinedload(Signal.security)
   ).filter(Signal.signal_date == today).all()
   ```

3. **Implement caching:**
   ```python
   import redis
   import json
   from functools import wraps

   redis_client = redis.Redis(host='localhost', port=6379, db=0)

   def cache_result(expiry=300):
       def decorator(func):
           @wraps(func)
           async def wrapper(*args, **kwargs):
               cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

               # Try to get from cache
               cached_result = redis_client.get(cache_key)
               if cached_result:
                   return json.loads(cached_result)

               # Compute and cache result
               result = await func(*args, **kwargs)
               redis_client.setex(cache_key, expiry, json.dumps(result))
               return result
           return wrapper
       return decorator

   @cache_result(expiry=600)  # Cache for 10 minutes
   async def get_portfolio_summary():
       # Expensive computation
       pass
   ```

### Memory Usage Issues

#### Issue: High memory consumption
**Symptoms:**
- Out of memory errors
- Slow garbage collection
- System becoming unresponsive

**Solutions:**
1. **Profile memory usage:**
   ```python
   import psutil
   import tracemalloc

   # Monitor process memory
   process = psutil.Process()
   print(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")

   # Use tracemalloc for detailed analysis
   tracemalloc.start()

   # Your code here

   current, peak = tracemalloc.get_traced_memory()
   print(f"Current memory usage: {current / 1024 / 1024:.2f} MB")
   print(f"Peak memory usage: {peak / 1024 / 1024:.2f} MB")
   tracemalloc.stop()
   ```

2. **Optimize data loading:**
   ```python
   # Process data in chunks
   def process_large_dataset(file_path, chunk_size=10000):
       for chunk in pd.read_csv(file_path, chunksize=chunk_size):
           # Process chunk
           processed_chunk = process_data(chunk)
           yield processed_chunk

   # Use generators instead of lists
   def get_signals_generator():
       for signal in query.yield_per(1000):
           yield process_signal(signal)

   # Instead of loading all at once
   # signals = [process_signal(s) for s in query.all()]  # Bad
   ```

3. **Implement memory limits:**
   ```python
   import resource

   # Set memory limit (in bytes)
   resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 * 1024 * 1024, -1))  # 2GB

   # Monitor and cleanup
   import gc

   def cleanup_memory():
       gc.collect()
       print(f"Memory after cleanup: {process.memory_info().rss / 1024 / 1024:.2f} MB")
   ```

## Data Feed Issues

### Market Data Connection Problems

#### Issue: Data feed disconnections
**Symptoms:**
- Missing price updates
- Stale data warnings
- Connection timeout errors

**Solutions:**
1. **Implement connection monitoring:**
   ```python
   import asyncio
   import websocket

   class DataFeedMonitor:
       def __init__(self):
           self.last_heartbeat = None
           self.reconnect_attempts = 0
           self.max_reconnect_attempts = 5

       async def monitor_connection(self):
           while True:
               if self.is_connection_stale():
                   await self.reconnect()
               await asyncio.sleep(30)  # Check every 30 seconds

       def is_connection_stale(self):
           if not self.last_heartbeat:
               return True
           return (datetime.now() - self.last_heartbeat).seconds > 60

       async def reconnect(self):
           if self.reconnect_attempts < self.max_reconnect_attempts:
               self.reconnect_attempts += 1
               await self.establish_connection()
           else:
               # Switch to backup data source
               await self.switch_to_backup()
   ```

2. **Validate data quality:**
   ```python
   def validate_market_data(data):
       issues = []

       # Check for missing required fields
       required_fields = ['symbol', 'price', 'volume', 'timestamp']
       for field in required_fields:
           if field not in data or data[field] is None:
               issues.append(f"Missing {field}")

       # Check for reasonable price values
       if 'price' in data and (data['price'] <= 0 or data['price'] > 1000000):
           issues.append(f"Unrealistic price: {data['price']}")

       # Check timestamp freshness
       if 'timestamp' in data:
           age = datetime.now() - data['timestamp']
           if age.seconds > 300:  # 5 minutes
               issues.append(f"Stale data: {age.seconds} seconds old")

       return issues
   ```

3. **Implement fallback data sources:**
   ```python
   class DataSourceManager:
       def __init__(self):
           self.primary_source = IDXDataFeed()
           self.backup_sources = [
               YahooFinanceAPI(),
               AlphaVantageAPI()
           ]
           self.current_source = self.primary_source

       async def get_market_data(self, symbol):
           try:
               return await self.current_source.get_data(symbol)
           except Exception as e:
               print(f"Primary source failed: {e}")
               return await self.try_backup_sources(symbol)

       async def try_backup_sources(self, symbol):
           for source in self.backup_sources:
               try:
                   data = await source.get_data(symbol)
                   if self.validate_data(data):
                       return data
               except Exception as e:
                   print(f"Backup source {source} failed: {e}")

           raise Exception("All data sources failed")
   ```

## Deployment Issues

### Docker Deployment Problems

#### Issue: Container startup failures
**Symptoms:**
```bash
docker: Error response from daemon: driver failed programming external connectivity
ERROR: for api  Cannot start service api: driver failed
```

**Solutions:**
1. **Check Docker resources:**
   ```bash
   # Check Docker system info
   docker system df
   docker system events

   # Clean up resources
   docker system prune -a
   docker volume prune

   # Check available disk space
   df -h
   ```

2. **Debug container startup:**
   ```bash
   # Run container with debug output
   docker run -it --rm project-aurum:latest /bin/bash

   # Check container logs
   docker logs container_name

   # Inspect container configuration
   docker inspect container_name
   ```

3. **Fix networking issues:**
   ```bash
   # Check Docker networks
   docker network ls
   docker network inspect bridge

   # Recreate network if needed
   docker network rm project-aurum_trading_network
   docker-compose up --force-recreate
   ```

### Production Deployment Issues

#### Issue: SSL/TLS certificate problems
**Symptoms:**
```bash
SSL: CERTIFICATE_VERIFY_FAILED
curl: (60) SSL certificate problem: unable to get local issuer certificate
```

**Solutions:**
1. **Check certificate validity:**
   ```bash
   # Test SSL certificate
   openssl s_client -connect yourdomain.com:443 -servername yourdomain.com

   # Check certificate expiration
   echo | openssl s_client -connect yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates
   ```

2. **Renew Let's Encrypt certificates:**
   ```bash
   # Renew certificate
   certbot renew --dry-run
   certbot renew

   # Manual renewal if needed
   certbot certonly --manual -d yourdomain.com
   ```

3. **Update Nginx configuration:**
   ```nginx
   server {
       listen 443 ssl http2;
       server_name yourdomain.com;

       ssl_certificate /etc/nginx/ssl/cert.pem;
       ssl_certificate_key /etc/nginx/ssl/key.pem;
       ssl_protocols TLSv1.2 TLSv1.3;
       ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;

       location / {
           proxy_pass http://api:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

## Monitoring & Debugging

### Log Analysis

#### Centralized Logging
```bash
# View all service logs
docker-compose logs

# Filter by service
docker-compose logs api | grep ERROR
docker-compose logs postgres | grep FATAL

# Follow logs in real-time
docker-compose logs -f --tail=100

# Search logs with context
grep -B 5 -A 5 "error_pattern" /var/log/app.log
```

#### Application Logging
```python
import logging
import sys
from datetime import datetime

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Add correlation IDs for request tracing
import uuid
from contextvars import ContextVar

request_id: ContextVar[str] = ContextVar('request_id')

class RequestIDFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id.get('unknown')
        return True

logger.addFilter(RequestIDFilter())
```

### Performance Monitoring

#### Application Metrics
```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Define metrics
REQUEST_COUNT = Counter('requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('request_duration_seconds', 'Request latency')
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Active database connections')

# Instrument code
@REQUEST_LATENCY.time()
def process_request():
    REQUEST_COUNT.labels(method='GET', endpoint='/signals').inc()
    # Process request

# Start metrics server
start_http_server(8090)
```

#### Health Checks
```python
async def comprehensive_health_check():
    health_status = {"status": "healthy", "checks": {}}

    # Database check
    try:
        await database.execute("SELECT 1")
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        health_status["checks"]["database"] = f"unhealthy: {e}"
        health_status["status"] = "degraded"

    # Redis check
    try:
        await redis.ping()
        health_status["checks"]["redis"] = "healthy"
    except Exception as e:
        health_status["checks"]["redis"] = f"unhealthy: {e}"
        health_status["status"] = "degraded"

    # External API check
    try:
        # Test external data source
        response = await external_api.health_check()
        health_status["checks"]["data_source"] = "healthy"
    except Exception as e:
        health_status["checks"]["data_source"] = f"unhealthy: {e}"
        health_status["status"] = "degraded"

    return health_status
```

### Emergency Procedures

#### System Recovery
```bash
#!/bin/bash
# emergency_recovery.sh

echo "Starting emergency recovery procedure..."

# 1. Stop all services
docker-compose down

# 2. Backup current state
mkdir -p /backup/emergency/$(date +%Y%m%d_%H%M%S)
docker-compose exec postgres pg_dump -U postgres trading_system > /backup/emergency/$(date +%Y%m%d_%H%M%S)/database.sql

# 3. Clean up resources
docker system prune -f
docker volume prune -f

# 4. Restore from last known good state
docker-compose pull
docker-compose up --build -d

# 5. Wait for services to be ready
sleep 30

# 6. Run health checks
curl -f http://localhost:8000/health || exit 1

echo "Recovery completed successfully"
```

#### Rollback Procedure
```bash
#!/bin/bash
# rollback.sh

VERSION=${1:-previous}

echo "Rolling back to version: $VERSION"

# 1. Stop current services
docker-compose down

# 2. Switch to previous version
git checkout $VERSION
docker-compose pull

# 3. Restore database if needed
if [ "$2" == "--restore-db" ]; then
    docker-compose exec postgres psql -U postgres -d trading_system < /backup/pre_deployment.sql
fi

# 4. Start services
docker-compose up -d

echo "Rollback completed"
```

This comprehensive troubleshooting guide covers the most common issues developers and operators will encounter when working with Project Aurum, providing practical solutions and debugging techniques for each scenario.
