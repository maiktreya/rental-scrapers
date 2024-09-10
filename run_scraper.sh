#!/bin/bash

# Activate virtual environment
source /home/other/dev/github/LocalWealthHousing/env/bin/activate

# Run Airbnb scrapers
echo "Running Airbnb Short-Term Scraper..."
/home/other/dev/github/LocalWealthHousing/env/bin/python /home/other/dev/github/LocalWealthHousing/scrapping/src/airbnb/airbnb_scraper.py --url "https://www.airbnb.es/s/Segovia--Espa%C3%B1a--Segovia--Espa%C3%B1a/homes?refinement_paths%5B%5D=%2Fhomes&property_type_id%5B%5D=1&place_id=ChIJpTALIQA_QQ0RwPB3-yycavA&checkin=2024-09-20&checkout=2024-09-22&adults=1&tab_id=home_tab" &&
echo "Airbnb Short-Term Scraper finished. Running Medium-Term Scraper..."

echo "Running Airbnb Medium-Term Scraper..."
/home/other/dev/github/LocalWealthHousing/env/bin/python /home/other/dev/github/LocalWealthHousing/scrapping/src/airbnb/airbnb_scraper.py --url "https://www.airbnb.es/s/Segovia--Espa%C3%B1a--Segovia--Espa%C3%B1a/homes?refinement_paths%5B%5D=%2Fhomes&property_type_id%5B%5D=1&place_id=ChIJpTALIQA_QQ0RwPB3-yycavA&checkin=2024-09-20&checkout=2024-09-22&adults=1&tab_id=home_tab" &&
&& \
echo "Airbnb Medium-Term Scraper finished. Running Long-Term Scraper..."
#
echo "Running Airbnb Long-Term Scraper..."
/home/other/dev/github/LocalWealthHousing/env/bin/python /home/other/dev/github/LocalWealthHousing/scrapping/src/airbnb/airbnb_scraper.py --url "https://www.airbnb.es/s/Segovia--Espa%C3%B1a--Segovia--Espa%C3%B1a/homes?refinement_paths%5B%5D=%2Fhomes&property_type_id%5B%5D=1&place_id=ChIJpTALIQA_QQ0RwPB3-yycavA&checkin=2024-09-20&checkout=2024-09-22&adults=1&tab_id=home_tab" &&
&& \echo "Airbnb Long-Term Scraper finished."

# Now run Idealista scrapers
echo "Running Idealista Segovia Sale Scraper..."
/home/other/dev/github/LocalWealthHousing/env/bin/python /home/other/dev/github/LocalWealthHousing/scrapping/src/idealista/idealista_httpx.ori.py --url "https://www.idealista.com/venta-viviendas/segovia-segovia/" --delay 5
echo "Finished scraping Segovia Sale. Waiting 5 minutes..."

# Sleep for 5 minutes (300 seconds)
sleep 300

# Run scraper for the second URL
echo "Running Idealista Segovia Rent Scraper..."
/home/other/dev/github/LocalWealthHousing/env/bin/python /home/other/dev/github/LocalWealthHousing/scrapping/src/idealista/idealista_httpx.ori.py --url "https://www.idealista.com/alquiler-viviendas/segovia-segovia/" --delay 5
echo "Finished scraping Segovia Rent."
