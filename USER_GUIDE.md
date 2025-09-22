# Project Aurum - User Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [Daily Trading Signals](#daily-trading-signals)
4. [Portfolio Management](#portfolio-management)
5. [Risk Management](#risk-management)
6. [Alert System](#alert-system)
7. [Performance Analytics](#performance-analytics)
8. [Reports & Exports](#reports--exports)
9. [Settings & Preferences](#settings--preferences)
10. [Mobile Usage](#mobile-usage)
11. [Troubleshooting](#troubleshooting)
12. [Best Practices](#best-practices)

## Getting Started

### System Requirements

**Supported Browsers:**
- Chrome 90+ (Recommended)
- Firefox 88+
- Safari 14+
- Edge 90+

**Screen Resolution:**
- Minimum: 1366x768
- Recommended: 1920x1080 or higher

### First Time Login

1. **Access the Platform**
   - Navigate to your Project Aurum dashboard URL
   - Bookmark the page for easy access

2. **Login Credentials**
   - Enter your username and password
   - Check "Remember me" for convenience (on secure devices only)

3. **Initial Setup**
   - Complete your profile information
   - Set notification preferences
   - Configure risk tolerance settings

### Dashboard Layout

The Project Aurum dashboard uses a modern, intuitive interface designed for professional traders:

```
┌─────────────────────────────────────────────────────────┐
│ Header: Logo | Navigation | User Menu | Notifications   │
├─────────────────────────────────────────────────────────┤
│ Sidebar:                │ Main Content Area            │
│ • Overview             │                               │
│ • Signals              │ [Dynamic content based on     │
│ • Portfolio            │  selected navigation item]    │
│ • Risk Management      │                               │
│ • Analytics            │                               │
│ • Reports              │                               │
│ • Settings             │                               │
├─────────────────────────────────────────────────────────┤
│ Footer: Status indicators | Market hours | Last update │
└─────────────────────────────────────────────────────────┘
```

## Dashboard Overview

### Quick Stats Panel

The overview dashboard provides a comprehensive view of your trading system's current status:

#### Performance Summary
- **Portfolio Value**: Current total portfolio value in IDR
- **Daily P&L**: Today's profit/loss amount and percentage
- **Total Return**: Overall portfolio performance since inception
- **Active Positions**: Number of stocks currently held

#### Market Status
- **Market Hours**: Current IDX trading session status
- **Last Update**: Timestamp of the most recent data refresh
- **Data Feed Status**: Real-time connection status to market data

#### Recent Activity
- **Latest Signals**: Most recent buy/sell/hold recommendations
- **Recent Trades**: Last executed transactions
- **Pending Alerts**: Unacknowledged notifications

### Key Performance Indicators (KPIs)

| Metric | Description | Target Range |
|--------|-------------|--------------|
| **Sharpe Ratio** | Risk-adjusted return measure | > 1.0 |
| **Maximum Drawdown** | Largest portfolio decline | < 15% |
| **Win Rate** | Percentage of profitable signals | 55-65% |
| **Beta** | Market correlation | 0.8-1.2 |
| **Volatility** | Portfolio price fluctuation | 12-18% |

## Daily Trading Signals

### Understanding Signals

Project Aurum generates three types of daily signals for LQ45 stocks:

#### Signal Types

1. **BUY** 🟢
   - Positive expected return
   - Signal strength: 0.3 to 1.0
   - Recommended action: Increase position

2. **SELL** 🔴
   - Negative expected return
   - Signal strength: -0.3 to -1.0
   - Recommended action: Reduce/close position

3. **HOLD** 🟡
   - Neutral expected return
   - Signal strength: -0.3 to 0.3
   - Recommended action: Maintain current position

#### Signal Strength Interpretation

| Strength Range | Interpretation | Action Priority |
|----------------|----------------|-----------------|
| 0.7 to 1.0 | Very Strong | High |
| 0.5 to 0.7 | Strong | Medium-High |
| 0.3 to 0.5 | Moderate | Medium |
| -0.3 to 0.3 | Weak/Neutral | Low |
| -0.5 to -0.3 | Moderate Sell | Medium |
| -0.7 to -0.5 | Strong Sell | Medium-High |
| -1.0 to -0.7 | Very Strong Sell | High |

### Daily Signal Workflow

#### Morning Routine (06:30 - 09:00 WIB)

1. **Check Signal Generation Status**
   - Verify that daily signals have been generated
   - Review any error messages or warnings

2. **Review Signal Summary**
   - Total number of signals by type
   - Average signal strength
   - Notable changes from previous day

3. **Prioritize Actions**
   - Focus on high-strength signals first
   - Consider current portfolio allocation
   - Check for risk limit violations

#### Signal Details Page

Each signal provides comprehensive information:

**Basic Information:**
- Stock symbol and company name
- Current price and daily change
- Signal type and strength
- Recommended allocation percentage

**Supporting Analysis:**
- Technical score (momentum, patterns)
- Fundamental score (valuation, quality)
- Sentiment score (news, market sentiment)
- Key supporting factors

**Risk Metrics:**
- Individual stock volatility
- Beta (market correlation)
- Liquidity score
- Position size limit

### Acting on Signals

#### Pre-Trade Checklist

Before executing any trade based on signals:

1. **Verify Signal Validity**
   - Check signal generation timestamp
   - Confirm no data quality issues
   - Review signal strength threshold

2. **Risk Assessment**
   - Check current position size
   - Verify sector concentration limits
   - Assess correlation with existing positions

3. **Market Conditions**
   - Confirm market is open
   - Check for major news events
   - Review volatility conditions

#### Trade Execution

**Manual Execution:**
1. Navigate to your broker platform
2. Enter trade details based on signal
3. Update position in Project Aurum
4. Monitor execution and confirm fill

**API Integration (Advanced):**
- Use provided APIs to automate trade execution
- Implement position sizing rules
- Set up automatic position updates

## Portfolio Management

### Portfolio Overview

The portfolio section provides a complete view of your holdings:

#### Summary Metrics
- **Total Value**: Current portfolio market value
- **Cash Balance**: Available cash for new positions
- **Invested Amount**: Total value of stock positions
- **Day's Change**: Daily profit/loss

#### Sector Allocation
Visual breakdown of portfolio by sector:
- Banking (target: 25-35%)
- Telecommunications (target: 15-25%)
- Consumer Goods (target: 20-30%)
- Mining (target: 10-20%)
- Other sectors (target: 5-15%)

### Position Management

#### Individual Positions

Each position displays:
- **Symbol & Name**: Stock identifier and company name
- **Quantity**: Number of shares held
- **Average Price**: Average purchase price
- **Current Price**: Latest market price
- **Market Value**: Current position value
- **Unrealized P&L**: Profit/loss since purchase
- **Weight**: Position size as percentage of portfolio

#### Position Actions

**Updating Positions:**
1. Click on any position row
2. Select action: Buy, Sell, or Adjust
3. Enter quantity and price
4. Add optional notes
5. Confirm transaction

**Position Alerts:**
- Set price alerts for individual stocks
- Configure stop-loss levels
- Enable rebalancing notifications

### Transaction History

Track all portfolio changes:
- **Date & Time**: When transaction occurred
- **Symbol**: Stock involved
- **Action**: Buy, Sell, Dividend, etc.
- **Quantity**: Number of shares
- **Price**: Execution price
- **Total Value**: Transaction amount
- **Fees**: Brokerage costs
- **Notes**: Additional comments

### Portfolio Rebalancing

#### Automatic Rebalancing
- Set target allocation percentages
- Define rebalancing triggers (time or threshold)
- Configure minimum trade sizes

#### Manual Rebalancing
1. Review current vs. target allocations
2. Identify overweight/underweight positions
3. Calculate required trades
4. Execute rebalancing transactions

## Risk Management

### Risk Dashboard

The risk management section helps monitor and control portfolio risk:

#### Risk Score Overview
- **Overall Risk Score**: 1-10 scale (1=very low, 10=very high)
- **Risk Level**: Conservative, Moderate, Aggressive
- **Trend**: Increasing, Stable, Decreasing

#### Value at Risk (VaR)
- **1-Day VaR (1%)**: Maximum expected loss over 1 day (99% confidence)
- **1-Day VaR (5%)**: Maximum expected loss over 1 day (95% confidence)
- **Expected Shortfall**: Average loss beyond VaR threshold

### Risk Limits

#### Position Limits
- **Maximum Position Size**: 5% per individual stock
- **Sector Concentration**: 35% maximum per sector
- **Cash Reserve**: 10-20% minimum cash allocation

#### Portfolio Limits
- **Maximum Drawdown**: 15% portfolio decline limit
- **Beta Range**: 0.8-1.2 market correlation
- **Volatility Ceiling**: 20% annualized volatility

#### Risk Alerts

The system automatically monitors for:
- Position size violations
- Sector concentration breaches
- Correlation increases
- Volatility spikes
- Drawdown approaching limits

### Risk Mitigation

#### Automatic Actions
When risk limits are approached:
1. **Yellow Alert** (80% of limit): Warning notification
2. **Orange Alert** (90% of limit): Recommended actions provided
3. **Red Alert** (100% of limit): Automatic position reduction (if enabled)

#### Manual Risk Reduction
- **Diversification**: Spread holdings across sectors
- **Position Sizing**: Reduce oversized positions
- **Correlation Management**: Avoid highly correlated stocks
- **Cash Increase**: Raise cash allocation during high volatility

## Alert System

### Alert Types

#### Trading Signals
- **Signal Generated**: New buy/sell/hold recommendations
- **Strong Signals**: High-confidence trading opportunities
- **Signal Changes**: Updates to existing recommendations

#### Risk Alerts
- **Limit Breaches**: Risk thresholds exceeded
- **Unusual Activity**: Abnormal market movements
- **Position Warnings**: Individual stock concerns

#### System Alerts
- **Data Issues**: Market data feed problems
- **System Maintenance**: Scheduled downtime notifications
- **Performance Updates**: Model retraining completions

### Notification Channels

#### Email Notifications
- **Immediate**: Critical alerts sent instantly
- **Daily Summary**: End-of-day report
- **Weekly Report**: Performance and activity summary

#### Telegram Integration
1. **Setup**: Add @ProjectAurumBot to Telegram
2. **Authentication**: Link account with verification code
3. **Configuration**: Choose alert types to receive

#### SMS Alerts (Critical Only)
- Risk limit breaches
- System failures
- Major position changes

### Managing Alerts

#### Alert Settings
- **Priority Filtering**: Choose alert importance levels
- **Time Windows**: Set active notification hours
- **Frequency Limits**: Prevent alert spam

#### Alert History
- **Review Past Alerts**: Track notification history
- **Performance Analysis**: Evaluate alert accuracy
- **Response Tracking**: Monitor action taken on alerts

## Performance Analytics

### Performance Metrics

#### Return Analysis
- **Total Return**: Cumulative portfolio performance
- **Annualized Return**: Year-over-year performance
- **Benchmark Comparison**: Performance vs. IDX Composite
- **Risk-Adjusted Returns**: Sharpe and Sortino ratios

#### Risk Metrics
- **Volatility**: Standard deviation of returns
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Beta**: Correlation with market movements
- **Value at Risk**: Potential loss estimates

### Performance Charts

#### Time Series Charts
- **Portfolio Value**: Historical portfolio value
- **Daily Returns**: Day-to-day performance changes
- **Cumulative Returns**: Running total performance
- **Drawdown Chart**: Portfolio decline periods

#### Comparison Charts
- **vs. Benchmark**: Portfolio vs. IDX Composite
- **vs. Sectors**: Performance vs. sector indices
- **vs. Individual Stocks**: Contribution analysis

### Attribution Analysis

#### Sector Attribution
- Performance contribution by sector
- Overweight/underweight impact
- Sector allocation effectiveness

#### Stock Attribution
- Individual stock contributions
- Best and worst performers
- Position sizing impact

#### Timing Attribution
- Entry/exit timing effectiveness
- Signal accuracy analysis
- Trade execution quality

## Reports & Exports

### Daily Reports

#### Automated Reports
Generated every trading day at 16:30 WIB:
- **Portfolio Summary**: Current positions and performance
- **Signal Summary**: Today's recommendations and actions
- **Risk Report**: Current risk metrics and alerts
- **Transaction Summary**: Trades executed today

#### Custom Reports
- **Date Range Selection**: Choose specific periods
- **Content Customization**: Select report sections
- **Format Options**: PDF, Excel, CSV formats

### Performance Reports

#### Monthly Performance
- **Return Analysis**: Monthly performance breakdown
- **Risk Metrics**: Rolling risk measurements
- **Attribution**: Sources of performance
- **Benchmark Comparison**: Relative performance

#### Quarterly Reviews
- **Strategy Performance**: Signal accuracy and returns
- **Portfolio Evolution**: Allocation changes over time
- **Risk Assessment**: Risk-adjusted performance
- **Recommendations**: Strategy improvements

### Data Exports

#### Portfolio Data
- **Current Positions**: CSV export of all holdings
- **Transaction History**: Complete trade records
- **Performance Data**: Historical returns and metrics

#### Signal Data
- **Historical Signals**: Past recommendations and outcomes
- **Signal Performance**: Accuracy and profitability analysis
- **Model Predictions**: Raw model outputs and confidence

## Settings & Preferences

### User Profile

#### Basic Information
- **Name**: Display name
- **Email**: Contact email for notifications
- **Phone**: Mobile number for SMS alerts
- **Timezone**: Default to Asia/Jakarta

#### Security Settings
- **Password Change**: Update login credentials
- **Two-Factor Authentication**: Enhanced security
- **Session Management**: Active login sessions
- **API Keys**: Generate keys for programmatic access

### Notification Preferences

#### Email Settings
- **Signal Alerts**: New trading recommendations
- **Risk Alerts**: Risk threshold breaches
- **Performance Reports**: Daily/weekly summaries
- **System Notifications**: Maintenance and updates

#### Alert Frequency
- **Immediate**: Send as events occur
- **Batched**: Combine into periodic summaries
- **Quiet Hours**: Suspend alerts during specified times

### Trading Preferences

#### Risk Tolerance
- **Conservative**: Lower risk, stable returns
- **Moderate**: Balanced risk/return
- **Aggressive**: Higher risk, higher potential returns

#### Position Sizing
- **Fixed Percentage**: Equal weight all positions
- **Signal-Weighted**: Size based on signal strength
- **Risk-Adjusted**: Size based on individual stock risk

### Display Preferences

#### Dashboard Layout
- **Widget Arrangement**: Customize dashboard layout
- **Color Scheme**: Light/dark mode
- **Chart Preferences**: Default chart types and periods
- **Currency Display**: IDR, USD, percentage formats

## Mobile Usage

### Mobile Web Access

The Project Aurum dashboard is fully responsive and optimized for mobile devices:

#### Supported Features
- **Signal Viewing**: Access daily recommendations
- **Portfolio Monitoring**: Track positions and performance
- **Alert Management**: Receive and acknowledge notifications
- **Basic Reporting**: View key metrics and charts

#### Mobile-Optimized Interface
- **Touch-Friendly**: Large buttons and touch targets
- **Simplified Navigation**: Streamlined menu structure
- **Responsive Charts**: Auto-scaling visualizations
- **Offline Support**: Limited functionality when offline

### Mobile Best Practices

#### Daily Routine
1. **Morning Check** (07:00 WIB): Review overnight signals
2. **Market Open** (09:00 WIB): Monitor opening positions
3. **Midday Update** (12:00 WIB): Check position changes
4. **Market Close** (16:00 WIB): Review daily performance

#### Security on Mobile
- **Auto-Lock**: Enable device screen lock
- **Secure Networks**: Avoid public WiFi for trading
- **App Updates**: Keep browser updated
- **Logout**: Always logout when finished

## Troubleshooting

### Common Issues

#### Login Problems
**Issue**: Cannot login to dashboard
**Solutions**:
1. Verify username/password spelling
2. Check Caps Lock status
3. Clear browser cache and cookies
4. Try different browser
5. Contact support if issue persists

#### Data Loading Issues
**Issue**: Dashboard shows outdated data
**Solutions**:
1. Refresh page (F5 or Ctrl+R)
2. Check internet connection
3. Verify market hours (data updates during trading)
4. Clear browser cache
5. Check system status page

#### Signal Generation Delays
**Issue**: Daily signals not appearing on time
**Solutions**:
1. Check signal generation status
2. Verify data feed connectivity
3. Review error logs (if accessible)
4. Contact technical support

### Performance Issues

#### Slow Dashboard Loading
**Causes & Solutions**:
- **Slow Internet**: Check connection speed
- **Browser Issues**: Clear cache, restart browser
- **Server Load**: Wait and retry, check status page
- **Too Many Charts**: Reduce displayed timeframes

#### Chart Display Problems
**Causes & Solutions**:
- **Browser Compatibility**: Update to supported version
- **JavaScript Disabled**: Enable JavaScript
- **Ad Blockers**: Whitelist dashboard domain
- **Graphics Issues**: Update graphics drivers

### Getting Help

#### Self-Service Resources
- **User Guide**: This comprehensive guide
- **FAQ Section**: Common questions and answers
- **Video Tutorials**: Step-by-step demonstrations
- **System Status**: Real-time system health

#### Support Channels
- **Email Support**: support@projectaurum.com
- **Live Chat**: Available during market hours
- **Phone Support**: Emergency issues only
- **Community Forum**: User discussions and tips

## Best Practices

### Daily Workflow

#### Pre-Market Preparation (06:00-09:00 WIB)
1. **Check System Status**: Verify all services operational
2. **Review Signals**: Analyze new recommendations
3. **Plan Trades**: Prioritize high-confidence signals
4. **Check Risk**: Ensure within risk limits
5. **Prepare Orders**: Ready trade execution

#### During Market Hours (09:00-15:49 WIB)
1. **Monitor Positions**: Track real-time performance
2. **Execute Trades**: Act on planned signals
3. **Update System**: Record executed trades
4. **Watch Alerts**: Respond to risk notifications
5. **Stay Informed**: Monitor market news

#### Post-Market Analysis (16:00-17:00 WIB)
1. **Review Performance**: Analyze day's results
2. **Update Records**: Ensure all trades recorded
3. **Check Alerts**: Address any outstanding issues
4. **Plan Tomorrow**: Preview next day's strategy
5. **Generate Reports**: Create daily summary

### Risk Management Best Practices

#### Position Sizing
- **Start Small**: Begin with smaller position sizes
- **Gradual Increases**: Scale up successful strategies
- **Diversification**: Spread risk across stocks/sectors
- **Cash Reserve**: Maintain minimum cash buffer
- **Regular Review**: Reassess position sizes monthly

#### Signal Usage
- **Confidence Thresholds**: Focus on high-confidence signals
- **Confirmation**: Cross-check with market conditions
- **Timing**: Consider market volatility and news
- **Gradual Implementation**: Phase in new positions
- **Performance Tracking**: Monitor signal accuracy

### Portfolio Optimization

#### Allocation Strategy
- **Sector Balance**: Maintain diversified sector exposure
- **Position Limits**: Respect maximum position sizes
- **Correlation Management**: Avoid highly correlated holdings
- **Rebalancing**: Regular portfolio rebalancing
- **Cash Management**: Strategic cash allocation

#### Performance Monitoring
- **Regular Reviews**: Weekly performance analysis
- **Benchmark Comparison**: Track relative performance
- **Risk Assessment**: Monitor risk metrics trends
- **Attribution Analysis**: Understand return sources
- **Strategy Adjustment**: Adapt based on results

### Technology Usage

#### Security Practices
- **Strong Passwords**: Use complex, unique passwords
- **Regular Updates**: Keep browsers updated
- **Secure Connections**: Always use HTTPS
- **Device Security**: Secure all access devices
- **Account Monitoring**: Regular security reviews

#### Efficiency Tips
- **Bookmark Dashboard**: Quick access to platform
- **Browser Shortcuts**: Learn keyboard shortcuts
- **Multiple Monitors**: Use multiple screens if available
- **Mobile Backup**: Have mobile access ready
- **Offline Planning**: Prepare for connectivity issues

This user guide provides comprehensive information for effectively using the Project Aurum quantitative trading system. Regular reference to this guide will help optimize your trading workflow and maximize the platform's benefits.