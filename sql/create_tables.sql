
CREATE SCHEMA IF NOT EXISTS housing;

CREATE TABLE IF NOT EXISTS housing.house_price_index (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city VARCHAR(100) NOT NULL,
    base_year VARCHAR(20) NOT NULL,
    observation_date DATE NOT NULL,
    financial_year VARCHAR(10) NOT NULL,
    calendar_year INTEGER NOT NULL,
    calendar_quarter INTEGER NOT NULL
        CHECK (calendar_quarter BETWEEN 1 AND 4),
    house_price_index DOUBLE PRECISION NOT NULL
        CHECK (house_price_index > 0),
    qoq_growth_pct DOUBLE PRECISION,
    yoy_growth_pct DOUBLE PRECISION,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_hpi_observation
        UNIQUE (city, base_year, observation_date)
);

CREATE INDEX IF NOT EXISTS idx_hpi_city_date
    ON housing.house_price_index (city, observation_date);
