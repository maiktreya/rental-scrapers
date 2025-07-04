import argparse
import asyncio
import json
import re
from typing import Dict, List
from urllib.parse import urljoin
import httpx
from parsel import Selector
from typing_extensions import TypedDict
import csv
from datetime import datetime
import logging
import os
import camoufox
from camoufox.pyplaywright.async_api import BrowserContext

# --- Logging and Output Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
os.makedirs("out", exist_ok=True)


# --- Camoufox Integration for Dynamic Headers ---
async def get_camoufox_headers(url: str) -> Dict[str, str]:
    """
    Launches a headless Camoufox instance to solve challenges and extract valid
    session headers and cookies for use with HTTPX.
    """
    logging.info("🚀 Launching Camoufox to generate session headers...")
    context: BrowserContext = None
    headers = {}
    try:
        context = await camoufox.async_launch(
            headless="virtual"  # Use "virtual" for headless on servers
        )
        page = await context.new_page()

        # We need to capture the headers from the first successful navigation
        def capture_request_headers(request):
            if request.is_navigation_request() and request.resource_type == "document":
                headers.update(request.headers)

        page.on("request", capture_request_headers)

        await page.goto(url, timeout=120000, wait_until="domcontentloaded")
        await page.remove_listener("request", capture_request_headers)

        if not headers:
            raise RuntimeError("Camoufox failed to capture initial headers.")

        all_cookies = await context.cookies()
        headers["cookie"] = "; ".join(
            [f"{cookie['name']}={cookie['value']}" for cookie in all_cookies]
        )
        logging.info("✅ Successfully generated dynamic headers and cookies.")
        return headers

    except Exception as e:
        logging.error(f"❌ Camoufox header generation failed: {e}")
        return None
    finally:
        if context:
            await context.close()


# --- Data Structures and Parsing (No changes needed here) ---
class PropertyResult(TypedDict, total=False):
    url: str
    title: str
    location: str
    price: int
    currency: str
    description: str
    updated: str
    rooms: int
    size_sqm: int
    features: Dict[str, List[str]]


def parse_property(response: httpx.Response) -> PropertyResult:
    """Parse Idealista.com property page"""
    selector = Selector(text=response.text)
    css = lambda x: selector.css(x).get("").strip()
    css_all = lambda x: selector.css(x).getall()

    data: PropertyResult = {}
    data["url"] = str(response.url)
    data["title"] = css("h1 .main-info__title-main::text")
    data["location"] = css(".main-info__title-minor::text")
    data["currency"] = css(".info-data-price::text")

    price_str = css(".info-data-price span::text")
    data["price"] = (
        int(price_str.replace(".", "").replace(",", "")) if price_str else None
    )

    data["description"] = "\n".join(css_all("div.comment ::text")).strip()
    updated_text = selector.xpath(
        "//p[@class='stats-text'][contains(text(),'updated on')]/text()"
    ).get("")
    if " on " in updated_text:
        data["updated"] = updated_text.split(" on ")[-1]

    data["features"] = {}
    for feature_block in selector.css(".details-property-h2"):
        label = feature_block.xpath("text()").get()
        if label:
            features = feature_block.xpath("following-sibling::div[1]//li")
            data["features"][label] = [
                "".join(feat.xpath(".//text()").getall()).strip() for feat in features
            ]

    basic_features = data["features"].get("Características básicas", [])
    for feature in basic_features:
        if "habitaci" in feature:
            if rooms_match := re.search(r"(\d+)", feature):
                data["rooms"] = int(rooms_match.group(1))
        if "m²" in feature:
            if size_match := re.search(r"(\d+)", feature):
                data["size_sqm"] = int(size_match.group(1))

    return data


# --- Scraping Logic (Adapted to use dynamic headers) ---
async def fetch_with_retry(url: str, session: httpx.AsyncClient, delay: float):
    """Fetches a URL with a retry mechanism and delay."""
    for attempt in range(3):
        try:
            # Add a small delay before each request to be polite
            await asyncio.sleep(delay)
            response = await session.get(url)
            response.raise_for_status()  # Will raise an exception for 4xx/5xx status
            return response
        except (httpx.ReadTimeout, httpx.RequestError, httpx.HTTPStatusError) as e:
            logging.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
            if attempt == 2:
                logging.error(f"Failed to retrieve URL after 3 attempts: {url}")
                return None


async def run(base_url: str, delay: float, output_formats: List[str]):
    """Main scraping orchestrator."""
    # Step 1: Get dynamic headers from Camoufox
    headers = await get_camoufox_headers(base_url)
    if not headers:
        logging.critical("Could not obtain session headers. Exiting.")
        return

    # Step 2: Use headers with a fast HTTPX client
    all_property_urls = []
    page_count = 1
    max_pages = 40

    async with httpx.AsyncClient(
        headers=headers, follow_redirects=True, timeout=20.0
    ) as session:
        current_url = base_url

        while current_url and page_count <= max_pages:
            logging.info(f"Scraping page {page_count}: {current_url}")
            response = await fetch_with_retry(current_url, session, delay)
            if not response:
                break  # Stop if a page fails to load

            selector = Selector(text=response.text)

            # Extract property URLs from the current page
            property_links = selector.css(
                "article.item a.item-link::attr(href)"
            ).getall()
            all_property_urls.extend(
                [urljoin(base_url, link) for link in property_links]
            )

            # Find the next page URL
            next_page_link = selector.css("a.icon-arrow-right-after::attr(href)").get()
            current_url = urljoin(base_url, next_page_link) if next_page_link else None
            page_count += 1

        logging.info(f"Found {len(all_property_urls)} total properties to scrape.")

        # Step 3: Scrape individual property pages
        tasks = [fetch_with_retry(url, session, delay) for url in all_property_urls]
        responses = await asyncio.gather(*tasks)

        data = [parse_property(res) for res in responses if res]

        # Step 4: Save the data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not data:
            logging.warning("No data was scraped. Nothing to save.")
            return

        if "json" in output_formats:
            json_filename = f"out/idealista_properties_{timestamp}.json"
            with open(json_filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logging.info(f"Data saved to {json_filename}")

        if "csv" in output_formats:
            csv_filename = f"out/idealista_properties_{timestamp}.csv"
            fieldnames = [
                "url",
                "title",
                "location",
                "price",
                "currency",
                "rooms",
                "size_sqm",
            ]
            with open(csv_filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(data)
            logging.info(f"Data saved to {csv_filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape property listings from Idealista using Camoufox and HTTPX."
    )
    parser.add_argument(
        "--url",
        type=str,
        default="https://www.idealista.com/venta-viviendas/madrid-madrid/",
        help="Base URL for scraping properties.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Base delay between requests in seconds.",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["csv", "json", "both"],
        default="both",
        help="Output format.",
    )

    args = parser.parse_args()
    output_formats = ["csv", "json"] if args.format == "both" else [args.format]

    # Ensure you have run 'playwright install' once in your terminal
    asyncio.run(run(args.url, args.delay, output_formats))
