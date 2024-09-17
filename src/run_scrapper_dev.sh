#!/bin/bash

# Activate virtual environment
source /home/other/dev/github/rental-scrapers/env/bin/activate

# Variables for dates
# Short-term dates: Weekend after the next weekend (approximately 15 days from now)
short_term_start=$(date -d "next Friday +1 week" +%Y-%m-%d)
short_term_end=$(date -d "$short_term_start +2 days" +%Y-%m-%d)

# Mid-term and long-term dates: Starting from the 1st of the next month
mid_term_start=$(date -d "$(date +%Y-%m-01) +1 month" +%Y-%m-%d)
mid_term_length=3
mid_term_end=$(date -d "$mid_term_start +$mid_term_length months" +%Y-%m-%d)

long_term_start=$mid_term_start
long_term_length=12
long_term_end=$(date -d "$long_term_start +$long_term_length months" +%Y-%m-%d)

# Airbnb base URL
airbnb_base_url="https://www.airbnb.es/s/Segovia--Espa%C3%B1a--Segovia--Espa%C3%B1a/homes"

# Airbnb URLs
short_term_url="${airbnb_base_url}?refinement_paths%5B%5D=%2Fhomes&property_type_id%5B%5D=1&place_id=ChIJpTALIQA_QQ0RwPB3-yycavA&checkin=${short_term_start}&checkout=${short_term_end}&adults=1&tab_id=home_tab"

mid_term_url="${airbnb_base_url}?refinement_paths%5B%5D=%2Fhomes&monthly_start_date=${mid_term_start}&monthly_length=${mid_term_length}&monthly_end_date=${mid_term_end}"

long_term_url="${airbnb_base_url}?refinement_paths%5B%5D=%2Fhomes&monthly_start_date=${long_term_start}&monthly_length=${long_term_length}&monthly_end_date=${long_term_end}"

# Idealista URLs
idealista_sale_url="https://www.idealista.com/venta-viviendas/segovia-segovia/"
idealista_rent_url="https://www.idealista.com/alquiler-viviendas/segovia-segovia/"

# Run Airbnb scrapers
echo "Running Airbnb Short-Term Scraper..."
/home/other/dev/github/rental-scrapers/env/bin/python /home/other/dev/github/rental-scrapers/src/airbnb_scraper.py --url "${short_term_url}" &&
echo "Airbnb Short-Term Scraper finished. Running Medium-Term Scraper..."

echo "Running Airbnb Medium-Term Scraper..."
/home/other/dev/github/rental-scrapers/env/bin/python /home/other/dev/github/rental-scrapers/src/airbnb_scraper.py --url "${mid_term_url}" &&
echo "Airbnb Medium-Term Scraper finished. Running Long-Term Scraper..."

echo "Running Airbnb Long-Term Scraper..."
/home/other/dev/github/rental-scrapers/env/bin/python /home/other/dev/github/rental-scrapers/src/airbnb_scraper.py --url "${long_term_url}" &&
echo "Airbnb Long-Term Scraper finished."

# Now run Idealista scrapers
echo "Running Idealista Segovia Sale Scraper..."
/home/other/dev/github/rental-scrapers/env/bin/python /home/other/dev/github/rental-scrapers/src/idealista_scraper.py --url "${idealista_sale_url}" --delay 5
echo "Finished scraping Segovia Sale. Waiting 5 minutes..."

# Sleep for 5 minutes (300 seconds)
sleep 300

# Run scraper for the second URL
echo "Running Idealista Segovia Rent Scraper..."
/home/other/dev/github/rental-scrapers/env/bin/python /home/other/dev/github/rental-scrapers/src/idealista_scraper.py --url "${idealista_rent_url}" --delay 5
echo "Finished scraping Segovia Rent."
