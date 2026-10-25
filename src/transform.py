
from pathlib import Path
import logging

import pandas as pd

from src.extract import extract_data

BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BASE_DIR / "data" / "processed"
OUTPUT_FILE = PROCESSED_DIR / "housing_price_index_clean.csv"

logger = logging.getLogger(__name__)

CITY_MAPPING = {
    "AL_INDIA": "All India",
    "BANGALORE": "Bengaluru",
    "AHMEDABAD": "Ahmedabad",
    "CHENNAI": "Chennai",
    "DELHI": "Delhi",
    "JAIPUR": "Jaipur",
    "KANPUR": "Kanpur",
    "KOCHI": "Kochi",
    "KOLKATA": "Kolkata",
    "LUCKNOW": "Lucknow",
    "MUMBAI": "Mumbai",
}

BASE_MAPPING = {
    "BY_2008_09": "2008-09",
    "BY_2010-11": "2010-11",
}


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Starting housing data transformation")

    required_columns = {
        "base_per", "center_rn", "time_period", "obs_value"
    }

    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    data = df.copy()

    # 1. Standardize column names
    data = data.rename(
        columns={
            "center_rn": "city",
            "base_per": "base_year",
            "time_period": "observation_date",
            "obs_value": "house_price_index",
        }
    )

    # 2. Standardize locations and base years
    data["city"] = data["city"].map(CITY_MAPPING)
    data["base_year"] = data["base_year"].map(BASE_MAPPING)

    if data["city"].isna().any():
        raise ValueError("Unknown city codes detected")

    if data["base_year"].isna().any():
        raise ValueError("Unknown base-year codes detected")

    # 3. Convert types
    data["observation_date"] = pd.to_datetime(
        data["observation_date"], errors="raise"
    )
    
    # Remove redundant August 2020 observations.
    # The source also contains September 30 records
    # with identical HPI values for all 11 locations.
    august_mask = (
        data["observation_date"] == pd.Timestamp("2020-08-31")
    )

    august_records = data.loc[august_mask].copy()

    for _, record in august_records.iterrows():
        september_match = data[
            (data["city"] == record["city"])
            & (data["base_year"] == record["base_year"])
            & (
                data["observation_date"]
                == pd.Timestamp("2020-09-30")
            )
        ]

        if (
            len(september_match) != 1
            or not pd.to_numeric(
                september_match["house_price_index"]
            ).iloc[0]
            == float(record["house_price_index"])
        ):
            raise ValueError(
                "August 2020 observation does not match "
                f"September 2020 for {record['city']}"
            )

    data = data.loc[~august_mask].copy()

    logger.info(
        "Removed %s redundant August 2020 records",
        len(august_records),
    )


    data["house_price_index"] = pd.to_numeric(
        data["house_price_index"], errors="raise"
    )

    # 4. Validate the HPI observations
    if data["house_price_index"].isna().any():
        raise ValueError("Missing house price index values")

    if (data["house_price_index"] <= 0).any():
        raise ValueError("Invalid non-positive HPI values")

    keys = ["city", "base_year", "observation_date"]

    if data.duplicated(subset=keys).any():
        raise ValueError("Duplicate city/base-year/date records")

    # 5. Sort chronologically within each series
    data = data.sort_values(keys).reset_index(drop=True)

    groups = data.groupby(
        ["city", "base_year"], sort=False
    )

    # 6. Growth calculations
    previous_date = groups["observation_date"].shift(1)
    previous_hpi = groups["house_price_index"].shift(1)

    one_year_ago_date = groups["observation_date"].shift(4)
    one_year_ago_hpi = groups["house_price_index"].shift(4)

    # Only compare genuinely consecutive quarters.
    consecutive_quarter = (
        previous_date.dt.to_period("Q")
        == data["observation_date"].dt.to_period("Q") - 1
    )

    same_quarter_last_year = (
        one_year_ago_date.dt.to_period("Q")
        == data["observation_date"].dt.to_period("Q") - 4
    )

    data["qoq_growth_pct"] = (
        (data["house_price_index"] / previous_hpi - 1) * 100
    ).where(consecutive_quarter)

    data["yoy_growth_pct"] = (
        (data["house_price_index"] / one_year_ago_hpi - 1) * 100
    ).where(same_quarter_last_year)

    # 7. Add time dimensions
    data["calendar_year"] = data["observation_date"].dt.year
    data["calendar_quarter"] = data["observation_date"].dt.quarter

    data["financial_year"] = data["observation_date"].apply(
        lambda date: (
            f"{date.year - 1}-{str(date.year)[-2:]}"
            if date.month <= 3
            else f"{date.year}-{str(date.year + 1)[-2:]}"
        )
    )

    # 8. Select warehouse-ready columns
    data = data[
        [
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
    ]

    logger.info("Transformation complete: %s rows", len(data))

    return data


def save_data(df: pd.DataFrame) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    df.to_csv(OUTPUT_FILE, index=False)

    logger.info("Cleaned dataset saved to %s", OUTPUT_FILE)


if __name__ == "__main__":
    raw_data = extract_data()
    clean_data = transform_data(raw_data)

    save_data(clean_data)

    print("\nTransformation successful!")
    print(f"Rows: {len(clean_data):,}")
    print(f"Columns: {len(clean_data.columns)}")

    print("\nPreview:")
    print(clean_data.head(10).to_string(index=False))

    print("\nMissing growth values:")
    print(
        clean_data[
            ["qoq_growth_pct", "yoy_growth_pct"]
        ].isna().sum()
    )

    print("\nLatest All India observations:")
    latest = clean_data[
        (clean_data["city"] == "All India")
        & (clean_data["base_year"] == "2010-11")
    ].sort_values("observation_date").tail(5)

    print(latest.to_string(index=False))
