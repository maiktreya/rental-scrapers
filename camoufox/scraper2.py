import argparse
import asyncio
import json
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin
import httpx
from parsel import Selector
from typing_extensions import TypedDict
import csv
from datetime import datetime
import logging
import os
import time
from camoufox.async_api import Camoufox

# --- Logging and Output Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
os.makedirs("out", exist_ok=True)


# --- Enhanced Camoufox Integration for Dynamic Headers ---
class HeaderManager:
    """Manages header refresh using Camoufox with configurable intervals."""

    def __init__(self, refresh_interval: int = 100, time_interval: int = 1800):
        self.refresh_interval = refresh_interval  # Refresh every N requests
        self.time_interval = time_interval  # Refresh every N seconds
        self.request_count = 0
        self.last_refresh = 0
        self.current_headers = None

    async def get_headers(self, url: str, force_refresh: bool = False) -> Optional[Dict[str, str]]:
        """Get headers, refreshing if needed based on intervals."""
        current_time = time.time()

        # Check if we need to refresh headers
        needs_refresh = (
            force_refresh or
            self.current_headers is None or
            self.request_count >= self.refresh_interval or
            (current_time - self.last_refresh) >= self.time_interval
        )

        if needs_refresh:
            logging.info(f"🔄 Refreshing headers (requests: {self.request_count}, time since last: {int(current_time - self.last_refresh)}s)")
            self.current_headers = await self._fetch_camoufox_headers(url)
            if self.current_headers:
                self.request_count = 0
                self.last_refresh = current_time
                logging.info("✅ Headers refreshed successfully")
            else:
                logging.error("❌ Failed to refresh headers")
                return None

        self.request_count += 1
        return self.current_headers

    async def _fetch_camoufox_headers(self, url: str) -> Optional[Dict[str, str]]:
        """Launch Camoufox to solve challenges and extract valid session headers."""
        logging.info("🚀 Launching Camoufox to generate session headers...")
        browser = None

        try:
            # Use the correct async context manager
            browser = await Camoufox(headless="virtual").__aenter__()
            page = await browser.new_page()

            # Capture headers from requests
            captured_headers = {}

            def capture_request_headers(request):
                """Capture headers from document requests."""
                if request.resource_type == "document" and any(domain in request.url for domain in ["idealista.com"]):
                    logging.info(f"📦 Capturing headers from: {request.url}")
                    captured_headers.update(request.headers)

            # Set up listener before navigation
            page.on("request", capture_request_headers)

            # Navigate to the page
            await page.goto(url, timeout=120000, wait_until="domcontentloaded")

            # Wait a moment for any additional requests
            await asyncio.sleep(2)

            # Remove listener
            page.remove_listener("request", capture_request_headers)

            if not captured_headers:
                logging.warning("No headers captured on initial load, trying reload...")
                await page.reload(wait_until="domcontentloaded")
                await asyncio.sleep(2)

            if not captured_headers:
                raise RuntimeError("Camoufox failed to capture any headers.")

            # Get cookies from the page context
            all_cookies = await page.context.cookies()
            if all_cookies:
                captured_headers["cookie"] = "; ".join(
                    [f"{cookie['name']}={cookie['value']}" for cookie in all_cookies]
                )

            # Clean up headers that should be managed by the HTTP client
            headers_to_remove = ["host", "connection", "content-length", "content-encoding"]
            for header in headers_to_remove:
                captured_headers.pop(header, None)

            logging.info(f"✅ Successfully captured {len(captured_headers)} headers with {len(all_cookies)} cookies")
            return captured_headers

        except Exception as e:
            logging.error(f"❌ Camoufox header generation failed: {e}")
            return None
        finally:
            if browser:
                try:
                    await browser.__aexit__(None, None, None)
                except:
                    pass


# --- Data Structures and Parsing ---
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


# --- Enhanced Scraping Logic ---
async def fetch_with_retry(url: str, session: httpx.AsyncClient, delay: float, max_retries: int = 3):
    """Fetches a URL with a retry mechanism and delay."""
    for attempt in range(max_retries):
        try:
            await asyncio.sleep(delay)
            response = await session.get(url)
            response.raise_for_status()
            return response
        except (httpx.ReadTimeout, httpx.RequestError, httpx.HTTPStatusError) as e:
            logging.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
            if attempt == max_retries - 1:
                logging.error(f"Failed to retrieve URL after {max_retries} attempts: {url}")
                return None
            # Exponential backoff on retries
            await asyncio.sleep(delay * (2 ** attempt))


async def run(base_url: str, delay: float, output_formats: List[str], header_refresh_interval: int = 100, time_refresh_interval: int = 1800):
    """Main scraping orchestrator with intelligent header management."""

    # Initialize header manager
    header_manager = HeaderManager(
        refresh_interval=header_refresh_interval,
        time_interval=time_refresh_interval
    )

    # Step 1: Get initial headers
    headers = await header_manager.get_headers(base_url, force_refresh=True)
    if not headers:
        logging.critical("Could not obtain initial session headers. Exiting.")
        return

    # Step 2: Use headers with efficient HTTPX client
    all_property_urls = []
    page_count = 1
    max_pages = 40

    async with httpx.AsyncClient(
        headers=headers,
        follow_redirects=True,
        timeout=30.0,
        limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
    ) as session:
        current_url = base_url

        # Scrape listing pages
        while current_url and page_count <= max_pages:
            logging.info(f"Scraping page {page_count}: {current_url}")

            # Check if we need to refresh headers
            fresh_headers = await header_manager.get_headers(base_url)
            if fresh_headers and fresh_headers != session.headers:
                logging.info("📋 Updating session headers")
                session.headers.update(fresh_headers)

            response = await fetch_with_retry(current_url, session, delay)
            if not response:
                break

            selector = Selector(text=response.text)

            # Check for anti-bot detection
            if "blocked" in response.text.lower() or "captcha" in response.text.lower():
                logging.warning("🚫 Possible bot detection. Forcing header refresh...")
                fresh_headers = await header_manager.get_headers(base_url, force_refresh=True)
                if fresh_headers:
                    session.headers.update(fresh_headers)
                    # Retry the same page
                    continue
                else:
                    logging.error("Failed to refresh headers. Stopping.")
                    break

            # Extract property URLs from the current page
            property_links = selector.css(
                "article.item a.item-link::attr(href)"
            ).getall()
            page_properties = [urljoin(base_url, link) for link in property_links]
            all_property_urls.extend(page_properties)

            logging.info(f"Found {len(page_properties)} properties on page {page_count}")

            # Find the next page URL
            next_page_link = selector.css("a.icon-arrow-right-after::attr(href)").get()
            current_url = urljoin(base_url, next_page_link) if next_page_link else None
            page_count += 1

        logging.info(f"Found {len(all_property_urls)} total properties to scrape.")

        # Step 3: Scrape individual property pages with batching
        if not all_property_urls:
            logging.warning("No property URLs found. Exiting.")
            return

        # Process in batches to manage memory and allow header refreshes
        batch_size = 50
        all_data = []

        for i in range(0, len(all_property_urls), batch_size):
            batch = all_property_urls[i:i + batch_size]
            logging.info(f"Processing batch {i//batch_size + 1}: {len(batch)} properties")

            # Refresh headers if needed
            fresh_headers = await header_manager.get_headers(base_url)
            if fresh_headers and fresh_headers != session.headers:
                logging.info("📋 Updating session headers for batch")
                session.headers.update(fresh_headers)

            # Fetch batch
            tasks = [fetch_with_retry(url, session, delay) for url in batch]
            responses = await asyncio.gather(*tasks)

            # Parse successful responses
            batch_data = [parse_property(res) for res in responses if res]
            all_data.extend(batch_data)

            logging.info(f"Successfully parsed {len(batch_data)} properties from batch")

        # Step 4: Save the data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not all_data:
            logging.warning("No data was scraped. Nothing to save.")
            return

        logging.info(f"Total properties scraped: {len(all_data)}")

        if "json" in output_formats:
            json_filename = f"out/idealista_properties_{timestamp}.json"
            with open(json_filename, "w", encoding="utf-8") as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
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
                "updated",
                "description"
            ]
            with open(csv_filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(all_data)
            logging.info(f"Data saved to {csv_filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape property listings from Idealista using hybrid Camoufox-HTTPX approach."
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
    parser.add_argument(
        "--header-refresh-requests",
        type=int,
        default=100,
        help="Refresh headers every N requests (default: 100).",
    )
    parser.add_argument(
        "--header-refresh-time",
        type=int,
        default=1800,
        help="Refresh headers every N seconds (default: 1800 = 30 minutes).",
    )

    args = parser.parse_args()
    output_formats = ["csv", "json"] if args.format == "both" else [args.format]

    # Run the scraper
    asyncio.run(run(
        args.url,
        args.delay,
        output_formats,
        args.header_refresh_requests,
        args.header_refresh_time
    ))


# Default: Refresh headers every 100 requests or 30 minutes
# python scraper.py --url "https://www.idealista.com/alquiler-viviendas/madrid-madrid/"

# More frequent header refresh for heavily protected sites
#python scraper.py --header-refresh-requests 25 --header-refresh-time 900

# Conservative approach with longer delays
#python scraper.py --delay 2.0 --header-refresh-requests 50