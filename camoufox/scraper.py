#!/usr/bin/env python3
"""
Rental property scraper with Camoufox for realistic browser headers.
Fixed version with proper AsyncCamoufox usage.

To use geoip features, install with: pip install camoufox[geoip]
"""

import asyncio
import logging
import argparse
import time
import random
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import aiohttp
import sys
import os

# Fixed import for AsyncCamoufox
from camoufox.async_api import AsyncCamoufox

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rental_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ScraperConfig:
    """Configuration for the scraper."""
    delay: float = 2.0
    header_refresh_requests: int = 100
    max_retries: int = 3
    timeout: int = 30
    user_agents: List[str] = field(default_factory=lambda: [
        'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0',
        'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/116.0',
        'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0'
    ])

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

            # Use AsyncCamoufox with proper configuration
            # Remove geoip=True if geoip extra is not installed
            async with AsyncCamoufox(
                headless=True,
                humanize=True,
                os="linux",
                block_images=True,
                enable_cache=False,
                window=(1920, 1080)
            ) as browser:
                page = await browser.new_page()

                # Navigate to a test page to generate realistic headers
                await page.goto("https://httpbin.org/headers", wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)  # Wait 2 seconds for full load

                # Get the generated headers from the browser
                headers = await page.evaluate("""
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
                """)

                await page.close()
                logger.info("✅ Successfully generated session headers")
                logger.info(f"📋 Generated User-Agent: {headers.get('User-Agent', 'N/A')}")
                return headers

        except Exception as e:
            logger.error(f"❌ Camoufox header generation failed: {e}")
            # Fallback to default headers
            return self.get_fallback_headers()

    def get_fallback_headers(self) -> Dict[str, str]:
        """Get fallback headers if Camoufox fails."""
        logger.warning("🔄 Using fallback headers")
        return {
            'User-Agent': random.choice(self.config.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1'
        }

    async def should_refresh_headers(self) -> bool:
        """Check if headers should be refreshed."""
        current_time = time.time()
        time_since_refresh = current_time - self.last_refresh

        return (
            self.headers is None or
            self.request_count >= self.config.header_refresh_requests or
            time_since_refresh >= self.refresh_interval
        )

    async def get_headers(self) -> Dict[str, str]:
        """Get current headers, refreshing if necessary."""
        if await self.should_refresh_headers():
            await self.refresh_headers()

        return self.headers.copy()

    async def refresh_headers(self):
        """Refresh the session headers."""
        logger.info(f"🔄 Refreshing headers (requests: {self.request_count}, time since last: {time.time() - self.last_refresh:.0f}s)")

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

class RentalScraper:
    """Main scraper class for rental properties."""

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.header_manager = HeaderManager(config)
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        # Initialize headers
        await self.header_manager.refresh_headers()

        # Create aiohttp session
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=aiohttp.TCPConnector(limit=10, limit_per_host=5)
        )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session and not self.session.closed:
            await self.session.close()
            # Give a small delay to ensure cleanup
            await asyncio.sleep(0.1)

    async def make_request(self, url: str, method: str = 'GET', **kwargs) -> Optional[Dict[str, Any]]:
        """Make an HTTP request with proper headers and retry logic."""
        headers = await self.header_manager.get_headers()

        # Update headers with any additional ones
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers

        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"🌐 Making {method} request to {url} (attempt {attempt + 1})")

                async with self.session.request(method, url, **kwargs) as response:
                    self.header_manager.increment_request_count()

                    if response.status == 200:
                        logger.info(f"✅ Request successful: {response.status}")
                        # Read content while connection is still open
                        content = await response.text()
                        return {
                            'content': content,
                            'status_code': response.status,
                            'headers': dict(response.headers),
                            'url': str(response.url)
                        }
                    elif response.status == 429:
                        logger.warning(f"🚫 Rate limited: {response.status}")
                        await asyncio.sleep(self.config.delay * (2 ** attempt))
                    else:
                        logger.warning(f"⚠️ Request failed with status: {response.status}")

            except asyncio.TimeoutError:
                logger.error(f"⏱️ Request timeout (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"❌ Request failed: {e} (attempt {attempt + 1})")

            if attempt < self.config.max_retries - 1:
                wait_time = self.config.delay * (2 ** attempt) + random.uniform(0, 1)
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

            content = response_data['content']

            # Basic extraction - you can enhance this based on your needs
            data = {
                'url': url,
                'status_code': response_data['status_code'],
                'content_length': len(content),
                'response_headers': response_data['headers'],
                'scraped_at': datetime.now().isoformat(),
                'title': self.extract_title(content),
                'content_preview': content[:500] + '...' if len(content) > 500 else content
            }

            logger.info(f"📄 Scraped {url}: {data['content_length']} chars")
            return data

        except Exception as e:
            logger.error(f"❌ Error scraping {url}: {e}")
            return None

    def extract_title(self, content: str) -> Optional[str]:
        """Extract title from HTML content."""
        try:
            import re
            match = re.search(r'<title[^>]*>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        except Exception as e:
            logger.error(f"Error extracting title: {e}")
        return None

    async def scrape_multiple_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Scrape multiple URLs with delays and header rotation."""
        results = []

        for i, url in enumerate(urls):
            logger.info(f"📊 Processing URL {i + 1}/{len(urls)}: {url}")

            # Scrape the URL
            result = await self.scrape_url(url)
            if result:
                results.append(result)

            # Add delay between requests
            if i < len(urls) - 1:  # Don't delay after the last URL
                delay = self.config.delay + random.uniform(0, 1)
                logger.info(f"⏳ Waiting {delay:.1f}s before next request...")
                await asyncio.sleep(delay)

        return results

async def main():
    """Main function to run the scraper."""
    parser = argparse.ArgumentParser(description='Rental property scraper with Camoufox')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between requests (seconds)')
    parser.add_argument('--header-refresh-requests', type=int, default=100, help='Refresh headers after N requests')
    parser.add_argument('--max-retries', type=int, default=3, help='Maximum retry attempts')
    parser.add_argument('--timeout', type=int, default=30, help='Request timeout (seconds)')
    parser.add_argument('--urls', nargs='+', help='URLs to scrape')
    parser.add_argument('--output', type=str, help='Output JSON file')

    args = parser.parse_args()

    # Create configuration
    config = ScraperConfig(
        delay=args.delay,
        header_refresh_requests=args.header_refresh_requests,
        max_retries=args.max_retries,
        timeout=args.timeout
    )

    # Default test URLs if none provided
    test_urls = args.urls or [
        "https://httpbin.org/headers",
        "https://httpbin.org/user-agent",
        "https://httpbin.org/ip"
    ]

    logger.info(f"🚀 Starting scraper with {len(test_urls)} URLs")
    logger.info(f"⚙️ Config: delay={config.delay}s, refresh_after={config.header_refresh_requests} requests")

    try:
        # Run the scraper
        async with RentalScraper(config) as scraper:
            results = await scraper.scrape_multiple_urls(test_urls)

            logger.info(f"✅ Scraping completed! Processed {len(results)} URLs successfully")

            # Output results
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                logger.info(f"💾 Results saved to {args.output}")
            else:
                # Print summary
                print("\n" + "="*50)
                print("SCRAPING RESULTS SUMMARY")
                print("="*50)
                for i, result in enumerate(results, 1):
                    print(f"{i}. {result['url']}")
                    print(f"   Status: {result['status_code']}")
                    print(f"   Length: {result['content_length']} chars")
                    print(f"   Title: {result.get('title', 'N/A')}")
                    print()

    except KeyboardInterrupt:
        logger.info("🛑 Scraper interrupted by user")
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Check if we need to initialize headers first
    if len(sys.argv) == 1:
        print("🔧 Running with default test URLs...")
        print("Use --help for more options")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)