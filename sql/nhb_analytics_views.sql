
-- ESTATEIQ: NHB RESIDEX ANALYTICS
-- Index: HPI@Assessment Prices

-- 1. Latest city performance

CREATE OR REPLACE VIEW housing.vw_nhb_latest_city AS

WITH ranked AS (
    SELECT
        city,
        observation_date,
        house_price_index,
        qoq_growth_pct,
        yoy_growth_pct,

        ROW_NUMBER() OVER (
            PARTITION BY city
            ORDER BY observation_date DESC
        ) AS rn

    FROM housing.nhb_residex
)

SELECT
    city,
    observation_date,
    house_price_index,
    qoq_growth_pct,
    yoy_growth_pct,

    CASE
        WHEN yoy_growth_pct > 0 THEN 'Appreciating'
        WHEN yoy_growth_pct < 0 THEN 'Declining'
        WHEN yoy_growth_pct = 0 THEN 'Stable'
        ELSE 'Insufficient History'
    END AS market_direction

FROM ranked
WHERE rn = 1;


-- 2. Full quarterly trend

CREATE OR REPLACE VIEW housing.vw_nhb_quarterly_trends AS

SELECT
    city,
    observation_date,
    financial_year,
    calendar_year,
    calendar_quarter,
    house_price_index,
    qoq_growth_pct,
    yoy_growth_pct,
    source,
    index_type

FROM housing.nhb_residex;


-- 3. Latest market momentum

CREATE OR REPLACE VIEW housing.vw_nhb_market_momentum AS

WITH trends AS (
    SELECT
        city,
        observation_date,
        house_price_index,
        qoq_growth_pct,
        yoy_growth_pct,

        LAG(qoq_growth_pct) OVER (
            PARTITION BY city
            ORDER BY observation_date
        ) AS previous_qoq_growth

    FROM housing.nhb_residex
),

latest AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY city
            ORDER BY observation_date DESC
        ) AS rn
    FROM trends
)

SELECT
    city,
    observation_date,
    house_price_index,
    qoq_growth_pct,
    previous_qoq_growth,
    yoy_growth_pct,

    ROUND(
        (
            qoq_growth_pct - previous_qoq_growth
        )::numeric,
        2
    ) AS momentum_change_pp,

    CASE
        WHEN previous_qoq_growth IS NULL
            OR qoq_growth_pct IS NULL
            THEN 'Insufficient History'
        WHEN qoq_growth_pct > previous_qoq_growth
            THEN 'Accelerating'
        WHEN qoq_growth_pct < previous_qoq_growth
            THEN 'Decelerating'
        ELSE 'Unchanged'
    END AS momentum_signal

FROM latest
WHERE rn = 1;


-- Verification

SELECT
    table_name
FROM information_schema.views
WHERE table_schema = 'housing'
ORDER BY table_name;
