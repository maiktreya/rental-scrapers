#!/bin/bash

# for headless and server use: install xvdf
export DISPLAY=:99 # Make sure to use the same display where Xvfb is running

# Define the path variable
BASE_PATH="/c/Users/70254057/Desktop/basic-hub/rental-scrapers"

# Get the format parameter from the user, default to "csv" if not provided
format=${1:-csv}

# Activate virtual environment
source "$BASE_PATH/.venv\Scripts\activate"

run_scraper() {
    local format=$1

    echo "Running Idealista Segovia Sale Scraper for format: $format"
    "$BASE_PATH/.venv/Scripts/python.exe" "$BASE_PATH/src/idealista_scraper.1.prod.py" \
        --url "https://www.idealista.com/venta-viviendas/segovia-segovia/" \
        --delay 5 --format "$format"
    echo "Finished scraping Segovia Sale"
}

# Check format option and run accordingly
run_scraper "$format"
