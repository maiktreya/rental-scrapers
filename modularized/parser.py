#!/usr/bin/env python3
"""
Parser with robust data extraction and URL handling.
"""

import logging
from typing import Dict, Optional, List, Any
from urllib.parse import urljoin, urlparse
from datetime import datetime
import re

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


class IdealistaParser:
    """Parser with critical fixes for data extraction."""

    def extract_listings_from_page(
        self, content: str, base_url: str, property_type: str
    ) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(content, "lxml")
        articles = soup.select("article.item")
        listings = [
            self._parse_article(article, base_url, property_type)
            for article in articles
        ]
        valid_listings = [listing for listing in listings if listing]
        logger.info(f"📋 Extracted {len(valid_listings)} valid listings.")
        return valid_listings

    def _parse_article(
        self, article: Tag, base_url: str, property_type: str
    ) -> Optional[Dict[str, Any]]:
        try:
            listing = {
                "scraped_at": datetime.now().isoformat(),  # Ensure timestamp exists
                "source_url": base_url,
                "property_type": property_type,
            }

            # Robust URL handling
            link_tag = article.select_one("a.item-link")
            if not link_tag or not link_tag.has_attr("href"):
                return None

            href = link_tag["href"].strip()
            # Handle protocol-relative URLs
            if href.startswith("//"):
                listing["url"] = "https:" + href
            # Handle absolute paths
            elif href.startswith("/"):
                listing["url"] = urljoin("https://www.idealista.com", href)
            # Handle full URLs
            else:
                listing["url"] = href

            # Extract title
            listing["title"] = link_tag.get_text(strip=True) or ""

            # Extract location from title attribute
            title_attr = link_tag.get("title", "")
            if " in " in title_attr:
                listing["location"] = title_attr.split(" in ")[-1]
            else:
                listing["location"] = ""

            # Robust price parsing
            price_tag = article.select_one("span.item-price")
            if price_tag:
                price_text = price_tag.get_text(strip=True)
                # Handle "€1.200" format
                clean_price = re.sub(r"[^\d,]", "", price_text).replace(",", "")
                try:
                    listing["price"] = int(clean_price) if clean_price else None
                except ValueError:
                    listing["price"] = None

            # Robust bedroom detection
            bedroom_tag = article.select_one("span.item-detail:has(span.icon-bedroom)")
            if bedroom_tag:
                try:
                    bedroom_text = bedroom_tag.get_text(strip=True)
                    listing["num_bedrooms"] = int(''.join(filter(str.isdigit, bedroom_text)))
                except (ValueError, TypeError):
                    listing["num_bedrooms"] = None

            # Size detection
            size_tag = article.select_one("span.item-detail:has(span.icon-meter)")
            if size_tag:
                try:
                    size_text = size_tag.get_text(strip=True)
                    clean_size = re.sub(r"[^\d,]", "", size_text).replace(",", "")
                    listing["size_sqm"] = int(clean_size) if clean_size else None
                except ValueError:
                    listing["size_sqm"] = None

            # Advertiser info
            branding_element = article.select_one("picture.logo-branding")
            if branding_element:
                listing["advertiser_type"] = "company"
                company_img = branding_element.select_one("img")
                listing["advertiser_name"] = company_img.get("alt", "").strip() if company_img else ""
            else:
                listing["advertiser_type"] = "individual"
                listing["advertiser_name"] = ""

            return listing
        except Exception as e:
            logger.error(f"❌ Parsing error: {e}")
            return None

    def find_next_page_url(self, content: str, base_url: str) -> Optional[str]:
        soup = BeautifulSoup(content, "lxml")
        # Handle both anchor and list item pagination
        next_link = soup.select_one('a[rel="next"], li.next > a')
        if next_link and next_link.has_attr("href"):
            return urljoin(base_url, next_link["href"])
        return None