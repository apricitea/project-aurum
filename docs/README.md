# Project Aurum - Indonesian Quantitative Trading System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Production Ready](https://img.shields.io/badge/Production-Ready-brightgreen.svg)](https://github.com/yourusername/project-aurum)

> **Professional-grade quantitative trading system optimized for the Indonesian Stock Exchange (IDX) with ensemble machine learning, real-time alerting, and comprehensive risk management.**

## 📚 Documentation Navigation

This documentation is organized using the **Diátaxis framework** for optimal user experience:

### 🎓 **[Tutorials](./tutorials/)** - *Learning-oriented*
**New to Project Aurum? Start here!**
- [Getting Started Guide](./tutorials/getting-started.md) - Set up your first instance
- [Your First Trading Signal](./tutorials/your-first-trading-signal.md) - Generate your first trade signal
- [Deploying to Production](./tutorials/deploying-to-production.md) - Full deployment walkthrough
- [Indonesian Market Basics](./tutorials/indonesian-market-basics.md) - Understanding IDX markets

### 🔧 **[How-to Guides](./how-to-guides/)** - *Problem-oriented*
**Need to accomplish a specific task? Look here!**

#### 🚀 [Deployment](./how-to-guides/deployment/)
- [Docker Deployment](./how-to-guides/deployment/docker-deployment.md)
- [Kubernetes Deployment](./how-to-guides/deployment/kubernetes-deployment.md)
- [Production Checklist](./how-to-guides/deployment/production-checklist.md)

#### 💻 [Development](./how-to-guides/development/)
- [Setting Up Dev Environment](./how-to-guides/development/setting-up-dev-environment.md)
- [Running Tests](./how-to-guides/development/running-tests.md)
- [Contributing Code](./how-to-guides/development/contributing-code.md)
- [Debugging Common Issues](./how-to-guides/development/debugging-common-issues.md)

#### 📈 [Trading](./how-to-guides/trading/)
- [Creating Custom Strategies](./how-to-guides/trading/creating-custom-strategies.md)
- [Backtesting Strategies](./how-to-guides/trading/backtesting-strategies.md)
- [Optimizing Performance](./how-to-guides/trading/optimizing-performance.md)

#### ⚖️ [Compliance](./how-to-guides/compliance/)
- [Indonesian Regulations](./how-to-guides/compliance/indonesian-regulations.md)
- [Security Implementation](./how-to-guides/compliance/security-implementation.md)

### 📖 **[Reference](./reference/)** - *Information-oriented*
**Looking up specific information? Quick reference here!**

#### 🔌 [API Reference](./reference/api/)
- [API Endpoints](./reference/api/endpoints.md)
- [Authentication](./reference/api/authentication.md)
- [Rate Limits](./reference/api/rate-limits.md)

#### 🏗️ [Architecture](./reference/architecture/)
- [System Overview](./reference/architecture/system-overview.md)
- [Database Schema](./reference/architecture/database-schema.md)
- [Domain Models](./reference/architecture/domain-models.md)
- [Integration Points](./reference/architecture/integration-points.md)

#### ⚙️ [Configuration](./reference/configuration/)
- [Environment Variables](./reference/configuration/environment-variables.md)
- [Feature Flags](./reference/configuration/feature-flags.md)
- [Monitoring Metrics](./reference/configuration/monitoring-metrics.md)

#### 💹 [Market Data](./reference/market-data/)
- [Data Sources](./reference/market-data/data-sources.md)
- [Data Formats](./reference/market-data/data-formats.md)
- [Trading Hours](./reference/market-data/trading-hours.md)

### 💡 **[Explanation](./explanation/)** - *Understanding-oriented*
**Want to understand the deeper concepts? Dive in here!**

#### 🧠 [Concepts](./explanation/concepts/)
- [Quantitative Trading](./explanation/concepts/quantitative-trading.md)
- [Risk Management](./explanation/concepts/risk-management.md)
- [Machine Learning Models](./explanation/concepts/machine-learning-models.md)
- [Indonesian Market Dynamics](./explanation/concepts/indonesian-market-dynamics.md)

#### 🎯 [Architecture Decisions](./explanation/architecture-decisions/)
- [Why FastAPI](./explanation/architecture-decisions/why-fastapi.md)
- [Database Design](./explanation/architecture-decisions/database-design.md)
- [Deployment Strategy](./explanation/architecture-decisions/deployment-strategy.md)
- [Security Approach](./explanation/architecture-decisions/security-approach.md)

#### 💼 [Business Context](./explanation/business/)
- [Project Vision](./explanation/business/project-vision.md)
- [Market Opportunity](./explanation/business/market-opportunity.md)
- [Regulatory Landscape](./explanation/business/regulatory-landscape.md)

### 👥 **[User Guides](./user-guides/)** - *User-focused*
**Using the platform as an end user? Start here!**
- [Trader Guide](./user-guides/trader-guide.md) - Complete guide for traders
- [Dashboard Overview](./user-guides/dashboard-overview.md) - Navigate the interface
- [Alert Configuration](./user-guides/alert-configuration.md) - Set up notifications
- [Portfolio Management](./user-guides/portfolio-management.md) - Manage your positions

### 🔧 **[Operations](./operations/)** - *DevOps & maintenance*
**Managing the system in production? Essential guides here!**
- [Monitoring Runbook](./operations/monitoring-runbook.md)
- [Incident Response](./operations/incident-response.md)
- [Backup Recovery](./operations/backup-recovery.md)
- [Performance Tuning](./operations/performance-tuning.md)

### 📋 **[Project Meta](./project-meta/)** - *Project information*
- [Changelog](./project-meta/changelog.md) - Version history and updates
- [Roadmap](./project-meta/roadmap.md) - Future plans and features
- [Load Test Results](./project-meta/load-test-results.md) - Performance benchmarks
- [Claude Context](./project-meta/claude-context.md) - AI assistant configuration

---

## 🚀 Quick Start

### New User? Start Here:
1. **First Time Setup**: [Getting Started Tutorial](./tutorials/getting-started.md)
2. **Learn the Platform**: [Your First Trading Signal](./tutorials/your-first-trading-signal.md)
3. **Use the Platform**: [Trader Guide](./user-guides/trader-guide.md)

### Developer? Jump To:
1. **Development Setup**: [Dev Environment Guide](./how-to-guides/development/setting-up-dev-environment.md)
2. **Architecture Overview**: [System Overview](./reference/architecture/system-overview.md)
3. **Contributing**: [Contributing Code](./how-to-guides/development/contributing-code.md)

### DevOps Engineer? Go To:
1. **Deployment**: [Production Deployment](./how-to-guides/deployment/kubernetes-deployment.md)
2. **Monitoring**: [Monitoring Runbook](./operations/monitoring-runbook.md)
3. **Security**: [Security Implementation](./how-to-guides/compliance/security-implementation.md)

---

## 🎯 System Overview

**Project Aurum** is a sophisticated, production-ready quantitative trading system specifically designed for the Indonesian Stock Exchange (IDX). The system combines advanced machine learning techniques, real-time data processing, and comprehensive risk management to generate daily trading signals with institutional-grade reliability.

### Key Features

- **🤖 Advanced ML Ensemble**: Multi-model approach combining technical, fundamental, sentiment, and momentum factors
- **📊 Real-time Dashboard**: React/TypeScript frontend with live market data and portfolio monitoring
- **⚡ Daily Signal Generation**: Automated buy/sell/hold recommendations for LQ45 stocks
- **🛡️ Comprehensive Risk Management**: Multi-layered risk controls and position sizing
- **📱 Multi-channel Alerts**: Email, Telegram, SMS, and WebSocket notifications
- **📈 Performance Analytics**: Detailed backtesting and performance tracking
- **🔒 Enterprise Security**: JWT authentication, role-based access, and audit logging
- **📊 Professional Monitoring**: Grafana dashboards, Prometheus metrics, ELK stack

### Target Performance Goals

| Metric | Target | Status |
|--------|--------|--------|
| Annual Return | 15-25% | ✅ Backtested |
| Sharpe Ratio | 1.2-1.8 | ✅ Validated |
| Maximum Drawdown | <15% | ✅ Risk-managed |
| Win Rate | 55-65% | ✅ Optimized |
| Signal Latency | <1 minute | ✅ Real-time |

---

## 💬 Support & Community

- **Issues**: [GitHub Issues](https://github.com/yourusername/project-aurum/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/project-aurum/discussions)
- **Email**: support@projectaurum.com
- **Documentation**: You're reading it! 📚

---

*Last Updated: 2025-09-27 | Version: 1.0.0 | [Changelog](./project-meta/changelog.md)*