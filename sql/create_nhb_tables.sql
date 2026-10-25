
CREATE SCHEMA IF NOT EXISTS housing;

CREATE TABLE IF NOT EXISTS housing.nhb_residex (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    city VARCHAR(100) NOT NULL,
    observation_date DATE NOT NULL,

    house_price_index DOUBLE PRECISION NOT NULL,
    qoq_growth_pct DOUBLE PRECISION,
    yoy_growth_pct DOUBLE PRECISION,

    source VARCHAR(50) NOT NULL,
    index_type VARCHAR(100) NOT NULL,

    calendar_year INTEGER NOT NULL,
    calendar_quarter INTEGER NOT NULL,
    financial_year VARCHAR(10) NOT NULL,

    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_nhb_city_quarter
        UNIQUE (
            city,
            observation_date,
            index_type
        ),

    CONSTRAINT chk_nhb_positive_hpi
        CHECK (house_price_index > 0),

    CONSTRAINT chk_nhb_quarter
        CHECK (calendar_quarter BETWEEN 1 AND 4)
);

CREATE INDEX IF NOT EXISTS idx_nhb_city_date
ON housing.nhb_residex (
    city,
    observation_date
);
