"""
Indonesian Market-Specific Test Fixtures
Provides realistic IDX market data, LQ45 stocks, and Indonesian market conditions
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from decimal import Decimal
import pytz
from typing import Dict, List, Any


class IndonesianMarketFixtures:
    """Indonesian market-specific test data generator"""

    @staticmethod
    def get_lq45_stocks() -> List[Dict[str, Any]]:
        """Get realistic LQ45 stock data"""
        return [
            {
                "code": "BBCA",
                "name": "Bank Central Asia Tbk",
                "sector": "Financial Services",
                "subsector": "Banks",
                "market_cap": 1250000000000,  # 1.25T IDR
                "listing_date": "2000-05-31",
                "shares_outstanding": 25000000000,
                "board": "MAIN",
                "is_lq45": True,
                "is_idx30": True,
                "weight_lq45": 8.5,
                "weight_idx30": 12.3
            },
            {
                "code": "BBRI",
                "name": "Bank Rakyat Indonesia (Persero) Tbk",
                "sector": "Financial Services",
                "subsector": "Banks",
                "market_cap": 900000000000,
                "listing_date": "2003-11-10",
                "shares_outstanding": 117000000000,
                "board": "MAIN",
                "is_lq45": True,
                "is_idx30": True,
                "weight_lq45": 7.2,
                "weight_idx30": 10.8
            },
            {
                "code": "TLKM",
                "name": "Telekomunikasi Indonesia (Persero) Tbk",
                "sector": "Technology",
                "subsector": "Telecommunications",
                "market_cap": 750000000000,
                "listing_date": "1995-11-14",
                "shares_outstanding": 100000000000,
                "board": "MAIN",
                "is_lq45": True,
                "is_idx30": True,
                "weight_lq45": 6.8,
                "weight_idx30": 9.5
            },
            {
                "code": "ASII",
                "name": "Astra International Tbk",
                "sector": "Consumer Cyclicals",
                "subsector": "Automotive & Components",
                "market_cap": 600000000000,
                "listing_date": "1990-04-04",
                "shares_outstanding": 40000000000,
                "board": "MAIN",
                "is_lq45": True,
                "is_idx30": True,
                "weight_lq45": 5.9,
                "weight_idx30": 8.2
            },
            {
                "code": "UNVR",
                "name": "Unilever Indonesia Tbk",
                "sector": "Consumer Non-Cyclicals",
                "subsector": "Household & Personal Products",
                "market_cap": 550000000000,
                "listing_date": "1982-01-11",
                "shares_outstanding": 7600000000,
                "board": "MAIN",
                "is_lq45": True,
                "is_idx30": True,
                "weight_lq45": 4.8,
                "weight_idx30": 7.1
            },
            {
                "code": "BMRI",
                "name": "Bank Mandiri (Persero) Tbk",
                "sector": "Financial Services",
                "subsector": "Banks",
                "market_cap": 480000000000,
                "listing_date": "2003-07-09",
                "shares_outstanding": 24000000000,
                "board": "MAIN",
                "is_lq45": True,
                "is_idx30": True,
                "weight_lq45": 4.2,
                "weight_idx30": 6.5
            },
            {
                "code": "GGRM",
                "name": "Gudang Garam Tbk",
                "sector": "Consumer Non-Cyclicals",
                "subsector": "Tobacco",
                "market_cap": 380000000000,
                "listing_date": "1990-08-27",
                "shares_outstanding": 1900000000,
                "board": "MAIN",
                "is_lq45": True,
                "is_idx30": False,
                "weight_lq45": 3.8,
                "weight_idx30": 0.0
            },
            {
                "code": "ICBP",
                "name": "Indofood CBP Sukses Makmur Tbk",
                "sector": "Consumer Non-Cyclicals",
                "subsector": "Food & Beverages",
                "market_cap": 340000000000,
                "listing_date": "2010-10-07",
                "shares_outstanding": 8750000000,
                "board": "MAIN",
                "is_lq45": True,
                "is_idx30": True,
                "weight_lq45": 3.5,
                "weight_idx30": 5.2
            },
            {
                "code": "INTP",
                "name": "Indocement Tunggal Prakarsa Tbk",
                "sector": "Basic Materials",
                "subsector": "Construction Materials",
                "market_cap": 320000000000,
                "listing_date": "1989-12-05",
                "shares_outstanding": 3100000000,
                "board": "MAIN",
                "is_lq45": True,
                "is_idx30": True,
                "weight_lq45": 3.2,
                "weight_idx30": 4.8
            },
            {
                "code": "KLBF",
                "name": "Kalbe Farma Tbk",
                "sector": "Healthcare",
                "subsector": "Pharmaceuticals",
                "market_cap": 300000000000,
                "listing_date": "1991-07-30",
                "shares_outstanding": 46000000000,
                "board": "MAIN",
                "is_lq45": True,
                "is_idx30": True,
                "weight_lq45": 2.9,
                "weight_idx30": 4.1
            }
        ]

    @staticmethod
    def get_market_hours() -> Dict[str, Any]:
        """Get IDX market hours in WIB timezone"""
        return {
            "timezone": "Asia/Jakarta",
            "currency": "IDR",
            "regular_session": {
                "start_time": "09:00",
                "end_time": "15:49",
                "break_start": "11:30",
                "break_end": "13:30"
            },
            "pre_market": {
                "start_time": "08:30",
                "end_time": "09:00"
            },
            "post_market": {
                "start_time": "15:50",
                "end_time": "16:00"
            },
            "trading_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "holidays": [
                "2024-01-01",  # New Year
                "2024-02-08",  # Chinese New Year
                "2024-02-09",  # Chinese New Year
                "2024-03-11",  # Nyepi
                "2024-03-29",  # Good Friday
                "2024-05-01",  # Labor Day
                "2024-05-09",  # Ascension Day
                "2024-06-01",  # Pancasila Day
                "2024-06-17",  # Eid al-Adha
                "2024-08-17",  # Independence Day
                "2024-12-25",  # Christmas
            ]
        }

    @staticmethod
    def get_currency_data(start_date: date, end_date: date) -> pd.DataFrame:
        """Generate realistic USD/IDR exchange rate data"""
        dates = pd.date_range(start=start_date, end=end_date, freq='D')

        # Realistic IDR exchange rate (around 15,000-16,000 per USD)
        np.random.seed(42)
        base_rate = 15500

        # Generate realistic exchange rate movements
        returns = np.random.normal(0.0002, 0.008, len(dates))  # Small daily changes
        rates = [base_rate]

        for ret in returns[1:]:
            new_rate = rates[-1] * (1 + ret)
            # Keep within realistic bounds
            rates.append(max(14000, min(17000, new_rate)))

        return pd.DataFrame({
            'date': dates,
            'usd_idr_rate': rates,
            'bid': [r * 0.9995 for r in rates],  # Bid slightly lower
            'ask': [r * 1.0005 for r in rates],  # Ask slightly higher
            'volume_usd': np.random.uniform(50000000, 200000000, len(dates))
        })

    @staticmethod
    def generate_stock_price_data(stock_code: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Generate realistic Indonesian stock price data"""
        dates = pd.date_range(start=start_date, end=end_date, freq='D')

        # Stock-specific base prices and characteristics
        stock_params = {
            "BBCA": {"base_price": 9000, "volatility": 0.02, "trend": 0.0002},
            "BBRI": {"base_price": 4500, "volatility": 0.025, "trend": 0.0001},
            "TLKM": {"base_price": 3500, "volatility": 0.022, "trend": -0.0001},
            "ASII": {"base_price": 6500, "volatility": 0.03, "trend": 0.0001},
            "UNVR": {"base_price": 3800, "volatility": 0.018, "trend": 0.0002},
            "BMRI": {"base_price": 8200, "volatility": 0.024, "trend": 0.0001},
            "GGRM": {"base_price": 68000, "volatility": 0.035, "trend": 0.0003},
            "ICBP": {"base_price": 11000, "volatility": 0.02, "trend": 0.0002},
            "INTP": {"base_price": 9500, "volatility": 0.028, "trend": -0.0002},
            "KLBF": {"base_price": 1500, "volatility": 0.025, "trend": 0.0001}
        }

        params = stock_params.get(stock_code, {"base_price": 5000, "volatility": 0.025, "trend": 0.0})

        np.random.seed(hash(stock_code) % 2147483647)  # Consistent but different for each stock

        # Generate price series
        returns = np.random.normal(params["trend"], params["volatility"], len(dates))
        prices = [params["base_price"]]

        for ret in returns[1:]:
            new_price = prices[-1] * (1 + ret)
            # Ensure prices stay positive and reasonable
            prices.append(max(100, new_price))

        # Generate OHLC data
        opens = []
        highs = []
        lows = []
        volumes = []

        for i, close_price in enumerate(prices):
            # Open price (previous close + gap)
            if i == 0:
                open_price = close_price
            else:
                gap = np.random.normal(0, params["volatility"] * 0.3)
                open_price = prices[i-1] * (1 + gap)
                open_price = max(100, open_price)

            # High and low
            intraday_range = np.random.uniform(0.005, 0.03)  # 0.5% to 3% daily range
            high_price = max(open_price, close_price) * (1 + intraday_range/2)
            low_price = min(open_price, close_price) * (1 - intraday_range/2)

            # Volume (larger volume on larger price moves)
            price_change = abs((close_price - open_price) / open_price) if open_price > 0 else 0
            base_volume = 2000000 if stock_code in ["BBCA", "BBRI", "TLKM"] else 1000000
            volume = int(base_volume * (1 + price_change * 5) * np.random.uniform(0.5, 2.0))

            opens.append(open_price)
            highs.append(high_price)
            lows.append(low_price)
            volumes.append(volume)

        return pd.DataFrame({
            'date': dates,
            'stock_code': stock_code,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': prices,
            'volume': volumes,
            'turnover': [p * v for p, v in zip(prices, volumes)]
        })

    @staticmethod
    def get_sector_classification() -> Dict[str, List[str]]:
        """Get Indonesian sector classification"""
        return {
            "Financial Services": [
                "BBCA", "BBRI", "BMRI", "BBNI", "BTPS", "BRIS",
                "MEGA", "BNLI", "NISP", "PNBN"
            ],
            "Technology": [
                "TLKM", "EXCL", "ISAT", "FREN", "BTEL"
            ],
            "Consumer Cyclicals": [
                "ASII", "AUTO", "BRAM", "IMAS", "INDS", "LPPF", "SMSM"
            ],
            "Consumer Non-Cyclicals": [
                "UNVR", "GGRM", "ICBP", "INDF", "MYOR", "SIDO", "ULTJ"
            ],
            "Basic Materials": [
                "INTP", "SMGR", "ADRO", "ITMG", "PTBA", "TINS", "ANTM"
            ],
            "Healthcare": [
                "KLBF", "KAEF", "PYFA", "DVLA", "MERK"
            ],
            "Energy": [
                "PGAS", "AKRA", "ENRG", "RUIS"
            ],
            "Industrials": [
                "WSKT", "WIKA", "PTPP", "ADHI", "JSMR"
            ],
            "Property": [
                "BSDE", "LPKR", "PWON", "APLN", "SMRA"
            ],
            "Transportation": [
                "JBFB", "TAXI", "BIRD", "HEAL"
            ]
        }

    @staticmethod
    def get_market_indicators(date_range: pd.DatetimeIndex) -> pd.DataFrame:
        """Generate Indonesian market indicators"""
        np.random.seed(42)

        # Generate IHSG (IDX Composite) index
        base_ihsg = 7000
        ihsg_returns = np.random.normal(0.0005, 0.015, len(date_range))
        ihsg_values = [base_ihsg]

        for ret in ihsg_returns[1:]:
            ihsg_values.append(ihsg_values[-1] * (1 + ret))

        # Generate LQ45 index
        base_lq45 = 950
        lq45_returns = np.random.normal(0.0006, 0.018, len(date_range))
        lq45_values = [base_lq45]

        for ret in lq45_returns[1:]:
            lq45_values.append(lq45_values[-1] * (1 + ret))

        return pd.DataFrame({
            'date': date_range,
            'ihsg': ihsg_values,
            'lq45': lq45_values,
            'idx30': [v * 0.95 for v in lq45_values],  # IDX30 typically lower
            'total_volume': np.random.uniform(5e9, 20e9, len(date_range)),
            'total_value': np.random.uniform(3e12, 12e12, len(date_range)),
            'total_transactions': np.random.randint(200000, 800000, len(date_range))
        })

    @staticmethod
    def get_economic_indicators() -> Dict[str, Any]:
        """Get Indonesian economic indicators"""
        return {
            "bi_rate": 6.0,  # Bank Indonesia 7-day reverse repo rate
            "inflation_rate": 2.5,  # Annual inflation rate
            "gdp_growth": 5.2,  # Annual GDP growth
            "government_bond_10y": 6.8,  # 10-year government bond yield
            "trade_balance": 2.5e9,  # Trade balance in USD
            "foreign_reserves": 140e9,  # Foreign reserves in USD
            "rupiah_volatility": 0.8,  # Daily volatility %
            "credit_growth": 8.5,  # Annual credit growth %
            "unemployment_rate": 5.1,  # Unemployment rate %
            "pmi_manufacturing": 52.3,  # Manufacturing PMI
            "consumer_confidence": 125.5  # Consumer confidence index
        }


@pytest.fixture
def lq45_stocks():
    """Fixture for LQ45 stocks data"""
    return IndonesianMarketFixtures.get_lq45_stocks()


@pytest.fixture
def indonesian_market_hours():
    """Fixture for Indonesian market hours"""
    return IndonesianMarketFixtures.get_market_hours()


@pytest.fixture
def usd_idr_rates():
    """Fixture for USD/IDR exchange rates"""
    start_date = date(2024, 1, 1)
    end_date = date(2024, 1, 31)
    return IndonesianMarketFixtures.get_currency_data(start_date, end_date)


@pytest.fixture
def bbca_price_data():
    """Fixture for BBCA stock price data"""
    start_date = date(2024, 1, 1)
    end_date = date(2024, 1, 31)
    return IndonesianMarketFixtures.generate_stock_price_data("BBCA", start_date, end_date)


@pytest.fixture
def lq45_price_data():
    """Fixture for LQ45 stocks price data"""
    start_date = date(2024, 1, 1)
    end_date = date(2024, 1, 31)

    lq45_codes = ["BBCA", "BBRI", "TLKM", "ASII", "UNVR"]
    all_data = []

    for code in lq45_codes:
        stock_data = IndonesianMarketFixtures.generate_stock_price_data(code, start_date, end_date)
        all_data.append(stock_data)

    return pd.concat(all_data, ignore_index=True)


@pytest.fixture
def indonesian_sectors():
    """Fixture for Indonesian sector classification"""
    return IndonesianMarketFixtures.get_sector_classification()


@pytest.fixture
def market_indicators():
    """Fixture for Indonesian market indicators"""
    date_range = pd.date_range(start='2024-01-01', end='2024-01-31', freq='D')
    return IndonesianMarketFixtures.get_market_indicators(date_range)


@pytest.fixture
def economic_indicators():
    """Fixture for Indonesian economic indicators"""
    return IndonesianMarketFixtures.get_economic_indicators()


@pytest.fixture
def jakarta_timezone():
    """Fixture for Jakarta timezone"""
    return pytz.timezone('Asia/Jakarta')


@pytest.fixture
def trading_calendar():
    """Fixture for Indonesian trading calendar"""
    market_data = IndonesianMarketFixtures.get_market_hours()

    # Generate trading dates for 2024 (excluding weekends and holidays)
    start_date = date(2024, 1, 1)
    end_date = date(2024, 12, 31)

    all_dates = pd.date_range(start=start_date, end=end_date, freq='D')

    # Filter out weekends
    weekdays = all_dates[all_dates.dayofweek < 5]  # Monday=0, Friday=4

    # Filter out holidays
    holidays = [datetime.strptime(h, '%Y-%m-%d').date() for h in market_data['holidays']]
    trading_dates = [d.date() for d in weekdays if d.date() not in holidays]

    return {
        'trading_dates': trading_dates,
        'holidays': holidays,
        'total_trading_days': len(trading_dates)
    }


@pytest.fixture
def idx_realtime_data():
    """Fixture for IDX real-time market data simulation"""
    jakarta_tz = pytz.timezone('Asia/Jakarta')
    current_time = datetime.now(jakarta_tz)

    # Generate real-time data for top 10 LQ45 stocks
    stocks = IndonesianMarketFixtures.get_lq45_stocks()[:10]

    realtime_data = []
    for stock in stocks:
        base_price = {
            "BBCA": 9000, "BBRI": 4500, "TLKM": 3500, "ASII": 6500, "UNVR": 3800,
            "BMRI": 8200, "GGRM": 68000, "ICBP": 11000, "INTP": 9500, "KLBF": 1500
        }.get(stock["code"], 5000)

        # Simulate current price with small random movement
        price_change = np.random.uniform(-0.02, 0.02)  # ±2% movement
        current_price = base_price * (1 + price_change)

        realtime_data.append({
            'stock_code': stock['code'],
            'stock_name': stock['name'],
            'current_price': round(current_price, 0),
            'change': round(current_price - base_price, 0),
            'change_percent': round(price_change * 100, 2),
            'volume': np.random.randint(500000, 5000000),
            'value': round(current_price * np.random.randint(500000, 5000000), 0),
            'bid': round(current_price * 0.995, 0),
            'ask': round(current_price * 1.005, 0),
            'last_update': current_time,
            'market_cap': stock['market_cap'],
            'sector': stock['sector'],
            'is_suspended': False,
            'circuit_breaker': None
        })

    return realtime_data


@pytest.fixture
def indonesian_trading_signals():
    """Fixture for Indonesian market trading signals"""
    signals = []
    stocks = ["BBCA", "BBRI", "TLKM", "ASII", "UNVR"]

    for i, stock in enumerate(stocks):
        signal_type = ["BUY", "SELL", "HOLD"][i % 3]

        signals.append({
            'id': i + 1,
            'stock_code': stock,
            'signal_type': signal_type,
            'confidence': np.random.uniform(0.6, 0.95),
            'price_target': np.random.uniform(8000, 12000),
            'stop_loss': np.random.uniform(7000, 9000),
            'time_horizon': np.random.choice(['1D', '3D', '1W', '2W']),
            'generated_at': datetime.now(),
            'valid_until': datetime.now() + timedelta(days=1),
            'strategy': np.random.choice(['momentum', 'mean_reversion', 'breakout', 'earnings']),
            'market_condition': np.random.choice(['bullish', 'bearish', 'neutral']),
            'sector_outlook': np.random.choice(['positive', 'negative', 'neutral']),
            'risk_level': np.random.choice(['low', 'medium', 'high']),
            'metadata': {
                'rsi': np.random.uniform(20, 80),
                'macd': np.random.uniform(-50, 50),
                'volume_profile': np.random.choice(['above_average', 'below_average', 'normal']),
                'news_sentiment': np.random.uniform(-1, 1),
                'analyst_rating': np.random.choice(['strong_buy', 'buy', 'hold', 'sell', 'strong_sell'])
            }
        })

    return signals