

# 🏠 Housing Scraper for Tenant Empowerment

**Contributors:** Maiktreya & Regex Wizard

This project is designed to empower tenants and small-scale users by providing an accessible and easy-to-use scraper for property listings on Idealista. Rising housing prices and unfair rental practices make access to information more important than ever. With this scraper, individuals can gather data on available properties without being subject to opaque real estate practices or rental oligarchs.

It is designed for **personal use**, focused on a tenant's right to information. **This is not intended for corporate-scale use or for exploiting property data on a large scale.** Its simplicity makes it robust for small use cases, but it will easily be blocked if abused for larger operations.

## 🎯 Project Aim

The goal is to empower individuals pressured by rising housing prices by giving them a tool to easily access public property listings, making the rental market more transparent. It simplifies scraping without corporate-level complexities like parallel requests, proxies, or sophisticated anti-block measures, ensuring that it stays small-scale and for personal use.

## 🚀 Usage

### Prerequisites:
- Python 3.7+
- `httpx`, `parsel`, and `argparse` Python packages. Install them via:
  ```bash
  pip install -r requirements.txt
  ```

### Run the Scraper:
By default, the scraper targets Segovia property listings. You can override the URL via command line as well as the default delay.

**Basic usage:**
```bash
python your_script.py
```

**Scrape another area (e.g., Madrid):**
```bash
python scrapping/src/idealista/idealista_httpx_dev.py --url "https://www.idealista.com/alquiler-viviendas/segovia-segovia/" --delay 2
```

The script will scrape up to two pages of listings, saving the output in both JSON and CSV formats in the `scrapping/out/` directory.

## 🛠️ Key Features
- Scrapes property listings for basic information (title, location, price, rooms, size).
- Provides both JSON and CSV output for easy data analysis.
- Simple, minimalist approach—perfect for personal use by tenants without the need for large-scale scraping tools.

## 🔒 License

This project is licensed under the MIT License. See the full license [here](LICENSE).

---

```text
MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
```


You can create a cron job on Ubuntu to run your Python scraper daily at 2:00 AM with the following steps:

1. **Open the crontab file for editing:**

   Open the terminal and type:

   ```bash
   crontab -e
   ```

2. **Add the cron job:**

   In the editor that opens, add the following line:

   ```bash
   0 2 * * * /home/other/dev/github/LocalWealthHousing/run_scraper.sh >> /home/other/dev/github/LocalWealthHousing/logs/scraper.log 2>&1
   ```

   - `0 2 * * *` sets the cron job to run daily at 2:00 AM.
   - `/usr/bin/python3` is the path to the Python 3 interpreter. If you're using a virtual environment, make sure to update this path.
   - `>> /home/other/dev/github/LocalWealthHousing/logs/scraper.log 2>&1` ensures that output and any errors are logged.

3. **Save and exit:**

   After adding the line, save the file and exit the editor. Your cron job will now run daily at 2:00 AM.

Make sure your script is executable and that all required permissions are correctly set.

---

### 📢 Shout-out

Thanks to all contributors and like-minded souls contributing to tenant empowerment and transparency in housing! This project is dedicated to small-scale users who believe in the right to information. Let’s continue making housing fairer, one scraped property at a time! ✊

---
