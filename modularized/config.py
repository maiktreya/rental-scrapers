from dataclasses import dataclass, field
from typing import List
import os

@dataclass
class ScraperConfig:
    """Central configuration for the scraper (prevents circular imports)."""
    delay: float = 5.0
    header_refresh_requests: int = 100
    max_retries: int = 3
    timeout: float = 45.0  # Changed to float for HTTPX
    max_pages: int = 50
    header_target_url: str = "https://www.idealista.com"
    postgrest_url: str = os.environ.get("POSTGREST_URL", "http://localhost:3001")
    user_agents: List[str] = field(
        default_factory=lambda: [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        ]
    )