# Indonesian Quantitative Trading Alert System - Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the Indonesian Quantitative Trading Alert System in production environments. The system is designed for reliable, scalable operation with comprehensive monitoring and alerting capabilities.

## System Requirements

### Minimum Hardware Requirements
- **CPU**: 8 cores (16 vCPU recommended)
- **Memory**: 32GB RAM (64GB recommended)
- **Storage**: 1TB SSD (2TB recommended)
- **Network**: 1Gbps connection with low latency to IDX

### Software Requirements
- **Operating System**: Ubuntu 20.04 LTS or CentOS 8+
- **Docker**: 24.0+ with Docker Compose v2
- **Git**: For source code management
- **SSL Certificates**: For production HTTPS

## Pre-Deployment Setup

### 1. Server Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y \
    docker.io \
    docker-compose \
    git \
    curl \
    wget \
    htop \
    nginx \
    certbot \
    python3-certbot-nginx

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Create application directories
sudo mkdir -p /opt/trading-system
sudo chown $USER:$USER /opt/trading-system
```

### 2. Clone Repository

```bash
cd /opt/trading-system
git clone https://github.com/yourcompany/project-aurum.git
cd project-aurum
```

### 3. Environment Configuration

```bash
# Copy and customize environment file
cp .env.example .env

# Edit environment variables
nano .env
```

#### Critical Environment Variables

```bash
# Security
JWT_SECRET_KEY="your-super-secret-256-bit-key-here"
DB_PASSWORD="secure-database-password"
REDIS_PASSWORD="secure-redis-password"

# Email Configuration (Production SMTP)
EMAIL_ENABLED=true
EMAIL_CONFIG='{"server":"smtp.yourcompany.com","port":587,"username":"alerts@yourcompany.com","password":"smtp_password","from_email":"Trading Alerts <alerts@yourcompany.com>"}'
DEFAULT_EMAIL_RECIPIENTS="trader1@company.com,trader2@company.com"

# Telegram Configuration
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
DEFAULT_TELEGRAM_CHATS="chat_id_1,chat_id_2"

# Data Sources
IDX_API_KEY="your_idx_api_key"
ALPHA_VANTAGE_API_KEY="your_alpha_vantage_key"

# Production Settings
ENVIRONMENT=production
DEBUG=false
ALLOWED_ORIGINS="https://trading.yourcompany.com"
```

### 4. SSL Certificate Setup (Production)

```bash
# Install SSL certificate with Let's Encrypt
sudo certbot --nginx -d trading.yourcompany.com

# Or copy existing certificates
sudo mkdir -p /etc/nginx/ssl
sudo cp your-cert.crt /etc/nginx/ssl/
sudo cp your-private.key /etc/nginx/ssl/
```

## Deployment Methods

### Method 1: Docker Compose (Recommended)

#### Production Deployment

```bash
# Set production environment
export ENVIRONMENT=production

# Create required directories
mkdir -p data logs models reports backups

# Download pre-trained models (if available)
wget -O models/idx_quant_model.pkl "https://models.yourcompany.com/idx_quant_model.pkl"

# Start services
docker-compose -f docker-compose.yml up -d

# Verify deployment
docker-compose ps
docker-compose logs -f api
```

#### Development Deployment

```bash
# Set development environment
export ENVIRONMENT=development

# Start development services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Access development services
# API: http://localhost:8000
# Grafana: http://localhost:3000
# Prometheus: http://localhost:9090
```

### Method 2: Manual Installation

#### Database Setup

```bash
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE trading_system;
CREATE USER trading_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE trading_system TO trading_user;
\q
EOF

# Initialize database schema
PGPASSWORD=secure_password psql -h localhost -U trading_user -d trading_system -f sql/init/01_create_tables.sql
```

#### Redis Setup

```bash
# Install Redis
sudo apt install -y redis-server

# Configure Redis
sudo nano /etc/redis/redis.conf
# Add: requirepass your_redis_password

# Restart Redis
sudo systemctl restart redis-server
```

#### Application Setup

```bash
# Install Python dependencies with uv
uv sync

# Run database migrations
uv run alembic upgrade head

# Start application
uv run gunicorn src.api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Post-Deployment Configuration

### 1. Create Admin User

```bash
# Using Docker Compose
docker-compose exec api python -c "
from src.api.auth import AuthManager
import asyncio

async def create_admin():
    auth = AuthManager()
    user = await auth.create_user(
        username='admin',
        email='admin@yourcompany.com',
        password='secure_admin_password',
        role='admin'
    )
    print(f'Admin user created: {user}')

asyncio.run(create_admin())
"
```

### 2. Load Initial Data

```bash
# Load LQ45 stock list
docker-compose exec api python scripts/load_stock_data.py

# Initialize risk limits
docker-compose exec api python scripts/init_risk_limits.py

# Load market calendar
docker-compose exec api python scripts/load_market_calendar.py
```

### 3. Configure Monitoring

#### Grafana Setup

1. Access Grafana at `http://localhost:3000`
2. Login with admin/admin123 (change password)
3. Import dashboard from `monitoring/grafana/dashboards/`
4. Configure data sources (Prometheus, PostgreSQL)

#### Prometheus Configuration

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'trading-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
```

### 4. Schedule Backup

```bash
# Create backup script
cat > /opt/trading-system/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/trading-system/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
docker-compose exec -T postgres pg_dump -U trading_user trading_system > "$BACKUP_DIR/db_backup_$DATE.sql"

# Models backup
tar -czf "$BACKUP_DIR/models_backup_$DATE.tar.gz" models/

# Clean old backups (keep 30 days)
find "$BACKUP_DIR" -name "*backup*" -mtime +30 -delete

echo "Backup completed: $DATE"
EOF

chmod +x /opt/trading-system/backup.sh

# Add to crontab
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/trading-system/backup.sh") | crontab -
```

## Monitoring and Maintenance

### Health Checks

```bash
# Check service health
curl -f http://localhost:8000/health

# Check detailed health
curl http://localhost:8000/health/detailed

# Check Docker services
docker-compose ps
docker-compose logs api
```

### Performance Monitoring

1. **Application Metrics**: Available at `/metrics` endpoint
2. **Grafana Dashboards**: System, API, and Trading metrics
3. **Log Analysis**: ELK stack for centralized logging
4. **Alert Manager**: Prometheus alerts for critical issues

### Maintenance Tasks

#### Daily Tasks
- Monitor signal generation completion
- Check for failed alerts
- Review system performance metrics
- Verify backup completion

#### Weekly Tasks
- Review model performance
- Update risk limits if needed
- Check for system updates
- Review and acknowledge alerts

#### Monthly Tasks
- Rotate logs and clean up old files
- Review and optimize database performance
- Update dependencies and security patches
- Conduct disaster recovery testing

## Scaling Considerations

### Horizontal Scaling

```yaml
# docker-compose.scale.yml
version: '3.8'
services:
  api:
    deploy:
      replicas: 3

  celery_worker:
    deploy:
      replicas: 4

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx/nginx-loadbalancer.conf:/etc/nginx/nginx.conf
```

### Database Scaling

```bash
# PostgreSQL read replicas
docker-compose -f docker-compose.yml -f docker-compose.replica.yml up -d

# Redis clustering
docker-compose -f docker-compose.yml -f docker-compose.redis-cluster.yml up -d
```

## Security Configuration

### Network Security

```bash
# Configure firewall
sudo ufw enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 8000/tcp   # Block direct API access
```

### Application Security

1. **JWT Secret**: Use 256-bit random key
2. **Database Encryption**: Enable TLS for PostgreSQL
3. **Redis Security**: Use password authentication
4. **API Rate Limiting**: Configure per-user limits
5. **Input Validation**: Enabled by default in FastAPI

### Secrets Management

```bash
# Using Docker secrets (Production)
echo "secure_jwt_key" | docker secret create jwt_secret -
echo "db_password" | docker secret create db_password -

# Update docker-compose.yml to use secrets
services:
  api:
    secrets:
      - jwt_secret
      - db_password
```

## Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check PostgreSQL status
docker-compose logs postgres

# Test connection
docker-compose exec api python -c "
import asyncpg
import asyncio
async def test():
    conn = await asyncpg.connect('postgresql://trading_user:password@postgres:5432/trading_system')
    result = await conn.fetchval('SELECT 1')
    print(f'Database test: {result}')
    await conn.close()
asyncio.run(test())
"
```

#### Redis Connection Issues
```bash
# Test Redis connection
docker-compose exec redis redis-cli ping

# Check Redis logs
docker-compose logs redis
```

#### Signal Generation Issues
```bash
# Check signal generation logs
docker-compose logs celery_worker

# Manually trigger signal generation
curl -X POST http://localhost:8000/signals/generate \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Performance Issues

#### High CPU Usage
```bash
# Check container resource usage
docker stats

# Profile Python application
docker-compose exec api py-spy top --pid 1
```

#### Memory Issues
```bash
# Check memory usage
docker-compose exec api python -c "
import psutil
print(f'Memory usage: {psutil.virtual_memory().percent}%')
"

# Restart services if needed
docker-compose restart api celery_worker
```

### Logs and Debugging

```bash
# View application logs
docker-compose logs -f api

# View specific service logs
docker-compose logs -f celery_worker
docker-compose logs -f postgres

# Debug with container shell
docker-compose exec api bash
```

## Support and Maintenance

### Contact Information
- **Technical Support**: tech-support@yourcompany.com
- **Emergency Contact**: +62-xxx-xxx-xxxx
- **Documentation**: https://docs.yourcompany.com/trading-system

### Update Procedure

```bash
# 1. Backup current system
./backup.sh

# 2. Pull latest changes
git pull origin main

# 3. Update containers
docker-compose pull
docker-compose up -d

# 4. Run database migrations if needed
docker-compose exec api alembic upgrade head

# 5. Verify deployment
curl -f http://localhost:8000/health
```

### Disaster Recovery

#### Database Recovery
```bash
# Restore from backup
docker-compose exec -T postgres psql -U trading_user -d trading_system < backups/db_backup_YYYYMMDD_HHMMSS.sql
```

#### Model Recovery
```bash
# Restore model files
tar -xzf backups/models_backup_YYYYMMDD_HHMMSS.tar.gz
docker-compose restart api celery_worker
```

This deployment guide provides comprehensive instructions for setting up, configuring, and maintaining the Indonesian Quantitative Trading Alert System in production environments. Follow the security best practices and monitoring guidelines to ensure reliable operation.
