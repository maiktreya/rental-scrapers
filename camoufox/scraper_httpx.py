#!/usr/bin/env python3
"""
Rental property scraper with Camoufox for realistic browser headers.
Enhanced version with Idealista listing extraction and pagination support.
Now using httpx for requests.

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

# Fixed import for AsyncCamoufox
from camoufox.async_api import AsyncCamoufox

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
    header_refresh_requests: int = 30
    max_retries: int = 3
    timeout: int = 30
    max_pages: int = 50  # Maximum pages to scrape per search
    max_listings: int = 1500  # Maximum listings to scrape
    extract_listings: bool = True  # Whether to extract individual listings
    user_agents: List[str] = field(
        default_factory=lambda: [
            "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/116.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0",
        ]
    )


class HeaderManager:
    """Manages browser headers using Camoufox."""

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.headers: Optional[Dict[str, str]] = None
        self.request_count = 0
        self.last_refresh = 0
        self.refresh_interval = 3600  # 1 hour in seconds

    async def generate_session_headers(self) -> Dict[str, str]:
        """Generate fresh session headers using Camoufox."""
        try:
            logger.info("🚀 Launching Camoufox to generate session headers...")

            async with AsyncCamoufox(
                headless=True,
                humanize=True,
                os=random.choice(["linux","macos", "windows"]),
                block_images=True,
                enable_cache=False,
                window=(1920, 1080),
                i_know_what_im_doing=True,
            ) as browser:
                page = await browser.new_page()
                await page.goto("https://idealista.com", wait_until="domcontentloaded")
                # https://www.idealista.com/alquiler-habitacion/segovia-segovia/
                #
                await page.wait_for_timeout(2000)
                headers = await page.evaluate(
                    """
                    () => {
                        const headers = {};
                        const userAgent = navigator.userAgent;
                        const languages = navigator.languages ? navigator.languages.join(',') : 'en-US,en;q=0.9';
                        return {
                            'User-Agent': userAgent,
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                            'Accept-Language': languages,
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
        """Check if headers should be refreshed."""
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
        try:
            self.headers = await self.generate_session_headers()
            self.request_count = 0
            self.last_refresh = time.time()
            logger.info("✅ Headers refreshed successfully")
        except Exception as e:
            logger.error(f"❌ Failed to refresh headers: {e}")
            if self.headers is None:
                self.headers = self.get_fallback_headers()

    def increment_request_count(self):
        """Increment the request counter."""
        self.request_count += 1


class ListingExtractor:
    """Extract listings from Idealista pages."""

    def __init__(self):
        self.listing_patterns = {
            "idealista": {
                "listing_container": r'<article[^>]*class="[^"]*item[^"]*"[^>]*>(.*?)</article>',
                "listing_url": r'<a[^>]*href="([^"]*)"[^>]*class="[^"]*item-link[^"]*"',
                "price": r'<span[^>]*class="[^"]*item-price[^"]*"[^>]*>([^<]+)',
                "title": r'<a[^>]*class="[^"]*item-link[^"]*"[^>]*>([^<]+)',
                "location": r'<span[^>]*class="[^"]*item-detail[^"]*"[^>]*>([^<]+)',
                "rooms": r"(\d+)\s*hab",
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
        """Extract data from a single listing."""
        try:
            listing = {"scraped_at": datetime.now().isoformat(), "source_url": base_url}
            url_match = re.search(patterns["listing_url"], listing_html, re.IGNORECASE)
            if url_match:
                listing["url"] = urljoin(base_url, url_match.group(1))
            price_match = re.search(patterns["price"], listing_html, re.IGNORECASE)
            if price_match:
                price_text = price_match.group(1).strip()
                listing["price_text"] = price_text
                price_numeric = re.search(r"([\d.,]+)", price_text.replace(".", "").replace(",", "."))
                if price_numeric:
                    try:
                        listing["price"] = float(price_numeric.group(1))
                    except ValueError:
                        pass
            title_match = re.search(patterns["title"], listing_html, re.IGNORECASE)
            if title_match:
                listing["title"] = title_match.group(1).strip()
            location_match = re.search(patterns["location"], listing_html, re.IGNORECASE)
            if location_match:
                listing["location"] = location_match.group(1).strip()
            rooms_match = re.search(patterns["rooms"], listing_html, re.IGNORECASE)
            if rooms_match:
                listing["rooms"] = int(rooms_match.group(1))
            size_match = re.search(patterns["size"], listing_html, re.IGNORECASE)
            if size_match:
                listing["size_m2"] = int(size_match.group(1))
            return listing if listing.get("url") else None
        except Exception as e:
            logger.error(f"Error extracting listing: {e}")
            return None

    def find_next_page_url(self, content: str, base_url: str) -> Optional[str]:
        """Find the URL of the next page."""
        site = self.detect_site(base_url)
        if site == "unknown":
            return None
        patterns = self.listing_patterns[site]
        next_match = re.search(patterns["next_page"], content, re.IGNORECASE)
        if next_match:
            return urljoin(base_url, next_match.group(1))
        pagination_matches = re.findall(patterns["pagination"], content, re.IGNORECASE)
        if pagination_matches:
            current_page = self.extract_current_page(base_url)
            next_page = current_page + 1
            for page_url in pagination_matches:
                if f"pagina-{next_page}" in page_url:
                    return urljoin(base_url, page_url)
        return None

    def extract_current_page(self, url: str) -> int:
        """Extract current page number from URL."""
        match = re.search(r"pagina-(\d+)", url)
        return int(match.group(1)) if match else 1


class RentalScraper:
    """Main scraper class for rental properties."""

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
        """Make an HTTP request with proper headers and retry logic."""
        headers = await self.header_manager.get_headers()
        if "headers" in kwargs:
            headers.update(kwargs["headers"])
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
                    logger.warning(f"🚫 Rate limited: {response.status_code}")
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
        """Scrape a single URL and return extracted data."""
        try:
            response_data = await self.make_request(url)
            if not response_data:
                return None
            content = response_data["content"]
            listings = []
            if self.config.extract_listings:
                listings = self.extractor.extract_listings_from_page(content, url)
                self.all_listings.extend(listings)
            data = {
                "url": url,
                "status_code": response_data["status_code"],
                "content_length": len(content),
                "response_headers": response_data["headers"],
                "scraped_at": datetime.now().isoformat(),
                "title": self.extract_title(content),
                "listings_count": len(listings),
                "listings": listings,
                "content_preview": (content[:500] + "..." if len(content) > 500 else content),
                "content": content,
            }
            logger.info(f"📄 Scraped {url}: {data['content_length']} chars, {len(listings)} listings")
            return data
        except Exception as e:
            logger.error(f"❌ Error scraping {url}: {e}")
            return None

    def extract_title(self, content: str) -> Optional[str]:
        """Extract title from HTML content."""
        try:
            match = re.search(r"<title[^>]*>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        except Exception as e:
            logger.error(f"Error extracting title: {e}")
        return None

    async def scrape_with_pagination(self, base_url: str) -> List[Dict[str, Any]]:
        """Scrape a URL with pagination support."""
        results = []
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
                results.append(result)
                next_url = self.extractor.find_next_page_url(result["content"], current_url)
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
                logger.error(f"❌ Failed to scrape page {page_num}")
                break
        logger.info(f"✅ Pagination complete: Scraped {page_num-1} pages, {len(self.all_listings)} total listings")
        return results

    async def scrape_multiple_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Scrape multiple URLs with delays and header rotation."""
        results = []
        for i, url in enumerate(urls):
            logger.info(f"📊 Processing URL {i + 1}/{len(urls)}: {url}")
            if self.config.extract_listings and "idealista.com" in url:
                page_results = await self.scrape_with_pagination(url)
                results.extend(page_results)
            else:
                result = await self.scrape_url(url)
                if result:
                    results.append(result)
            if i < len(urls) - 1:
                delay = self.config.delay + random.uniform(0, 1)
                logger.info(f"⏳ Waiting {delay:.1f}s before next URL...")
                await asyncio.sleep(delay)
        return results


async def main():
    """Main function to run the scraper."""
    parser = argparse.ArgumentParser(description="Rental property scraper with Camoufox")
    parser.add_argument("--delay", type=float, default=5.0, help="Delay between requests (seconds)")
    parser.add_argument("--header-refresh-requests", type=int, default=100, help="Refresh headers after N requests")
    parser.add_argument("--max-retries", type=int, default=3, help="Maximum retry attempts")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout (seconds)")
    parser.add_argument("--max-pages", type=int, default=50, help="Maximum pages to scrape per URL")
    parser.add_argument("--max-listings", type=int, default=1500, help="Maximum listings to extract")
    parser.add_argument("--no-extract-listings", action="store_true", help="Disable listing extraction")
    parser.add_argument("--urls", nargs="+", help="URLs to scrape")
    parser.add_argument("--output", type=str, help="Output JSON file for page data")
    parser.add_argument("--listings-output", type=str, help="Output JSON file for listings only")
    args = parser.parse_args()

    config = ScraperConfig(
        delay=args.delay,
        header_refresh_requests=args.header_refresh_requests,
        max_retries=args.max_retries,
        timeout=args.timeout,
        max_pages=args.max_pages,
        max_listings=args.max_listings,
        extract_listings=not args.no_extract_listings,
    )

    if not args.urls:
        logger.error("❌ No URLs provided. Please specify URLs to scrape using the --urls argument.")
        parser.print_help()
        sys.exit(1)

    urls_to_scrape = args.urls
    logger.info(f"🚀 Starting scraper with {len(urls_to_scrape)} URLs")
    logger.info(f"⚙️ Config: delay={config.delay}s, refresh_after={config.header_refresh_requests} requests")
    logger.info(f"📄 Pagination: max_pages={config.max_pages}, max_listings={config.max_listings}")
    logger.info(f"🔍 Extract listings: {config.extract_listings}")

    try:
        async with RentalScraper(config) as scraper:
            results = await scraper.scrape_multiple_urls(urls_to_scrape)
            total_listings = len(scraper.all_listings)
            logger.info(f"✅ Scraping completed! Processed {len(results)} pages, extracted {total_listings} listings")
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    for res in results:
                        res.pop('content', None)
                    json.dump(results, f, indent=2, ensure_ascii=False)
                logger.info(f"💾 Page data saved to {args.output}")
            if args.listings_output and scraper.all_listings:
                with open(args.listings_output, "w", encoding="utf-8") as f:
                    json.dump(scraper.all_listings, f, indent=2, ensure_ascii=False)
                logger.info(f"🏠 Listings saved to {args.listings_output}")
            if not args.output and not args.listings_output:
                print("\n" + "=" * 50)
                print("SCRAPING SUMMARY (No output file specified)")
                print("=" * 50)
                if scraper.all_listings:
                    print(f"🏠 Extracted {len(scraper.all_listings)} listings.")
                    for i, listing in enumerate(scraper.all_listings[:5], 1):
                        print(f"  {i}. {listing.get('title', 'N/A')} - {listing.get('price_text', 'N/A')}")
                else:
                    print("No listings were extracted.")
    except KeyboardInterrupt:
        logger.info("🛑 Scraper interrupted by user")
    except Exception as e:
        logger.error(f"❌ Critical error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Fatal error in startup: {e}")
        sys.exit(1)
