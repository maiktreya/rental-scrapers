#!/usr/bin/env python3
"""
Upgraded rental property scraper with professional-grade features:
- Dedicated stealth header module (`base_headers.py`).
- Resilient HTML parsing with BeautifulSoup.
- State management for resuming interrupted scrapes.
- Human-like randomized delays ("jitter").

To run this script, install dependencies:
pip install httpx[http2] camoufox beautifulsoup4 lxml
"""

import asyncio
import logging
import argparse
import time
import random
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
import httpx
import sys
import os
from urllib.parse import urljoin

# New dependency for robust parsing
from bs4 import BeautifulSoup

# Local module for stealth headers
from base_headers import StealthHeaderManager

# --- CONFIGURATION AND LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("rental_scraper.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


@dataclass
class ScraperConfig:
    """Configuration for the scraper."""

    delay: float = 5.0
    header_refresh_requests: int = 100
    max_retries: int = 3
    timeout: int = 45
    max_pages: int = 50
    max_listings: int = 3000
    header_target_url: str = "https://www.idealista.com"
    user_agents: List[str] = field(
        default_factory=lambda: [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        ]
    )


# --- IMPROVEMENT 3: STATE MANAGEMENT ---
class StateManager:
    """Handles the state of the scrape to allow for resuming."""

    def __init__(self, state_dir: str = "scraper_state"):
        self.state_dir = state_dir
        self.completed_urls_file = os.path.join(state_dir, "completed_urls.txt")
        os.makedirs(state_dir, exist_ok=True)

    def get_completed_urls(self) -> set:
        """Reads the set of already completed URLs."""
        if not os.path.exists(self.completed_urls_file):
            return set()
        with open(self.completed_urls_file, "r", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}

    def mark_url_as_completed(self, url: str):
        """Appends a successfully scraped URL to the completed file."""
        with open(self.completed_urls_file, "a", encoding="utf-8") as f:
            f.write(url + "\n")


# --- IMPROVEMENT 1: RESILIENT PARSING ---
class ListingExtractor:
    """Extracts listing data from Idealista HTML using BeautifulSoup."""

    def extract_listings_from_page(
        self, content: str, base_url: str
    ) -> List[Dict[str, Any]]:
        """Extracts all listings from a page's HTML content."""
        soup = BeautifulSoup(content, "lxml")
        articles = soup.select("article.item")
        listings = [self._parse_article(article, base_url) for article in articles]
        # Filter out any None values that result from parsing errors
        valid_listings = [listing for listing in listings if listing]
        logger.info(
            f"📋 Extracted {len(valid_listings)} listings from page using BeautifulSoup."
        )
        return valid_listings

    def _parse_article(
        self, article: BeautifulSoup, base_url: str
    ) -> Optional[Dict[str, Any]]:
        """Parses a single <article> tag to extract listing data."""
        try:
            listing = {"scraped_at": datetime.now().isoformat(), "source_url": base_url}

            link_tag = article.select_one("a.item-link")
            if not link_tag:
                return None  # Skip if no main link

            listing["url"] = urljoin(base_url, link_tag.get("href"))
            listing["title"] = link_tag.get_text(strip=True)
            listing["location"] = link_tag.get("title", "").split(" in ")[-1]

            price_tag = article.select_one("span.item-price")
            if price_tag:
                listing["price_text"] = price_tag.get_text(strip=True)

            # Details are more complex, use select to find all and then process
            details = article.select("div.item-detail-char span.item-detail")
            for detail in details:
                text = detail.get_text(strip=True)
                if "m²" in text:
                    listing["size_m2"] = int(text.replace("m²", "").strip())
                elif "hab." in text:
                    listing["rooms"] = int(text.replace("hab.", "").strip())

            # --- New feature: Identify provider type (company vs. individual) ---
            branding_element = article.select_one("picture.logo-branding")
            if branding_element:
                listing["provider_type"] = "company"
                # Try to extract the company name from the link's title or image's alt text
                company_link = branding_element.select_one("a")
                if company_link and company_link.get("title"):
                    listing["company_name"] = company_link.get("title").strip()
                else:
                    company_img = branding_element.select_one("img")
                    if company_img and company_img.get("alt"):
                        listing["company_name"] = company_img.get("alt").strip()
                    else:
                        listing["company_name"] = None  # Found branding but no name
            else:
                listing["provider_type"] = "individual"
                listing["company_name"] = None

            return listing
        except Exception as e:
            logger.error(f"Error parsing listing article: {e}", exc_info=False)
            return None

    def find_next_page_url(self, content: str, base_url: str) -> Optional[str]:
        """Finds the URL of the next page."""
        soup = BeautifulSoup(content, "lxml")
        next_link = soup.select_one("a.next")
        if next_link and next_link.get("href"):
            return urljoin(base_url, next_link["href"])
        return None


class RentalScraper:
    """Main scraper class integrating all features."""

    def __init__(self, config: ScraperConfig, state_manager: StateManager):
        self.config = config
        self.state_manager = state_manager
        self.header_manager = StealthHeaderManager(
            user_agents=config.user_agents,
            refresh_requests=config.header_refresh_requests,
        )
        self.client: Optional[httpx.AsyncClient] = None
        self.extractor = ListingExtractor()
        self.all_listings: List[Dict[str, Any]] = []

    async def __aenter__(self):
        await self.header_manager.refresh_headers(self.config.header_target_url)
        timeout = httpx.Timeout(self.config.timeout)
        self.client = httpx.AsyncClient(
            timeout=timeout, http2=True, follow_redirects=True
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client and not self.client.is_closed:
            await self.client.aclose()

    async def make_request(self, url: str) -> Optional[str]:
        """Makes an HTTP request and returns the HTML content."""
        headers = await self.header_manager.get_headers(self.config.header_target_url)
        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"🌐 Making request to {url} (attempt {attempt + 1})")
                response = await self.client.get(url, headers=headers)
                self.header_manager.increment_request_count()

                if response.status_code == 200:
                    logger.info(f"✅ Request successful: {response.status_code}")
                    return response.text

                logger.warning(f"⚠️ Request failed with status: {response.status_code}")
                if response.status_code in [403, 429]:
                    logger.info("Forcing header refresh due to block/rate limit.")
                    await self.header_manager.refresh_headers(
                        self.config.header_target_url
                    )

            except httpx.RequestError as e:
                logger.error(f"❌ Request error: {e} (attempt {attempt + 1})")

            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self.config.delay * (2**attempt))
        return None

    async def scrape_with_pagination(self, base_url: str):
        """Scrapes a base URL and follows pagination, respecting state."""
        current_url = base_url
        page_num = 1
        completed_urls = self.state_manager.get_completed_urls()

        while (
            current_url
            and page_num <= self.config.max_pages
            and len(self.all_listings) < self.config.max_listings
        ):
            if current_url in completed_urls:
                logger.info(f"⏭️ Skipping already completed page: {current_url}")
                # We need to get the content to find the next page link
                content = await self.make_request(current_url)
                if not content:
                    break
            else:
                logger.info(f"📄 Scraping page {page_num}: {current_url}")
                content = await self.make_request(current_url)
                if not content:
                    break

                listings = self.extractor.extract_listings_from_page(
                    content, current_url
                )
                self.all_listings.extend(listings)
                self.state_manager.mark_url_as_completed(current_url)

            next_url = self.extractor.find_next_page_url(content, current_url)
            if next_url and next_url != current_url:
                current_url = next_url
                page_num += 1

                # --- IMPROVEMENT 2: HUMAN-LIKE DELAYS ---
                base_delay = self.config.delay
                jitter = random.uniform(base_delay * 0.7, base_delay * 1.3)
                logger.info(f"⏳ Waiting {jitter:.2f}s before next page...")
                await asyncio.sleep(jitter)
            else:
                logger.info("🏁 No more pages found.")
                break

    async def scrape_multiple_urls(self, urls: List[str]):
        """Scrapes multiple base URLs."""
        for url in urls:
            logger.info(f"🚀 Starting scrape for base URL: {url}")
            await self.scrape_with_pagination(url)


async def main():
    """Main function to set up and run the scraper."""
    parser = argparse.ArgumentParser(
        description="Professional-grade rental property scraper."
    )
    parser.add_argument(
        "--urls", nargs="+", required=True, help="One or more base URLs to scrape."
    )
    parser.add_argument(
        "--listings-output",
        type=str,
        default="listings.json",
        help="Output JSON file for all listings.",
    )
    args = parser.parse_args()

    config = ScraperConfig()
    state_manager = StateManager()

    # Determine which URLs still need to be scraped
    all_initial_urls = set(args.urls)
    completed_urls = state_manager.get_completed_urls()
    urls_to_scrape = list(all_initial_urls - completed_urls)

    if not urls_to_scrape and completed_urls:
        logger.info("✅ All provided URLs have already been scraped. Nothing to do.")
        return

    if completed_urls:
        logger.info(f"Resuming scrape. {len(completed_urls)} URLs already completed.")

    try:
        async with RentalScraper(config, state_manager) as scraper:
            await scraper.scrape_multiple_urls(urls_to_scrape)
            logger.info(
                f"✅ Scraping completed! Extracted {len(scraper.all_listings)} new listings."
            )

            if args.listings_output and scraper.all_listings:
                # To avoid duplicates, we can load existing listings and merge
                existing_listings = []
                if os.path.exists(args.listings_output):
                    with open(args.listings_output, "r", encoding="utf-8") as f:
                        existing_listings = json.load(f)

                # Create a set of existing URLs for quick lookup
                existing_urls = {listing["url"] for listing in existing_listings}

                # Add only new listings
                for new_listing in scraper.all_listings:
                    if new_listing["url"] not in existing_urls:
                        existing_listings.append(new_listing)

                with open(args.listings_output, "w", encoding="utf-8") as f:
                    json.dump(existing_listings, f, indent=2, ensure_ascii=False)
                logger.info(
                    f"🏠 Listings saved to {args.listings_output}. Total listings: {len(existing_listings)}"
                )

    except Exception as e:
        logger.critical(
            f"❌ A critical error occurred in the main process: {e}", exc_info=True
        )
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n🛑 Scraper interrupted by user.")
