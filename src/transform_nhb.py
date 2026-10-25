
from pathlib import Path

import pandas as pd


RAW_PATH = Path("data/raw/nhb_residex_assessment.xls")
OUTPUT_PATH = Path("data/processed/nhb_residex_clean.csv")


def transform_nhb():
    tables = pd.read_html(RAW_PATH)

    df = tables[0].copy()
    df.columns = df.columns.astype(str).str.strip()

    df = df.melt(
        id_vars=["City"],
        var_name="quarter",
        value_name="house_price_index"
    )

    df = df.rename(columns={"City": "city"})

    df["city"] = df["city"].astype(str).str.strip()

    df["observation_date"] = pd.to_datetime(
        df["quarter"].str.replace(
            r"\s+", " ", regex=True
        ).str.strip(),
        format="%b- %Y"
    ) + pd.offsets.MonthEnd(0)

    df["house_price_index"] = pd.to_numeric(
        df["house_price_index"],
        errors="raise"
    )

    df = df[
        ["city", "observation_date", "house_price_index"]
    ].sort_values(
        ["city", "observation_date"]
    ).reset_index(drop=True)

    if df.isna().any().any():
        raise ValueError("Missing NHB values detected")

    if (df["house_price_index"] <= 0).any():
        raise ValueError("Invalid NHB index values")

    if df.duplicated(
        ["city", "observation_date"]
    ).any():
        raise ValueError("Duplicate NHB observations")

    grouped = df.groupby("city")

    previous_date = grouped["observation_date"].shift(1)
    previous_index = grouped["house_price_index"].shift(1)

    previous_year_date = grouped["observation_date"].shift(4)
    previous_year_index = grouped["house_price_index"].shift(4)

    valid_qoq = (
        previous_date.dt.to_period("Q")
        == df["observation_date"].dt.to_period("Q") - 1
    )

    valid_yoy = (
        previous_year_date.dt.to_period("Q")
        == df["observation_date"].dt.to_period("Q") - 4
    )

    df["qoq_growth_pct"] = (
        (df["house_price_index"] / previous_index - 1) * 100
    ).where(valid_qoq)

    df["yoy_growth_pct"] = (
        (df["house_price_index"] / previous_year_index - 1) * 100
    ).where(valid_yoy)

    df["source"] = "NHB RESIDEX"
    df["index_type"] = "Assessment Prices"

    
    # Derive calendar and Indian financial-year fields
    df["calendar_year"] = (
        df["observation_date"].dt.year.astype(int)
    )

    df["calendar_quarter"] = (
        df["observation_date"].dt.quarter.astype(int)
    )

    df["financial_year"] = df["observation_date"].apply(
        lambda d: (
            f"{d.year}-{str(d.year + 1)[-2:]}"
            if d.month >= 4
            else f"{d.year - 1}-{str(d.year)[-2:]}"
        )
    )


    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Processed {len(df)} NHB observations")
    print(f"Cities: {df['city'].nunique()}")
    print(f"Quarters: {df['observation_date'].nunique()}")
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    transform_nhb()
