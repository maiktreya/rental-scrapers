#!/usr/bin/env python3
"""
The main orchestration module with critical bug fixes.
"""

import asyncio
import logging
import argparse
import random
from typing import Optional
import sys
import re
import httpx
# Import from new config module
from .config import ScraperConfig
from .base_headers import HeaderManager
from .parser import IdealistaParser
from .database import DatabaseManager

# --- CONFIGURATION AND LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("rental_scraper.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class RentalScraper:
    """Main scraper class with critical fixes."""

    def __init__(self, config: ScraperConfig, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        self.header_manager = HeaderManager(config=config)
        self.parser = IdealistaParser()
        # Create dedicated HTTP client for scraping
        self.client = httpx.AsyncClient(
            http2=True,
            follow_redirects=True,
            timeout=config.timeout  # Proper float timeout
        )

    async def make_request(self, url: str) -> Optional[str]:
        """Makes an HTTP request with proper error propagation."""
        headers = await self.header_manager.get_headers()
        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"🌐 Making request to {url} (attempt {attempt + 1})")
                response = await self.client.get(
                    url, headers=headers, timeout=self.config.timeout
                )
                self.header_manager.increment_request_count()
                response.raise_for_status()
                return response.text
            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"⚠️ HTTP Error: {e.response.status_code} for URL {e.request.url}"
                )
                if e.response.status_code in [403, 429]:
                    await self.header_manager.refresh_headers()
            except httpx.RequestError as e:
                logger.error(f"❌ Request error: {e} (attempt {attempt + 1})")

            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self.config.delay * (2**attempt))

        # Critical: Re-raise after max retries to avoid silent failures
        raise Exception(f"Max retries exceeded for URL: {url}")

    async def scrape_target(
        self, capital_slug: str, property_type: str, capital_id: int
    ):
        """Scrapes a single target with robust URL handling."""
        # Sanitize capital slug
        sanitized_slug = re.sub(r'\s+', '-', capital_slug.strip()).lower()

        property_path = "habitaciones" if property_type == "habitacion" else "viviendas"
        base_url_template = (
            f"https://www.idealista.com/alquiler-{property_path}/{sanitized_slug}/"
        )
        current_url = base_url_template
        page_num = 1

        while current_url and page_num <= self.config.max_pages:
            try:
                content = await self.make_request(current_url)
            except Exception as e:
                logger.error(f"🚨 Critical failure for {current_url}: {e}")
                break

            if not content:
                break

            listings = self.parser.extract_listings_from_page(
                content, current_url, property_type
            )
            if not listings:
                logger.info(
                    f"No listings found on page {page_num} for {sanitized_slug}. Moving to next capital."
                )
                break

            for listing in listings:
                await self.db_manager.save_listing(listing, property_type, capital_id)

            next_url = self.parser.find_next_page_url(content, current_url)
            if next_url and next_url != current_url:
                current_url = next_url
                page_num += 1
                jitter = random.uniform(
                    self.config.delay * 0.7, self.config.delay * 1.3
                )
                logger.info(f"⏳ Waiting {jitter:.2f}s before next page...")
                await asyncio.sleep(jitter)
            else:
                logger.info(f"🏁 No more pages found for {sanitized_slug}.")
                break


async def main():
    """Main function with robust capital tracking."""
    parser = argparse.ArgumentParser(
        description="Professional-grade rental property scraper."
    )
    parser.add_argument(
        "property_type",
        choices=["viviendas", "habitacion"],
        help="The type of property to scrape ('viviendas' or 'habitacion').",
    )
    args = parser.parse_args()
    config = ScraperConfig()

    async with httpx.AsyncClient(http2=True, follow_redirects=True) as session:
        db_manager = DatabaseManager(config.postgrest_url, session)

        capitals = await db_manager.fetch_active_capitals()
        if not capitals:
            logger.critical("No active capitals fetched from the database. Exiting.")
            return

        # Get last processed ID
        last_processed_id = await db_manager.get_scraper_status(args.property_type)

        # Find position in capitals list
        start_index = 0
        if last_processed_id > 0:
            # Find the index of the last processed capital
            for i, capital in enumerate(capitals):
                if capital["id"] == last_processed_id:
                    start_index = i + 1
                    break

        if start_index >= len(capitals):
            logger.info("✅ All capitals processed. Resetting for next run.")
            await db_manager.update_scraper_status(args.property_type, 0)
            start_index = 0

        scraper = RentalScraper(config, db_manager)
        for i in range(start_index, len(capitals)):
            capital = capitals[i]
            capital_id = capital["id"]
            capital_slug = capital["idealista_slug"]

            logger.info(
                f"--- Processing capital {i+1}/{len(capitals)}: {capital_slug} (ID: {capital_id}) ---"
            )
            try:
                await scraper.scrape_target(capital_slug, args.property_type, capital_id)
                await db_manager.update_scraper_status(args.property_type, capital_id)
            except Exception as e:
                logger.error(f"🚨 Failed to process {capital_slug}: {e}")
                # Move to next capital on failure
                continue

    logger.info("🎉 Full scraping run completed successfully!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n🛑 Scraper interrupted by user.")
    except Exception as e:
        logger.critical(
            f"❌ A critical error occurred in the main process: {e}", exc_info=True
        )
        sys.exit(1)