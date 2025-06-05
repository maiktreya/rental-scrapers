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
import json
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Function to parse command-line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description="Airbnb Scraper")
    parser.add_argument(
        "--url", type=str, required=True, help="URL to scrape Airbnb listings from"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["csv", "json", "both"],
        default="csv",
        help="Choose the export format: 'csv', 'json', or 'both'",
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

        # Extract Listing URL
        try:
            link_element = item.find("a", href=True)
            if link_element:
                relative_url = link_element['href']
                listing['url'] = f"https://www.airbnb.com{relative_url}"
            else:
                listing['url'] = None
        except (AttributeError, TypeError) as e:
            logger.warning(f"Error extracting URL: {str(e)}")
            listing['url'] = None

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
            price_element = item.find("span", string=lambda text: text and ("€" in text or "$" in text))
            if price_element:
                price_text = price_element.get_text(strip=True)
                listing["price_with_tax"] = price_text
            else:
                listing["price_with_tax"] = None
        except AttributeError as e:
            logger.warning(f"Error extracting price: {str(e)}")
            listing["price_with_tax"] = None

        # Extract Property Type
        try:
            property_type_element = item.select_one('[data-testid="listing-card-title"] + div > div')
            listing["property_type"] = (
                property_type_element.text.strip() if property_type_element else None
            )
        except AttributeError as e:
            logger.warning(f"Error extracting property type: {str(e)}")
            listing["property_type"] = None

        # Extract Beds and Rooms
        try:
            beds_rooms_elements = item.select('[data-testid="listing-card-title"] + div + div span')
            listing["beds_rooms"] = (
                ' · '.join(span.text for span in beds_rooms_elements if span.text) if beds_rooms_elements else None
            )
        except AttributeError as e:
            logger.warning(f"Error extracting beds/rooms: {str(e)}")
            listing["beds_rooms"] = None

        listings_data.append(listing)

    return listings_data


# Function to handle popups
def handle_popups(driver):
    try:
        close_button = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'close') or contains(@aria-label, 'Close')]"))
        )
        close_button.click()
        logger.info("Popup closed")
    except TimeoutException:
        logger.info("No popup found within the time limit.")


# Function to save data to CSV or JSON
def save_data(listings_data, format):
    output_dir = "out"
    os.makedirs(output_dir, exist_ok=True)
    datetime_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    if not listings_data:
        logger.warning("No data was scraped. Nothing to save.")
        return

    if format in ["csv", "both"]:
        output_file_csv = os.path.join(output_dir, f"airbnb_{datetime_str}.csv")
        try:
            df = pd.DataFrame(listings_data)
            df.to_csv(output_file_csv, index=False, encoding="utf-8")
            logger.info(f"Data saved to CSV: {output_file_csv}")
        except Exception as e:
            logger.error(f"Error saving to CSV: {str(e)}")

    if format in ["json", "both"]:
        output_file_json = os.path.join(output_dir, f"airbnb_{datetime_str}.json")
        try:
            with open(output_file_json, "w", encoding="utf-8") as json_file:
                json.dump(listings_data, json_file, ensure_ascii=False, indent=4)
            logger.info(f"Data saved to JSON: {output_file_json}")
        except Exception as e:
            logger.error(f"Error saving to JSON: {str(e)}")


# Main scraper function
def scrape_airbnb(url, format):
    CHROMEDRIVER_PATH = "/usr/bin/chromedriver"
    service = Service(executable_path=CHROMEDRIVER_PATH)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)

    listings_data = []
    page_limit = 20
    current_page = 1

    try:
        logger.info(f"Navigating to URL: {url}")
        driver.get(url)
        wait_for_element(driver, By.CSS_SELECTOR, "[data-testid='card-container']")
        handle_popups(driver)

        while current_page <= page_limit:
            logger.info(f"Scraping page {current_page}")

            # Get a reference to the current set of listings before clicking next
            page_listings = driver.find_elements(By.CSS_SELECTOR, "[data-testid='card-container']")
            if not page_listings:
                logger.warning("No listing cards found on the page.")
                break

            listings_data.extend(extract_data(driver))

            try:
                # Find the 'Next' button
                next_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "a[aria-label='Next'], a[aria-label='Siguiente']")
                    )
                )

                # This is the robust way to click and wait for page change
                # 1. Click the button
                next_button.click()
                logger.info("Clicked 'Next' button, waiting for page to update...")

                # 2. Wait for the old content to disappear (become stale)
                WebDriverWait(driver, 15).until(EC.staleness_of(page_listings[0]))

                # 3. (Optional but good practice) Wait for new content to appear
                wait_for_element(driver, By.CSS_SELECTOR, "[data-testid='card-container']")
                logger.info(f"Page {current_page + 1} loaded successfully.")
                current_page += 1

            except TimeoutException:
                logger.info("No more 'Next' buttons found. Ending scraping.")
                break
            except Exception as e:
                logger.error(f"Error during page navigation: {str(e)}")
                break
    except Exception as e:
        logger.error(f"A critical error occurred: {str(e)}")
    finally:
        # Save any data that was collected before an error
        save_data(listings_data, format)
        logger.info("Attempting to close the browser.")
        try:
            driver.quit()
        except PermissionError:
            logger.warning("Permission denied when trying to terminate the chromedriver process. This can happen in some environments but the script has finished.")
        except Exception as e:
            logger.error(f"An error occurred during driver quit: {str(e)}")


if __name__ == "__main__":
    args = parse_arguments()
    scrape_airbnb(args.url, args.format)