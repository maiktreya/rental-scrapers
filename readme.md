
---

# 🏠 Rental Scrapers for Tenant Empowerment

**Contributors:** Maiktreya & Regex Wizard

This project is designed to empower tenants and small-scale users by providing accessible scrapers for property listings on Airbnb and Idealista. With rising housing prices and unfair rental practices, access to data is crucial. This tool allows individuals to gather data on available properties without being subject to opaque an advert based practices.

**Note:** This is not intended for corporate-scale use or to exploit property data on a large scale. The scrapers are built for **personal use**, focusing on the right to information for tenants.

## 🎯 Project Aim

The goal of this project is to empower individuals impacted by rising housing costs, by offering them an easy way to access public property listings and make the rental market more transparent. It simplifies scraping without the corporate complexities (like parallel requests or proxies), staying focused on personal, small-scale uses.

## 🛠️ Key Features

- Scrapes Airbnb listings (short, medium, and long-term).
- Scrapes property listings from Idealista for both sales and rentals.
- Handles pagination and saves data in JSON and CSV formats.
- Supports customizable delays to prevent blocking.
- Simple and minimalist approach tailored to personal users.

## 🚀 Usage

### Prerequisites
- Python 3.7+
- ChromeDriver for Airbnb scraping (via Selenium)
- Virtual environment with required packages (`httpx`, `selenium`, `parsel`, `argparse`, `pandas`, `beautifulsoup4`)

Install dependencies:
```bash
pip install -r requirements.txt
```

### Run the Airbnb Scraper
To scrape Airbnb listings:
```bash
python scrapping/src/airbnb_scraper.py --url "AIRBNB_URL"
```

### Run the Idealista Scraper
To scrape Idealista listings:
```bash
python scrapping/src/idealista_httpx_dev.py --url "IDEALISTA_URL" --delay 2
```

### Running All Scrapers
You can run all scrapers using the provided Bash script:
```bash
./run_scraper.sh
```

### Output
Scraped data will be saved in the `scrapping/out/` directory as both JSON and CSV files.

## 💼 Legal Disclaimer

This tool is provided solely for personal use and informational purposes. It is intended to give small-scale users fair access to housing data. The developers are not responsible for any misuse of this tool or for legal consequences that may arise from large-scale scraping or commercial use. Users should ensure they comply with the terms of service of the websites they scrape.

## 🔒 License

This project is licensed under the MIT License. See the full license [here](LICENSE).

---
