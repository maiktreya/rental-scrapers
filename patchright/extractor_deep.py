from patchright.sync_api import sync_playwright
import time
import os

# Configure paths and settings
USER_DATA_DIR = "./chrome_profile"
LOG_FILE = "console_log.txt"
SCREENSHOT_FILE = "idealista_screenshot.png"
os.makedirs(USER_DATA_DIR, exist_ok=True)

def get_datadome_cookie():
    with sync_playwright() as p:
        # Launch persistent context with stealth settings
        browser = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            channel="chrome",
            headless=False,  # Visible browser helps avoid detection
            no_viewport=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--lang=en-US,en;q=0.9",
                f"--user-data-dir={USER_DATA_DIR}"
            ],
            ignore_https_errors=True,
            record_har_path="network_trace.har"
        )

        page = browser.new_page()
        page.on("console", lambda msg: open(LOG_FILE, "a").write(f"{time.ctime()} - {msg.text}\n"))

        # Set natural language headers
        page.set_extra_http_headers({
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        })

        # Navigate to target site with human-like delays
        page.goto("https://www.idealista.com", wait_until="domcontentloaded")
        time.sleep(2)

        # Simulate human interactions
        page.mouse.move(100, 100)
        page.mouse.wheel(0, 500)
        time.sleep(1)
        page.mouse.wheel(0, 300)
        time.sleep(3)

        # Save screenshot for debugging
        page.screenshot(path=SCREENSHOT_FILE, full_page=True)

        # Extract DataDome cookie
        cookies = page.context.cookies("https://www.idealista.com")
        datadome_cookie = next(
            (c for c in cookies if c["name"] == "datadome"),
            None
        )

        browser.close()
        return datadome_cookie["value"] if datadome_cookie else None

if __name__ == "__main__":
    cookie = get_datadome_cookie()
    if cookie:
        print(f"Success! DataDome cookie: {cookie}")
    else:
        print("Failed to retrieve DataDome cookie")