-- Migration to add exchange-related tables

-- Exchange credentials table
CREATE TABLE IF NOT EXISTS exchange_credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR NOT NULL,
    location VARCHAR NOT NULL,
    api_key VARCHAR NOT NULL,
    api_secret VARCHAR,
    passphrase VARCHAR,
    CONSTRAINT unique_exchange_name_location UNIQUE (name, location)
);

CREATE INDEX IF NOT EXISTS idx_exchange_credentials_name ON exchange_credentials(name);
CREATE INDEX IF NOT EXISTS idx_exchange_credentials_location ON exchange_credentials(location);

-- Exchange extras table for additional configuration
CREATE TABLE IF NOT EXISTS exchange_extras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange_name VARCHAR NOT NULL,
    exchange_location VARCHAR NOT NULL,
    extras JSON NOT NULL DEFAULT '{}',
    CONSTRAINT unique_exchange_extras UNIQUE (exchange_name, exchange_location)
);

CREATE INDEX IF NOT EXISTS idx_exchange_extras_name ON exchange_extras(exchange_name);
CREATE INDEX IF NOT EXISTS idx_exchange_extras_location ON exchange_extras(exchange_location);

-- Cached exchange data table
CREATE TABLE IF NOT EXISTS exchange_cached_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange_name VARCHAR NOT NULL,
    exchange_location VARCHAR NOT NULL,
    data_type VARCHAR NOT NULL,
    timestamp INTEGER NOT NULL,
    data JSON NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_exchange_cached_name ON exchange_cached_data(exchange_name);
CREATE INDEX IF NOT EXISTS idx_exchange_cached_location ON exchange_cached_data(exchange_location);
CREATE INDEX IF NOT EXISTS idx_exchange_cached_type ON exchange_cached_data(data_type);

-- Available trading pairs table
CREATE TABLE IF NOT EXISTS exchange_trade_pairs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange_location VARCHAR NOT NULL,
    pair VARCHAR NOT NULL,
    base_asset VARCHAR NOT NULL,
    quote_asset VARCHAR NOT NULL,
    active BOOLEAN NOT NULL DEFAULT 1,
    min_trade_size VARCHAR,
    timestamp INTEGER NOT NULL,
    CONSTRAINT unique_location_pair UNIQUE (exchange_location, pair)
);

CREATE INDEX IF NOT EXISTS idx_trade_pairs_location ON exchange_trade_pairs(exchange_location);

-- User-selected trading pairs table
CREATE TABLE IF NOT EXISTS user_exchange_pairs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange_name VARCHAR NOT NULL,
    exchange_location VARCHAR NOT NULL,
    pair VARCHAR NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT 1,
    CONSTRAINT unique_user_pair UNIQUE (exchange_name, exchange_location, pair)
);

CREATE INDEX IF NOT EXISTS idx_user_pairs_name ON user_exchange_pairs(exchange_name);
CREATE INDEX IF NOT EXISTS idx_user_pairs_location ON user_exchange_pairs(exchange_location);