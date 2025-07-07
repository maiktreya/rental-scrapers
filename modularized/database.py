#!/usr/bin/env python3
"""
Database module with fixed key mappings.
"""

import logging
from typing import Dict, Any, List
from urllib.parse import urljoin
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database interactions with correct field mappings."""

    def __init__(self, postgrest_url: str, session: httpx.AsyncClient):
        if not postgrest_url:
            raise ValueError("PostgREST URL cannot be empty.")
        self.postgrest_url = postgrest_url
        self.session = session

    async def fetch_active_capitals(self) -> List[Dict[str, Any]]:
        """
        Fetches active capitals (scraping targets) from the PostgREST API.
        """
        endpoint = urljoin(self.postgrest_url, "/capitals")
        params = {"is_active": "eq.true", "select": "id,idealista_slug"}
        headers = {"Accept": "application/json"}

        logger.info(f"Fetching active capitals from: {endpoint}")
        try:
            response = await self.session.get(
                endpoint, params=params, headers=headers, timeout=30.0
            )
            response.raise_for_status()
            capitals = response.json()
            logger.info(f"Successfully fetched {len(capitals)} active capitals.")
            return capitals
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error fetching capitals: {e.response.status_code} - {e.response.text}"
            )
        except (httpx.RequestError, ValueError) as e:
            logger.error(f"Error fetching or parsing capitals: {e}")
        return []

    async def save_listing(
        self, listing_data: Dict[str, Any], property_type: str, capital_id: int
    ):
        # Determine endpoint
        table_name = "listings" if property_type == "viviendas" else "rooms"
        endpoint = urljoin(self.postgrest_url, f"/{table_name}")
        headers = {
            "Content-Type": "application/json",
            "Prefer": "resolution=ignore-duplicates",
        }

        # Build payload with correct keys
        static_listing_payload = {
            "url": listing_data.get("url"),
            "title": listing_data.get("title"),
            "location": listing_data.get("location"),
            "property_type": property_type,  # Use parameter, not scraped value
            "advertiser_type": listing_data.get("advertiser_type"),
            "advertiser_name": listing_data.get("advertiser_name"),
            "capital_id": capital_id,
        }

        # Add property-specific fields
        if property_type == "viviendas":
            static_listing_payload["size_sqm"] = listing_data.get("size_sqm")
            static_listing_payload["num_bedrooms"] = listing_data.get("num_bedrooms")
        else:  # habitacion
            static_listing_payload["available_from_date"] = listing_data.get(
                "available_from_date"
            )

        # Remove None values
        static_listing_payload = {
            k: v for k, v in static_listing_payload.items() if v is not None
        }

        try:
            response = await self.session.post(
                endpoint, json=static_listing_payload, headers=headers, timeout=15.0
            )

            if response.status_code == 201:
                logger.debug(f"✅ Saved listing: {listing_data.get('url')}")
            elif response.status_code != 409:  # Ignore duplicates
                response.raise_for_status()

            # Save observation with scraped_at
            await self._save_observation(listing_data, property_type)

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP error saving listing: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"🌐 Network error saving listing: {e}")

    async def _save_observation(self, listing_data: Dict[str, Any], property_type: str):
        obs_table_name = (
            "observations" if property_type == "viviendas" else "room_observations"
        )
        obs_endpoint = urljoin(self.postgrest_url, f"/{obs_table_name}")

        obs_payload = {
            "listing_url": listing_data.get("url"),
            "price": listing_data.get("price"),
            "scraped_at": listing_data.get("scraped_at", datetime.now().isoformat()),
        }

        try:
            response = await self.session.post(
                obs_endpoint, json=obs_payload, timeout=15.0
            )
            response.raise_for_status()
            logger.debug(f"📊 Saved observation for: {obs_payload['listing_url']}")
        except Exception as e:
            logger.error(f"❌ Failed to save observation: {e}")


    async def get_scraper_status(self, scraper_type: str) -> int:
        """Retrieves the last processed capital ID for a given scraper type."""
        endpoint = urljoin(self.postgrest_url, "/scraper_status")
        params = {
            "scraper_type": f"eq.{scraper_type}",
            "select": "last_processed_capital_id",
        }
        try:
            response = await self.session.get(endpoint, params=params, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            if data:
                last_id = data[0].get("last_processed_capital_id", 0)
                logger.info(
                    f"Resuming {scraper_type} scrape from capital_id: {last_id + 1}"
                )
                return last_id
            logger.info(
                f"No previous status found for {scraper_type}. Starting from the beginning."
            )
            return 0
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as e:
            logger.error(
                f"Could not get scraper status for {scraper_type}, starting from beginning. Error: {e}"
            )
            return 0

    async def update_scraper_status(self, scraper_type: str, capital_id: int):
        """Updates (or inserts) the last processed capital ID."""
        endpoint = urljoin(self.postgrest_url, "/scraper_status")
        payload = {
            "scraper_type": scraper_type,
            "last_processed_capital_id": capital_id,
            "last_updated": datetime.now().isoformat(),
        }
        headers = {
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        }
        try:
            response = await self.session.post(
                endpoint, json=payload, headers=headers, timeout=15.0
            )
            response.raise_for_status()
            logger.info(
                f"Successfully updated status for {scraper_type} to capital_id: {capital_id}"
            )
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.error(f"Failed to update scraper status: {e}")
