#!/bin/bash

# Function to calculate next weekend after the next one (roughly 15 days from today)
get_short_term_dates() {
  current_date=$(date +%Y-%m-%d)
  next_friday=$(date -d "$current_date +$(( (5-$(date +%u)) % 7 + 7 )) days" +%Y-%m-%d)
  next_sunday=$(date -d "$next_friday +2 days" +%Y-%m-%d)
  echo "$next_friday $next_sunday"
}

# Function to calculate the 1st day of the next month and add 3 months for mid-term
get_mid_term_dates() {
  next_month_first=$(date -d "$(date +'%Y-%m-01') +1 month" +%Y-%m-%d)
  three_months_later=$(date -d "$next_month_first +3 months" +%Y-%m-%d)
  echo "$next_month_first $three_months_later"
}

# Function to calculate the 1st day of the next month and add 12 months for long-term
get_long_term_dates() {
  next_month_first=$(date -d "$(date +'%Y-%m-01') +1 month" +%Y-%m-%d)
  twelve_months_later=$(date -d "$next_month_first +12 months" +%Y-%m-%d)
  echo "$next_month_first $twelve_months_later"
}

# Airbnb URLs dynamically generated
short_term_dates=$(get_short_term_dates)
short_term_checkin=$(echo $short_term_dates | cut -d ' ' -f 1)
short_term_checkout=$(echo $short_term_dates | cut -d ' ' -f 2)
airbnb_short_url="https://www.airbnb.es/s/Segovia--Espa%C3%B1a--Segovia--Espa%C3%B1a/homes?refinement_paths%5B%5D=%2Fhomes&property_type_id%5B%5D=1&place_id=ChIJpTALIQA_QQ0RwPB3-yycavA&checkin=$short_term_checkin&checkout=$short_term_checkout&adults=1&tab_id=home_tab"

mid_term_dates=$(get_mid_term_dates)
mid_term_start=$(echo $mid_term_dates | cut -d ' ' -f 1)
mid_term_end=$(echo $mid_term_dates | cut -d ' ' -f 2)
airbnb_mid_url="https://www.airbnb.es/s/Segovia--Espa%C3%B1a--Segovia--Espa%C3%B1a/homes?refinement_paths%5B%5D=%2Fhomes&monthly_start_date=$mid_term_start&monthly_length=3&monthly_end_date=$mid_term_end"

long_term_dates=$(get_long_term_dates)
long_term_start=$(echo $long_term_dates | cut -d ' ' -f 1)
long_term_end=$(echo $long_term_dates | cut -d ' ' -f 2)
airbnb_long_url="https://www.airbnb.es/s/Segovia--Espa%C3%B1a--Segovia--Espa%C3%B1a/homes?refinement_paths%5B%5D=%2Fhomes&monthly_start_date=$long_term_start&monthly_length=12&monthly_end_date=$long_term_end"

# Activate virtual environment
source /home/other/dev/github/rental-scrapers/env/bin/activate

# Run Airbnb scrapers
echo "Running Airbnb Short-Term Scraper..."
/home/other/dev/github/rental-scrapers/env/bin/python /home/other/dev/github/rental-scrapers/src/airbnb_scraper.py --url "$airbnb_short_url" &&
echo "Airbnb Short-Term Scraper finished."

echo "Running Airbnb Medium-Term Scraper..."
/home/other/dev/github/rental-scrapers/env/bin/python /home/other/dev/github/rental-scrapers/src/airbnb_scraper.py --url "$airbnb_mid_url" &&
echo "Airbnb Medium-Term Scraper finished."

echo "Running Airbnb Long-Term Scraper..."
/home/other/dev/github/rental-scrapers/env/bin/python /home/other/dev/github/rental-scrapers/src/airbnb_scraper.py --url "$airbnb_long_url" &&
echo "Airbnb Long-Term Scraper finished."

# Now run Idealista scrapers
echo "Running Idealista Segovia Sale Scraper..."
/home/other/dev/github/rental-scrapers/env/bin/python /home/other/dev/github/rental-scrapers/src/idealista_scraper.py --url "https://www.idealista.com/venta-viviendas/segovia-segovia/" --delay 5
echo "Finished scraping Segovia Sale. Waiting 5 minutes..."

# Sleep for 5 minutes (300 seconds)
sleep 300

# Run scraper for the second URL
echo "Running Idealista Segovia Rent Scraper..."
/home/other/dev/github/rental-scrapers/env/bin/python /home/other/dev/github/rental-scrapers/src/idealista_scraper.py --url "https://www.idealista.com/alquiler-viviendas/segovia-segovia/" --delay 5
echo "Finished scraping Segovia Rent."
