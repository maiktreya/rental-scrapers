import os
import json
import time
from playwright.sync_api import sync_playwright, Playwright, TimeoutError as PlaywrightTimeoutError
from xvfbwrapper import Xvfb

# --- Configuration ---
# This table outlines the key parameters for configuring the script's behavior.
# Modifying these values allows for easy adaptation to different targets or requirements.
# For more details on each parameter, refer to the configuration table in the report.
TARGET_URL = "https://www.idealista.com"
OUTPUT_FILE = "cookie.txt"
# This User-Agent corresponds to a recent version of Chrome on Linux (X11),
# which is consistent with our Ubuntu Server + Xvfb environment.
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080
LOAD_TIMEOUT = 30000  # 30 seconds

def extract_datadome_cookie(playwright: Playwright) -> bool:
    """
    Main logic for launching the browser, navigating, and extracting the cookie.
    """
    print("Launching Chromium in headed mode within the virtual display...")

    # We launch in headed mode (headless=False). Playwright automatically detects
    # the DISPLAY environment variable set by xvfbwrapper and uses the virtual display.
    # This is the core of the strategy to defeat rendering-based fingerprinting.
    browser = playwright.chromium.launch(headless=False)

    # Create a new browser context with a realistic viewport and user agent.
    # Consistency between the User-Agent and the actual environment is key.
    context = browser.new_context(
        user_agent=USER_AGENT,
        viewport={'width': VIEWPORT_WIDTH, 'height': VIEWPORT_HEIGHT}
    )

    page = context.new_page()

    try:
        print(f"Navigating to {TARGET_URL}...")
        # Navigate to the target page. The timeout is set to allow sufficient time
        # for all scripts, including DataDome's JS challenges, to execute.
        page.goto(TARGET_URL, timeout=LOAD_TIMEOUT, wait_until='networkidle')

        print("Page loaded. Waiting for DataDome script to execute and set cookie...")
        # A small explicit wait can sometimes help ensure all async JS has completed.
        # DataDome's cookie is often set after a series of checks.
        page.wait_for_timeout(5000)

        print("Retrieving cookies from the browser context...")
        cookies = context.cookies()

        # Find the 'datadome' cookie from the list of all cookies.
        datadome_cookie = next((cookie for cookie in cookies if cookie['name'] == 'datadome'), None)

        if not datadome_cookie:
            print("Error: 'datadome' cookie not found. The site may have presented a CAPTCHA or blocked the request.")
            # Taking a screenshot can be useful for debugging in case of failure.
            screenshot_path = "debug_screenshot_failure.png"
            page.screenshot(path=screenshot_path)
            print(f"A debug screenshot has been saved to: {screenshot_path}")
            return False

        print("'datadome' cookie found successfully.")

        # Extract the value and format the string as "datadome=VALUE".
        cookie_value = datadome_cookie.get('value', '')
        formatted_cookie_string = f"datadome={cookie_value}"

        # Save the specifically formatted cookie to the output file.
        with open(OUTPUT_FILE, 'w') as f:
            f.write(formatted_cookie_string)

        print(f"The 'datadome' cookie has been exported to '{OUTPUT_FILE}'.")
        return True

    except PlaywrightTimeoutError:
        print(f"Error: Navigation timed out after {LOAD_TIMEOUT / 1000} seconds.")
        print("This could be due to a network issue or the page being blocked.")
        screenshot_path = "debug_screenshot_timeout.png"
        page.screenshot(path=screenshot_path)
        print(f"A debug screenshot has been saved to: {screenshot_path}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        screenshot_path = "debug_screenshot_error.png"
        page.screenshot(path=screenshot_path)
        print(f"A debug screenshot has been saved to: {screenshot_path}")
        return False
    finally:
        print("Cleaning up: closing browser context and browser.")
        context.close()
        browser.close()

if __name__ == "__main__":
    # The Xvfb() context manager ensures the virtual display is started before
    # any browser operations and is cleanly stopped afterward, even if errors occur.
    print("Starting X Virtual Framebuffer (Xvfb)...")
    with Xvfb(width=VIEWPORT_WIDTH, height=VIEWPORT_HEIGHT) as xvfb:
        print("Xvfb started successfully. Display is on:", os.environ.get('DISPLAY'))
        with sync_playwright() as playwright:
            success = extract_datadome_cookie(playwright)
            if success:
                print("\nProcess completed successfully.")
            else:
                print("\nProcess failed. Please check the logs and debug screenshot.")
    print("Xvfb stopped.")
