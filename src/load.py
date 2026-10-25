
from pathlib import Path
import logging

import pandas as pd
from sqlalchemy import text

from src.database import get_engine

BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_FILE = (
    BASE_DIR / "data" / "processed"
    / "housing_price_index_clean.csv"
)
SCHEMA_FILE = BASE_DIR / "sql" / "create_tables.sql"

logger = logging.getLogger(__name__)

COLUMNS = [
    "city",
    "base_year",
    "observation_date",
    "financial_year",
    "calendar_year",
    "calendar_quarter",
    "house_price_index",
    "qoq_growth_pct",
    "yoy_growth_pct",
]


def load_data():
    if not PROCESSED_FILE.exists():
        raise FileNotFoundError(PROCESSED_FILE)

    df = pd.read_csv(
        PROCESSED_FILE,
        parse_dates=["observation_date"],
    )

    if df.empty:
        raise ValueError("Processed dataset is empty")

    if df[COLUMNS[:7]].isna().any().any():
        raise ValueError("Required fields contain null values")

    df["observation_date"] = (
        df["observation_date"].dt.date
    )

    # Convert pandas NaN to SQL NULL
    records = (
        df[COLUMNS]
        .astype(object)
        .where(pd.notna(df[COLUMNS]), None)
        .to_dict(orient="records")
    )

    engine = get_engine()

    upsert_sql = text("""
        INSERT INTO housing.house_price_index (
            city, base_year, observation_date,
            financial_year, calendar_year,
            calendar_quarter, house_price_index,
            qoq_growth_pct, yoy_growth_pct
        )
        VALUES (
            :city, :base_year, :observation_date,
            :financial_year, :calendar_year,
            :calendar_quarter, :house_price_index,
            :qoq_growth_pct, :yoy_growth_pct
        )
        ON CONFLICT (city, base_year, observation_date)
        DO UPDATE SET
            financial_year = EXCLUDED.financial_year,
            calendar_year = EXCLUDED.calendar_year,
            calendar_quarter = EXCLUDED.calendar_quarter,
            house_price_index = EXCLUDED.house_price_index,
            qoq_growth_pct = EXCLUDED.qoq_growth_pct,
            yoy_growth_pct = EXCLUDED.yoy_growth_pct
    """)

    try:
        with engine.begin() as connection:
            # Run schema statements
            schema_sql = SCHEMA_FILE.read_text(
                encoding="utf-8"
            )

            for statement in schema_sql.split(";"):
                if statement.strip():
                    connection.execute(text(statement))

            # Insert or update records in one transaction
            connection.execute(upsert_sql, records)

            total = connection.execute(
                text("""
                    SELECT COUNT(*)
                    FROM housing.house_price_index
                """)
            ).scalar_one()

        logger.info(
            "Upserted %s records. Warehouse total: %s",
            len(records),
            total,
        )

        print("PostgreSQL load successful!")
        print(f"Processed records: {len(records):,}")
        print(f"Warehouse total: {total:,}")

    finally:
        engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    load_data()
