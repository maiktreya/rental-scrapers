#!/bin/bash

# This script launches the Airbnb scraper for short, medium, and long-term stays in Segovia.
# for headless and server use: you may need to run 'export DISPLAY=:99' if using Xvfb.

# Define the path to your project directory
BASE_PATH="/home/other/dev/github/rental-scrapers"

# Get the desired output format from the first command-line argument. Defaults to "csv".
format=${1:-csv}

# --- Dynamic Date Calculations for Airbnb URLs ---

# Calculate dates for a weekend stay (Friday to Sunday) in about two weeks.
# On Friday, June 6th, 2025, this will calculate checkin=2025-06-20 and checkout=2025-06-22
next_friday_in_two_weeks=$(date -d "Friday +1 week" +%Y-%m-%d)
next_sunday_in_two_weeks=$(date -d "$next_friday_in_two_weeks +2 days" +%Y-%m-%d)

# Calculate dates for a 3-month stay starting the first of next month.
# In June 2025, this will calculate start=2025-07-01 and end=2025-10-01
start_of_next_month=$(date -d "$(date +%Y-%m-01) +1 month" +%Y-%m-%d)
end_of_3_month_stay=$(date -d "$start_of_next_month +3 months" +%Y-%m-%d)

# Calculate dates for a 12-month stay starting the first of next month.
# In June 2025, this will calculate start=2025-07-01 and end=2026-07-01
end_of_12_month_stay=$(date -d "$start_of_next_month +12 months" +%Y-%m-%d)


# --- Dynamic Airbnb URL Generation ---

# Note: The 'place_id' and other parameters are specific to a "Segovia, Spain" search.
airbnb_base_query="https://www.airbnb.es/s/Segovia--Espa%C3%B1a/homes?place_id=ChIJpTALIQA_QQ0RwPB3-yycavA"

airbnb_short_term_url="${airbnb_base_query}&checkin=${next_friday_in_two_weeks}&checkout=${next_sunday_in_two_weeks}&adults=1&tab_id=home_tab"

airbnb_medium_term_url="${airbnb_base_query}&monthly_start_date=${start_of_next_month}&monthly_length=3&monthly_end_date=${end_of_3_month_stay}"

airbnb_long_term_url="${airbnb_base_query}&monthly_start_date=${start_of_next_month}&monthly_length=12&monthly_end_date=${end_of_12_month_stay}"

# --- Scraper Execution ---

# Activate Python virtual environment
source "$BASE_PATH/env/bin/activate"

# Function to run the scrapers
run_airbnb_scrapers() {
    local output_format=$1
    local python_executable="$BASE_PATH/env/bin/python"
    local scraper_script="$BASE_PATH/src/airbnb_scraper.py"

    echo "--- Starting Airbnb Scrapers (Format: $output_format) ---"

    echo "Running Airbnb Short-Term Scraper..."
    "$python_executable" "$scraper_script" \
        --url "$airbnb_short_term_url" --format "$output_format"
    echo "Airbnb Short-Term Scraper finished."

    echo "Running Airbnb Medium-Term Scraper..."
    "$python_executable" "$scraper_script" \
        --url "$airbnb_medium_term_url" --format "$output_format"
    echo "Airbnb Medium-Term Scraper finished."

    echo "Running Airbnb Long-Term Scraper..."
    "$python_executable" "$scraper_script" \
        --url "$airbnb_long_term_url" --format "$output_format"
    echo "Airbnb Long-Term Scraper finished."

    echo "--- All Airbnb scraping tasks are complete. ---"
}

# Run the scrapers with the specified format
run_airbnb_scrapers "$format"

# Deactivate the virtual environment
deactivate