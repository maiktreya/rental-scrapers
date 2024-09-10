import argparse
import asyncio
import json
import random
import re
from typing import Dict, List
from urllib.parse import urljoin
import httpx
from parsel import Selector
from typing_extensions import TypedDict
import csv
from datetime import datetime
import logging

# Logging setup
logging.basicConfig(level=logging.INFO)

# List of user agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36",
    # More user agents can be added here
]

# Establish persistent HTTPX session with browser-like headers to avoid blocking
BASE_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "en-US;en;q=0.9",
    "accept-encoding": "gzip, deflate, br",
}

# Function to get a random user agent
def get_random_user_agent():
    return random.choice(USER_AGENTS)

# Type hints for expected results
class PropertyResult(TypedDict, total=False):
    url: str
    title: str
    location: str
    price: int
    currency: str
    updated: str
    rooms: int
    size_sqm: int
    features: Dict[str, List[str]]

def parse_property(response: httpx.Response) -> PropertyResult:
    selector = Selector(text=response.text)
    css = lambda x: selector.css(x).get("").strip()
    css_all = lambda x: selector.css(x).getall()

    data: PropertyResult = {}
    data["url"] = str(response.url)
    data["title"] = css("h1 .main-info__title-main::text")
    data["location"] = css(".main-info__title-minor::text")
    data["currency"] = css(".info-data-price::text")

    price_str = css(".info-data-price span::text")
    if price_str:
        price_str = price_str.replace(".", "").replace(",", "")
        data["price"] = int(price_str)
    else:
        data["price"] = None

    data["description"] = "\n".join(css_all("div.comment ::text")).strip()
    data["updated"] = (
        selector.xpath("//p[@class='stats-text'][contains(text(),'updated on')]/text()")
        .get("")
        .split(" on ")[-1]
    )

    data["features"] = {}
    for feature_block in selector.css(".details-property-h2"):
        label = feature_block.xpath("text()").get()
        features = feature_block.xpath("following-sibling::div[1]//li")
        data["features"][label] = [
            "".join(feat.xpath(".//text()").getall()).strip() for feat in features
        ]

    basic_features = data["features"].get("Características básicas", [])
    data["rooms"] = None
    data["size_sqm"] = None

    for feature in basic_features:
        if "habitaciones" in feature:
            rooms_match = re.search(r"(\d+)\s*habitaciones?", feature)
            if rooms_match:
                data["rooms"] = int(rooms_match.group(1))

        if "m²" in feature:
            size_match = re.search(r"(\d+)\s*m²", feature)
            if size_match:
                data["size_sqm"] = int(size_match.group(1))

    return data

async def extract_property_urls(
    area_url: str, session: httpx.AsyncClient, delay: float
) -> List[str]:
    headers = BASE_HEADERS.copy()
    headers["user-agent"] = get_random_user_agent()  # Rotate user-agent for each request
    response = await session.get(area_url, headers=headers)
    selector = Selector(text=response.text)
    property_links = selector.css("article.item a.item-link::attr(href)").getall()
    full_urls = [urljoin(area_url, link) for link in property_links]
    await asyncio.sleep(delay)
    return full_urls

async def get_next_page_url(
    current_url: str, session: httpx.AsyncClient, delay: float
) -> str:
    response = await session.get(current_url)
    selector = Selector(text=response.text)
    next_page_link = selector.css("a.icon-arrow-right-after::attr(href)").get()
    await asyncio.sleep(delay)
    return urljoin(current_url, next_page_link) if next_page_link else None

async def scrape_properties(
    urls: List[str], session: httpx.AsyncClient, delay: float
) -> List[PropertyResult]:
    properties = []
    for url in urls:
        for attempt in range(3):
            try:
                headers = BASE_HEADERS.copy()
                headers["user-agent"] = get_random_user_agent()  # Rotate user-agent for each request
                response = await session.get(url, headers=headers)
                if response.status_code == 200:
                    properties.append(parse_property(response))
                else:
                    logging.error(
                        f"Failed to scrape property: {response.url} with status code {response.status_code}"
                    )
                await asyncio.sleep(delay)
                break
            except (httpx.ReadTimeout, httpx.RequestError) as e:
                logging.error(
                    f"Attempt {attempt + 1} failed for URL: {url}, Error: {str(e)}"
                )
                if attempt == 2:
                    logging.error(f"Failed to retrieve URL: {url} after 3 attempts")
    return properties

def save_to_json(data: List[PropertyResult], filename: str) -> None:
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_to_csv(data: List[PropertyResult], filename: str) -> None:
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = [
            "url",
            "title",
            "location",
            "price",
            "currency",
            "rooms",
            "size_sqm",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for property in data:
            writer.writerow(
                {
                    "url": property.get("url", ""),
                    "title": property.get("title", ""),
                    "location": property.get("location", ""),
                    "price": property.get("price", ""),
                    "currency": property.get("currency", ""),
                    "rooms": property.get("rooms", ""),
                    "size_sqm": property.get("size_sqm", ""),
                }
            )

async def run(base_url: str, delay: float):
    all_property_urls = []
    page_count = 1
    max_pages = 40

    async with httpx.AsyncClient(
        headers=BASE_HEADERS, follow_redirects=True, timeout=10.0
    ) as session:
        current_url = base_url

        while current_url and page_count <= max_pages:
            logging.info(f"Scraping page {page_count}: {current_url}")
            property_urls = await extract_property_urls(current_url, session, delay)
            all_property_urls.extend(property_urls)

            if not property_urls:
                logging.info("No more property URLs found, stopping pagination.")
                break

            current_url = await get_next_page_url(current_url, session, delay)
            page_count += 1

        logging.info(f"Total properties found: {len(all_property_urls)}")
        data = await scrape_properties(all_property_urls, session, delay)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"scrapping/out/idealista_properties_{timestamp}.json"
        csv_filename = f"scrapping/out/idealista_properties_{timestamp}.csv"

        save_to_json(data, json_filename)
        save_to_csv(data, csv_filename)

        logging.info(f"Data saved to {json_filename} and {csv_filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape property listings from Idealista"
    )
    parser.add_argument(
        "--url",
        type=str,
        default="https://www.idealista.com/venta-viviendas/segovia-segovia/",
        help="Base URL for scraping properties (default is Segovia)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between requests in seconds (default is 2.0 seconds)",
    )

    args = parser.parse_args()
    asyncio.run(run(args.url, args.delay))
