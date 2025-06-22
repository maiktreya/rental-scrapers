import asyncio
from rebrowser_playwright.async_api import async_playwright
import re

# The target URL for Idealista
TARGET_URL = "https://www.idealista.com/"

async def get_datadome_cookie():
    """
    Launches a rebrowser instance, navigates to Idealista, and extracts
    the Datadome cookie after passing the anti-bot checks.

    Returns:
        str: The value of the Datadome cookie, or None if not found.
    """
    async with async_playwright() as p:
        print("▶️  Launching patched browser...")
        # We launch a patched version of Chromium. rebrowser modifies the browser
        # executable and its configuration to hide common automation flags.
        browser = await p.chromium.launch(headless=False) # Headless can sometimes be detected, so starting with False is safer.

        # Create a new browser context. This is like a separate browser profile.
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print(f"🌍 Navigating to {TARGET_URL}...")

        try:
            # Go to the target URL. rebrowser will handle the low-level
            # modifications to make the request seem like it's from a real user.
            # Datadome's JavaScript challenge will run in the background.
            await page.goto(TARGET_URL, timeout=60000, wait_until='domcontentloaded')

            print("⏳ Waiting for the page to load and for Datadome challenge to complete...")

            # To ensure the Datadome challenge is passed, we wait for a specific
            # element that only appears on the main content page.
            # '.item-info-container' is a selector for the property listings.
            # If this element appears, it means we have successfully bypassed the block.
            await page.wait_for_selector('div.item-info-container', timeout=30000)

            print("✅ Successfully loaded the page.")

            # Retrieve all cookies from the current context.
            cookies = await context.cookies()

            # Find the 'datadome' cookie from the list of cookies.
            datadome_cookie = next((cookie['value'] for cookie in cookies if cookie['name'] == 'datadome'), None)

            if datadome_cookie:
                print("\n🍪 Found Datadome Cookie!")
                return datadome_cookie
            else:
                print("\n❌ Datadome cookie not found. The anti-bot page might have appeared.")
                # You can uncomment the line below to take a screenshot for debugging
                # await page.screenshot(path='debug_screenshot.png')
                return None

        except Exception as e:
            print(f"An error occurred: {e}")
            # Taking a screenshot helps diagnose if we are stuck on a captcha.
            await page.screenshot(path='error_screenshot.png')
            return None
        finally:
            print("▶️  Closing browser...")
            await browser.close()

async def main():
    """Main function to run the script."""
    print("🚀 Starting Datadome cookie extraction process...")

    cookie = await get_datadome_cookie()

    if cookie:
        print("==================================================")
        print(f"Datadome Cookie: {cookie}")
        print("==================================================")
    else:
        print("Could not retrieve the cookie. Check the screenshots (error_screenshot.png or debug_screenshot.png) for more details.")


if __name__ == "__main__":
    # Ensure you have installed the necessary components:
    # 1. pip install rebrowser-playwright
    # 2. python -m rebrowser_playwright install
    asyncio.run(main())
