


[![en](https://img.shields.io/badge/lang-en-red.svg)](https://github.com/maiktreya/rental-scrapers/blob/main/readme.md)
[![es](https://img.shields.io/badge/lang-es-yellow.svg)](https://github.com/maiktreya/rental-scrapers/blob/main/readme.es.md)

---

# 🏠 Rental Scrapers for Tenant Empowerment

This project is designed to empower tenants and small-scale users by providing accessible scrapers for property listings on Airbnb and Idealista. With rising housing prices and unfair rental practices, access to data is crucial. This tool allows individuals to gather data on available properties without being subject to opaque and ad-based practices.

**Note:** This is not intended for corporate-scale use or to exploit property data on a large scale. The scrapers are built for **personal use**, focusing on the right to information for tenants.

## ⚙️ Installation

For non-experts, here's a simple way to get started with a Python virtual environment:

1. **Install Python:** Ensure you have [Python 3.7+](https://www.python.org/downloads/) installed on your machine.

2. **Create a virtual environment:**

   In your project root directory (where the README file is located), run the following commands to create and activate a virtual environment called `env`:

   ```bash
   python -m venv env
   source env/bin/activate  # On Windows use: .\env\Scripts\activate
   ```

3. **Install the required dependencies:**

   Once the virtual environment is activated, install the necessary packages by running:

   ```bash
   pip install -r requirements.txt
   ```

Now your environment is ready to run the scrapers!

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
- Virtual environment with required packages (`httpx`, `selenium`, `parsel`, `argparse`, `pandas`, `beautifulsoup4`)s

### Run the Airbnb Scraper

To scrape Airbnb listings:

```bash
python src/airbnb_scraper.py --url "AIRBNB_URL --format csv"
```

### Run the Idealista Scraper

To scrape Idealista listings:

```bash
python src/idealista_scraper.py --url "IDEALISTA_URL" --delay 2 --format csv
```

### Running All Scrapers

You can run all scrapers using the provided Bash script:

```bash
bash src/run_scraper.sh
```

### Output

Scraped data will be saved in the `out/` directory as CSV or JSON files.

You can create a cron job on Ubuntu to run your Python scraper daily at 2:00 AM with the following steps:

1. **Open the crontab file for editing:**

   Open the terminal and type:

   ```bash
   crontab -e
   ```

2. **Add the cron job:**

   In the editor that opens, add the following line (where path is the path to the rental-scrapers directory):

   ```bash
   0 2 * * * $PATH/rental-scrapers/src/run_scraper.sh >> $PATH/rental-scrapers/out/scraper.log 2>&1
   ```

   - `0 2 * * *` sets the cron job to run daily at 2:00 AM.
   - `/usr/bin/python3` is the path to the Python 3 interpreter. If you're using a virtual environment, make sure to update this path.
   - `>> $PATH/rental-scrapers/out/scraper.log 2>&1` ensures that output and any errors are logged.

3. **Save and exit:**

   After adding the line, save the file and exit the editor. Your cron job will now run daily at 2:00 AM.

Make sure your script is executable and that all required permissions are correctly set. Remember to modify the $BASE_PATH variable in the run_scraper.sh script to the appropriate local path.

---

## 💼 Legal Disclaimer

This tool is provided solely for personal use and informational purposes. It is intended to give small-scale users fair access to housing data. The developers are not responsible for any misuse of this tool or for legal consequences that may arise from large-scale scraping or commercial use. Users should ensure they comply with the terms of service of the websites they scrape.

## 🔒 License

This project is licensed under the The GNU General Public License (GPL-3). See the full license [here](https://www.gnu.org/licenses/gpl-3.0.en.html).

---
