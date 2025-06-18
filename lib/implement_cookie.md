# Implement a metadate cookie


## Selenium extractor

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

def get_fresh_cookie():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36")

    driver = webdriver.Chrome(options=options)
    driver.get("https://www.idealista.com")
    time.sleep(5)  # Wait for JavaScript to execute

    cookies = driver.get_cookies()
    driver.quit()

    datadome_cookie = next((c for c in cookies if c['name'] == 'datadome'), None)
    if datadome_cookie:
        return datadome_cookie['name'] + '=' + datadome_cookie['value']
    else:
        raise Exception("Failed to obtain datadome cookie")

if __name__ == "__main__":
    fresh_cookie = get_fresh_cookie()
    with open('cookie.txt', 'w') as f:
        f.write(fresh_cookie)
    print("Cookie renewed successfully.")
```

## Updated headers construction


```python
# Read the cookie from the file
try:
    with open('cookie.txt', 'r') as f:
        datadome_cookie = f.read()
except FileNotFoundError:
    # If the cookie file doesn't exist, get a fresh cookie
    from renew_cookie import get_fresh_cookie
    datadome_cookie = get_fresh_cookie()
    with open('cookie.txt', 'w') as f:
        f.write(datadome_cookie)

BASE_HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "en-US;en;q=0.9",
    "accept-encoding": "gzip, deflate, br",
    "cookie": datadome_cookie
}

```

## Cron job automation

```bash
0 */6 * * * /usr/bin/python3 /path/to/renew_cookie.py
```
