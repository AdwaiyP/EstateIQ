
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from src.database import get_engine


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data/processed/nhb_residex_clean.csv"


# --------------------------------------------------
# PostgreSQL UPSERT
# --------------------------------------------------

UPSERT_SQL = text("""
INSERT INTO housing.nhb_residex (
    city,
    observation_date,
    house_price_index,
    qoq_growth_pct,
    yoy_growth_pct,
    source,
    index_type,
    calendar_year,
    calendar_quarter,
    financial_year
)
VALUES (
    :city,
    :observation_date,
    :house_price_index,
    :qoq_growth_pct,
    :yoy_growth_pct,
    :source,
    :index_type,
    :calendar_year,
    :calendar_quarter,
    :financial_year
)
ON CONFLICT (
    city,
    observation_date,
    index_type
)
DO UPDATE SET
    house_price_index = EXCLUDED.house_price_index,
    qoq_growth_pct = EXCLUDED.qoq_growth_pct,
    yoy_growth_pct = EXCLUDED.yoy_growth_pct,
    source = EXCLUDED.source,
    calendar_year = EXCLUDED.calendar_year,
    calendar_quarter = EXCLUDED.calendar_quarter,
    financial_year = EXCLUDED.financial_year,
    loaded_at = CURRENT_TIMESTAMP;
""")


# --------------------------------------------------
# Load NHB RESIDEX data
# --------------------------------------------------

def load_nhb():

    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"NHB processed CSV not found: {CSV_PATH}"
        )

    # Read processed data
    df = pd.read_csv(
        CSV_PATH,
        parse_dates=["observation_date"]
    )

    if df.empty:
        raise ValueError("NHB CSV is empty.")

    # Validate required source columns
    required_columns = [
        "city",
        "observation_date",
        "house_price_index",
        "qoq_growth_pct",
        "yoy_growth_pct",
        "source",
        "index_type",
    ]

    missing_columns = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing columns in NHB CSV: "
            f"{missing_columns}. "
            "Rerun python -m src.transform_nhb"
        )

    # Validate city, date, and index
    if df[
        ["city", "observation_date", "house_price_index"]
    ].isna().any().any():
        raise ValueError(
            "Missing required NHB city, date, or index values."
        )

    if (df["house_price_index"] <= 0).any():
        raise ValueError(
            "NHB house price index must be positive."
        )

    if df.duplicated(
        ["city", "observation_date", "index_type"]
    ).any():
        raise ValueError(
            "Duplicate NHB city-quarter records detected."
        )

    # --------------------------------------------------
    # Derive calendar and financial-year fields
    # --------------------------------------------------

    df["calendar_year"] = (
        df["observation_date"].dt.year.astype(int)
    )

    df["calendar_quarter"] = (
        df["observation_date"].dt.quarter.astype(int)
    )

    df["financial_year"] = (
        df["observation_date"].apply(
            lambda d: (
                f"{d.year}-{str(d.year + 1)[-2:]}"
                if d.month >= 4
                else f"{d.year - 1}-{str(d.year)[-2:]}"
            )
        )
    )

    # Validate quarter-end dates
    quarter_end = (
        df["observation_date"]
        + pd.offsets.QuarterEnd(0)
    )

    if not (
        df["observation_date"] == quarter_end
    ).all():
        raise ValueError(
            "Some NHB observation dates are not quarter-end dates."
        )

    # Convert pandas timestamps to Python dates
    df["observation_date"] = (
        df["observation_date"].dt.date
    )

    # Replace pandas NaN with PostgreSQL NULL
    df = df.astype(object).where(
        pd.notna(df),
        None
    )

    # Convert DataFrame into SQL parameter records
    records = df.to_dict(orient="records")

    # --------------------------------------------------
    # Load records into PostgreSQL
    # --------------------------------------------------

    engine = get_engine()

    try:
        with engine.begin() as conn:

            conn.execute(
                UPSERT_SQL,
                records
            )

            count = conn.execute(
                text("""
                    SELECT COUNT(*)
                    FROM housing.nhb_residex
                """)
            ).scalar_one()

    finally:
        engine.dispose()

    print("=" * 45)
    print("ESTATEIQ — NHB RESIDEX DATA LOAD")
    print("=" * 45)
    print(f"Processed records : {len(records)}")
    print(f"Warehouse total   : {count}")
    print("Status            : SUCCESS")
    print("=" * 45)


if __name__ == "__main__":
    load_nhb()
