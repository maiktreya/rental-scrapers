#!/bin/bash

# for headless and server use: install xvdf
export DISPLAY=:99 # Make sure to use the same display where Xvfb is running

# Define the path variable
BASE_PATH="/home/other/dev/github/rental-scrapers"

# Add the project root to PYTHONPATH so Python can find 'lib' module
# This ensures that 'lib' is accessible when scripts in 'src' try to import from it.
export PYTHONPATH="$BASE_PATH:$PYTHONPATH"

# Get the format parameter from the user, default to "csv" if not provided
format=${1:-csv}

# Activate virtual environment
source "$BASE_PATH/env/bin/activate"

run_scraper() {
    local format=$1

    echo "Running Idealista Segovia Sale Scraper for format: $format"
    "$BASE_PATH/env/bin/python" "$BASE_PATH/src/idealista_scraper.2.py" \
        --url "https://www.idealista.com/venta-viviendas/segovia-segovia/" \
        --delay 5 --format "$format"
    echo "Finished scraping Segovia Sale. Waiting 5 minutes..."

}

# Check format option and run accordingly
run_scraper "$format"