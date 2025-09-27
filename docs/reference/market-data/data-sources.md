# Project Aurum - Indonesian Market Implementation

## Table of Contents

1. [Market Overview](#market-overview)
2. [IDX Market Structure](#idx-market-structure)
3. [Regulatory Environment](#regulatory-environment)
4. [LQ45 Focus Strategy](#lq45-focus-strategy)
5. [Currency Considerations](#currency-considerations)
6. [Trading Hours & Calendar](#trading-hours--calendar)
7. [Market Data Sources](#market-data-sources)
8. [Local Broker Integration](#local-broker-integration)
9. [Risk Management Adaptations](#risk-management-adaptations)
10. [Performance Benchmarking](#performance-benchmarking)

## Market Overview

### Indonesia Stock Exchange (IDX) Characteristics

The Indonesian Stock Exchange represents the largest stock market in Southeast Asia by market capitalization and is the 4th largest in Asia Pacific. Project Aurum is specifically optimized for the unique characteristics of this emerging market.

#### Key Market Statistics (2024)
| Metric | Value | Global Rank |
|--------|-------|-------------|
| **Market Capitalization** | USD 650+ billion | 15th globally |
| **Listed Companies** | 800+ companies | - |
| **Daily Trading Volume** | IDR 8-12 trillion | - |
| **Foreign Ownership Limit** | 49% (most sectors) | - |
| **Settlement Cycle** | T+2 | Standard |
| **Trading Currency** | Indonesian Rupiah (IDR) | - |

#### Market Segments
```
IDX Market Structure:
├── Main Board
│   ├── First Board (Blue chips, >IDR 3T market cap)
│   └── Second Board (Mid-caps, >IDR 200B market cap)
├── Development Board
│   └── Small-caps and growth companies
└── Acceleration Board
    └── Early-stage companies
```

### Economic Context

#### Macroeconomic Indicators
- **GDP Growth**: 5.0-5.3% annually (2020-2024)
- **Inflation Rate**: 2.5-4.0% target range
- **Interest Rate**: 5.75-6.25% (BI 7-Day Reverse Repo)
- **Currency Stability**: IDR 15,000-16,000 per USD

#### Sectoral Composition
```python
IDX_SECTOR_WEIGHTS = {
    'banking': 0.285,                    # Dominant sector
    'telecommunications': 0.165,         # Infrastructure growth
    'consumer_goods': 0.145,            # Domestic consumption
    'mining': 0.125,                    # Commodity exports
    'infrastructure': 0.085,            # Government spending
    'property': 0.075,                  # Real estate
    'transportation': 0.055,            # Logistics growth
    'energy': 0.045,                    # Oil & gas
    'others': 0.015                     # Miscellaneous
}
```

## IDX Market Structure

### Trading Mechanisms

#### Order Types and Execution
```python
class IDXOrderTypes:
    """
    Supported order types in IDX
    """
    ORDER_TYPES = {
        'market': {
            'description': 'Execute at best available price',
            'execution_priority': 1,
            'price_protection': False
        },
        'limit': {
            'description': 'Execute at specified price or better',
            'execution_priority': 2,
            'price_protection': True
        },
        'stop_limit': {
            'description': 'Stop order that becomes limit order',
            'execution_priority': 3,
            'price_protection': True
        }
    }

    LOT_SIZE = 100  # Minimum trading unit
    TICK_SIZE_RULES = {
        'below_200': 1,      # IDR 1 for prices < IDR 200
        '200_500': 2,        # IDR 2 for prices IDR 200-500
        '500_2000': 5,       # IDR 5 for prices IDR 500-2,000
        '2000_5000': 10,     # IDR 10 for prices IDR 2,000-5,000
        'above_5000': 25     # IDR 25 for prices > IDR 5,000
    }
```

#### Auto Rejection (ARA) System
```python
class AutoRejectionLimits:
    """
    IDX automatic rejection limits to prevent extreme price movements
    """
    def __init__(self):
        self.rejection_limits = {
            'individual_stock': {
                'upper_limit': 0.35,  # +35% from previous close
                'lower_limit': -0.35, # -35% from previous close
                'duration': 'entire_session'
            },
            'index_circuit_breaker': {
                'level_1': -0.05,     # 5% decline triggers 30min halt
                'level_2': -0.10,     # 10% decline triggers trading halt
                'level_3': -0.15      # 15% decline closes market
            }
        }

    def calculate_price_limits(self, previous_close):
        """Calculate daily price limits for a stock"""
        upper_limit = previous_close * 1.35
        lower_limit = previous_close * 0.65

        return {
            'upper_limit': upper_limit,
            'lower_limit': lower_limit,
            'previous_close': previous_close
        }
```

### Market Microstructure

#### Opening and Closing Auctions
```python
class IDXTradingSessions:
    """
    IDX trading session structure
    """
    def __init__(self):
        self.session_schedule = {
            'pre_opening': {
                'start': '08:45:00',
                'end': '09:00:00',
                'description': 'Order collection phase',
                'order_types': ['limit'],
                'execution': 'auction'
            },
            'opening_auction': {
                'start': '09:00:00',
                'end': '09:00:30',
                'description': 'Opening price determination',
                'execution': 'auction'
            },
            'continuous_trading': {
                'start': '09:00:30',
                'end': '11:30:00',
                'description': 'Morning session',
                'execution': 'continuous'
            },
            'trading_break': {
                'start': '11:30:00',
                'end': '13:30:00',
                'description': 'Lunch break'
            },
            'afternoon_session': {
                'start': '13:30:00',
                'end': '15:49:30',
                'description': 'Afternoon continuous trading',
                'execution': 'continuous'
            },
            'closing_auction': {
                'start': '15:49:30',
                'end': '16:00:00',
                'description': 'Closing price determination',
                'execution': 'auction'
            },
            'post_trading': {
                'start': '16:00:00',
                'end': '17:00:00',
                'description': 'After-hours negotiated trades'
            }
        }
```

#### Liquidity Characteristics
```python
def analyze_idx_liquidity_patterns():
    """
    IDX-specific liquidity patterns and implications
    """
    liquidity_patterns = {
        'intraday_patterns': {
            'opening_30min': 'High volume, wide spreads',
            'mid_morning': 'Moderate volume, tighter spreads',
            'lunch_approach': 'Declining volume',
            'afternoon_opening': 'Volume revival',
            'closing_30min': 'High volume, auction effects'
        },
        'weekly_patterns': {
            'monday': 'Weekend news impact, higher volatility',
            'tuesday_thursday': 'Normal trading patterns',
            'friday': 'Position squaring, lower volume'
        },
        'monthly_patterns': {
            'month_end': 'Institutional rebalancing',
            'earning_season': 'Higher volatility and volume',
            'dividend_season': 'June-August peak activity'
        }
    }

    return liquidity_patterns
```

## Regulatory Environment

### OJK (Otoritas Jasa Keuangan) Compliance

#### Investment Management Regulations
```python
class OJKCompliance:
    """
    OJK regulatory requirements for investment management
    """
    def __init__(self):
        self.investment_limits = {
            'single_issuer_limit': 0.05,        # Max 5% in single stock
            'affiliate_limit': 0.20,            # Max 20% in affiliated companies
            'illiquid_assets_limit': 0.10,      # Max 10% in illiquid assets
            'foreign_securities_limit': 0.15,   # Max 15% in foreign securities
            'derivatives_limit': 0.05,          # Max 5% notional in derivatives
        }

        self.reporting_requirements = {
            'daily_nav': 'T+1',
            'monthly_report': 'T+7',
            'quarterly_report': 'T+14',
            'annual_report': 'T+120',
            'material_changes': 'immediate'
        }

    def validate_portfolio_compliance(self, portfolio):
        """Check portfolio against OJK limits"""
        compliance_status = {}

        # Single issuer limit check
        max_position = portfolio.get_max_position_weight()
        compliance_status['single_issuer'] = {
            'compliant': max_position <= self.investment_limits['single_issuer_limit'],
            'current': max_position,
            'limit': self.investment_limits['single_issuer_limit']
        }

        # Calculate illiquid assets exposure
        illiquid_exposure = portfolio.calculate_illiquid_exposure()
        compliance_status['illiquid_assets'] = {
            'compliant': illiquid_exposure <= self.investment_limits['illiquid_assets_limit'],
            'current': illiquid_exposure,
            'limit': self.investment_limits['illiquid_assets_limit']
        }

        return compliance_status
```

#### Foreign Investment Restrictions
```python
class ForeignInvestmentLimits:
    """
    Manage foreign ownership limits per sector
    """
    def __init__(self):
        self.sector_limits = {
            'banking': 0.40,                # 40% foreign ownership
            'telecommunications': 0.49,     # 49% in telecommunications
            'mining': 0.49,                # 49% in mining (varies by commodity)
            'retail': 0.67,                # 67% in retail trade
            'property': 0.49,              # 49% in property
            'media': 0.20,                 # 20% in mass media
            'aviation': 0.49,              # 49% in aviation
            'shipping': 0.49,              # 49% in shipping
            'energy': 0.49,                # 49% in energy (varies)
            'manufacturing': 1.00          # 100% in most manufacturing
        }

    def check_foreign_ownership_room(self, symbol, sector):
        """Check available foreign ownership room"""
        current_foreign_ownership = self.get_current_foreign_ownership(symbol)
        sector_limit = self.sector_limits.get(sector, 0.49)  # Default 49%

        available_room = max(0, sector_limit - current_foreign_ownership)

        return {
            'current_foreign_ownership': current_foreign_ownership,
            'sector_limit': sector_limit,
            'available_room': available_room,
            'can_buy': available_room > 0.01  # Minimum 1% room
        }
```

### Tax Considerations

#### Indonesian Capital Gains Tax
```python
class IDXTaxCalculator:
    """
    Calculate Indonesian tax implications for trading
    """
    def __init__(self):
        self.tax_rates = {
            'capital_gains_resident': 0.025,      # 2.5% for residents
            'capital_gains_nonresident': 0.20,    # 20% for non-residents
            'dividend_tax_resident': 0.10,        # 10% for residents
            'dividend_tax_nonresident': 0.20,     # 20% for non-residents
            'transaction_tax': 0.001,             # 0.1% transaction tax
            'stamp_duty': 6000                    # IDR 6,000 per transaction
        }

    def calculate_trading_taxes(self, trades, investor_type='resident'):
        """Calculate total tax liability for trading activity"""
        total_tax = 0

        for trade in trades:
            # Transaction tax (on sale value)
            if trade['type'] == 'sell':
                transaction_value = trade['quantity'] * trade['price']
                transaction_tax = transaction_value * self.tax_rates['transaction_tax']
                total_tax += transaction_tax

                # Stamp duty
                total_tax += self.tax_rates['stamp_duty']

                # Capital gains tax (if profitable)
                if trade['profit'] > 0:
                    cgt_rate = self.tax_rates[f'capital_gains_{investor_type}']
                    capital_gains_tax = trade['profit'] * cgt_rate
                    total_tax += capital_gains_tax

        return total_tax
```

## LQ45 Focus Strategy

### LQ45 Index Composition

#### Selection Criteria
```python
class LQ45IndexManager:
    """
    Manage LQ45 index composition and updates
    """
    def __init__(self):
        self.selection_criteria = {
            'market_cap_rank': 'Top 60 by market capitalization',
            'liquidity_rank': 'Top 60 by transaction value',
            'financial_health': 'Positive book value and operating profit',
            'listing_duration': 'Minimum 3 months since IPO',
            'trading_frequency': 'Minimum 90% trading days',
            'final_selection': 'Top 45 from combined ranking'
        }

        self.update_schedule = {
            'review_frequency': 'Every 6 months',
            'review_months': ['February', 'August'],
            'effective_months': ['March', 'September'],
            'fast_track_criteria': 'Significant changes trigger early review'
        }

    def get_current_lq45_composition(self):
        """Get current LQ45 constituents with weights"""
        # This would be updated from official IDX data
        return {
            'BBCA': {'weight': 0.095, 'sector': 'banking'},
            'BMRI': {'weight': 0.078, 'sector': 'banking'},
            'BBRI': {'weight': 0.072, 'sector': 'banking'},
            'TLKM': {'weight': 0.065, 'sector': 'telecommunications'},
            'ASII': {'weight': 0.058, 'sector': 'automotive'},
            'UNVR': {'weight': 0.045, 'sector': 'consumer_goods'},
            'INDF': {'weight': 0.042, 'sector': 'consumer_goods'},
            'ICBP': {'weight': 0.038, 'sector': 'consumer_goods'},
            'KLBF': {'weight': 0.035, 'sector': 'healthcare'},
            'GGRM': {'weight': 0.033, 'sector': 'consumer_goods'},
            # ... additional 35 stocks
        }
```

#### LQ45 Trading Advantages
```python
def analyze_lq45_advantages():
    """
    Advantages of focusing on LQ45 stocks
    """
    advantages = {
        'liquidity_benefits': {
            'tight_spreads': 'Average bid-ask spread <0.5% vs 2%+ for others',
            'large_orders': 'Can execute large orders without significant impact',
            'quick_execution': 'Orders fill quickly during normal market hours',
            'exit_flexibility': 'Easy to exit positions when needed'
        },
        'information_quality': {
            'analyst_coverage': 'Extensive research coverage by local and international analysts',
            'financial_reporting': 'High quality and timely financial disclosures',
            'news_coverage': 'Regular media attention and market updates',
            'management_access': 'Regular investor relations activities'
        },
        'market_impact': {
            'index_tracking': 'Significant ETF and index fund flows',
            'foreign_interest': 'Primary focus for foreign institutional investors',
            'correlation_benefits': 'Better correlation with macroeconomic factors',
            'volatility_management': 'More predictable volatility patterns'
        },
        'operational_benefits': {
            'data_quality': 'Better market data coverage and accuracy',
            'model_reliability': 'More reliable technical and fundamental analysis',
            'risk_management': 'Better risk assessment and position sizing',
            'cost_efficiency': 'Lower transaction costs due to competition'
        }
    }

    return advantages
```

### Sector Allocation within LQ45

#### Dynamic Sector Weights
```python
class LQ45SectorManager:
    """
    Manage sector allocation within LQ45 universe
    """
    def __init__(self):
        self.target_sector_weights = {
            'banking': {'min': 0.25, 'target': 0.30, 'max': 0.35},
            'telecommunications': {'min': 0.10, 'target': 0.15, 'max': 0.20},
            'consumer_goods': {'min': 0.15, 'target': 0.20, 'max': 0.25},
            'mining': {'min': 0.08, 'target': 0.12, 'max': 0.18},
            'automotive': {'min': 0.05, 'target': 0.08, 'max': 0.12},
            'infrastructure': {'min': 0.05, 'target': 0.08, 'max': 0.12},
            'others': {'min': 0.05, 'target': 0.07, 'max': 0.10}
        }

    def calculate_optimal_allocation(self, market_conditions, economic_indicators):
        """Calculate optimal sector allocation based on conditions"""
        allocation = {}

        for sector, bounds in self.target_sector_weights.items():
            # Base allocation
            base_weight = bounds['target']

            # Adjust based on sector outlook
            sector_adjustment = self.get_sector_adjustment(sector, market_conditions, economic_indicators)

            # Apply bounds
            adjusted_weight = np.clip(
                base_weight + sector_adjustment,
                bounds['min'],
                bounds['max']
            )

            allocation[sector] = adjusted_weight

        # Normalize to sum to 1.0
        total_weight = sum(allocation.values())
        allocation = {k: v/total_weight for k, v in allocation.items()}

        return allocation

    def get_sector_adjustment(self, sector, market_conditions, economic_indicators):
        """Calculate sector-specific adjustments"""
        adjustments = {
            'banking': self.banking_adjustment(economic_indicators),
            'telecommunications': self.telecom_adjustment(market_conditions),
            'consumer_goods': self.consumer_adjustment(economic_indicators),
            'mining': self.mining_adjustment(economic_indicators),
        }

        return adjustments.get(sector, 0.0)
```

## Currency Considerations

### IDR Volatility Impact

#### Exchange Rate Modeling
```python
class IDRVolatilityManager:
    """
    Manage IDR volatility impact on portfolio performance
    """
    def __init__(self):
        self.idr_factors = {
            'oil_prices': 0.35,           # Indonesia is oil importer
            'fed_interest_rates': -0.45,  # Capital flow sensitivity
            'china_growth': 0.25,         # Trade relationship
            'commodity_prices': 0.30,     # Commodity exporter
            'political_stability': 0.20,  # Emerging market risk
        }

    def forecast_idr_volatility(self, external_factors):
        """Forecast IDR volatility based on external factors"""
        volatility_score = 0

        for factor, sensitivity in self.idr_factors.items():
            if factor in external_factors:
                factor_impact = external_factors[factor] * sensitivity
                volatility_score += factor_impact

        # Convert to expected volatility range
        if volatility_score > 0.5:
            volatility_regime = 'high'
            expected_volatility = 0.20  # 20% annualized
        elif volatility_score > 0.2:
            volatility_regime = 'medium'
            expected_volatility = 0.15  # 15% annualized
        else:
            volatility_regime = 'low'
            expected_volatility = 0.10  # 10% annualized

        return {
            'volatility_regime': volatility_regime,
            'expected_volatility': expected_volatility,
            'volatility_score': volatility_score
        }

    def adjust_position_sizes_for_idr(self, base_positions, idr_volatility):
        """Adjust position sizes based on IDR volatility expectations"""
        adjusted_positions = {}

        # Volatility adjustment factor
        if idr_volatility['volatility_regime'] == 'high':
            adjustment_factor = 0.8  # Reduce positions by 20%
        elif idr_volatility['volatility_regime'] == 'medium':
            adjustment_factor = 0.9  # Reduce positions by 10%
        else:
            adjustment_factor = 1.0  # No adjustment

        for symbol, position in base_positions.items():
            # Get stock's USD revenue exposure
            usd_exposure = self.get_usd_revenue_exposure(symbol)

            # Stocks with high USD exposure benefit from IDR weakness
            if usd_exposure > 0.3:  # 30%+ USD revenue
                currency_adjustment = 1.1  # Increase by 10%
            elif usd_exposure > 0.1:  # 10-30% USD revenue
                currency_adjustment = 1.05  # Increase by 5%
            else:
                currency_adjustment = 1.0  # No currency adjustment

            # Combined adjustment
            final_adjustment = adjustment_factor * currency_adjustment
            adjusted_positions[symbol] = position * final_adjustment

        return adjusted_positions
```

#### Currency Hedging Strategies
```python
class CurrencyHedgingManager:
    """
    Manage currency exposure for Indonesian equity portfolio
    """
    def __init__(self):
        self.hedging_instruments = {
            'usd_idr_forwards': {
                'available': True,
                'max_tenor': '12_months',
                'minimum_notional': 1000000,  # USD 1M
                'cost_bps': 15  # 15 basis points per month
            },
            'usd_idr_options': {
                'available': True,
                'max_tenor': '6_months',
                'cost_percentage': 0.02,  # 2% premium
                'strike_flexibility': True
            },
            'currency_swaps': {
                'available': False,  # Limited availability
                'institutional_only': True
            }
        }

    def calculate_currency_exposure(self, portfolio):
        """Calculate portfolio's currency exposure"""
        total_exposure = {}

        for symbol, position in portfolio.items():
            company_data = self.get_company_data(symbol)

            # Revenue exposure by currency
            usd_revenue = company_data.get('usd_revenue_pct', 0)
            sgd_revenue = company_data.get('sgd_revenue_pct', 0)
            eur_revenue = company_data.get('eur_revenue_pct', 0)
            idr_revenue = 1 - (usd_revenue + sgd_revenue + eur_revenue)

            position_value = position['market_value']

            # Aggregate exposure
            total_exposure['USD'] = total_exposure.get('USD', 0) + (position_value * usd_revenue)
            total_exposure['SGD'] = total_exposure.get('SGD', 0) + (position_value * sgd_revenue)
            total_exposure['EUR'] = total_exposure.get('EUR', 0) + (position_value * eur_revenue)
            total_exposure['IDR'] = total_exposure.get('IDR', 0) + (position_value * idr_revenue)

        return total_exposure

    def recommend_hedging_strategy(self, currency_exposure, risk_tolerance):
        """Recommend optimal hedging strategy"""
        portfolio_value = sum(currency_exposure.values())
        usd_exposure_pct = currency_exposure.get('USD', 0) / portfolio_value

        hedging_recommendation = {}

        if usd_exposure_pct > 0.3 and risk_tolerance == 'conservative':
            # High USD exposure, conservative investor
            hedge_ratio = min(0.75, usd_exposure_pct * 0.8)  # Hedge up to 75%
            hedging_recommendation = {
                'instrument': 'usd_idr_forwards',
                'hedge_ratio': hedge_ratio,
                'notional_usd': currency_exposure['USD'] * hedge_ratio,
                'tenor': '6_months',
                'expected_cost_bps': 90  # 6 months * 15 bps
            }
        elif usd_exposure_pct > 0.2:
            # Moderate hedging with options
            hedge_ratio = min(0.5, usd_exposure_pct * 0.6)
            hedging_recommendation = {
                'instrument': 'usd_idr_options',
                'hedge_ratio': hedge_ratio,
                'notional_usd': currency_exposure['USD'] * hedge_ratio,
                'strategy': 'put_options',  # Protect against IDR strengthening
                'expected_cost_pct': 0.02
            }
        else:
            # Natural hedging sufficient
            hedging_recommendation = {
                'instrument': 'natural_hedge',
                'recommendation': 'Currency exposure below hedging threshold',
                'alternative': 'Increase USD-revenue stocks in portfolio'
            }

        return hedging_recommendation
```

## Trading Hours & Calendar

### Indonesian Market Calendar

#### Trading Schedule Management
```python
class IDXTradingCalendar:
    """
    Manage Indonesian trading calendar and holidays
    """
    def __init__(self):
        self.standard_hours = {
            'market_open': time(9, 0),      # 09:00 WIB
            'lunch_break_start': time(11, 30),  # 11:30 WIB
            'lunch_break_end': time(13, 30),    # 13:30 WIB
            'market_close': time(15, 49),       # 15:49 WIB
            'timezone': 'Asia/Jakarta'
        }

        # Indonesian public holidays that affect trading
        self.holiday_categories = {
            'national_holidays': [
                'New Year\'s Day', 'Chinese New Year', 'Nyepi (Balinese New Year)',
                'Good Friday', 'Labor Day', 'Vesak Day', 'Independence Day',
                'Eid al-Fitr (2 days)', 'Eid al-Adha', 'Islamic New Year',
                'Prophet Muhammad\'s Birthday', 'Christmas Day'
            ],
            'market_specific': [
                'IDX Anniversary', 'Year-end half day'
            ],
            'emergency_closures': [
                'Natural disasters', 'System maintenance', 'Unusual market conditions'
            ]
        }

    def is_trading_day(self, date):
        """Check if given date is a trading day"""
        # Convert to Jakarta timezone
        jakarta_tz = pytz.timezone('Asia/Jakarta')
        if isinstance(date, str):
            date = pd.to_datetime(date).tz_localize(jakarta_tz)

        # Check if weekend
        if date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False

        # Check against holiday calendar
        if self.is_holiday(date):
            return False

        return True

    def get_trading_session_times(self, date):
        """Get trading session times for specific date"""
        if not self.is_trading_day(date):
            return None

        jakarta_tz = pytz.timezone('Asia/Jakarta')
        date_obj = pd.to_datetime(date).date()

        session_times = {
            'pre_opening_start': datetime.combine(date_obj, time(8, 45)).replace(tzinfo=jakarta_tz),
            'market_open': datetime.combine(date_obj, time(9, 0)).replace(tzinfo=jakarta_tz),
            'lunch_break_start': datetime.combine(date_obj, time(11, 30)).replace(tzinfo=jakarta_tz),
            'lunch_break_end': datetime.combine(date_obj, time(13, 30)).replace(tzinfo=jakarta_tz),
            'market_close': datetime.combine(date_obj, time(15, 49)).replace(tzinfo=jakarta_tz),
            'post_trading_end': datetime.combine(date_obj, time(17, 0)).replace(tzinfo=jakarta_tz)
        }

        # Check for half-day sessions
        if self.is_half_day(date):
            session_times['market_close'] = datetime.combine(date_obj, time(12, 0)).replace(tzinfo=jakarta_tz)

        return session_times

    def get_next_trading_day(self, date, n_days=1):
        """Get next N trading days"""
        current_date = pd.to_datetime(date)
        trading_days = []

        while len(trading_days) < n_days:
            current_date += timedelta(days=1)
            if self.is_trading_day(current_date):
                trading_days.append(current_date)

        return trading_days[0] if n_days == 1 else trading_days
```

#### Ramadan and Eid Impact
```python
class IslamicCalendarImpact:
    """
    Manage Islamic calendar impact on Indonesian markets
    """
    def __init__(self):
        self.ramadan_effects = {
            'trading_volume': -0.15,        # 15% lower volume during Ramadan
            'volatility': -0.10,            # 10% lower volatility
            'foreign_participation': -0.05,  # 5% lower foreign participation
            'lunch_hour_activity': -0.30    # 30% lower activity during lunch
        }

        self.eid_effects = {
            'pre_eid_selling': {
                'period': '5_days_before',
                'volume_increase': 0.25,
                'selling_pressure': 0.15
            },
            'post_eid_buying': {
                'period': '3_days_after',
                'volume_increase': 0.20,
                'buying_interest': 0.10
            }
        }

    def adjust_trading_strategy_for_ramadan(self, base_strategy):
        """Adjust trading strategy during Ramadan period"""
        adjusted_strategy = base_strategy.copy()

        # Reduce position sizes due to lower liquidity
        adjusted_strategy['position_sizing_factor'] *= 0.9

        # Avoid lunch hour trading
        adjusted_strategy['avoid_trading_hours'] = ['11:30-13:30']

        # Focus on more liquid LQ45 stocks
        adjusted_strategy['minimum_liquidity_score'] *= 1.2

        # Reduce trading frequency
        adjusted_strategy['signal_threshold'] *= 1.1

        return adjusted_strategy
```

## Market Data Sources

### Primary Data Providers

#### IDX Official Data Feed
```python
class IDXDataManager:
    """
    Manage connection to official IDX market data
    """
    def __init__(self):
        self.data_sources = {
            'idx_market_data_feed': {
                'type': 'real_time',
                'latency': '< 100ms',
                'coverage': 'All listed securities',
                'cost_monthly_usd': 3500,
                'data_types': ['trades', 'quotes', 'indices', 'corporate_actions']
            },
            'idx_historical_data': {
                'type': 'historical',
                'coverage': '10+ years',
                'granularity': 'tick_level',
                'cost_monthly_usd': 1500
            },
            'idx_fundamental_data': {
                'type': 'fundamental',
                'update_frequency': 'quarterly',
                'coverage': 'Listed companies',
                'cost_monthly_usd': 800
            }
        }

    async def connect_to_idx_feed(self):
        """Establish connection to IDX market data feed"""
        connection_config = {
            'host': 'marketdata.idx.co.id',
            'port': 9999,
            'protocol': 'FIX/FAST',
            'authentication': 'certificate_based',
            'heartbeat_interval': 30,
            'reconnect_attempts': 5
        }

        try:
            self.idx_connection = await self.establish_connection(connection_config)
            await self.subscribe_to_lq45_feeds()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to IDX feed: {e}")
            return False

    async def subscribe_to_lq45_feeds(self):
        """Subscribe to LQ45 stock data feeds"""
        lq45_symbols = self.get_lq45_symbols()

        subscriptions = []
        for symbol in lq45_symbols:
            subscriptions.extend([
                f"TRADE.{symbol}",      # Trade data
                f"QUOTE.{symbol}",      # Best bid/offer
                f"DEPTH.{symbol}",      # Market depth
                f"STATS.{symbol}"       # Daily statistics
            ])

        await self.idx_connection.subscribe(subscriptions)
```

#### Alternative Data Sources
```python
class AlternativeDataSources:
    """
    Manage alternative data sources for enhanced signals
    """
    def __init__(self):
        self.data_sources = {
            'refinitiv_eikon': {
                'coverage': 'IDX + regional',
                'cost_monthly_usd': 1200,
                'data_types': ['fundamentals', 'estimates', 'news']
            },
            'bloomberg_terminal': {
                'coverage': 'Global + IDX',
                'cost_monthly_usd': 2000,
                'data_types': ['real_time', 'analytics', 'news']
            },
            'yahoo_finance_indonesia': {
                'coverage': 'IDX major stocks',
                'cost_monthly_usd': 0,  # Free
                'delay': '15_minutes',
                'reliability': 'backup_only'
            },
            'bank_indonesia': {
                'coverage': 'Economic indicators',
                'cost_monthly_usd': 0,  # Public data
                'data_types': ['interest_rates', 'inflation', 'forex']
            },
            'indonesia_news_apis': {
                'sources': ['detik.com', 'cnnindonesia.com', 'kompas.com'],
                'cost_monthly_usd': 300,
                'data_types': ['financial_news', 'market_sentiment']
            }
        }

    def get_news_sentiment_data(self, symbols, lookback_days=7):
        """Collect and process Indonesian financial news"""
        news_data = []

        for symbol in symbols:
            # Search for news mentioning the company
            company_name = self.get_company_name(symbol)
            search_terms = [symbol, company_name]

            # Collect from multiple sources
            for source in self.news_sources:
                articles = source.search_articles(
                    search_terms=search_terms,
                    start_date=datetime.now() - timedelta(days=lookback_days),
                    language='id'  # Indonesian language
                )

                # Process sentiment for each article
                for article in articles:
                    sentiment_score = self.analyze_indonesian_sentiment(article['content'])

                    news_data.append({
                        'symbol': symbol,
                        'headline': article['title'],
                        'content': article['content'],
                        'sentiment_score': sentiment_score,
                        'source': source.name,
                        'publish_date': article['date'],
                        'relevance_score': self.calculate_relevance(article, symbol)
                    })

        return news_data

    def analyze_indonesian_sentiment(self, text):
        """Analyze sentiment of Indonesian financial text"""
        # Use Indonesian-specific sentiment model
        sentiment_model = IndonesianFinancialSentiment()

        # Clean and preprocess text
        cleaned_text = self.preprocess_indonesian_text(text)

        # Get sentiment score
        sentiment_result = sentiment_model.analyze(cleaned_text)

        return {
            'score': sentiment_result['score'],        # -1 to 1
            'confidence': sentiment_result['confidence'],  # 0 to 1
            'keywords': sentiment_result['keywords']
        }
```

## Local Broker Integration

### Broker API Integration

#### Major Indonesian Brokers
```python
class IndonesianBrokerIntegration:
    """
    Integration with major Indonesian securities brokers
    """
    def __init__(self):
        self.supported_brokers = {
            'mandiri_sekuritas': {
                'api_available': True,
                'api_type': 'REST + WebSocket',
                'commission_rate': 0.0015,  # 0.15%
                'minimum_commission': 25000,  # IDR 25,000
                'api_costs': 0  # No API fees
            },
            'bni_securities': {
                'api_available': True,
                'api_type': 'REST',
                'commission_rate': 0.0018,  # 0.18%
                'minimum_commission': 25000,
                'api_costs': 0
            },
            'cimb_niaga': {
                'api_available': True,
                'api_type': 'FIX Protocol',
                'commission_rate': 0.0015,
                'minimum_commission': 25000,
                'api_costs': 500  # USD per month
            },
            'mirae_asset': {
                'api_available': True,
                'api_type': 'REST + WebSocket',
                'commission_rate': 0.0012,  # 0.12%
                'minimum_commission': 25000,
                'api_costs': 0
            }
        }

    async def execute_trade_via_broker(self, broker_name, trade_order):
        """Execute trade through broker API"""
        broker_config = self.supported_brokers.get(broker_name)
        if not broker_config:
            raise ValueError(f"Broker {broker_name} not supported")

        # Calculate total costs
        trade_value = trade_order['quantity'] * trade_order['price']
        commission = max(
            trade_value * broker_config['commission_rate'],
            broker_config['minimum_commission']
        )

        # Add Indonesian taxes
        transaction_tax = trade_value * 0.001 if trade_order['side'] == 'sell' else 0
        stamp_duty = 6000 if trade_order['side'] == 'sell' else 0

        total_costs = commission + transaction_tax + stamp_duty

        # Format order for broker API
        broker_order = {
            'symbol': trade_order['symbol'],
            'side': trade_order['side'],
            'quantity': trade_order['quantity'],
            'price': trade_order['price'],
            'order_type': trade_order.get('order_type', 'limit'),
            'time_in_force': 'DAY',
            'client_order_id': self.generate_order_id()
        }

        # Submit to broker
        broker_api = self.get_broker_api(broker_name)
        execution_result = await broker_api.submit_order(broker_order)

        # Process execution result
        if execution_result['status'] == 'filled':
            return {
                'status': 'executed',
                'fill_price': execution_result['fill_price'],
                'fill_quantity': execution_result['fill_quantity'],
                'commission': commission,
                'total_costs': total_costs,
                'order_id': execution_result['order_id'],
                'execution_time': execution_result['timestamp']
            }
        else:
            return {
                'status': 'pending',
                'order_id': execution_result['order_id'],
                'estimated_costs': total_costs
            }
```

#### Order Management System
```python
class IDXOrderManager:
    """
    Specialized order management for IDX trading
    """
    def __init__(self):
        self.order_types = {
            'market': 'Execute at best available price',
            'limit': 'Execute at specified price or better',
            'stop_limit': 'Stop order that becomes limit order'
        }

        self.execution_algorithms = {
            'twap': 'Time-Weighted Average Price',
            'vwap': 'Volume-Weighted Average Price',
            'implementation_shortfall': 'Minimize market impact',
            'arrival_price': 'Trade close to decision price'
        }

    def optimize_order_execution(self, order, market_conditions):
        """Optimize order execution strategy"""
        order_size = order['quantity'] * order['price']
        daily_volume = market_conditions.get('avg_daily_volume', 0)

        # Calculate as percentage of daily volume
        volume_participation = order_size / daily_volume if daily_volume > 0 else 1

        execution_strategy = {}

        if volume_participation < 0.05:  # Less than 5% of daily volume
            execution_strategy = {
                'method': 'single_order',
                'order_type': 'limit',
                'urgency': 'normal',
                'expected_slippage': 0.05  # 5 basis points
            }
        elif volume_participation < 0.15:  # 5-15% of daily volume
            execution_strategy = {
                'method': 'twap',
                'duration_minutes': 30,
                'slice_size': 0.03,  # 3% of daily volume per slice
                'expected_slippage': 0.15  # 15 basis points
            }
        else:  # Large order > 15% of daily volume
            execution_strategy = {
                'method': 'implementation_shortfall',
                'duration_minutes': 120,  # Spread over 2 hours
                'max_participation': 0.10,  # Max 10% participation
                'expected_slippage': 0.30  # 30 basis points
            }

        return execution_strategy

    def apply_idx_specific_constraints(self, order):
        """Apply IDX-specific trading constraints"""
        constraints = {}

        # Lot size constraint (100 shares minimum)
        if order['quantity'] % 100 != 0:
            constraints['lot_size_error'] = f"Quantity must be multiple of 100, got {order['quantity']}"

        # Price tick size constraint
        tick_size = self.get_tick_size(order['price'])
        if order['price'] % tick_size != 0:
            constraints['tick_size_error'] = f"Price must be multiple of {tick_size}"

        # Auto-rejection limits
        if 'previous_close' in order:
            price_limits = self.calculate_price_limits(order['previous_close'])
            if order['price'] > price_limits['upper_limit']:
                constraints['upper_limit_error'] = f"Price exceeds upper limit of {price_limits['upper_limit']}"
            elif order['price'] < price_limits['lower_limit']:
                constraints['lower_limit_error'] = f"Price below lower limit of {price_limits['lower_limit']}"

        # Foreign ownership limits
        if order.get('investor_type') == 'foreign':
            foreign_room = self.check_foreign_ownership_room(order['symbol'])
            if not foreign_room['can_buy'] and order['side'] == 'buy':
                constraints['foreign_limit_error'] = "No foreign ownership room available"

        return constraints
```

## Risk Management Adaptations

### IDX-Specific Risk Factors

#### Emerging Market Risk Adjustments
```python
class IDXRiskManager:
    """
    Risk management adapted for Indonesian market characteristics
    """
    def __init__(self):
        self.risk_adjustments = {
            'emerging_market_premium': 0.05,    # 5% additional risk premium
            'liquidity_risk_factor': 1.2,       # 20% higher liquidity risk
            'political_risk_factor': 1.15,      # 15% political risk adjustment
            'currency_risk_factor': 1.3,        # 30% higher currency volatility
            'concentration_penalty': 1.25       # 25% penalty for concentration
        }

        self.sector_risk_multipliers = {
            'banking': 1.0,              # Base risk
            'telecommunications': 1.1,   # Regulatory risk
            'mining': 1.4,              # Commodity price volatility
            'property': 1.3,            # Interest rate sensitivity
            'consumer_goods': 0.9,       # Defensive characteristics
            'infrastructure': 1.2        # Government policy risk
        }

    def calculate_adjusted_var(self, portfolio_var, portfolio_composition):
        """Calculate VaR adjusted for IDX-specific risks"""
        base_var = portfolio_var

        # Emerging market adjustment
        em_adjusted_var = base_var * (1 + self.risk_adjustments['emerging_market_premium'])

        # Sector concentration adjustment
        sector_weights = self.calculate_sector_weights(portfolio_composition)
        concentration_penalty = self.calculate_concentration_penalty(sector_weights)

        # Liquidity adjustment
        liquidity_score = self.calculate_portfolio_liquidity_score(portfolio_composition)
        liquidity_adjustment = self.risk_adjustments['liquidity_risk_factor'] * (1 - liquidity_score)

        # Final adjusted VaR
        adjusted_var = em_adjusted_var * concentration_penalty * (1 + liquidity_adjustment)

        return {
            'base_var': base_var,
            'emerging_market_var': em_adjusted_var,
            'concentration_penalty': concentration_penalty,
            'liquidity_adjustment': liquidity_adjustment,
            'final_adjusted_var': adjusted_var,
            'adjustment_factors': {
                'em_premium': self.risk_adjustments['emerging_market_premium'],
                'concentration': concentration_penalty - 1,
                'liquidity': liquidity_adjustment
            }
        }

    def apply_indonesian_position_limits(self, target_positions):
        """Apply position limits specific to Indonesian regulations"""
        adjusted_positions = {}
        total_portfolio_value = sum(pos['market_value'] for pos in target_positions.values())

        for symbol, position in target_positions.items():
            # Basic position size limit (5% of portfolio)
            max_position_value = total_portfolio_value * 0.05

            # Get stock-specific factors
            stock_info = self.get_stock_info(symbol)

            # Liquidity adjustment
            liquidity_score = stock_info.get('liquidity_score', 0.5)
            if liquidity_score < 0.7:  # Low liquidity stocks
                max_position_value *= 0.7  # Reduce by 30%

            # Sector limits
            sector = stock_info.get('sector', 'unknown')
            sector_limit = self.get_sector_limit(sector)
            sector_current_exposure = self.calculate_sector_exposure(symbol, target_positions)

            if sector_current_exposure > sector_limit:
                # Reduce position to stay within sector limit
                reduction_factor = sector_limit / sector_current_exposure
                max_position_value *= reduction_factor

            # Foreign ownership room check
            if stock_info.get('foreign_room_limited', False):
                max_position_value *= 0.8  # Conservative sizing

            # Apply the most restrictive limit
            current_value = position['market_value']
            if current_value > max_position_value:
                adjustment_factor = max_position_value / current_value
                adjusted_positions[symbol] = {
                    'original_size': position,
                    'adjusted_size': position.copy(),
                    'adjustment_factor': adjustment_factor,
                    'reason': 'Position limit compliance'
                }
                adjusted_positions[symbol]['adjusted_size']['market_value'] = max_position_value
            else:
                adjusted_positions[symbol] = {
                    'original_size': position,
                    'adjusted_size': position,
                    'adjustment_factor': 1.0,
                    'reason': 'No adjustment needed'
                }

        return adjusted_positions
```

### Stress Testing for IDX

#### Indonesian Market Stress Scenarios
```python
class IDXStressTestingFramework:
    """
    Stress testing framework for Indonesian market conditions
    """
    def __init__(self):
        self.stress_scenarios = {
            'fed_rate_hike': {
                'description': 'US Federal Reserve aggressive rate hiking',
                'idr_impact': -0.15,        # 15% IDR weakening
                'foreign_outflow': -0.25,   # 25% foreign selling
                'banking_sector_impact': -0.20,
                'duration_days': 30
            },
            'china_slowdown': {
                'description': 'Chinese economic growth slowdown',
                'commodity_impact': -0.30,  # 30% commodity price decline
                'mining_sector_impact': -0.35,
                'export_impact': -0.15,
                'duration_days': 90
            },
            'oil_price_shock': {
                'description': 'Oil price spike due to geopolitical tensions',
                'oil_price_increase': 0.50,  # 50% oil price increase
                'inflation_impact': 0.03,    # 3% additional inflation
                'transportation_impact': -0.25,
                'consumer_impact': -0.15,
                'duration_days': 60
            },
            'domestic_political_crisis': {
                'description': 'Major domestic political instability',
                'market_decline': -0.25,     # 25% market decline
                'idr_impact': -0.20,         # 20% IDR weakening
                'volatility_increase': 2.0,   # 100% volatility increase
                'duration_days': 45
            },
            'banking_crisis': {
                'description': 'Major bank failure or credit crisis',
                'banking_sector_decline': -0.40,  # 40% banking sector decline
                'credit_crunch': True,
                'liquidity_crisis': True,
                'contagion_effect': -0.15,   # 15% overall market impact
                'duration_days': 120
            }
        }

    def run_stress_test(self, portfolio, scenario_name):
        """Run specific stress test scenario"""
        scenario = self.stress_scenarios.get(scenario_name)
        if not scenario:
            raise ValueError(f"Unknown scenario: {scenario_name}")

        stress_results = {}

        # Calculate base portfolio metrics
        base_value = sum(pos['market_value'] for pos in portfolio.values())
        base_sector_exposure = self.calculate_sector_exposure_dict(portfolio)

        # Apply scenario stresses
        stressed_portfolio = {}
        total_impact = 0

        for symbol, position in portfolio.items():
            stock_info = self.get_stock_info(symbol)
            sector = stock_info.get('sector', 'unknown')

            # Base market impact
            market_impact = scenario.get('market_decline', 0)

            # Sector-specific impacts
            sector_impact = 0
            if 'banking_sector_impact' in scenario and sector == 'banking':
                sector_impact = scenario['banking_sector_impact']
            elif 'mining_sector_impact' in scenario and sector == 'mining':
                sector_impact = scenario['mining_sector_impact']
            elif 'transportation_impact' in scenario and sector == 'transportation':
                sector_impact = scenario['transportation_impact']
            elif 'consumer_impact' in scenario and sector == 'consumer_goods':
                sector_impact = scenario['consumer_impact']

            # Currency impact for USD-revenue companies
            currency_impact = 0
            if 'idr_impact' in scenario:
                usd_revenue_pct = stock_info.get('usd_revenue_pct', 0)
                # Positive for USD revenue companies when IDR weakens
                currency_impact = scenario['idr_impact'] * usd_revenue_pct * -1

            # Total impact
            total_stock_impact = market_impact + sector_impact + currency_impact

            # Apply to position
            stressed_value = position['market_value'] * (1 + total_stock_impact)
            stressed_portfolio[symbol] = {
                'original_value': position['market_value'],
                'stressed_value': stressed_value,
                'impact_breakdown': {
                    'market': market_impact,
                    'sector': sector_impact,
                    'currency': currency_impact,
                    'total': total_stock_impact
                }
            }

            total_impact += stressed_value - position['market_value']

        # Calculate portfolio-level results
        stressed_portfolio_value = sum(pos['stressed_value'] for pos in stressed_portfolio.values())
        portfolio_impact_pct = total_impact / base_value

        stress_results = {
            'scenario': scenario_name,
            'scenario_description': scenario['description'],
            'portfolio_impact': {
                'base_value': base_value,
                'stressed_value': stressed_portfolio_value,
                'absolute_impact': total_impact,
                'percentage_impact': portfolio_impact_pct
            },
            'position_impacts': stressed_portfolio,
            'risk_metrics': self.calculate_stressed_risk_metrics(stressed_portfolio, scenario),
            'duration_days': scenario.get('duration_days', 30)
        }

        return stress_results

    def run_comprehensive_stress_test(self, portfolio):
        """Run all stress test scenarios"""
        comprehensive_results = {}

        for scenario_name in self.stress_scenarios.keys():
            comprehensive_results[scenario_name] = self.run_stress_test(portfolio, scenario_name)

        # Identify worst-case scenario
        worst_case = min(
            comprehensive_results.items(),
            key=lambda x: x[1]['portfolio_impact']['percentage_impact']
        )

        # Calculate diversification benefits
        individual_worst_case = sum(
            min(result['position_impacts'][symbol]['impact_breakdown']['total'] for result in comprehensive_results.values())
            * portfolio[symbol]['market_value']
            for symbol in portfolio.keys()
        )

        actual_worst_case = worst_case[1]['portfolio_impact']['absolute_impact']
        diversification_benefit = individual_worst_case - actual_worst_case

        return {
            'individual_scenarios': comprehensive_results,
            'worst_case_scenario': worst_case[0],
            'worst_case_impact': worst_case[1]['portfolio_impact']['percentage_impact'],
            'diversification_benefit': diversification_benefit / sum(pos['market_value'] for pos in portfolio.values()),
            'stress_test_date': datetime.now()
        }
```

## Performance Benchmarking

### Indonesian Market Benchmarks

#### Benchmark Selection and Comparison
```python
class IDXBenchmarkManager:
    """
    Manage benchmarking against Indonesian market indices
    """
    def __init__(self):
        self.benchmarks = {
            'jci': {
                'name': 'Jakarta Composite Index',
                'description': 'Main market index',
                'coverage': 'All listed stocks',
                'weighting': 'market_cap',
                'base_date': '1982-08-10',
                'base_value': 100
            },
            'lq45': {
                'name': 'LQ45 Index',
                'description': 'Top 45 liquid stocks',
                'coverage': '45 most liquid stocks',
                'weighting': 'market_cap',
                'review_frequency': 'semi_annual'
            },
            'idx30': {
                'name': 'IDX30 Index',
                'description': 'Top 30 stocks by liquidity and market cap',
                'coverage': '30 largest and most liquid stocks',
                'weighting': 'market_cap'
            },
            'jii': {
                'name': 'Jakarta Islamic Index',
                'description': 'Sharia-compliant stocks',
                'coverage': 'Sharia-compliant stocks',
                'screening': 'islamic_principles'
            }
        }

    def calculate_benchmark_performance(self, benchmark_name, start_date, end_date):
        """Calculate benchmark performance over period"""
        benchmark_data = self.get_benchmark_data(benchmark_name, start_date, end_date)

        # Calculate returns
        benchmark_returns = benchmark_data['close'].pct_change().dropna()

        performance_metrics = {
            'total_return': (benchmark_data['close'].iloc[-1] / benchmark_data['close'].iloc[0]) - 1,
            'annualized_return': self.annualize_return(
                benchmark_data['close'].iloc[-1] / benchmark_data['close'].iloc[0] - 1,
                (end_date - start_date).days
            ),
            'volatility': benchmark_returns.std() * np.sqrt(252),
            'max_drawdown': self.calculate_max_drawdown(benchmark_data['close']),
            'sharpe_ratio': self.calculate_sharpe_ratio(benchmark_returns),
            'calmar_ratio': self.calculate_calmar_ratio(benchmark_returns),
            'positive_days': (benchmark_returns > 0).mean(),
            'average_up_day': benchmark_returns[benchmark_returns > 0].mean(),
            'average_down_day': benchmark_returns[benchmark_returns < 0].mean()
        }

        return performance_metrics

    def compare_portfolio_to_benchmarks(self, portfolio_returns, benchmarks=['jci', 'lq45']):
        """Compare portfolio performance to multiple benchmarks"""
        comparison_results = {}

        for benchmark_name in benchmarks:
            benchmark_returns = self.get_benchmark_returns(benchmark_name, portfolio_returns.index)

            # Calculate relative metrics
            active_returns = portfolio_returns - benchmark_returns
            tracking_error = active_returns.std() * np.sqrt(252)
            information_ratio = active_returns.mean() / active_returns.std() * np.sqrt(252)

            # Beta calculation
            portfolio_var = portfolio_returns.var()
            covariance = np.cov(portfolio_returns, benchmark_returns)[0, 1]
            beta = covariance / benchmark_returns.var()

            # Alpha calculation (using 6% risk-free rate)
            risk_free_rate = 0.06 / 252  # Daily risk-free rate
            alpha = (portfolio_returns.mean() - risk_free_rate) - beta * (benchmark_returns.mean() - risk_free_rate)
            alpha_annualized = alpha * 252

            # Up/down capture ratios
            up_market_days = benchmark_returns > 0
            down_market_days = benchmark_returns < 0

            up_capture = (portfolio_returns[up_market_days].mean() / benchmark_returns[up_market_days].mean()) if up_market_days.any() else 0
            down_capture = (portfolio_returns[down_market_days].mean() / benchmark_returns[down_market_days].mean()) if down_market_days.any() else 0

            comparison_results[benchmark_name] = {
                'portfolio_total_return': (1 + portfolio_returns).prod() - 1,
                'benchmark_total_return': (1 + benchmark_returns).prod() - 1,
                'excess_return': (1 + portfolio_returns).prod() - (1 + benchmark_returns).prod(),
                'tracking_error': tracking_error,
                'information_ratio': information_ratio,
                'beta': beta,
                'alpha_annualized': alpha_annualized,
                'up_capture_ratio': up_capture,
                'down_capture_ratio': down_capture,
                'correlation': np.corrcoef(portfolio_returns, benchmark_returns)[0, 1]
            }

        return comparison_results

    def generate_attribution_analysis(self, portfolio_holdings, benchmark_weights, returns_data):
        """Generate performance attribution analysis"""
        attribution_results = {}

        # Calculate portfolio and benchmark returns by sector
        portfolio_sector_returns = self.calculate_sector_returns(portfolio_holdings, returns_data)
        benchmark_sector_returns = self.calculate_sector_returns(benchmark_weights, returns_data)

        # Allocation effect: (wp - wb) * rb
        # Selection effect: wb * (rp - rb)
        # Interaction effect: (wp - wb) * (rp - rb)

        for sector in set(portfolio_sector_returns.keys()) | set(benchmark_sector_returns.keys()):
            wp = portfolio_holdings.get(sector, {}).get('weight', 0)  # Portfolio weight
            wb = benchmark_weights.get(sector, {}).get('weight', 0)   # Benchmark weight
            rp = portfolio_sector_returns.get(sector, 0)             # Portfolio sector return
            rb = benchmark_sector_returns.get(sector, 0)             # Benchmark sector return

            allocation_effect = (wp - wb) * rb
            selection_effect = wb * (rp - rb)
            interaction_effect = (wp - wb) * (rp - rb)

            attribution_results[sector] = {
                'portfolio_weight': wp,
                'benchmark_weight': wb,
                'portfolio_return': rp,
                'benchmark_return': rb,
                'allocation_effect': allocation_effect,
                'selection_effect': selection_effect,
                'interaction_effect': interaction_effect,
                'total_effect': allocation_effect + selection_effect + interaction_effect
            }

        # Summary attribution
        total_allocation = sum(attr['allocation_effect'] for attr in attribution_results.values())
        total_selection = sum(attr['selection_effect'] for attr in attribution_results.values())
        total_interaction = sum(attr['interaction_effect'] for attr in attribution_results.values())

        attribution_summary = {
            'total_allocation_effect': total_allocation,
            'total_selection_effect': total_selection,
            'total_interaction_effect': total_interaction,
            'total_active_return': total_allocation + total_selection + total_interaction,
            'sector_attribution': attribution_results
        }

        return attribution_summary
```

This comprehensive documentation demonstrates Project Aurum's deep understanding and optimization for the Indonesian market, ensuring the system operates effectively within the unique characteristics, regulations, and constraints of the IDX ecosystem.