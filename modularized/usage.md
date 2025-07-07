# Rental Scraper Usage Guide

This document outlines how to run the rental property scraper. The scraper is designed to fetch listings from Idealista based on a predefined list of targets stored in a database.

## 1. Standard Scraper Operation

The primary mode of operation is to scrape all active capital cities as defined in your database. The scraper requires one command-line argument to specify the type of property you wish to scrape.

### Argument:

`property_type`: (Required) Specifies the listing category.
`viviendas`: For scraping entire homes (apartments, houses).
`habitacion`: For scraping individual rooms for rent.

### How It Works:

When you run the scraper with one of the property types, it will:
Connect to your PostgREST database.
Call the ``method to get a list of all cities where is_active is true.
Call the`fetch_active_capitals method to get a list of all cities where is_active is true.
Iterate through each city one by one, scraping all available listings up to the configured page limit.
Save the results back to the database.
Keep track of its progress, so if it's stopped, it can resume where it left off on the next run.

### Example Commands:

To scrape all active capitals for entire homes:

```bash
python scraper_new.py viviendas
```

To scrape all active capitals for rooms:

```bash
python scraper_new.py habitacion
```

## 2. Scraping Custom URLs

The current version of the scraper is not designed to accept custom, one-off URLs from the command line.
Its logic is tightly integrated with the `DatabaseManager` to:
Fetch a list of targets (the active capitals).
Maintain state (`get_scraper_status`, `update_scraper_status`) to ensure it can resume if interrupted.
Associate scraped listings with a capital_id from the database.
To scrape a specific city or URL, the recommended approach is to modify the is_active flag for that city in your capitals database table. This allows you to control the scraping targets without changing the code.

## 3. Configuration Parameters

The scraper's behavior can be tweaked by modifying the parameters within the ScraperConfig class in the main script (scraper_new.py). To change these values, you must edit the file directly.

```bash
delay (Default: 5.0):
```

The base delay in seconds between consecutive requests to the same domain. This helps avoid rate-limiting.

```bash
header_refresh_requests (Default: 100):
```

The number of requests to make before automatically fetching a new set of browser headers to mimic a new session.

```bash
max_retries (Default: 3):
```

The maximum number of times the scraper will retry a failed network request.

```bash
timeout (Default: 45):
```

The number of seconds to wait for a server response before giving up.

```bash
max_pages (Default: 50):
```

The maximum number of pages to scrape for any single capital city. This acts as a safeguard to prevent excessively long scraping runs.

```bash
postgrest_url (Default: http://localhost:3000):
```

The URL for your PostgREST database API. It's recommended to set this using the POSTGREST_URL environment variable instead of changing it in the code.

## 4. Fully fledged example

An example of a complex customized run.

- For a tailored list of urls

```bash
python -u -m services.idealista_scraper.main \
            --postgrest-url "http://localhost:3001" \
            --idealista-base-url "https://www.idealista.com/alquiler-viviendas/" \
            --scraper-type "viviendas" \
            --delay 7 \
            --max-pages 1
```

- A full loop over all Spain capitals

```bash
python -u -m services.idealista_scraper.main \
            --postgrest-url "http://localhost:3001" \
            --idealista-base-url "https://www.idealista.com/alquiler-viviendas/" \
            --scraper-type "viviendas" \
            --delay 7 \
            --max-pages 1
```