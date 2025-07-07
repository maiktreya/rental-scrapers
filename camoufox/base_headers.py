#!/usr/bin/env python3
"""
An independent module for generating and managing stealth browser headers using Camoufox.
This module captures real browser headers during navigation and injects anti-bot cookies.
"""

import asyncio
import logging
import random
import time
from typing import Dict, Optional, List

# Ensure camoufox is installed: pip install camoufox
from camoufox.async_api import AsyncCamoufox

logger = logging.getLogger(__name__)


class StealthHeaderManager:
    """
    Manages browser headers using Camoufox with advanced stealth techniques.

    This class launches a real browser, navigates to a target site,
    captures the exact headers sent during the navigation request,
    and extracts the 'datadome' cookie to bypass anti-bot measures.
    """

    def __init__(
        self,
        user_agents: List[str],
        refresh_requests: int = 30,
        refresh_interval: int = 3600,
    ):
        """
        Initializes the StealthHeaderManager.

        Args:
            user_agents (List[str]): A list of fallback User-Agent strings.
            refresh_requests (int): Refresh headers after this many requests.
            refresh_interval (int): Refresh headers if they are older than this (in seconds).
        """
        self.fallback_user_agents = user_agents
        self.header_refresh_requests = refresh_requests
        self.refresh_interval = refresh_interval

        self.headers: Optional[Dict[str, str]] = None
        self.request_count = 0
        self.last_refresh_time = 0

    async def generate_session_headers(self, target_url: str) -> Dict[str, str]:
        """
        Generate a full set of real browser headers by launching a browser,
        visiting the target URL, and capturing the navigation request.

        This method implements the logic for capturing headers and injecting
        the datadome cookie.

        Args:
            target_url (str): The URL to visit for header generation (e.g., "https://www.idealista.com").

        Returns:
            A dictionary of captured browser headers.
        """
        try:
            logger.info("🚀 Launching Camoufox to generate real session headers...")
            domain = target_url.split("://")[1].split("/")[0]

            # Use a persistent context to handle challenges and cookies more effectively
            async with AsyncCamoufox(
                headless=False,  # Run in headed mode to solve potential challenges
                humanize=True,
                os=random.choice(["linux", "macos", "windows"]),
                enable_cache=False,
                persistent_context=True,
                user_data_dir="camoufox-user-data",  # Directory for persistent session
                window=(1366, 768),
            ) as browser:

                page = await browser.new_page()
                headers_capture = {}

                # Define a handler to capture headers of the first navigation request to the target domain
                def capture_request_headers(request):
                    if request.is_navigation_request() and domain in request.url:
                        # Use a non-blocking call to update headers
                        asyncio.create_task(
                            self._update_captured_headers(request.headers)
                        )

                # Use 'once' to capture only the first matching request
                page.on("request", capture_request_headers)

                logger.info(
                    f"Navigating to {target_url} to capture headers and cookies..."
                )
                await page.goto(
                    target_url, wait_until="domcontentloaded", timeout=60000
                )

                # Wait for human-like interaction and for the page to settle.
                # This is crucial for anti-bot systems to process.
                logger.info(
                    "Waiting for page to settle and potential anti-bot checks..."
                )
                await page.wait_for_timeout(20000)

                # Wait until headers are captured or timeout
                for _ in range(10):  # Wait up to 10 seconds for headers
                    if headers_capture:
                        break
                    await asyncio.sleep(1)

                # Get cookies from the context, specifically looking for datadome
                cookies = await page.context.cookies(target_url)
                datadome_cookie = next(
                    (c for c in cookies if c["name"].lower() == "datadome"), None
                )

                await page.close()

                if headers_capture:
                    logger.info("✅ Captured real browser headers.")
                    logger.info(
                        f"📋 User-Agent: {headers_capture.get('user-agent', 'N/A')}"
                    )

                    if datadome_cookie:
                        cookie_str = f"datadome={datadome_cookie['value']}"
                        # Append to existing cookie header or create a new one
                        headers_capture["cookie"] = (
                            headers_capture.get("cookie", "") + "; " + cookie_str
                        )
                        logger.info(
                            f"🍪 Injected datadome cookie: {cookie_str[:60]}..."
                        )
                    else:
                        logger.warning("⚠️ Datadome cookie not found.")

                    return headers_capture
                else:
                    logger.warning(
                        "⚠️ No navigation headers were captured, falling back to defaults."
                    )
                    return self.get_fallback_headers()

        except Exception as e:
            logger.error(f"❌ Camoufox header capture failed: {e}", exc_info=True)
            return self.get_fallback_headers()

    async def _update_captured_headers(self, headers: Dict[str, str]):
        """Coroutine-safe method to update the captured headers."""
        self.headers = dict(headers)

    def get_fallback_headers(self) -> Dict[str, str]:
        """Provides a basic set of headers if Camoufox fails."""
        logger.warning("🔄 Using fallback headers.")
        return {
            "User-Agent": random.choice(self.fallback_user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def _should_refresh_headers(self) -> bool:
        """Determines if headers need to be refreshed based on age or usage."""
        current_time = time.time()
        time_since_refresh = current_time - self.last_refresh_time
        is_stale = time_since_refresh >= self.refresh_interval
        is_overused = self.request_count >= self.header_refresh_requests

        if is_stale:
            logger.info("Header refresh triggered: headers are stale.")
        if is_overused:
            logger.info("Header refresh triggered: request limit reached.")

        return self.headers is None or is_stale or is_overused

    async def get_headers(self, target_url: str) -> Dict[str, str]:
        """
        Gets the current headers, refreshing them if necessary.

        Args:
            target_url (str): The target URL, passed to the generation function if a refresh is needed.

        Returns:
            A dictionary of headers.
        """
        if self._should_refresh_headers():
            await self.refresh_headers(target_url)
        return self.headers.copy()

    async def refresh_headers(self, target_url: str):
        """Forces a refresh of the session headers."""
        logger.info(
            f"🔄 Refreshing headers (requests: {self.request_count}, "
            f"time since last: {time.time() - self.last_refresh_time:.0f}s)"
        )
        try:
            self.headers = await self.generate_session_headers(target_url)
            self.request_count = 0
            self.last_refresh_time = time.time()
            logger.info("✅ Headers refreshed successfully.")
        except Exception as e:
            logger.error(f"❌ Failed to refresh headers: {e}", exc_info=True)
            if self.headers is None:
                self.headers = self.get_fallback_headers()

    def increment_request_count(self):
        """Increments the request counter."""
        self.request_count += 1
