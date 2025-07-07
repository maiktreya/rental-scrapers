#!/usr/bin/env python3
"""
Rental property scraper with a dedicated stealth header module.
This version uses an external `StealthHeaderManager` for generating realistic
browser headers and handling anti-bot measures.

To run this script, install dependencies:
pip install httpx[http2] camoufox
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
import re
from urllib.parse import urljoin

# Refactored header logic is now in its own module
from base_headers import StealthHeaderManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("rental_scraper.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


@dataclass
class ScraperConfig:
    """Configuration for the scraper."""

    delay: float = 5.0
    header_refresh_requests: int = 100
    max_retries: int = 3
    timeout: int = 30
    max_pages: int = 50
    max_listings: int = 3000
    extract_listings: bool = True
    header_target_url: str = "https://www.idealista.com"
    user_agents: List[str] = field(
        default_factory=lambda: [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        ]
    )


class ListingExtractor:
    """Extract listings from Idealista pages."""

    def __init__(self):
        """
        Initializes the extractor with detailed regex patterns for Idealista.
        These patterns are designed to be "molecular" to capture a wide range of
        data points for both full properties and individual rooms.
        """
        self.listing_patterns = {
            "idealista": {
                "listing_container": r'<article[^>]*class="[^"]*item[^"]*"[^>]*>(.*?)</article>',
                "listing_url": r'<a[^>]*href="([^"]*)"[^>]*class="[^"]*item-link[^"]*"',
                "price": r'<span[^>]*class="[^"]*item-price[^"]*"[^>]*>([^<]+)',
                "original_price": r'<span[^>]*class="pricedown_price"[^>]*>([^<]+)</span>',
                "price_drop_percentage": r'<span[^>]*class="pricedown_icon[^"]*">(\d+)%</span>',
                "title": r'<a[^>]*class="[^"]*item-link[^"]*"[^>]*>([^<]+)',
                "location": r'<a[^>]*class="[^"]*item-link[^"]*"[^>]*title="[^"]*en\s([^"]*)"',
                "total_rooms_in_flat": r"(\d+)\s*hab",
                "flatmates": r'<span class="item-detail"><span class="icon-sex-circle[^"]*"></span>\s*([\d\s\w/]+)</span>',
                "smoking_policy": r'<span class="item-detail"><span class="[^"]*icon-(?:no-)?smokers[^"]*"></span>\s*([^<]+)</span>',
                "availability_date": r'<span class="item-detail">\s*(\d{1,2}\s+[a-zA-ZñÑáéíóúÁÉÍÓÚ]+\.?)\s*</span>',
                "size": r"(\d+)\s*m²",
                "next_page": r'<a[^>]*class="[^"]*next[^"]*"[^>]*href="([^"]*)"',
                "pagination": r'<a[^>]*href="([^"]*pagina-\d+[^"]*)"',
            }
        }

    def detect_site(self, url: str) -> str:
        """Detect which real estate site we're scraping."""
        if "idealista.com" in url:
            return "idealista"
        return "unknown"

    def extract_listings_from_page(
        self, content: str, base_url: str
    ) -> List[Dict[str, Any]]:
        """Extract all listings from a page."""
        site = self.detect_site(base_url)
        if site == "unknown":
            return []
        patterns = self.listing_patterns[site]
        listings = []
        listing_matches = re.findall(
            patterns["listing_container"], content, re.DOTALL | re.IGNORECASE
        )
        for i, listing_html in enumerate(listing_matches):
            listing_data = self.extract_single_listing(listing_html, patterns, base_url)
            if listing_data:
                listing_data["listing_index"] = i + 1
                listings.append(listing_data)
        logger.info(f"📋 Extracted {len(listings)} listings from page")
        return listings

    def extract_single_listing(
        self, listing_html: str, patterns: Dict[str, str], base_url: str
    ) -> Optional[Dict[str, Any]]:
        """Extract detailed data from a single listing HTML block."""
        try:
            listing = {"scraped_at": datetime.now().isoformat(), "source_url": base_url}

            # Basic info
            url_match = re.search(patterns["listing_url"], listing_html, re.IGNORECASE)
            if url_match:
                listing["url"] = urljoin(base_url, url_match.group(1))

            title_match = re.search(patterns["title"], listing_html, re.IGNORECASE)
            if title_match:
                listing["title"] = title_match.group(1).strip()

            location_match = re.search(
                patterns["location"], listing_html, re.IGNORECASE
            )
            if location_match:
                listing["location"] = location_match.group(1).strip()

            # Price details
            price_match = re.search(patterns["price"], listing_html, re.IGNORECASE)
            if price_match:
                price_text = price_match.group(1).strip()
                listing["price_text"] = price_text
                price_numeric = re.search(
                    r"([\d.,]+)", price_text.replace(".", "").replace(",", ".")
                )
                if price_numeric:
                    try:
                        listing["price_eur_per_month"] = float(price_numeric.group(1))
                    except ValueError:
                        pass

            # Optional price drop info
            original_price_match = re.search(
                patterns["original_price"], listing_html, re.IGNORECASE
            )
            if original_price_match:
                listing["original_price_text"] = original_price_match.group(1).strip()

            price_drop_match = re.search(
                patterns["price_drop_percentage"], listing_html, re.IGNORECASE
            )
            if price_drop_match:
                try:
                    listing["price_drop_percentage"] = int(price_drop_match.group(1))
                except ValueError:
                    pass

            # Room-specific details from the 'item-detail-char' div
            details_html_match = re.search(
                r'<div[^>]*class="[^"]*item-detail-char[^"]*"[^>]*>(.*?)</div>',
                listing_html,
                re.DOTALL | re.IGNORECASE,
            )
            if details_html_match:
                details_html = details_html_match.group(1)

                total_rooms_match = re.search(
                    patterns["total_rooms_in_flat"], details_html, re.IGNORECASE
                )
                if total_rooms_match:
                    listing["total_rooms_in_flat"] = int(total_rooms_match.group(1))

                flatmates_match = re.search(
                    patterns["flatmates"], details_html, re.IGNORECASE
                )
                if flatmates_match:
                    listing["flatmates_info"] = (
                        flatmates_match.group(1)
                        .strip()
                        .replace("<span>", " ")
                        .replace("</span>", "")
                    )

                smoking_policy_match = re.search(
                    patterns["smoking_policy"], details_html, re.IGNORECASE
                )
                if smoking_policy_match:
                    listing["smoking_policy"] = smoking_policy_match.group(1).strip()

                availability_match = re.search(
                    patterns["availability_date"], details_html, re.IGNORECASE
                )
                if availability_match:
                    listing["availability_date"] = availability_match.group(1).strip()

            # General size
            size_match = re.search(patterns["size"], listing_html, re.IGNORECASE)
            if size_match:
                listing["size_m2"] = int(size_match.group(1))

            return listing if listing.get("url") else None
        except Exception as e:
            logger.error(f"Error extracting listing: {e}")
            return None

    def find_next_page_url(self, content: str, base_url: str) -> Optional[str]:
        """Find the URL of the next page, with fallback to pagination links."""
        site = self.detect_site(base_url)
        if site == "unknown":
            return None
        patterns = self.listing_patterns[site]

        # First, try to find the direct "next" button
        next_match = re.search(patterns["next_page"], content, re.IGNORECASE)
        if next_match:
            return urljoin(base_url, next_match.group(1))

        # As a fallback, check numbered pagination links
        pagination_matches = re.findall(patterns["pagination"], content, re.IGNORECASE)
        if pagination_matches:
            current_page = self._extract_current_page(base_url)
            next_page_num = current_page + 1
            for page_url in pagination_matches:
                if f"pagina-{next_page_num}" in page_url:
                    return urljoin(base_url, page_url)

        return None

    def _extract_current_page(self, url: str) -> int:
        """Extracts the current page number from a URL."""
        match = re.search(r"pagina-(\d+)", url)
        return int(match.group(1)) if match else 1


class RentalScraper:
    """Main scraper class for rental properties."""

    def __init__(self, config: ScraperConfig):
        self.config = config
        # Use the new, dedicated header manager
        self.header_manager = StealthHeaderManager(
            user_agents=config.user_agents,
            refresh_requests=config.header_refresh_requests,
        )
        self.client: Optional[httpx.AsyncClient] = None
        self.extractor = ListingExtractor()
        self.all_listings: List[Dict[str, Any]] = []

    async def __aenter__(self):
        """Async context manager entry."""
        # Initialize headers on startup
        await self.header_manager.refresh_headers(self.config.header_target_url)
        timeout = httpx.Timeout(self.config.timeout)
        self.client = httpx.AsyncClient(
            timeout=timeout, http2=True, follow_redirects=True
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client and not self.client.is_closed:
            await self.client.aclose()

    async def make_request(
        self, url: str, method: str = "GET", **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Make an HTTP request with proper headers and retry logic."""
        # Get headers, which may trigger a refresh if needed
        headers = await self.header_manager.get_headers(self.config.header_target_url)
        kwargs["headers"] = headers

        for attempt in range(self.config.max_retries):
            try:
                logger.info(
                    f"🌐 Making {method} request to {url} (attempt {attempt + 1})"
                )
                response = await self.client.request(method, url, **kwargs)
                self.header_manager.increment_request_count()

                if response.status_code == 200:
                    logger.info(f"✅ Request successful: {response.status_code}")
                    return {
                        "content": response.text,
                        "status_code": response.status_code,
                        "url": str(response.url),
                    }
                else:
                    logger.warning(
                        f"⚠️ Request failed with status: {response.status_code}"
                    )
                    if response.status_code == 403:
                        logger.info(
                            "Got a 403 Forbidden. Forcing header refresh for next request."
                        )
                        await self.header_manager.refresh_headers(
                            self.config.header_target_url
                        )

            except httpx.RequestError as e:
                logger.error(f"❌ Request failed: {e} (attempt {attempt + 1})")

            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self.config.delay * (2**attempt))

        return None

    async def scrape_with_pagination(self, base_url: str):
        """Scrape a URL with pagination support."""
        current_url = base_url
        page_num = 1
        while (
            current_url
            and page_num <= self.config.max_pages
            and len(self.all_listings) < self.config.max_listings
        ):
            logger.info(f"📄 Scraping page {page_num}: {current_url}")
            response_data = await self.make_request(current_url)
            if response_data:
                content = response_data["content"]
                if self.config.extract_listings:
                    listings = self.extractor.extract_listings_from_page(
                        content, current_url
                    )
                    self.all_listings.extend(listings)

                next_url = self.extractor.find_next_page_url(content, current_url)
                if next_url and next_url != current_url:
                    current_url = next_url
                    page_num += 1
                    await asyncio.sleep(self.config.delay + random.uniform(0, 2))
                else:
                    logger.info("🏁 No more pages found or reached duplicate URL")
                    break
            else:
                break

    async def scrape_multiple_urls(self, urls: List[str]):
        """Scrape multiple URLs."""
        for url in urls:
            await self.scrape_with_pagination(url)


async def main():
    """Main function to run the scraper."""
    parser = argparse.ArgumentParser(
        description="Rental property scraper with stealth headers."
    )
    parser.add_argument("--urls", nargs="+", required=True, help="URLs to scrape")
    parser.add_argument(
        "--listings-output",
        type=str,
        default="listings.json",
        help="Output JSON file for listings",
    )
    # Add other arguments from original script as needed
    args = parser.parse_args()

    config = ScraperConfig()

    try:
        async with RentalScraper(config) as scraper:
            await scraper.scrape_multiple_urls(args.urls)
            logger.info(
                f"✅ Scraping completed! Extracted {len(scraper.all_listings)} total listings."
            )

            if args.listings_output and scraper.all_listings:
                with open(args.listings_output, "w", encoding="utf-8") as f:
                    json.dump(scraper.all_listings, f, indent=2, ensure_ascii=False)
                logger.info(f"🏠 Listings saved to {args.listings_output}")

    except Exception as e:
        logger.error(f"❌ A critical error occurred: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
