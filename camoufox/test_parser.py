#!/usr/bin/env python3
import logging
from bs4 import BeautifulSoup
import sys
from pathlib import Path
import json


# Add the parent directory of modularized to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from modularized.parser import IdealistaParser

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_parser():
    # Read the HTML file
    with open("alquiler.html", "r", encoding="utf-8") as file:
        content = file.read()

    # Initialize the parser
    parser = IdealistaParser()
    base_url = "https://www.idealista.com"
    property_type = "alquiler"

    # Extract listings
    listings = parser.extract_listings_from_page(content, base_url, property_type)

    # Count articles for comparison
    soup = BeautifulSoup(content, "lxml")
    num_articles = len(soup.select("article.item"))

    # Print results
    print(f"Number of article.item elements found: {num_articles}")
    print(f"Number of extracted listings: {len(listings)}")

    if listings:
        print("\nFirst listing details:")
        for key, value in listings[0].items():
            print(f"{key}: {value}")
        # Save all listings to a JSON file
        with open("listings.json", "w", encoding="utf-8") as f:
            json.dump(listings, f, ensure_ascii=False, indent=2)
            print("All 30 listings saved to 'listings.json'.")
    else:
        print("No listings extracted.")

if __name__ == "__main__":
    test_parser()