#!/usr/bin/env python3
"""
Parser with robust data extraction and URL handling, enhanced for compatibility.
"""
import logging
from typing import Dict, Optional, List, Any
from urllib.parse import urljoin
from datetime import datetime
import re
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

class IdealistaParser:
    """Parser with critical fixes and enhanced compatibility."""

    def _parse_numeric(self, text: str) -> Optional[float]:
        """
        Robustly parses a string to a float, handling different decimal
        and thousands separators.
        """
        if not text:
            return None
        # Remove all non-digit, non-dot, non-comma characters
        clean_text = re.sub(r"[^\d,.]", "", text.strip())
        if "," in clean_text:
            # Treat comma as decimal separator, remove dots
            clean_text = clean_text.replace(".", "").replace(",", ".")
        elif "." in clean_text:
            # Treat dots as thousands separators, remove them
            clean_text = clean_text.replace(".", "")
        # If neither, clean_text is already digits
        try:
            return float(clean_text)
        except ValueError:
            logger.warning(f"Could not parse '{text}' to a number.")
            return None

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
                "scraped_at": datetime.now().isoformat(),
                "source_url": base_url,
                "property_type": property_type,
            }
            # Robust URL handling
            link_tag = article.select_one("a.item-link")
            if not link_tag or not link_tag.has_attr("href"):
                logger.warning("No valid link tag found in article")
                return None
            href = link_tag["href"].strip()
            if href.startswith("//"):
                listing["url"] = "https:" + href
            elif href.startswith("/"):
                listing["url"] = urljoin("https://www.idealista.com", href)
            else:
                listing["url"] = href
            # Extract title and location
            listing["title"] = link_tag.get_text(strip=True) or ""
            if " en " in listing["title"]:
                listing["location"] = listing["title"].split(" en ", 1)[-1]
            else:
                listing["location"] = ""
            # Robust price parsing
            price_tag = article.select_one("span.item-price")
            if price_tag:
                price_float = self._parse_numeric(price_tag.get_text(strip=True))
                if price_float is not None:
                    listing["price"] = int(price_float)
            # Pricedown price (if applicable)
            pricedown_price_tag = article.select_one("span.pricedown_price")
            if pricedown_price_tag:
                pricedown_float = self._parse_numeric(pricedown_price_tag.get_text(strip=True))
                if pricedown_float is not None:
                    listing["pricedown_price"] = int(pricedown_float)
            # Bedroom detection
            bedroom_tag = None
            for detail in article.select("span.item-detail"):
                detail_text = detail.get_text(strip=True)
                if "hab." in detail_text:
                    bedroom_tag = detail
                    break
            if bedroom_tag:
                try:
                    bedroom_text = bedroom_tag.get_text(strip=True)
                    listing["num_bedrooms"] = int(re.search(r'\d+', bedroom_text).group())
                except (AttributeError, ValueError):
                    listing["num_bedrooms"] = None
                    logger.warning(f"Failed to parse bedrooms: {bedroom_text}")
            else:
                listing["num_bedrooms"] = None
            # Size detection
            size_tag = None
            for detail in article.select("span.item-detail"):
                detail_text = detail.get_text(strip=True)
                if "m²" in detail_text or "m2" in detail_text:
                    size_tag = detail
                    break
            if size_tag:
                size_float = self._parse_numeric(size_tag.get_text(strip=True))
                if size_float is not None:
                    listing["size_sqm"] = int(size_float)
            else:
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
            # Description
            description_tag = article.select_one("div.item-description p.ellipsis")
            if description_tag:
                listing["description"] = description_tag.get_text(strip=True)
            # Flat floor number
            floor_number_tag = article.select_one("span.item-detail:nth-of-type(3)")
            if floor_number_tag:
                listing["flat_floor_number"] = floor_number_tag.get_text(strip=True)
            return listing
        except Exception as e:
            logger.error(f"❌ Parsing error: {e}")
            return None

    def find_next_page_url(self, content: str, base_url: str) -> Optional[str]:
        soup = BeautifulSoup(content, "lxml")
        next_link = soup.select_one('a[rel="next"], li.next > a')
        if next_link and next_link.has_attr("href"):
            return urljoin(base_url, next_link["href"])
        return None