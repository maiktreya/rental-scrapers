#!/usr/bin/env python3
"""
Rental property scraper with Camoufox for realistic browser headers.
This version is adapted to extract detailed information from Idealista's
room rental listings ("alquiler-habitacion").

To use geoip features, install with: pip install camoufox[geoip]
To run this script, install httpx: pip install httpx[http2]
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
import re
from urllib.parse import urljoin

# Camoufox is used for generating realistic browser headers.
# If you don't have it, the script will use fallback headers.
try:
    from camoufox.async_api import AsyncCamoufox
    CAMOUFOX_AVAILABLE = True
except ImportError:
    CAMOUFOX_AVAILABLE = False

# --- Configure Logging ---
# Sets up logging to both a file and the console for better monitoring.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("room_scraper.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


@dataclass
class ScraperConfig:
    """Configuration for the scraper."""

    delay: float = 5.0
    header_refresh_requests: int = 30
    max_retries: int = 3
    timeout: int = 30
    max_pages: int = 50  # Maximum pages to scrape per search
    max_listings: int = 1500  # Maximum listings to scrape
    extract_listings: bool = True  # Whether to extract individual listings
    user_agents: List[str] = field(
        default_factory=lambda: [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        ]
    )


class HeaderManager:
    """Manages browser headers using Camoufox for realism."""

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.headers: Optional[Dict[str, str]] = None
        self.request_count = 0
        self.last_refresh = 0
        self.refresh_interval = 3600  # 1 hour in seconds

    async def generate_session_headers(self) -> Dict[str, str]:
        """Generate fresh session headers using Camoufox."""
        if not CAMOUFOX_AVAILABLE:
            logger.warning("Camoufox not found. Using fallback headers.")
            return self.get_fallback_headers()

        try:
            logger.info("🚀 Launching Camoufox to generate session headers...")
            async with AsyncCamoufox(
                headless=True,
                humanize=True,
                os=random.choice(["linux", "macos", "windows"]),
                block_images=True,
                enable_cache=False,
                window=(1920, 1080),
                i_know_what_im_doing=True,
            ) as browser:
                page = await browser.new_page()
                await page.goto("https://idealista.com/alquiler-habitacion/", wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)
                headers = await page.evaluate(
                    """
                    () => {
                        return {
                            'User-Agent': navigator.userAgent,
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                            'Accept-Language': navigator.languages ? navigator.languages.join(',') : 'en-US,en;q=0.9',
                            'Accept-Encoding': 'gzip, deflate, br',
                            'Connection': 'keep-alive',
                            'Upgrade-Insecure-Requests': '1',
                            'Sec-Fetch-Dest': 'document',
                            'Sec-Fetch-Mode': 'navigate',
                            'Sec-Fetch-Site': 'none',
                            'DNT': '1',
                            'Cache-Control': 'max-age=0'
                        };
                    }
                """
                )
                await page.close()
                logger.info("✅ Successfully generated session headers")
                logger.info(f"📋 Generated User-Agent: {headers.get('User-Agent', 'N/A')}")
                return headers
        except Exception as e:
            logger.error(f"❌ Camoufox header generation failed: {e}")
            return self.get_fallback_headers()

    def get_fallback_headers(self) -> Dict[str, str]:
        """Get fallback headers if Camoufox fails."""
        logger.warning("🔄 Using fallback headers")
        return {
            "User-Agent": random.choice(self.config.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "DNT": "1",
        }

    async def should_refresh_headers(self) -> bool:
        """Check if headers should be refreshed based on time or request count."""
        current_time = time.time()
        time_since_refresh = current_time - self.last_refresh
        return (
            self.headers is None
            or self.request_count >= self.config.header_refresh_requests
            or time_since_refresh >= self.refresh_interval
        )

    async def get_headers(self) -> Dict[str, str]:
        """Get current headers, refreshing if necessary."""
        if await self.should_refresh_headers():
            await self.refresh_headers()
        return self.headers.copy()

    async def refresh_headers(self):
        """Refresh the session headers."""
        logger.info(
            f"🔄 Refreshing headers (requests: {self.request_count}, time since last: {time.time() - self.last_refresh:.0f}s)"
        )
        self.headers = await self.generate_session_headers()
        self.request_count = 0
        self.last_refresh = time.time()
        logger.info("✅ Headers refreshed successfully")

    def increment_request_count(self):
        """Increment the request counter."""
        self.request_count += 1


class ListingExtractor:
    """
    Extracts listings from Idealista pages.
    This class now differentiates between general property listings and room listings.
    """

    def __init__(self):
        # Regex patterns for different sections of Idealista
        self.listing_patterns = {
            "idealista_rooms": {
                "listing_container": r'<article[^>]*class="[^"]*item[^"]*"[^>]*data-element-id="(\d+)"[^>]*>(.*?)</article>',
                "listing_url": r'<a[^>]*href="(/inmueble/[^"]*)"',
                "price": r'<span[^>]*class="[^"]*item-price[^"]*"[^>]*>(.*?)</span>',
                "title": r'<a[^>]*class="[^"]*item-link[^"]*"[^>]*title="([^"]*)"',
                "details_container": r'<div class="item-detail-char">(.*?)</div>',
                "description": r'<div class="item-description[^"]*">\s*<p class="ellipsis">(.*?)</p>\s*</div>',
                # Updated regex to be more robust for finding the next page link.
                # It looks for the <li> with class="next" and then finds the href within the enclosed <a> tag.
                "next_page": r'<li\s+class="next">.*?<a[^>]*href="([^"]*)"',
                "pagination": r'<a[^>]*href="([^"]*pagina-\d+[^"]*)"',
            }
        }

    def detect_site(self, url: str) -> str:
        """Detect which real estate site and section we're scraping."""
        if "idealista.com" in url:
            if "/alquiler-habitacion/" in url:
                return "idealista_rooms"
            return "idealista_rooms"
        return "unknown"

    def extract_listings_from_page(
        self, content: str, base_url: str
    ) -> List[Dict[str, Any]]:
        """Extract all listings from a page's HTML content."""
        site = self.detect_site(base_url)
        if site == "unknown":
            return []

        patterns = self.listing_patterns.get(site)
        if not patterns:
            logger.warning(f"No patterns found for site type: {site}")
            return []

        listings = []
        listing_matches = re.findall(
            patterns["listing_container"], content, re.DOTALL | re.IGNORECASE
        )

        for i, (listing_id, listing_html) in enumerate(listing_matches):
            listing_data = self.extract_single_listing(
                listing_id, listing_html, patterns, base_url, site
            )
            if listing_data:
                listing_data["listing_index_on_page"] = i + 1
                listings.append(listing_data)

        logger.info(f"📋 Extracted {len(listings)} listings from page")
        return listings

    def extract_single_listing(
        self, listing_id: str, listing_html: str, patterns: Dict[str, str], base_url: str, site: str
    ) -> Optional[Dict[str, Any]]:
        """Extract data from a single listing's HTML."""
        try:
            listing = {
                "id": int(listing_id),
                "scraped_at": datetime.now().isoformat(),
                "source_page": base_url,
            }

            url_match = re.search(patterns["listing_url"], listing_html, re.IGNORECASE)
            if url_match:
                listing["url"] = urljoin(base_url, url_match.group(1))

            price_match = re.search(patterns["price"], listing_html, re.DOTALL | re.IGNORECASE)
            if price_match:
                price_text = re.sub(r"<[^>]+>", "", price_match.group(1)).strip()
                listing["price_text"] = price_text
                price_numeric = re.search(r"([\d.,]+)", price_text.replace(".", "").replace(",", "."))
                if price_numeric:
                    try:
                        listing["price_eur_per_month"] = float(price_numeric.group(1))
                    except (ValueError, IndexError):
                        pass

            title_match = re.search(patterns["title"], listing_html, re.IGNORECASE)
            if title_match:
                listing["title"] = title_match.group(1).strip()

            description_match = re.search(patterns["description"], listing_html, re.DOTALL | re.IGNORECASE)
            if description_match:
                listing["description"] = re.sub(r'\s+', ' ', description_match.group(1).strip())

            if site == 'idealista_rooms':
                self.extract_room_details(listing_html, listing)

            return listing if listing.get("url") else None
        except Exception as e:
            logger.error(f"Error extracting listing ID {listing_id}: {e}", exc_info=True)
            return None

    def extract_room_details(self, html: str, listing: Dict[str, Any]):
        """Helper to extract details specific to room listings from the details container."""
        details_container_match = re.search(r'<div class="item-detail-char">(.*?)</div>', html, re.DOTALL | re.IGNORECASE)
        if not details_container_match:
            return

        details_html = details_container_match.group(1)
        details = re.findall(r'<span class="item-detail">(.*?)</span>', details_html, re.DOTALL | re.IGNORECASE)

        for detail in details:
            detail_text = ' '.join(re.sub(r'<[^>]+>', ' ', detail).strip().split())

            if "hab." in detail_text:
                match = re.search(r'(\d+)\s*hab', detail_text)
                if match:
                    listing['total_rooms_in_flat'] = int(match.group(1))
            elif "chico" in detail_text or "chica" in detail_text or "máx." in detail_text:
                listing['flatmates_info'] = detail_text
            elif "fumar" in detail_text:
                listing['smoking_policy'] = detail_text
            elif any(month in detail_text.lower() for month in ['jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']):
                 listing['availability'] = detail_text.replace('&nbsp;', ' ')

    def find_next_page_url(self, content: str, base_url: str) -> Optional[str]:
        """Find the URL of the next page from pagination links."""
        site = self.detect_site(base_url)
        if site == "unknown":
            return None
        patterns = self.listing_patterns[site]
        # Use DOTALL flag to ensure the regex can span multiple lines
        next_match = re.search(patterns["next_page"], content, re.IGNORECASE | re.DOTALL)
        if next_match:
            # Clean up the URL and make it absolute
            relative_url = next_match.group(1).replace("&amp;", "&")
            return urljoin(base_url, relative_url)
        return None

class RentalScraper:
    """Main scraper class to orchestrate the scraping process."""

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.header_manager = HeaderManager(config)
        self.client: Optional[httpx.AsyncClient] = None
        self.extractor = ListingExtractor()
        self.all_listings: List[Dict[str, Any]] = []

    async def __aenter__(self):
        """Async context manager entry."""
        await self.header_manager.refresh_headers()
        timeout = httpx.Timeout(self.config.timeout)
        self.client = httpx.AsyncClient(timeout=timeout, http2=True, follow_redirects=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client and not self.client.is_closed:
            await self.client.aclose()

    async def make_request(
        self, url: str, method: str = "GET", **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Make an HTTP request with headers, retries, and error handling."""
        headers = await self.header_manager.get_headers()
        kwargs["headers"] = headers

        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"🌐 Making {method} request to {url} (attempt {attempt + 1})")
                response = await self.client.request(method, url, **kwargs)
                self.header_manager.increment_request_count()

                if response.status_code == 200:
                    logger.info(f"✅ Request successful: {response.status_code}")
                    return {
                        "content": response.text,
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                        "url": str(response.url),
                    }
                elif response.status_code == 429:
                    logger.warning(f"🚫 Rate limited: {response.status_code}. Retrying...")
                    await asyncio.sleep(self.config.delay * (2**attempt))
                else:
                    logger.warning(f"⚠️ Request failed with status: {response.status_code}")

            except httpx.TimeoutException:
                logger.error(f"⏱️ Request timeout (attempt {attempt + 1})")
            except httpx.RequestError as e:
                logger.error(f"❌ Request failed: {e} (attempt {attempt + 1})")

            if attempt < self.config.max_retries - 1:
                wait_time = self.config.delay * (2**attempt) + random.uniform(0, 1)
                logger.info(f"⏳ Waiting {wait_time:.1f}s before retry...")
                await asyncio.sleep(wait_time)

        logger.error(f"❌ All {self.config.max_retries} attempts failed for {url}")
        return None

    async def scrape_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape a single URL and return its content and extracted data."""
        response_data = await self.make_request(url)
        if not response_data:
            return None
        content = response_data["content"]
        listings = []
        if self.config.extract_listings:
            listings = self.extractor.extract_listings_from_page(content, str(response_data['url']))
            self.all_listings.extend(listings)

        data = {
            "url": str(response_data['url']),
            "status_code": response_data["status_code"],
            "content_length": len(content),
            "scraped_at": datetime.now().isoformat(),
            "listings_on_page": len(listings),
            "full_content_for_debug": content,
        }
        logger.info(f"📄 Scraped {url}: {data['content_length']} chars, {len(listings)} listings")
        return data

    async def scrape_with_pagination(self, base_url: str) -> List[Dict[str, Any]]:
        """Scrape a URL and follow its pagination links."""
        page_results = []
        current_url = base_url
        page_num = 1

        logger.info(f"🔄 Starting pagination scrape from {base_url}")
        while (
            current_url
            and page_num <= self.config.max_pages
            and len(self.all_listings) < self.config.max_listings
        ):
            logger.info(f"📄 Scraping page {page_num}: {current_url}")
            result = await self.scrape_url(current_url)
            if result:
                page_results.append(result)
                # The content for finding the next page is in the result dictionary
                next_url = self.extractor.find_next_page_url(result["full_content_for_debug"], current_url)
                if next_url and next_url != current_url:
                    current_url = next_url
                    page_num += 1
                    delay = self.config.delay + random.uniform(0, 2)
                    logger.info(f"⏳ Waiting {delay:.1f}s before next page...")
                    await asyncio.sleep(delay)
                else:
                    logger.info("🏁 No more pages found or reached duplicate URL")
                    break
            else:
                logger.error(f"❌ Failed to scrape page {page_num}, stopping pagination.")
                break

        # Corrected logging message
        logger.info(f"✅ Pagination complete: Scraped {len(page_results)} pages, found {len(self.all_listings)} total listings")
        return page_results


async def main():
    """Main function to parse arguments and run the scraper."""
    parser = argparse.ArgumentParser(description="Idealista room rental scraper with Camoufox")
    parser.add_argument("--urls", nargs="+", required=True, help="URLs to scrape (e.g., https://www.idealista.com/alquiler-habitacion/madrid-madrid/)")
    parser.add_argument("--output", type=str, default="scraped_rooms.json", help="Output JSON file for listings")
    parser.add_argument("--delay", type=float, default=5.0, help="Base delay between requests (seconds)")
    parser.add_argument("--max-pages", type=int, default=10, help="Maximum pages to scrape per URL")
    parser.add_argument("--max-listings", type=int, default=500, help="Maximum total listings to extract")
    args = parser.parse_args()

    config = ScraperConfig(
        delay=args.delay,
        max_pages=args.max_pages,
        max_listings=args.max_listings,
    )

    logger.info(f"🚀 Starting scraper for {len(args.urls)} URLs")
    logger.info(f"⚙️ Config: delay={config.delay}s, max_pages={config.max_pages}, max_listings={config.max_listings}")

    try:
        async with RentalScraper(config) as scraper:
            for url in args.urls:
                await scraper.scrape_with_pagination(url)

            total_listings = len(scraper.all_listings)
            logger.info(f"✅ Scraping completed! Extracted {total_listings} total listings.")

            if args.output and scraper.all_listings:
                # Remove duplicates based on listing ID
                unique_listings = list({listing['id']: listing for listing in scraper.all_listings}.values())
                logger.info(f"Found {len(unique_listings)} unique listings.")

                with open(args.output, "w", encoding="utf-8") as f:
                    json.dump(unique_listings, f, indent=2, ensure_ascii=False)
                logger.info(f"🏠 Listings saved to {args.output}")
            else:
                logger.info("No output file specified or no listings found.")

    except KeyboardInterrupt:
        logger.info("🛑 Scraper interrupted by user")
    except Exception as e:
        logger.error(f"❌ Critical error in main execution: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Example usage from command line:
    # python your_script_name.py --urls "https://www.idealista.com/alquiler-habitacion/segovia-segovia/" --max-pages 5
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Fatal error in startup: {e}")
        sys.exit(1)
