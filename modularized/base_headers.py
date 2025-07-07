import time
import random
import logging
from typing import Dict
from typing import Optional
# Import from new config module
from .config import ScraperConfig
from camoufox.async_api import AsyncCamoufox

logger = logging.getLogger(__name__)


class HeaderManager:
    """Manages headers with improved anti-bot cookie handling."""

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.headers: Optional[Dict[str, str]] = None
        self.request_count = 0
        self.last_refresh_time = 0
        self.refresh_interval_seconds = 3600

    async def get_headers(self) -> Dict[str, str]:
        if await self._should_refresh_headers():
            await self.refresh_headers()
        return self.headers

    def increment_request_count(self):
        self.request_count += 1

    async def refresh_headers(self):
        logger.info("🔄 Refreshing headers...")
        self.headers = await self._generate_session_headers()
        self.request_count = 0
        self.last_refresh_time = time.time()

    async def _should_refresh_headers(self) -> bool:
        is_first_run = self.headers is None
        is_stale_by_count = self.request_count >= self.config.header_refresh_requests
        is_stale_by_time = (
            time.time() - self.last_refresh_time
        ) >= self.refresh_interval_seconds
        return is_first_run or is_stale_by_count or is_stale_by_time

    async def _generate_session_headers(self) -> Dict[str, str]:
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
                    if "idealista.com" in request.url:
                        headers_capture.update(dict(request.headers))

                page.on("request", capture_request_headers)

                await page.goto(
                    "https://www.idealista.com", wait_until="domcontentloaded", timeout=60000
                )
                await page.wait_for_timeout(5000)

                cookies = await page.context.cookies("https://www.idealista.com")
                cookie_str = self._build_cookie_string(cookies)
                await page.close()

                if headers_capture:
                    logger.info("✅ Captured real browser headers")
                    if cookie_str:
                        headers_capture["cookie"] = cookie_str
                        logger.info(f"🍪 Injected cookies: {cookie_str[:80]}...")
                    return headers_capture
                else:
                    logger.warning("⚠️ No headers captured, using fallback.")
                    return self._get_fallback_headers()
        except Exception as e:
            logger.error(f"❌ Camoufox header capture failed: {e}")
            return self._get_fallback_headers()

    def _build_cookie_string(self, cookies) -> str:
        """Builds cookie string with all anti-bot cookies."""
        important_cookies = []
        for cookie in cookies:
            # Capture all cookies (not just DataDome)
            if cookie.get('name') and cookie.get('value'):
                important_cookies.append(f"{cookie['name']}={cookie['value']}")
        return '; '.join(important_cookies)

    def _get_fallback_headers(self) -> Dict[str, str]:
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