from dataclasses import dataclass, field
from typing import List
import os
import argparse # Import argparse

@dataclass
class ScraperConfig:
    """Central configuration for the scraper (prevents circular imports)."""
    # Initialize with argparse arguments if provided, otherwise use defaults
    delay: float = field(default=5.0)
    header_refresh_requests: int = field(default=100)
    max_retries: int = field(default=3)
    timeout: float = field(default=45.0)  # Changed to float for HTTPX
    max_pages: int = field(default=50)
    header_target_url: str = "https://www.idealista.com"
    postgrest_url: str = os.environ.get("POSTGREST_URL", "http://localhost:3001")
    user_agents: List[str] = field(
        default_factory=lambda: [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        ]
    )

    def __post_init__(self):
        # This method is called after __init__ and can be used for post-initialization logic
        # For example, if you want to ensure timeout is always a float, or other validations
        pass

    @classmethod
    def from_args(cls, args: argparse.Namespace):
        """Creates a ScraperConfig instance from argparse arguments."""
        return cls(
            delay=args.delay,
            header_refresh_requests=args.header_refresh_requests,
            max_retries=args.max_retries,
            timeout=float(args.timeout), # Ensure timeout is float
            max_pages=args.max_pages
        )