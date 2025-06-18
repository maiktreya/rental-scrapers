import argparse
import asyncio
import json
import re
from typing import Dict, List
from urllib.parse import urljoin
import csv
from datetime import datetime
import logging

# Import Playwright
from playwright.async_api import async_playwright, Page, BrowserContext

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Type definition for property results
from typing_extensions import TypedDict
class PropertyResult(TypedDict, total=False):
    url: str
    title: str
    location: str
    price: int
    currency: str
    updated: str
    rooms: int
    size_sqm: int
    features: Dict[str, List[str]]
    description: str # Added description as it's parsed

def parse_property(html_content: str, url: str) -> PropertyResult:
    """
    Parse Idealista.com property page from its HTML content.
    This function remains largely the same as it operates on the rendered HTML.
    """
    from parsel import Selector # Import Selector here, as it's not needed globally for Playwright operations
    selector = Selector(text=html_content)
    css = lambda x: selector.css(x).get("").strip()
    css_all = lambda x: selector.css(x).getall()

    data: PropertyResult = {}
    data["url"] = url # Use the URL passed to the function
    data["title"] = css("h1 .main-info__title-main::text")
    data["location"] = css(".main-info__title-minor::text")
    data["currency"] = css(".info-data-price::text")

    price_str = css(".info-data-price span::text")
    if price_str:
        price_str = price_str.replace(".", "").replace(",", "")
        data["price"] = int(price_str)
    else:
        data["price"] = None

    data["description"] = "\n".join(css_all("div.comment ::text")).strip()
    data["updated"] = (
        selector.xpath("//p[@class='stats-text'][contains(text(),'updated on')]/text()")
        .get("")
        .split(" on ")[-1]
    )

    data["features"] = {}
    for feature_block in selector.css(".details-property-h2"):
        label = feature_block.xpath("text()").get()
        features = feature_block.xpath("following-sibling::div[1]//li")
        # Ensure label is not None before using it as a key
        if label:
            data["features"][label] = [
                "".join(feat.xpath(".//text()").getall()).strip() for feat in features
            ]

    basic_features = data["features"].get("Características básicas", [])
    data["rooms"] = None
    data["size_sqm"] = None

    for feature in basic_features:
        if "habitaciones" in feature:
            rooms_match = re.search(r"(\d+)\s*habitaciones?", feature)
            if rooms_match:
                data["rooms"] = int(rooms_match.group(1))

        if "m²" in feature:
            size_match = re.search(r"(\d+)\s*m²", feature)
            if size_match:
                data["size_sqm"] = int(size_match.group(1))

    return data


async def extract_property_urls(area_url: str, page: Page, delay: float) -> List[str]:
    """
    Extract property URLs from an area page using Playwright.
    Navigates to the page and waits for content to render.
    """
    try:
        # Navigate to the URL and wait until the DOM is loaded.
        # Increased timeout to allow for potential JS loading.
        logging.info(f"Navigating to area page: {area_url}")
        await page.goto(area_url, wait_until="domcontentloaded", timeout=60000)

        # You might want to add a more specific wait if content loads dynamically
        # For example, wait for an article to appear:
        await page.wait_for_selector("article.item a.item-link", timeout=30000) # Wait for property links to appear

        # Get all href attributes from the property links
        property_links_elements = await page.locator("article.item a.item-link").all()
        property_links = [
            await element.get_attribute("href") for element in property_links_elements
        ]
        full_urls = [urljoin(area_url, link) for link in property_links if link]

        logging.info(f"Found {len(full_urls)} property URLs on {area_url}")
        await asyncio.sleep(delay) # Respect the delay
        return full_urls
    except Exception as e:
        logging.error(f"Failed to extract property URLs from {area_url}. Error: {e}")
        # If navigation fails, the page object might be in a bad state or the URL is unreachable.
        # Returning an empty list allows the scraper to continue with other pages.
        return []


async def get_next_page_url(current_url: str, page: Page, delay: float) -> str | None:
    """
    Get the URL of the next page using Playwright.
    Navigates to the current page to find the next page link.
    """
    try:
        logging.info(f"Checking for next page from: {current_url}")
        await page.goto(current_url, wait_until="domcontentloaded", timeout=60000)

        # Try to locate the next page arrow link.
        # Using a direct attribute selector for robustness.
        next_page_link_element = await page.locator("a.icon-arrow-right-after")

        # Check if the element exists and is visible
        if await next_page_link_element.is_visible():
            next_page_link = await next_page_link_element.get_attribute("href")
            full_next_url = urljoin(current_url, next_page_link) if next_page_link else None
            logging.info(f"Next page found: {full_next_url}")
            await asyncio.sleep(delay) # Respect the delay
            return full_next_url
        else:
            logging.info("No next page link found.")
            await asyncio.sleep(delay) # Still respect the delay before stopping
            return None
    except Exception as e:
        logging.error(f"Failed to get next page URL for {current_url}. Error: {e}")
        return None


async def scrape_properties(urls: List[str], page: Page, delay: float) -> List[PropertyResult]:
    """
    Scrape Idealista.com properties using Playwright.
    Navigates to each property URL and extracts data after rendering.
    """
    properties = []
    for i, url in enumerate(urls):
        logging.info(f"Scraping property {i+1}/{len(urls)}: {url}")
        for attempt in range(3):
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                # You might need to wait for specific content on the property page to load, e.g., the price
                await page.wait_for_selector(".info-data-price", timeout=30000)

                # Get the final URL after any redirects
                final_url = page.url
                # Get the full HTML content of the rendered page
                html_content = await page.content()

                if html_content:
                    properties.append(parse_property(html_content, final_url))
                    logging.info(f"Successfully scraped: {final_url}")
                    break # Success, break out of retry loop
                else:
                    logging.warning(f"Failed to get HTML content for {url} on attempt {attempt + 1}")

            except Exception as e:
                logging.error(f"Attempt {attempt + 1} failed for URL: {url}. Error: {e}")
                if attempt == 2:
                    logging.error(f"Failed to retrieve URL: {url} after 3 attempts.")
            finally:
                await asyncio.sleep(delay) # Always wait for the delay, even on error
    return properties


def save_to_json(data: List[PropertyResult], filename: str) -> None:
    """Save data to a JSON file"""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logging.info(f"Data saved to {filename}")
    except IOError as e:
        logging.error(f"Error saving to JSON file {filename}: {e}")

def save_to_csv(data: List[PropertyResult], filename: str) -> None:
    """Save data to a CSV file"""
    try:
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "url",
                "title",
                "location",
                "price",
                "currency",
                "rooms",
                "size_sqm",
                "description", # Include description in CSV if desired
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for property_item in data: # Renamed 'property' to 'property_item' to avoid conflict with built-in
                writer.writerow(
                    {
                        "url": property_item.get("url", ""),
                        "title": property_item.get("title", ""),
                        "location": property_item.get("location", ""),
                        "price": property_item.get("price", ""),
                        "currency": property_item.get("currency", ""),
                        "rooms": property_item.get("rooms", ""),
                        "size_sqm": property_item.get("size_sqm", ""),
                        "description": property_item.get("description", ""),
                    }
                )
        logging.info(f"Data saved to {filename}")
    except IOError as e:
        logging.error(f"Error saving to CSV file {filename}: {e}")


async def run(base_url: str, delay: float, output_format: List[str]):
    all_property_urls = []
    page_count = 1
    max_pages = 40 # Limit pages to avoid extremely long runs

    # Initialize Playwright
    async with async_playwright() as p:
        # Launch a headless Chromium browser
        # set headless=False to see the browser UI during scraping for debugging
        browser = await p.chromium.launch(headless=True) # Change to False for debugging

        # Create a new browser context. This is crucial for isolating sessions
        # and setting specific browser properties like user-agent and viewport.
        context: BrowserContext = await browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.104 Mobile Safari/537.36",
            viewport={"width": 390, "height": 844, "deviceScaleFactor": 3}, # Simulate a common mobile viewport (e.g., iPhone 12/13 Pro Max)
            # You can add more options like extra_http_headers if needed for specific anti-bot measures
        )
        page: Page = await context.new_page() # Create a new page within the context

        current_url = base_url

        while current_url and page_count <= max_pages:
            logging.info(f"Starting scraping for page {page_count}: {current_url}")
            property_urls = await extract_property_urls(current_url, page, delay)
            all_property_urls.extend(property_urls)

            if not property_urls and page_count > 1: # If no properties are found on a subsequent page, stop
                logging.info("No more property URLs found, stopping pagination.")
                break

            current_url = await get_next_page_url(current_url, page, delay)
            page_count += 1
            if not current_url: # If get_next_page_url returns None, stop
                logging.info("No next page URL found. Ending pagination.")
                break


        logging.info(f"Finished collecting all property URLs. Total found: {len(all_property_urls)}")
        # Remove duplicate URLs if any were collected across pages (important for large scrapes)
        all_property_urls = list(dict.fromkeys(all_property_urls))
        logging.info(f"Total unique property URLs: {len(all_property_urls)}")

        if all_property_urls:
            data = await scrape_properties(all_property_urls, page, delay)
        else:
            logging.warning("No property URLs collected. Skipping detailed scraping.")
            data = []

        # Ensure browser and context are closed
        await context.close()
        await browser.close()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = "out"
        import os
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        if "json" in output_format:
            json_filename = os.path.join(output_dir, f"idealista_properties_{timestamp}.json")
            save_to_json(data, json_filename)

        if "csv" in output_format:
            csv_filename = os.path.join(output_dir, f"idealista_properties_{timestamp}.csv")
            save_to_csv(data, csv_filename)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape property listings from Idealista using Playwright"
    )
    parser.add_argument(
        "--url",
        type=str,
        default="https://www.idealista.com/venta-viviendas/segovia-segovia/",
        help="Base URL for scraping properties (default is Segovia)",
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

    args = parser.parse_args()
    output_formats = ["csv", "json"] if args.format == "both" else [args.format]
    asyncio.run(run(args.url, args.delay, output_formats))
