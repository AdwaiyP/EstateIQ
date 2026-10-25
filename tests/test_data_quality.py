
import pandas as pd
import pytest
from sqlalchemy import text

from src.database import get_engine


@pytest.fixture(scope="module")
def connection():
    engine = get_engine()

    try:
        with engine.connect() as conn:
            yield conn
    finally:
        engine.dispose()


def test_table_not_empty(connection):
    count = connection.execute(
        text("SELECT COUNT(*) FROM housing.house_price_index")
    ).scalar_one()

    assert count > 0, "Housing warehouse is empty"


def test_no_duplicate_observations(connection):
    duplicates = connection.execute(
        text("""
            SELECT COUNT(*)
            FROM (
                SELECT city, base_year, observation_date
                FROM housing.house_price_index
                GROUP BY city, base_year, observation_date
                HAVING COUNT(*) > 1
            ) duplicate_groups
        """)
    ).scalar_one()

    assert duplicates == 0, "Duplicate observations found"


def test_no_missing_required_fields(connection):
    missing = connection.execute(
        text("""
            SELECT COUNT(*)
            FROM housing.house_price_index
            WHERE city IS NULL
               OR base_year IS NULL
               OR observation_date IS NULL
               OR house_price_index IS NULL
        """)
    ).scalar_one()

    assert missing == 0, "Missing required values found"


def test_positive_house_price_index(connection):
    invalid = connection.execute(
        text("""
            SELECT COUNT(*)
            FROM housing.house_price_index
            WHERE house_price_index <= 0
        """)
    ).scalar_one()

    assert invalid == 0, "Invalid HPI values detected"


def test_quarterly_dates(connection):
    invalid = connection.execute(
        text("""
            SELECT COUNT(*)
            FROM housing.house_price_index
            WHERE observation_date <>
                (
                    DATE_TRUNC('quarter', observation_date)
                    + INTERVAL '3 months'
                    - INTERVAL '1 day'
                )::date
        """)
    ).scalar_one()

    assert invalid == 0, "Non-quarter-end dates found"


def test_growth_calculation_consistency(connection):
    query = text("""
        SELECT
            city,
            base_year,
            observation_date,
            house_price_index,
            qoq_growth_pct,
            LAG(house_price_index) OVER (
                PARTITION BY city, base_year
                ORDER BY observation_date
            ) AS previous_hpi,
            LAG(observation_date) OVER (
                PARTITION BY city, base_year
                ORDER BY observation_date
            ) AS previous_date
        FROM housing.house_price_index
    """)

    df = pd.read_sql(query, connection)

    df["observation_date"] = pd.to_datetime(
        df["observation_date"]
    )
    df["previous_date"] = pd.to_datetime(
        df["previous_date"]
    )

    consecutive = (
        df["previous_date"].dt.to_period("Q")
        == df["observation_date"].dt.to_period("Q") - 1
    )

    expected = (
        (df["house_price_index"] / df["previous_hpi"] - 1)
        * 100
    ).where(consecutive)

    actual = df["qoq_growth_pct"]

    mismatch = ~(
        (actual.isna() & expected.isna())
        | ((actual - expected).abs() < 0.0001)
    )

    assert not mismatch.any(), (
        f"{mismatch.sum()} inconsistent QoQ calculations"
    )


def test_reporting_views_exist(connection):
    count = connection.execute(
        text("""
            SELECT COUNT(*)
            FROM information_schema.views
            WHERE table_schema = 'housing'
              AND table_name IN (
                  'vw_latest_city_performance',
                  'vw_quarterly_market_trends',
                  'vw_annual_city_performance'
              )
        """)
    ).scalar_one()

    assert count == 3, "Missing analytics views"
