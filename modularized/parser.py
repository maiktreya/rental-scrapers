#!/usr/bin/env python3
"""
A dedicated module for parsing HTML content from real estate websites.
This module uses BeautifulSoup for robust and resilient data extraction.
"""

import logging
from typing import Dict, Optional, List, Any
from urllib.parse import urljoin
from datetime import datetime

# Dependencies: pip install beautifulsoup4 lxml
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


class IdealistaParser:
    """A parser specifically designed for Idealista listing pages."""

    def extract_listings_from_page(
        self, content: str, base_url: str, property_type: str
    ) -> List[Dict[str, Any]]:
        """
        Extracts all listings from a page's HTML content.
        """
        soup = BeautifulSoup(content, "lxml")
        articles = soup.select("article.item")
        listings = [
            self._parse_article(article, base_url, property_type)
            for article in articles
        ]
        valid_listings = [listing for listing in listings if listing]
        logger.info(
            f"📋 Extracted {len(valid_listings)} listings from page using BeautifulSoup."
        )
        return valid_listings

    def _parse_article(
        self, article: Tag, base_url: str, property_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Parses a single <article> tag to extract detailed listing data.
        """
        try:
            listing = {
                "scraped_at": datetime.now().isoformat(),
                "source_url": base_url,
                "property_type": property_type,
            }

            link_tag = article.select_one("a.item-link")
            if not link_tag or not link_tag.has_attr("href"):
                return None

            listing["url"] = urljoin(base_url, link_tag["href"])
            listing["title"] = link_tag.get_text(strip=True)

            title_attr = link_tag.get("title", "")
            if " in " in title_attr:
                listing["location"] = title_attr.split(" in ")[-1]
            else:
                listing["location"] = "N/A"

            price_tag = article.select_one("span.item-price")
            if price_tag:
                price_text = price_tag.get_text(strip=True)
                try:
                    listing["price"] = int("".join(filter(str.isdigit, price_text)))
                except (ValueError, TypeError):
                    listing["price"] = None

            details = article.select("div.item-detail-char span.item-detail")
            for detail in details:
                text = detail.get_text(strip=True)
                if "m²" in text and "€/m²" not in text:
                    try:
                        listing["size_sqm"] = int("".join(filter(str.isdigit, text)))
                    except ValueError:
                        pass
                elif "hab." in text:
                    try:
                        listing["num_bedrooms"] = int(
                            "".join(filter(str.isdigit, text))
                        )
                    except ValueError:
                        pass

            # Identify provider type (company vs. individual)
            branding_element = article.select_one("picture.logo-branding")
            if branding_element:
                listing["advertiser_type"] = "company"
                company_img = branding_element.select_one("img")
                if company_img and company_img.get("alt"):
                    listing["advertiser_name"] = company_img.get("alt").strip()
            else:
                listing["advertiser_type"] = "individual"
                listing["advertiser_name"] = None

            return listing
        except Exception as e:
            logger.error(f"Error parsing listing article: {e}", exc_info=True)
            return None

    def find_next_page_url(self, content: str, base_url: str) -> Optional[str]:
        """
        Finds the URL of the next page from the pagination controls.
        """
        soup = BeautifulSoup(content, "lxml")
        next_link = soup.select_one("a.next")
        if next_link and next_link.has_attr("href"):
            return urljoin(base_url, next_link["href"])
        return None
