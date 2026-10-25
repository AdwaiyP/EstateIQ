
import pytest
from sqlalchemy import text

from src.database import get_engine


@pytest.fixture(scope="module")
def conn():
    engine = get_engine()
    try:
        with engine.connect() as connection:
            yield connection
    finally:
        engine.dispose()


def scalar(conn, sql):
    return conn.execute(text(sql)).scalar_one()


def test_nhb_not_empty(conn):
    assert scalar(
        conn,
        "SELECT COUNT(*) FROM housing.nhb_residex"
    ) > 0


def test_nhb_unique_city_quarter(conn):
    assert scalar(conn, """
        SELECT COUNT(*) FROM (
            SELECT city, observation_date, index_type
            FROM housing.nhb_residex
            GROUP BY city, observation_date, index_type
            HAVING COUNT(*) > 1
        ) x
    """) == 0


def test_nhb_positive_hpi(conn):
    assert scalar(conn, """
        SELECT COUNT(*)
        FROM housing.nhb_residex
        WHERE house_price_index <= 0
    """) == 0


def test_nhb_no_missing_required_values(conn):
    assert scalar(conn, """
        SELECT COUNT(*)
        FROM housing.nhb_residex
        WHERE city IS NULL
           OR observation_date IS NULL
           OR house_price_index IS NULL
           OR index_type IS NULL
    """) == 0


def test_nhb_quarter_end_dates(conn):
    assert scalar(conn, """
        SELECT COUNT(*)
        FROM housing.nhb_residex
        WHERE observation_date <>
            (
                DATE_TRUNC('quarter', observation_date)
                + INTERVAL '3 months'
                - INTERVAL '1 day'
            )::date
    """) == 0


def test_nhb_qoq_growth(conn):
    assert scalar(conn, """
        WITH calculated AS (
            SELECT
                observation_date,
                qoq_growth_pct,
                LAG(observation_date) OVER w AS prev_date,
                LAG(house_price_index) OVER w AS prev_hpi,
                house_price_index
            FROM housing.nhb_residex
            WINDOW w AS (
                PARTITION BY city, index_type
                ORDER BY observation_date
            )
        ),
        checked AS (
            SELECT
                qoq_growth_pct,
                CASE
                    WHEN prev_date IS NOT NULL
                     AND (
                         EXTRACT(YEAR FROM observation_date) * 4
                         + EXTRACT(QUARTER FROM observation_date)
                     ) - (
                         EXTRACT(YEAR FROM prev_date) * 4
                         + EXTRACT(QUARTER FROM prev_date)
                     ) = 1
                    THEN (
                        house_price_index / prev_hpi - 1
                    ) * 100
                    ELSE NULL
                END AS expected
            FROM calculated
        )
        SELECT COUNT(*)
        FROM checked
        WHERE (
            qoq_growth_pct IS NULL
            AND expected IS NOT NULL
        ) OR (
            qoq_growth_pct IS NOT NULL
            AND expected IS NULL
        ) OR (
            ABS(qoq_growth_pct - expected) > 0.0001
        )
    """) == 0


def test_nhb_views_exist(conn):
    assert scalar(conn, """
        SELECT COUNT(*)
        FROM information_schema.views
        WHERE table_schema = 'housing'
          AND table_name IN (
            'vw_nhb_latest_city',
            'vw_nhb_quarterly_trends',
            'vw_nhb_market_momentum'
          )
    """) == 3
