#!/usr/bin/env python3
"""
The main orchestration module for the rental property scraper.
This script coordinates fetching pages, managing state via a database,
and saving data, delegating tasks to specialized modules.
"""

import asyncio
import logging
import argparse
import time
import random
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
import httpx
import sys
import os

from base_headers import StealthHeaderManager
from parser import IdealistaParser
from database import DatabaseManager

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
    header_target_url: str = "https://www.idealista.com"
    postgrest_url: str = os.environ.get("POSTGREST_URL", "http://localhost:3000")
    user_agents: List[str] = field(
        default_factory=lambda: [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        ]
    )


class RentalScraper:
    """Main scraper class integrating all features."""

    def __init__(self, config: ScraperConfig, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        self.header_manager = StealthHeaderManager(
            user_agents=config.user_agents,
            refresh_requests=config.header_refresh_requests
        )
        self.parser = IdealistaParser()
        self.client: Optional[httpx.AsyncClient] = db_manager.session

    async def make_request(self, url: str) -> Optional[str]:
        """Makes an HTTP request and returns the HTML content."""
        headers = await self.header_manager.get_headers(self.config.header_target_url)
        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"🌐 Making request to {url} (attempt {attempt + 1})")
                response = await self.client.get(url, headers=headers)
                self.header_manager.increment_request_count()
                response.raise_for_status()
                return response.text
            except httpx.HTTPStatusError as e:
                logger.warning(f"⚠️ HTTP Error: {e.response.status_code} for URL {e.request.url}")
                if e.response.status_code in [403, 429]:
                    await self.header_manager.refresh_headers(self.config.header_target_url)
            except httpx.RequestError as e:
                logger.error(f"❌ Request error: {e} (attempt {attempt + 1})")
            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self.config.delay * (2 ** attempt))
        return None

    async def scrape_target(self, capital_slug: str, property_type: str, capital_id: int):
        """Scrapes a single target (capital) with pagination."""
        base_url_template = "https://www.idealista.com/alquiler-{}/{}/"
        current_url = base_url_template.format("habitacion" if property_type == "habitacion" else "viviendas", capital_slug)
        page_num = 1
        
        while current_url and page_num <= self.config.max_pages:
            logger.info(f"📄 Scraping page {page_num} for {capital_slug}: {current_url}")
            content = await self.make_request(current_url)
            if not content: break

            listings = self.parser.extract_listings_from_page(content, current_url, property_type)
            if not listings:
                logger.info(f"No listings found on page {page_num} for {capital_slug}. Moving to next capital.")
                break

            for listing in listings:
                await self.db_manager.save_listing(listing, property_type, capital_id)

            next_url = self.parser.find_next_page_url(content, current_url)
            if next_url and next_url != current_url:
                current_url = next_url
                page_num += 1
                jitter = random.uniform(self.config.delay * 0.7, self.config.delay * 1.3)
                logger.info(f"⏳ Waiting {jitter:.2f}s before next page...")
                await asyncio.sleep(jitter)
            else:
                logger.info(f"🏁 No more pages found for {capital_slug}.")
                break


async def main():
    """Main function to set up and run the scraper."""
    parser = argparse.ArgumentParser(description="Professional-grade rental property scraper.")
    parser.add_argument(
        "property_type",
        choices=["viviendas", "habitacion"],
        help="The type of property to scrape ('viviendas' or 'habitacion')."
    )
    args = parser.parse_args()
    config = ScraperConfig()
    
    async with httpx.AsyncClient(http2=True, follow_redirects=True) as session:
        db_manager = DatabaseManager(config.postgrest_url, session)
        
        capitals = await db_manager.fetch_active_capitals()
        if not capitals:
            logger.critical("No active capitals fetched from the database. Exiting.")
            return
            
        last_processed_id = await db_manager.get_scraper_status(args.property_type)
        
        start_index = 0
        if last_processed_id > 0:
            for i, capital in enumerate(capitals):
                if capital['id'] == last_processed_id:
                    start_index = i + 1
                    break
        
        if start_index >= len(capitals):
            logger.info("✅ All capitals have been processed. Resetting for next run.")
            await db_manager.update_scraper_status(args.property_type, 0)
            start_index = 0

        scraper = RentalScraper(config, db_manager)
        for i in range(start_index, len(capitals)):
            capital = capitals[i]
            capital_id = capital['id']
            capital_slug = capital['idealista_slug']
            
            logger.info(f"--- Processing capital {i+1}/{len(capitals)}: {capital_slug} (ID: {capital_id}) ---")
            await scraper.scrape_target(capital_slug, args.property_type, capital_id)
            
            await db_manager.update_scraper_status(args.property_type, capital_id)

    logger.info("🎉 Full scraping run completed successfully!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n🛑 Scraper interrupted by user.")
    except Exception as e:
        logger.critical(f"❌ A critical error occurred in the main process: {e}", exc_info=True)
        sys.exit(1)
