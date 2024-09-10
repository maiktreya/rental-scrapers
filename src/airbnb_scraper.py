# python scrapping/src/airbnb/airbnb_scraper.py --url "https://www.airbnb.es/s/Segovia--Espa%C3%B1a--Segovia--Espa%C3%B1a/homes?refinement_paths%5B%5D=%2Fhomes&property_type_id%5B%5D=1&place_id=ChIJpTALIQA_QQ0RwPB3-yycavA&checkin=2024-09-20&checkout=2024-09-22&adults=1&tab_id=home_tab"

import argparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import pandas as pd
import logging
import os
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Function to parse command-line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description="Airbnb Scraper")
    parser.add_argument(
        "--url", type=str, required=True, help="URL to scrape Airbnb listings from"
    )
    return parser.parse_args()


# Function to wait for element
def wait_for_element(driver, by, value, timeout=10):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )


# Function to extract data
def extract_data(driver):
    listings_data = []
    html_content = driver.page_source
    soup = BeautifulSoup(html_content, "html.parser")
    all_listings = soup.find_all("div", {"data-testid": "card-container"})

    for item in all_listings:
        listing = {}

        # Extract Property Title
        try:
            title_element = item.find("div", {"data-testid": "listing-card-title"})
            listing["property_title"] = (
                title_element.text.strip() if title_element else None
            )
        except AttributeError as e:
            logger.warning(f"Error extracting property title: {str(e)}")
            listing["property_title"] = None

        # Extract Price
        try:
            price_element = item.find("span", string=lambda text: text and "€" in text)
            if price_element:
                price_text = price_element.text.strip()
                listing["price_with_tax"] = (
                    price_text.split(" total")[0]
                    if "total" in price_text
                    else price_text
                )
            else:
                listing["price_with_tax"] = None
        except AttributeError as e:
            logger.warning(f"Error extracting price: {str(e)}")
            listing["price_with_tax"] = None

        # Extract Property Type
        try:
            property_type_element = item.find(
                "span",
                string=lambda text: text
                and any(
                    word in text.lower()
                    for word in ["apartamento", "casa", "habitación"]
                ),
            )
            listing["property_type"] = (
                property_type_element.text.strip() if property_type_element else None
            )
        except AttributeError as e:
            logger.warning(f"Error extracting property type: {str(e)}")
            listing["property_type"] = None

        # Extract Beds and Rooms
        try:
            beds_rooms_element = item.find(
                "span",
                string=lambda text: text
                and any(
                    word in text.lower() for word in ["dormitorio", "cama", "baño"]
                ),
            )
            listing["beds_rooms"] = (
                beds_rooms_element.text.strip() if beds_rooms_element else None
            )
        except AttributeError as e:
            logger.warning(f"Error extracting beds/rooms: {str(e)}")
            listing["beds_rooms"] = None

        listings_data.append(listing)

    return listings_data


# Function to handle popups
def handle_popups(driver):
    try:
        close_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Close']"))
        )
        close_button.click()
        logger.info("Popup closed")
    except TimeoutException:
        logger.info("No popup found or couldn't close popup")


# Main scraper function
def scrape_airbnb(url):
    # ChromeDriver path for Ubuntu
    CHROMEDRIVER_PATH = "/usr/bin/chromedriver"
    service = Service(executable_path=CHROMEDRIVER_PATH)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(service=service, options=options)

    listings_data = []
    page_limit = 20
    current_page = 1

    try:
        driver.get(url)
        wait_for_element(driver, By.CSS_SELECTOR, "[data-testid='card-container']")

        while current_page <= page_limit:
            logger.info(f"Scraping page {current_page}")
            handle_popups(driver)
            listings_data.extend(extract_data(driver))

            try:
                next_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "a[aria-label='Siguiente']")
                    )
                )
                next_button.click()
                logger.info("Clicked 'Next' button")
                wait_for_element(
                    driver, By.CSS_SELECTOR, "[data-testid='card-container']"
                )
                current_page += 1
            except TimeoutException:
                logger.info("No 'Next' button found or not clickable. Ending scraping.")
                break
            except Exception as e:
                logger.error(f"Error while navigating to next page: {str(e)}")
                break
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
    finally:
        driver.quit()

    # Ensure output directory exists
    output_dir = "scrapping/out"
    os.makedirs(output_dir, exist_ok=True)

    # Generate CSV filename with datetime
    datetime_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"airbnb_{datetime_str}.csv")

    # Save data to CSV
    try:
        df = pd.DataFrame(listings_data)
        df.to_csv(output_file, index=False, encoding="utf-8")
        logger.info(
            f"Scraped {len(listings_data)} listings. Data saved to {output_file}"
        )
    except Exception as e:
        logger.error(f"Error saving to CSV: {str(e)}")


# Entry point for the script
if __name__ == "__main__":
    args = parse_arguments()
    scrape_airbnb(args.url)
