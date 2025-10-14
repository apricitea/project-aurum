#!/usr/bin/env python3
"""
Setup Stock Data Pipeline
Creates database tables and seeds stock master data for Indonesian stocks
Run this script once to initialize the data pipeline
"""

import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime, date

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

from api.database import Base
from api.database_extensions import (
    StockMaster, DailyStockPrice, DataRefreshLog,
    StockFundamentals, DataQualityMetric
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Indonesian Stock Master Data
# LQ45 stocks (liquid 45 stocks - most actively traded on IDX)
INDONESIAN_STOCKS = [
    # Banking Sector
    {"stock_code": "BBCA", "yahoo_symbol": "BBCA.JK", "company_name": "Bank Central Asia Tbk",
     "sector": "Banking", "industry": "Commercial Banks", "is_lq45": True, "market_cap_category": "Large"},
    {"stock_code": "BBRI", "yahoo_symbol": "BBRI.JK", "company_name": "Bank Rakyat Indonesia Tbk",
     "sector": "Banking", "industry": "Commercial Banks", "is_lq45": True, "market_cap_category": "Large"},
    {"stock_code": "BMRI", "yahoo_symbol": "BMRI.JK", "company_name": "Bank Mandiri Tbk",
     "sector": "Banking", "industry": "Commercial Banks", "is_lq45": True, "market_cap_category": "Large"},
    {"stock_code": "BBNI", "yahoo_symbol": "BBNI.JK", "company_name": "Bank Negara Indonesia Tbk",
     "sector": "Banking", "industry": "Commercial Banks", "is_lq45": True, "market_cap_category": "Large"},
    {"stock_code": "BRIS", "yahoo_symbol": "BRIS.JK", "company_name": "Bank BRISyariah Indonesia Tbk",
     "sector": "Banking", "industry": "Islamic Banks", "is_lq45": False, "market_cap_category": "Mid"},

    # Consumer Goods
    {"stock_code": "UNVR", "yahoo_symbol": "UNVR.JK", "company_name": "Unilever Indonesia Tbk",
     "sector": "Consumer Goods", "industry": "Personal Care", "is_lq45": True, "market_cap_category": "Large"},
    {"stock_code": "ICBP", "yahoo_symbol": "ICBP.JK", "company_name": "Indofood CBP Sukses Makmur Tbk",
     "sector": "Consumer Goods", "industry": "Food & Beverages", "is_lq45": True, "market_cap_category": "Large"},
    {"stock_code": "INDF", "yahoo_symbol": "INDF.JK", "company_name": "Indofood Sukses Makmur Tbk",
     "sector": "Consumer Goods", "industry": "Food & Beverages", "is_lq45": True, "market_cap_category": "Large"},
    {"stock_code": "KLBF", "yahoo_symbol": "KLBF.JK", "company_name": "Kalbe Farma Tbk",
     "sector": "Healthcare", "industry": "Pharmaceuticals", "is_lq45": True, "market_cap_category": "Large"},

    # Automotive & Industrial
    {"stock_code": "ASII", "yahoo_symbol": "ASII.JK", "company_name": "Astra International Tbk",
     "sector": "Industrial", "industry": "Automotive", "is_lq45": True, "market_cap_category": "Large"},
    {"stock_code": "AUTO", "yahoo_symbol": "AUTO.JK", "company_name": "Astra Otoparts Tbk",
     "sector": "Industrial", "industry": "Auto Parts", "is_lq45": False, "market_cap_category": "Mid"},

    # Telecommunications
    {"stock_code": "TLKM", "yahoo_symbol": "TLKM.JK", "company_name": "Telkom Indonesia Tbk",
     "sector": "Telecommunications", "industry": "Telecom Services", "is_lq45": True, "market_cap_category": "Large"},
    {"stock_code": "ISAT", "yahoo_symbol": "ISAT.JK", "company_name": "Indosat Ooredoo Hutchison Tbk",
     "sector": "Telecommunications", "industry": "Wireless Telecom", "is_lq45": False, "market_cap_category": "Mid"},
    {"stock_code": "EXCL", "yahoo_symbol": "EXCL.JK", "company_name": "XL Axiata Tbk",
     "sector": "Telecommunications", "industry": "Wireless Telecom", "is_lq45": False, "market_cap_category": "Mid"},

    # Mining & Energy
    {"stock_code": "ADRO", "yahoo_symbol": "ADRO.JK", "company_name": "Adaro Energy Indonesia Tbk",
     "sector": "Mining", "industry": "Coal Mining", "is_lq45": True, "market_cap_category": "Large"},
    {"stock_code": "PTBA", "yahoo_symbol": "PTBA.JK", "company_name": "Bukit Asam Tbk",
     "sector": "Mining", "industry": "Coal Mining", "is_lq45": True, "market_cap_category": "Large"},
    {"stock_code": "ITMG", "yahoo_symbol": "ITMG.JK", "company_name": "Indo Tambangraya Megah Tbk",
     "sector": "Mining", "industry": "Coal Mining", "is_lq45": True, "market_cap_category": "Large"},
    {"stock_code": "ANTM", "yahoo_symbol": "ANTM.JK", "company_name": "Aneka Tambang Tbk",
     "sector": "Mining", "industry": "Diversified Metals", "is_lq45": True, "market_cap_category": "Large"},
    {"stock_code": "INCO", "yahoo_symbol": "INCO.JK", "company_name": "Vale Indonesia Tbk",
     "sector": "Mining", "industry": "Nickel Mining", "is_lq45": False, "market_cap_category": "Mid"},
    {"stock_code": "PGAS", "yahoo_symbol": "PGAS.JK", "company_name": "Perusahaan Gas Negara Tbk",
     "sector": "Energy", "industry": "Gas Utilities", "is_lq45": True, "market_cap_category": "Large"},

    # Cement & Construction
    {"stock_code": "SMGR", "yahoo_symbol": "SMGR.JK", "company_name": "Semen Indonesia Tbk",
     "sector": "Basic Materials", "industry": "Cement", "is_lq45": True, "market_cap_category": "Large"},
    {"stock_code": "INTP", "yahoo_symbol": "INTP.JK", "company_name": "Indocement Tunggal Prakarsa Tbk",
     "sector": "Basic Materials", "industry": "Cement", "is_lq45": True, "market_cap_category": "Large"},
    {"stock_code": "WIKA", "yahoo_symbol": "WIKA.JK", "company_name": "Wijaya Karya Tbk",
     "sector": "Infrastructure", "industry": "Construction", "is_lq45": False, "market_cap_category": "Mid"},
    {"stock_code": "PTPP", "yahoo_symbol": "PTPP.JK", "company_name": "PP (Persero) Tbk",
     "sector": "Infrastructure", "industry": "Construction", "is_lq45": False, "market_cap_category": "Mid"},
    {"stock_code": "WSKT", "yahoo_symbol": "WSKT.JK", "company_name": "Waskita Karya Tbk",
     "sector": "Infrastructure", "industry": "Construction", "is_lq45": False, "market_cap_category": "Small"},

    # Property & Real Estate
    {"stock_code": "BSDE", "yahoo_symbol": "BSDE.JK", "company_name": "Bumi Serpong Damai Tbk",
     "sector": "Property", "industry": "Real Estate Development", "is_lq45": True, "market_cap_category": "Large"},
    {"stock_code": "SMRA", "yahoo_symbol": "SMRA.JK", "company_name": "Summarecon Agung Tbk",
     "sector": "Property", "industry": "Real Estate Development", "is_lq45": False, "market_cap_category": "Mid"},
    {"stock_code": "LPKR", "yahoo_symbol": "LPKR.JK", "company_name": "Lippo Karawaci Tbk",
     "sector": "Property", "industry": "Real Estate Development", "is_lq45": False, "market_cap_category": "Mid"},

    # Agriculture
    {"stock_code": "CPIN", "yahoo_symbol": "CPIN.JK", "company_name": "Charoen Pokphand Indonesia Tbk",
     "sector": "Agriculture", "industry": "Poultry & Livestock", "is_lq45": True, "market_cap_category": "Large"},
    {"stock_code": "JPFA", "yahoo_symbol": "JPFA.JK", "company_name": "Japfa Comfeed Indonesia Tbk",
     "sector": "Agriculture", "industry": "Poultry & Livestock", "is_lq45": False, "market_cap_category": "Mid"},

    # Tobacco
    {"stock_code": "HMSP", "yahoo_symbol": "HMSP.JK", "company_name": "HM Sampoerna Tbk",
     "sector": "Consumer Goods", "industry": "Tobacco", "is_lq45": True, "market_cap_category": "Large"},
    {"stock_code": "GGRM", "yahoo_symbol": "GGRM.JK", "company_name": "Gudang Garam Tbk",
     "sector": "Consumer Goods", "industry": "Tobacco", "is_lq45": True, "market_cap_category": "Large"},

    # Retail
    {"stock_code": "MAPI", "yahoo_symbol": "MAPI.JK", "company_name": "Mitra Adiperkasa Tbk",
     "sector": "Retail", "industry": "Department Stores", "is_lq45": False, "market_cap_category": "Mid"},
    {"stock_code": "ACES", "yahoo_symbol": "ACES.JK", "company_name": "Ace Hardware Indonesia Tbk",
     "sector": "Retail", "industry": "Home Improvement", "is_lq45": False, "market_cap_category": "Mid"},
    {"stock_code": "ERAA", "yahoo_symbol": "ERAA.JK", "company_name": "Erajaya Swasembada Tbk",
     "sector": "Retail", "industry": "Electronics Retail", "is_lq45": False, "market_cap_category": "Small"},

    # Infrastructure & Transportation
    {"stock_code": "JSMR", "yahoo_symbol": "JSMR.JK", "company_name": "Jasa Marga Tbk",
     "sector": "Infrastructure", "industry": "Toll Roads", "is_lq45": True, "market_cap_category": "Large"},
    {"stock_code": "BIRD", "yahoo_symbol": "BIRD.JK", "company_name": "Blue Bird Tbk",
     "sector": "Transportation", "industry": "Transportation Services", "is_lq45": False, "market_cap_category": "Small"},

    # Technology & Media
    {"stock_code": "GOTO", "yahoo_symbol": "GOTO.JK", "company_name": "GoTo Gojek Tokopedia Tbk",
     "sector": "Technology", "industry": "Internet Services", "is_lq45": True, "market_cap_category": "Large"},
    {"stock_code": "EMTK", "yahoo_symbol": "EMTK.JK", "company_name": "Elang Mahkota Teknologi Tbk",
     "sector": "Media", "industry": "Broadcasting", "is_lq45": False, "market_cap_category": "Mid"},

    # Finance (Non-Bank)
    {"stock_code": "BBTN", "yahoo_symbol": "BBTN.JK", "company_name": "Bank Tabungan Negara Tbk",
     "sector": "Banking", "industry": "Mortgage Banks", "is_lq45": False, "market_cap_category": "Mid"},
]


def create_tables(engine):
    """Create all database tables"""
    logger.info("Creating database tables...")

    try:
        # Create all tables defined in Base
        Base.metadata.create_all(engine)
        logger.info("✓ Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to create tables: {str(e)}")
        return False


def seed_stock_master(session):
    """Seed stock_master table with Indonesian stocks"""
    logger.info("Seeding stock master data...")

    try:
        # Check if data already exists
        existing_count = session.query(StockMaster).count()
        if existing_count > 0:
            logger.info(f"Stock master already has {existing_count} records. Updating...")

        added = 0
        updated = 0

        for stock_data in INDONESIAN_STOCKS:
            # Check if stock exists
            existing = session.query(StockMaster).filter(
                StockMaster.stock_code == stock_data['stock_code']
            ).first()

            if existing:
                # Update existing record
                for key, value in stock_data.items():
                    setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                existing.is_active = True
                updated += 1
            else:
                # Create new record
                new_stock = StockMaster(
                    **stock_data,
                    exchange="IDX",
                    currency="IDR",
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                session.add(new_stock)
                added += 1

        session.commit()

        logger.info(f"✓ Stock master data seeded: {added} added, {updated} updated")
        logger.info(f"  Total stocks: {len(INDONESIAN_STOCKS)}")
        logger.info(f"  LQ45 stocks: {len([s for s in INDONESIAN_STOCKS if s.get('is_lq45', False)])}")

        return True

    except Exception as e:
        logger.error(f"✗ Failed to seed stock master: {str(e)}")
        session.rollback()
        return False


def verify_setup(session):
    """Verify that setup was successful"""
    logger.info("\nVerifying setup...")

    try:
        # Check stock_master
        stock_count = session.query(StockMaster).count()
        active_count = session.query(StockMaster).filter(StockMaster.is_active == True).count()
        lq45_count = session.query(StockMaster).filter(StockMaster.is_lq45 == True).count()

        logger.info(f"✓ Stock Master: {stock_count} total, {active_count} active, {lq45_count} LQ45")

        # Sample stocks by sector
        sectors = session.query(StockMaster.sector, StockMaster).distinct().all()
        sector_counts = {}
        for sector, _ in sectors:
            count = session.query(StockMaster).filter(StockMaster.sector == sector).count()
            sector_counts[sector] = count

        logger.info("\n  Stocks by sector:")
        for sector, count in sorted(sector_counts.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"    {sector}: {count}")

        return True

    except Exception as e:
        logger.error(f"✗ Verification failed: {str(e)}")
        return False


def main():
    """Main setup function"""
    logger.info("="*80)
    logger.info("Stock Data Pipeline Setup")
    logger.info("="*80)

    # Determine database type (PostgreSQL or SQLite)
    try:
        from api.config import settings
        db_url = (
            f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}"
            f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
        )
        logger.info("Using PostgreSQL database")
    except:
        db_url = "sqlite:///data/trading_system.db"
        logger.info("Using SQLite database (local development)")

    # Create engine and session
    engine = create_engine(db_url, echo=False)
    SessionFactory = sessionmaker(bind=engine)
    session = SessionFactory()

    # Step 1: Create tables
    if not create_tables(engine):
        logger.error("Setup failed at table creation")
        return

    # Step 2: Seed stock master data
    if not seed_stock_master(session):
        logger.error("Setup failed at stock master seeding")
        return

    # Step 3: Verify setup
    if not verify_setup(session):
        logger.error("Setup verification failed")
        return

    session.close()

    logger.info("\n" + "="*80)
    logger.info("Setup completed successfully!")
    logger.info("="*80)
    logger.info("\nNext steps:")
    logger.info("1. Run initial data backfill:")
    logger.info("   python -m src.data_pipeline.daily_price_scheduler --backfill 2")
    logger.info("\n2. Start the daily scheduler:")
    logger.info("   python -m src.data_pipeline.daily_price_scheduler")
    logger.info("\n3. Or run a manual refresh:")
    logger.info("   python -m src.data_pipeline.daily_price_scheduler --run-once")
    logger.info("="*80)


if __name__ == "__main__":
    main()
