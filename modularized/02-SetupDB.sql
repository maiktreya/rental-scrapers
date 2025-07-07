-- Create the schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS idealista_scrapper;

-----------------------------------------
-- Table: scraper_status
-- Stores the progress of different scrapers
-----------------------------------------
CREATE TABLE IF NOT EXISTS idealista_scrapper.scraper_status (
    scraper_type TEXT PRIMARY KEY NOT NULL,
    last_processed_capital_id INTEGER NOT NULL DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE idealista_scrapper.scraper_status IS 'Tracks the progress of different scraper types by storing the last processed capital ID.';

-----------------------------------------
-- Table: capitals
-- Stores target areas for scraping
-----------------------------------------
CREATE TABLE IF NOT EXISTS idealista_scrapper.capitals (
    id SERIAL PRIMARY KEY,
    province_code CHAR(2) NOT NULL,
    capital_name TEXT NOT NULL,
    zona TEXT NOT NULL,
    distrito TEXT,
    idealista_slug TEXT NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

COMMENT ON TABLE idealista_scrapper.capitals IS 'Stores target areas (province capitals/regions) for scraping from Idealista, linking slugs to standard province codes.';
COMMENT ON COLUMN idealista_scrapper.capitals.idealista_slug IS 'Unique URL slug component identifying the area on Idealista.';
COMMENT ON COLUMN idealista_scrapper.capitals.is_active IS 'Indicates if this target should currently be scraped (TRUE) or skipped (FALSE).';

-- Indexes for capitals
CREATE INDEX IF NOT EXISTS idx_capitals_slug ON idealista_scrapper.capitals (idealista_slug);
CREATE INDEX IF NOT EXISTS idx_capitals_capital_name ON idealista_scrapper.capitals (capital_name);
CREATE INDEX IF NOT EXISTS idx_capitals_is_active ON idealista_scrapper.capitals (is_active);

-- Drop existing tables to ensure clean slate
DROP TABLE IF EXISTS idealista_scrapper.observations;
DROP TABLE IF EXISTS idealista_scrapper.room_observations;
DROP TABLE IF EXISTS idealista_scrapper.listings;
DROP TABLE IF EXISTS idealista_scrapper.rooms;

-----------------------------------------
-- Table: listings
-- Stores static information for property listings (viviendas)
-- Matches PropertyResult TypedDict structure
-----------------------------------------
CREATE TABLE IF NOT EXISTS idealista_scrapper.listings (
    -- Primary identification - integer ID for performance
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,             -- URL with unique constraint for database.py logic

    -- Fields matching PropertyResult TypedDict and database.py save_listing method
    title TEXT NULL,
    location TEXT NULL,                    -- Matches 'location' field in PropertyResult
    property_type TEXT NULL,
    size_sqm INTEGER NULL,
    num_bedrooms INTEGER NULL,
    advertiser_type TEXT NULL,
    advertiser_name TEXT NULL,
    capital_id INTEGER NOT NULL,          -- Foreign key to capitals table

    -- Additional fields from PropertyResult (optional/not used in database.py but in model)
    listing_id INTEGER NULL,              -- Optional numeric ID from URL
    flat_floor_number TEXT NULL,
    description TEXT NULL,
    pricedown_price NUMERIC(10,2) NULL,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE idealista_scrapper.listings IS 'Stores static information for property listings (viviendas), matching the PropertyResult TypedDict structure.';
COMMENT ON COLUMN idealista_scrapper.listings.id IS 'Auto-incrementing integer primary key for optimal performance.';
COMMENT ON COLUMN idealista_scrapper.listings.url IS 'Full original URL of the listing. Has UNIQUE constraint for database.py logic.';
COMMENT ON COLUMN idealista_scrapper.listings.title IS 'The title of the listing.';
COMMENT ON COLUMN idealista_scrapper.listings.location IS 'Location string scraped from the listing.';
COMMENT ON COLUMN idealista_scrapper.listings.property_type IS 'The type of property (e.g., "Piso", "Chalet").';
COMMENT ON COLUMN idealista_scrapper.listings.size_sqm IS 'The size in square meters.';
COMMENT ON COLUMN idealista_scrapper.listings.num_bedrooms IS 'The number of bedrooms listed.';
COMMENT ON COLUMN idealista_scrapper.listings.advertiser_type IS 'Category of the advertiser (e.g., "particular", "profesional").';
COMMENT ON COLUMN idealista_scrapper.listings.advertiser_name IS 'The display name of the advertiser.';
COMMENT ON COLUMN idealista_scrapper.listings.capital_id IS 'Foreign key referencing the capital where this listing was found.';

-- Indexes for listings
CREATE INDEX IF NOT EXISTS idx_listings_url ON idealista_scrapper.listings (url);
CREATE INDEX IF NOT EXISTS idx_listings_capital_id ON idealista_scrapper.listings (capital_id);
CREATE INDEX IF NOT EXISTS idx_listings_property_type ON idealista_scrapper.listings (property_type);
CREATE INDEX IF NOT EXISTS idx_listings_location ON idealista_scrapper.listings (location);

-----------------------------------------
-- Table: rooms
-- Stores static information for room listings (habitaciones)
-- Matches RoomResult TypedDict structure
-----------------------------------------
CREATE TABLE IF NOT EXISTS idealista_scrapper.rooms (
    -- Primary identification - integer ID for performance
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,             -- URL with unique constraint for database.py logic

    -- Fields matching RoomResult TypedDict and database.py save_listing method
    title TEXT NULL,
    location TEXT NULL,                    -- Matches 'location' field in RoomResult
    property_type TEXT NULL,
    advertiser_type TEXT NULL,
    advertiser_name TEXT NULL,
    available_from_date TEXT NULL,        -- Specific to rooms, stored as TEXT
    capital_id INTEGER NOT NULL,          -- Foreign key to capitals table

    -- Additional fields from RoomResult (optional/not used in database.py but in model)
    room_id INTEGER NULL,                 -- Optional numeric ID from URL
    flat_floor_number TEXT NULL,
    description TEXT NULL,
    num_bedrooms INTEGER NULL,
    pricedown_price NUMERIC(10,2) NULL,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE idealista_scrapper.rooms IS 'Stores static information for room listings (habitaciones), matching the RoomResult TypedDict structure.';
COMMENT ON COLUMN idealista_scrapper.rooms.id IS 'Auto-incrementing integer primary key for optimal performance.';
COMMENT ON COLUMN idealista_scrapper.rooms.url IS 'Full original URL of the room listing. Has UNIQUE constraint for database.py logic.';
COMMENT ON COLUMN idealista_scrapper.rooms.title IS 'Title of the room listing.';
COMMENT ON COLUMN idealista_scrapper.rooms.location IS 'Location string scraped from the listing.';
COMMENT ON COLUMN idealista_scrapper.rooms.property_type IS 'Type of property, typically "habitación".';
COMMENT ON COLUMN idealista_scrapper.rooms.advertiser_type IS 'Type of advertiser (e.g., "Particular" or "Agencia").';
COMMENT ON COLUMN idealista_scrapper.rooms.advertiser_name IS 'The display name of the advertiser.';
COMMENT ON COLUMN idealista_scrapper.rooms.available_from_date IS 'Date from which the room is available.';
COMMENT ON COLUMN idealista_scrapper.rooms.capital_id IS 'Foreign key referencing the capital where this room listing was found.';

-- Indexes for rooms
CREATE INDEX IF NOT EXISTS idx_rooms_url ON idealista_scrapper.rooms (url);
CREATE INDEX IF NOT EXISTS idx_rooms_capital_id ON idealista_scrapper.rooms (capital_id);
CREATE INDEX IF NOT EXISTS idx_rooms_available_from_date ON idealista_scrapper.rooms (available_from_date);
CREATE INDEX IF NOT EXISTS idx_rooms_property_type ON idealista_scrapper.rooms (property_type);

-----------------------------------------
-- Table: observations
-- Stores time-series price data for property listings
-- Matches the observation saving logic in database.py
-----------------------------------------
CREATE TABLE IF NOT EXISTS idealista_scrapper.observations (
    id SERIAL PRIMARY KEY,               -- Auto-incrementing primary key for performance
    listing_url TEXT NOT NULL,           -- URL reference to listings table
    price INTEGER NULL,                  -- Price observed at scrape time
    scraped_at TIMESTAMPTZ NOT NULL,     -- Timestamp when data was scraped

    -- Ensure unique combinations of listing_url and scraped_at
    UNIQUE(listing_url, scraped_at)
);

COMMENT ON TABLE idealista_scrapper.observations IS 'Stores time-series price observations for property listings, matching database.py logic.';
COMMENT ON COLUMN idealista_scrapper.observations.listing_url IS 'Foreign key referencing the listing URL this observation belongs to.';
COMMENT ON COLUMN idealista_scrapper.observations.price IS 'The price of the listing observed at scraped_at timestamp.';
COMMENT ON COLUMN idealista_scrapper.observations.scraped_at IS 'The exact timestamp when the observation data was scraped.';

-- Indexes for observations
CREATE INDEX IF NOT EXISTS idx_observations_listing_url ON idealista_scrapper.observations (listing_url);
CREATE INDEX IF NOT EXISTS idx_observations_scraped_at ON idealista_scrapper.observations (scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_observations_price ON idealista_scrapper.observations (price);

-----------------------------------------
-- Table: room_observations
-- Stores time-series price data for room listings
-- Matches the observation saving logic in database.py
-----------------------------------------
CREATE TABLE IF NOT EXISTS idealista_scrapper.room_observations (
    id SERIAL PRIMARY KEY,               -- Auto-incrementing primary key for performance
    listing_url TEXT NOT NULL,           -- URL reference to rooms table
    price INTEGER NULL,                  -- Price observed at scrape time
    scraped_at TIMESTAMPTZ NOT NULL,     -- Timestamp when data was scraped

    -- Ensure unique combinations of listing_url and scraped_at
    UNIQUE(listing_url, scraped_at)
);

COMMENT ON TABLE idealista_scrapper.room_observations IS 'Stores time-series price observations for room listings, matching database.py logic.';
COMMENT ON COLUMN idealista_scrapper.room_observations.listing_url IS 'Foreign key referencing the room URL this observation belongs to.';
COMMENT ON COLUMN idealista_scrapper.room_observations.price IS 'The price of the room listing observed at scraped_at timestamp.';
COMMENT ON COLUMN idealista_scrapper.room_observations.scraped_at IS 'The exact timestamp when the observation data was scraped.';

-- Indexes for room_observations
CREATE INDEX IF NOT EXISTS idx_room_observations_listing_url ON idealista_scrapper.room_observations (listing_url);
CREATE INDEX IF NOT EXISTS idx_room_observations_scraped_at ON idealista_scrapper.room_observations (scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_room_observations_price ON idealista_scrapper.room_observations (price);

-----------------------------------------
-- Foreign Key Constraints
-----------------------------------------

-- Link listings back to capitals
ALTER TABLE idealista_scrapper.listings
ADD CONSTRAINT fk_listings_capital FOREIGN KEY (capital_id)
REFERENCES idealista_scrapper.capitals (id)
ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED;

-- Link rooms back to capitals
ALTER TABLE idealista_scrapper.rooms
ADD CONSTRAINT fk_rooms_capital FOREIGN KEY (capital_id)
REFERENCES idealista_scrapper.capitals (id)
ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED;

-- Link observations to listings
ALTER TABLE idealista_scrapper.observations
ADD CONSTRAINT fk_observations_listing FOREIGN KEY (listing_url)
REFERENCES idealista_scrapper.listings (url)
ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;

-- Link room_observations to rooms
ALTER TABLE idealista_scrapper.room_observations
ADD CONSTRAINT fk_room_observations_room FOREIGN KEY (listing_url)
REFERENCES idealista_scrapper.rooms (url)
ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;

-----------------------------------------
-- Example Grants (Adjust user 'your_app_user' as needed)
-----------------------------------------
-- GRANT USAGE ON SCHEMA idealista_scrapper TO your_app_user;
-- GRANT SELECT ON ALL TABLES IN SCHEMA idealista_scrapper TO your_app_user;
-- GRANT INSERT, UPDATE, DELETE ON TABLE idealista_scrapper.capitals TO your_app_user;
-- GRANT INSERT, UPDATE, SELECT ON TABLE idealista_scrapper.listings TO your_app_user;
-- GRANT INSERT, UPDATE, SELECT ON TABLE idealista_scrapper.rooms TO your_app_user;
-- GRANT INSERT, SELECT ON TABLE idealista_scrapper.observations TO your_app_user;
-- GRANT INSERT, SELECT ON TABLE idealista_scrapper.room_observations TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE idealista_scrapper.capitals_id_seq TO your_app_user;