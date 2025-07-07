# base_headers.py

import time
import random
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from camoufox.async_api import AsyncCamoufox

logger = logging.getLogger(__name__)


@dataclass
class ScraperConfig:
    delay: float = 2.0
    header_refresh_requests: int = 100
    timeout: int = 30
    user_agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/116.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0",
    ])


class HeaderManager:
    def __init__(self, config: ScraperConfig):
        self.config = config
        self.headers: Optional[Dict[str, str]] = None
        self.request_count = 0
        self.last_refresh = 0
        self.refresh_interval = 3600  # 1 hour

    async def generate_session_headers(self) -> Dict[str, str]:
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
                    if request.is_navigation_request() and "idealista.com" in request.url:
                        headers_capture.update(dict(request.headers))

                page.once("request", capture_request_headers)

                await page.goto("https://www.idealista.com", wait_until="domcontentloaded")
                await page.wait_for_timeout(40000)  # Humanize duration

                # Get cookies from context for idealista
                cookies = await page.context.cookies("https://www.idealista.com")
                datadome_cookie = next(
                    (c for c in cookies if c["name"].lower() == "datadome"), None
                )

                await page.close()

                if headers_capture:
                    logger.info("✅ Captured real browser headers")
                    logger.info(f"📋 User-Agent: {headers_capture.get('user-agent', 'N/A')}")

                    if datadome_cookie:
                        cookie_str = f"datadome={datadome_cookie['value']}"
                        headers_capture["cookie"] = cookie_str
                        logger.info(f"🍪 datadome cookie injected: {cookie_str[:50]}...")

                    return headers_capture
                else:
                    logger.warning("⚠️ No headers captured, falling back to defaults")
                    return self.get_fallback_headers()

        except Exception as e:
            logger.error(f"❌ Camoufox header capture failed: {e}")
            return self.get_fallback_headers()

    def get_fallback_headers(self) -> Dict[str, str]:
        """Return simple randomized fallback headers if Camoufox fails."""
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
        now = time.time()
        return (
            self.headers is None or
            self.request_count >= self.config.header_refresh_requests or
            (now - self.last_refresh) >= self.refresh_interval
        )

    async def refresh_headers(self):
        logger.info(
            f"🔄 Refreshing headers (requests={self.request_count}, age={time.time() - self.last_refresh:.0f}s)"
        )
        self.headers = await self.generate_session_headers()
        self.request_count = 0
        self.last_refresh = time.time()

    async def get_headers(self) -> Dict[str, str]:
        if await self.should_refresh_headers():
            await self.refresh_headers()
        return self.headers.copy()

    def increment_request_count(self):
        self.request_count += 1
