CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    asin VARCHAR(32) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    brand VARCHAR(120),
    category VARCHAR(120),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sellers (
    id SERIAL PRIMARY KEY,
    seller_name VARCHAR(255) UNIQUE NOT NULL,
    rating NUMERIC(3,2),
    fulfillment_type VARCHAR(40),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS locations (
    id SERIAL PRIMARY KEY,
    pincode VARCHAR(12) NOT NULL,
    city VARCHAR(120),
    state VARCHAR(120),
    CONSTRAINT uq_locations_pincode_city UNIQUE (pincode, city)
);

CREATE TABLE IF NOT EXISTS price_history (
    id BIGSERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    seller_id INTEGER REFERENCES sellers(id),
    location_id INTEGER REFERENCES locations(id),
    price NUMERIC(12,2),
    availability VARCHAR(60),
    rating NUMERIC(3,2),
    review_count INTEGER,
    is_fba BOOLEAN NOT NULL DEFAULT FALSE,
    captured_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_price_history_product_time ON price_history(product_id, captured_at DESC);

CREATE TABLE IF NOT EXISTS offers (
    id BIGSERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    seller_id INTEGER NOT NULL REFERENCES sellers(id),
    location_id INTEGER REFERENCES locations(id),
    offer_price NUMERIC(12,2),
    availability VARCHAR(60),
    is_buy_box BOOLEAN NOT NULL DEFAULT FALSE,
    is_fba BOOLEAN NOT NULL DEFAULT FALSE,
    seller_rating NUMERIC(3,2),
    captured_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_offers_product_time ON offers(product_id, captured_at DESC);

CREATE TABLE IF NOT EXISTS buy_box_history (
    id BIGSERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    seller_id INTEGER NOT NULL REFERENCES sellers(id),
    location_id INTEGER REFERENCES locations(id),
    price NUMERIC(12,2),
    captured_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_buy_box_history_product_time ON buy_box_history(product_id, captured_at DESC);

CREATE TABLE IF NOT EXISTS alert_events (
    id BIGSERIAL PRIMARY KEY,
    alert_type VARCHAR(60) NOT NULL,
    asin VARCHAR(32) NOT NULL,
    seller_name VARCHAR(255),
    location VARCHAR(120),
    message TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'info',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
