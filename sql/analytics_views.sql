
-- ============================================================
-- ESTATEIQ: INDIA HOUSING MARKET INTELLIGENCE
-- File: sql/analytics_views.sql
-- Source: Reserve Bank of India (RBI)
-- Database: estateiq_db
-- Schema: housing
-- Description: Analytical views for housing market insights
-- ============================================================


-- ============================================================
-- VIEW 1: LATEST CITY HOUSING MARKET PERFORMANCE
-- ============================================================
-- Purpose:
-- Retrieve the latest available HPI observation for each city.
-- Classify markets based on year-over-year growth.
-- Uses only the 2010-11 base-year series.
-- ============================================================

CREATE OR REPLACE VIEW housing.vw_latest_city_performance AS

WITH ranked AS (
    SELECT
        city,
        base_year,
        observation_date,
        house_price_index,
        qoq_growth_pct,
        yoy_growth_pct,

        ROW_NUMBER() OVER (
            PARTITION BY city, base_year
            ORDER BY observation_date DESC
        ) AS rn

    FROM housing.house_price_index
    WHERE base_year = '2010-11'
)

SELECT
    city,
    base_year,
    observation_date,
    house_price_index,
    qoq_growth_pct,
    yoy_growth_pct,

    CASE
        WHEN yoy_growth_pct > 0 THEN 'Appreciating'
        WHEN yoy_growth_pct < 0 THEN 'Declining'
        WHEN yoy_growth_pct = 0 THEN 'Stable'
        ELSE 'Unavailable'
    END AS market_direction

FROM ranked
WHERE rn = 1;



-- ============================================================
-- VIEW 2: QUARTERLY HOUSING MARKET TRENDS
-- ============================================================
-- Purpose:
-- Historical HPI values and quarterly/annual growth.
-- Supports Power BI line charts and time-series analysis.
-- ============================================================

CREATE OR REPLACE VIEW housing.vw_quarterly_market_trends AS

SELECT
    city,
    base_year,
    observation_date,
    financial_year,
    calendar_year,
    calendar_quarter,
    house_price_index,
    qoq_growth_pct,
    yoy_growth_pct

FROM housing.house_price_index

WHERE base_year = '2010-11';



-- ============================================================
-- VIEW 3: ANNUAL CITY HOUSING MARKET PERFORMANCE
-- ============================================================
-- Purpose:
-- Summarize city-level housing appreciation by financial year.
-- Annual averages represent the mean of quarterly YoY rates,
-- not cumulative annual price appreciation.
-- ============================================================

CREATE OR REPLACE VIEW housing.vw_annual_city_performance AS

SELECT
    city,
    base_year,
    financial_year,

    COUNT(*) AS quarters_reported,

    ROUND(
        AVG(yoy_growth_pct)::numeric, 2
    ) AS avg_yoy_growth_pct,

    ROUND(
        MIN(yoy_growth_pct)::numeric, 2
    ) AS min_yoy_growth_pct,

    ROUND(
        MAX(yoy_growth_pct)::numeric, 2
    ) AS max_yoy_growth_pct

FROM housing.house_price_index

WHERE base_year = '2010-11'
  AND yoy_growth_pct IS NOT NULL

GROUP BY
    city,
    base_year,
    financial_year;



-- ============================================================
-- VERIFICATION: CONFIRM ALL THREE VIEWS EXIST
-- ============================================================

SELECT
    table_schema,
    table_name
FROM information_schema.views
WHERE table_schema = 'housing'
ORDER BY table_name;



-- ============================================================
-- TEST QUERY 1: LATEST CITY PERFORMANCE
-- ============================================================

SELECT
    city,
    observation_date,
    ROUND(house_price_index::numeric, 2) AS hpi,
    ROUND(yoy_growth_pct::numeric, 2) AS yoy_growth_pct,
    market_direction
FROM housing.vw_latest_city_performance
ORDER BY yoy_growth_pct DESC NULLS LAST;



-- ============================================================
-- TEST QUERY 2: QUARTERLY NATIONAL MARKET TRENDS
-- ============================================================

SELECT
    observation_date,
    ROUND(house_price_index::numeric, 2) AS hpi,
    ROUND(qoq_growth_pct::numeric, 2) AS qoq_growth_pct,
    ROUND(yoy_growth_pct::numeric, 2) AS yoy_growth_pct
FROM housing.vw_quarterly_market_trends
WHERE city = 'All India'
ORDER BY observation_date DESC
LIMIT 12;



-- ============================================================
-- TEST QUERY 3: ANNUAL CITY PERFORMANCE
-- ============================================================

SELECT
    city,
    financial_year,
    quarters_reported,
    avg_yoy_growth_pct,
    min_yoy_growth_pct,
    max_yoy_growth_pct
FROM housing.vw_annual_city_performance
WHERE financial_year = '2024-25'
ORDER BY avg_yoy_growth_pct DESC NULLS LAST;
