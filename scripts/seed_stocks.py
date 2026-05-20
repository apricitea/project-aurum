"""
Seed script: populate stock_master with IDX LQ45 + major blue chip stocks.

Yahoo Finance symbols for IDX stocks use the .JK suffix (e.g. BBCA.JK).

Run once after the initial migration:
    uv run python scripts/seed_stocks.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.api.database_extensions import StockMaster, Base
from src.api.config import settings

# Core IDX stocks — LQ45 constituents + major blue chips
# Format: (stock_code, yahoo_symbol, company_name, sector)
STOCKS = [
    # Finance
    ("BBCA", "BBCA.JK", "Bank Central Asia", "Finance"),
    ("BBRI", "BBRI.JK", "Bank Rakyat Indonesia", "Finance"),
    ("BMRI", "BMRI.JK", "Bank Mandiri", "Finance"),
    ("BBNI", "BBNI.JK", "Bank Negara Indonesia", "Finance"),
    ("BRIS", "BRIS.JK", "Bank Syariah Indonesia", "Finance"),
    ("BTPS", "BTPS.JK", "Bank BTPN Syariah", "Finance"),
    ("BNGA", "BNGA.JK", "Bank CIMB Niaga", "Finance"),
    ("ARTO", "ARTO.JK", "Bank Jago", "Finance"),

    # Consumer
    ("UNVR", "UNVR.JK", "Unilever Indonesia", "Consumer Goods"),
    ("ICBP", "ICBP.JK", "Indofood CBP Sukses Makmur", "Consumer Goods"),
    ("INDF", "INDF.JK", "Indofood Sukses Makmur", "Consumer Goods"),
    ("KLBF", "KLBF.JK", "Kalbe Farma", "Consumer Goods"),
    ("MYOR", "MYOR.JK", "Mayora Indah", "Consumer Goods"),
    ("SIDO", "SIDO.JK", "Industri Jamu dan Farmasi Sido Muncul", "Consumer Goods"),
    ("GGRM", "GGRM.JK", "Gudang Garam", "Consumer Goods"),
    ("HMSP", "HMSP.JK", "HM Sampoerna", "Consumer Goods"),

    # Telco & Tech
    ("TLKM", "TLKM.JK", "Telkom Indonesia", "Telecommunications"),
    ("EXCL",  "EXCL.JK",  "XL Axiata", "Telecommunications"),
    ("ISAT", "ISAT.JK", "Indosat Ooredoo Hutchison", "Telecommunications"),
    ("GOTO", "GOTO.JK", "GoTo Gojek Tokopedia", "Technology"),
    ("BUKA", "BUKA.JK", "Bukalapak.com", "Technology"),
    ("EMTK", "EMTK.JK", "Elang Mahkota Teknologi", "Technology"),

    # Energy & Mining
    ("ADRO", "ADRO.JK", "Adaro Energy Indonesia", "Mining"),
    ("PTBA", "PTBA.JK", "Bukit Asam", "Mining"),
    ("ITMG", "ITMG.JK", "Indo Tambangraya Megah", "Mining"),
    ("INCO", "INCO.JK", "Vale Indonesia", "Mining"),
    ("ANTM", "ANTM.JK", "Aneka Tambang", "Mining"),
    ("MDKA", "MDKA.JK", "Merdeka Copper Gold", "Mining"),
    ("MEDC", "MEDC.JK", "Medco Energi Internasional", "Energy"),
    ("PGAS", "PGAS.JK", "Perusahaan Gas Negara", "Energy"),
    ("AKRA", "AKRA.JK", "AKR Corporindo", "Energy"),

    # Infrastructure & Property
    ("JSMR", "JSMR.JK", "Jasa Marga", "Infrastructure"),
    ("WIKA", "WIKA.JK", "Wijaya Karya", "Infrastructure"),
    ("PTPP", "PTPP.JK", "PP (Pembangunan Perumahan)", "Infrastructure"),
    ("WSKT", "WSKT.JK", "Waskita Karya", "Infrastructure"),
    ("BSDE", "BSDE.JK", "Bumi Serpong Damai", "Property"),
    ("CTRA", "CTRA.JK", "Ciputra Development", "Property"),
    ("PWON", "PWON.JK", "Pakuwon Jati", "Property"),
    ("SMRA", "SMRA.JK", "Summarecon Agung", "Property"),

    # Consumer Discretionary / Retail
    ("MAPI", "MAPI.JK", "Mitra Adiperkasa", "Consumer Discretionary"),
    ("ACES", "ACES.JK", "Ace Hardware Indonesia", "Consumer Discretionary"),
    ("AMRT", "AMRT.JK", "Sumber Alfaria Trijaya", "Consumer Discretionary"),

    # Healthcare
    ("MIKA", "MIKA.JK", "Mitra Keluarga Karyasehat", "Healthcare"),
    ("HEAL", "HEAL.JK", "Medikaloka Hermina", "Healthcare"),

    # Cement & Basic Materials
    ("SMGR", "SMGR.JK", "Semen Indonesia", "Basic Materials"),
    ("INTP", "INTP.JK", "Indocement Tunggal Prakarsa", "Basic Materials"),

    # Automotive
    ("ASII", "ASII.JK", "Astra International", "Automotive"),
    ("AUTO", "AUTO.JK", "Astra Otoparts", "Automotive"),
]


def main():
    db_url = (
        f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )
    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    session = Session()

    inserted = 0
    skipped = 0
    for stock_code, yahoo_symbol, company_name, sector in STOCKS:
        existing = session.query(StockMaster).filter_by(stock_code=stock_code).first()
        if existing:
            skipped += 1
            continue
        session.add(StockMaster(
            stock_code=stock_code,
            yahoo_symbol=yahoo_symbol,
            company_name=company_name,
            sector=sector,
            is_active=True,
            is_lq45=True,
        ))
        inserted += 1

    session.commit()
    session.close()
    print(f"Seeded {inserted} stocks, skipped {skipped} existing.")


if __name__ == "__main__":
    main()
