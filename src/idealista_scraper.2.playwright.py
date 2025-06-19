import argparse
import asyncio
import json
import re
from typing import Dict, List
from playwright.async_api import async_playwright, Page, Locator, TimeoutError as PlaywrightTimeoutError
from typing_extensions import TypedDict
import csv
from datetime import datetime
import logging

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PropertyResult(TypedDict, total=False):
    """A dictionary to hold the scraped property data."""
    url: str
    title: str
    location: str
    price: int
    currency: str
    updated: str
    rooms: int
    size_sqm: int
    features: Dict[str, List[str]]
    description: str

async def parse_property(page: Page) -> PropertyResult:
    """Parse an Idealista.com property page using Playwright locators."""
    data: PropertyResult = {}
    data["url"] = page.url
    data["title"] = await page.locator("h1 .main-info__title-main").text_content()
    data["location"] = await page.locator(".main-info__title-minor").text_content()

    price_text = await page.locator(".info-data-price span").first.text_content()
    data["currency"] = await page.locator(".info-data-price").first.text_content()

    if price_text:
        price_cleaned = re.sub(r'[.,€]', '', price_text).strip()
        data["price"] = int(price_cleaned) if price_cleaned.isdigit() else None
    else:
        data["price"] = None

    data["description"] = await page.locator("div.comment").inner_text()

    # Extract updated date
    try:
        updated_text = await page.locator("p.stats-text:has-text('updated on')").text_content()
        data["updated"] = updated_text.split(" on ")[-1]
    except (PlaywrightTimeoutError, IndexError):
        data["updated"] = None
        logging.warning(f"Could not find updated date for {page.url}")

    # Extract features
    data["features"] = {}
    feature_blocks = await page.locator(".details-property-h2").all()
    for feature_block in feature_blocks:
        label = await feature_block.text_content()
        # Find the following sibling div (container for list items)
        list_container = feature_block.locator("xpath=./following-sibling::div[1]")
        list_items = await list_container.locator("li").all()
        data["features"][label] = [await item.text_content() for item in list_items]

    # Extract key details like rooms and size from features
    basic_features = data["features"].get("Basic features", [])
    data["rooms"] = None
    data["size_sqm"] = None

    for feature in basic_features:
        if "rooms" in feature or "bed" in feature:
            rooms_match = re.search(r'(\d+)', feature)
            if rooms_match:
                data["rooms"] = int(rooms_match.group(1))

        if "m²" in feature or "sqm" in feature:
            size_match = re.search(r'(\d+)', feature)
            if size_match:
                data["size_sqm"] = int(size_match.group(1))

    return data

def save_to_json(data: List[PropertyResult], filename: str) -> None:
    """Save data to a JSON file."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def save_to_csv(data: List[PropertyResult], filename: str) -> None:
    """Save data to a CSV file."""
    if not data:
        logging.warning("No data to save to CSV.")
        return

    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        # Use a flexible set of fieldnames based on the first item
        fieldnames = list(data[0].keys())
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data)


async def run(base_url: str, delay: float, output_format: List[str], max_pages: int):
    """Main function to orchestrate the scraping process with Playwright."""
    all_property_urls = set() # Use a set to avoid duplicate URLs
    page_count = 1

    logging.info("Starting Playwright browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        current_url = base_url

        # --- 1. Scrape listing URLs from all pages ---
        while current_url and page_count <= max_pages:
            logging.info(f"Scraping property URLs from page {page_count}: {current_url}")
            try:
                await page.goto(current_url, timeout=30000)
                await page.wait_for_selector("article.item a.item-link", timeout=15000)

                # Extract URLs from the current page
                property_links = await page.locator("article.item a.item-link").all()
                for link in property_links:
                    href = await link.get_attribute("href")
                    if href:
                        # Construct absolute URL
                        full_url = f"https://www.idealista.com{href}"
                        all_property_urls.add(full_url)

                # Check for and click the "Next" button
                next_button = page.locator("a.icon-arrow-right-after").first
                if await next_button.is_visible():
                    await next_button.click()
                    await page.wait_for_load_state('domcontentloaded')
                    current_url = page.url
                    page_count += 1
                    await asyncio.sleep(delay) # Wait before scraping the next page
                else:
                    logging.info("No 'Next' page button found. Reached the last page.")
                    break

            except PlaywrightTimeoutError:
                logging.warning(f"Timeout while loading or finding links on page: {current_url}. Stopping pagination.")
                break
            except Exception as e:
                logging.error(f"An error occurred during URL extraction on page {page_count}: {e}")
                break

        # --- 2. Scrape detailed data for each property URL ---
        scraped_properties = []
        logging.info(f"Found {len(all_property_urls)} unique property URLs. Starting detailed scrape...")

        for i, url in enumerate(all_property_urls):
            logging.info(f"Scraping property {i+1}/{len(all_property_urls)}: {url}")
            try:
                await page.goto(url, timeout=30000)
                property_data = await parse_property(page)
                scraped_properties.append(property_data)
                await asyncio.sleep(delay) # Be polite to the server
            except PlaywrightTimeoutError:
                logging.error(f"Timeout error scraping details for: {url}")
            except Exception as e:
                logging.error(f"Failed to scrape property details for {url}: {e}")

        await browser.close()

        # --- 3. Save the results ---
        if not scraped_properties:
            logging.warning("Scraping finished, but no data was collected.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if "json" in output_format:
            json_filename = f"out/idealista_properties_{timestamp}.json"
            save_to_json(scraped_properties, json_filename)
            logging.info(f"Data saved to {json_filename}")

        if "csv" in output_format:
            csv_filename = f"out/idealista_properties_{timestamp}.csv"
            save_to_csv(scraped_properties, csv_filename)
            logging.info(f"Data saved to {csv_filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape property listings from Idealista using Playwright."
    )
    parser.add_argument(
        "--url",
        type=str,
        default="https://www.idealista.com/en/venta-viviendas/segovia-segovia/",
        help="Base URL for scraping properties (default is Segovia, Spain)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between requests in seconds (default is 2.0 seconds)",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["csv", "json", "both"],
        default="both",
        help="Choose the output format: 'csv', 'json', or 'both'",
    )
    parser.add_argument(
        "--max_pages",
        type=int,
        default=40,
        help="Maximum number of pages to scrape (default is 40)",
    )

    # Ensure the 'out' directory exists
    import os
    if not os.path.exists("out"):
        os.makedirs("out")

    args = parser.parse_args()
    output_formats = ["csv", "json"] if args.format == "both" else [args.format]

    # Run the main async function
    asyncio.run(run(args.url, args.delay, output_formats, args.max_pages))