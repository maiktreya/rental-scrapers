# base_headers.py

import time
import random
import logging
from typing import Dict, Optional
from camoufox.async_api import AsyncCamoufox

# --- FIX: Import the single, authoritative config class ---
from .config import ScraperConfig

logger = logging.getLogger(__name__)


class HeaderManager:
    """Manages the generation, caching, and rotation of browser headers."""

    def __init__(self, config: ScraperConfig):
        """
        Initializes the HeaderManager.

        Args:
            config (ScraperConfig): The central scraper configuration object.
        """
        self.config = config
        self.headers: Optional[Dict[str, str]] = None
        self.request_count = 0
        self.last_refresh_time = 0
        self.refresh_interval_seconds = 3600  # 1 hour

    async def get_headers(self) -> Dict[str, str]:
        """
        Retrieves valid browser headers, refreshing them if necessary.
        """
        if await self._should_refresh_headers():
            await self.refresh_headers()
        return self.headers

    def increment_request_count(self):
        """Increments the counter for requests made with the current headers."""
        self.request_count += 1

    async def refresh_headers(self):
        """
        Forces a refresh of the browser headers using Camoufox.
        """
        logger.info(
            f"🔄 Refreshing headers (reason: count={self.request_count}, age={time.time() - self.last_refresh_time:.0f}s)"
        )
        self.headers = await self._generate_session_headers()
        self.request_count = 0
        self.last_refresh_time = time.time()

    async def _should_refresh_headers(self) -> bool:
        """
        Determines if headers should be refreshed based on age or usage count.
        """
        is_first_run = self.headers is None
        is_stale_by_count = self.request_count >= self.config.header_refresh_requests
        is_stale_by_time = (
            time.time() - self.last_refresh_time
        ) >= self.refresh_interval_seconds
        return is_first_run or is_stale_by_count or is_stale_by_time

    async def _generate_session_headers(self) -> Dict[str, str]:
        """
        Uses Camoufox to launch a browser and capture real request headers.
        """
        try:
            logger.info("🚀 Launching Camoufox to generate real session headers...")
            async with AsyncCamoufox(
                headless=False,
                humanize=True,
                os=random.choice(["linux", "macos", "windows"]),
                enable_cache=False,
                persistent_context=True,
                user_data_dir="usr-data-dir",
                window=(1366, 768),
            ) as browser:
                page = await browser.new_page()
                headers_capture = {}

                def capture_request_headers(request):
                    if (
                        request.is_navigation_request()
                        and "idealista.com" in request.url
                    ):
                        headers_capture.update(dict(request.headers))

                page.once("request", capture_request_headers)

                await page.goto(
                    "https://www.idealista.com", wait_until="domcontentloaded"
                )
                await page.wait_for_timeout(5000)  # Humanize duration

                cookies = await page.context.cookies("https://www.idealista.com")
                datadome_cookie = next(
                    (c for c in cookies if c["name"].lower() == "datadome"), None
                )
                await page.close()

                if headers_capture:
                    logger.info("✅ Captured real browser headers")
                    if datadome_cookie:
                        cookie_str = f"datadome={datadome_cookie['value']}"
                        headers_capture["cookie"] = cookie_str
                        logger.info(
                            f"🍪 Datadome cookie injected: {cookie_str[:50]}..."
                        )
                    return headers_capture
                else:
                    logger.warning("⚠️ No navigation headers captured, using fallback.")
                    return self._get_fallback_headers()
        except Exception as e:
            logger.error(f"❌ Camoufox header capture failed: {e}", exc_info=True)
            return self._get_fallback_headers()

    def _get_fallback_headers(self) -> Dict[str, str]:
        """
        Returns simple randomized fallback headers if Camoufox fails.
        """
        logger.warning("🔄 Using fallback headers")
        return {
            "User-Agent": random.choice(self.config.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "DNT": "1",
        }
