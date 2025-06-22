import asyncio
import os
import tempfile
# Option 1: Standard Playwright
# from playwright.async_api import async_playwright

# Option 2: Rebrowser Playwright (drop-in replacement with anti-detection patches)
from rebrowser_playwright.async_api import async_playwright

# Configuration
BOTBROWSER_EXEC_PATH =  "/usr/bin/chromium-browser"  # Update this path
BOT_PROFILE_PATH = "/home/other/Downloads/BotBrowser-main/profiles/v137/chrome137_win10_x64.enc"  # Update this path

async def main():
    async with async_playwright() as p:
        # Launch BotBrowser with stealth profile
        browser = await p.chromium.launch(
            headless=True,  # Set to False for visible browser
            executable_path=BOTBROWSER_EXEC_PATH,
            args=[
                f"--bot-profile={BOT_PROFILE_PATH}",
                "--no-sandbox",  # Recommended for stability
                f"--user-data-dir={tempfile.mkdtemp()}"  # Unique temp directory
            ]
        )

        # Create a new page
        page = await browser.new_page()

        # Remove Playwright's bindings to avoid detection
        await page.add_init_script("""
            () => {
                delete window.__playwright__;
                delete window.__pwInitScripts;
            }
        """)

        try:
            # Navigate to test page
            print("Navigating to creepjs test...")
            await page.goto("https://abrahamjuliot.github.io/creepjs/")

            # Wait for page to load
            await page.wait_for_load_state("networkidle")

            # Take a screenshot (optional)
            await page.screenshot(path="creepjs_test.png")
            print("Screenshot saved as creepjs_test.png")

            # Get page title
            title = await page.title()
            print(f"Page title: {title}")

            # You can add more interactions here
            # For example, checking specific elements or running tests

        except Exception as e:
            print(f"Error occurred: {e}")

        finally:
            # Clean up
            await browser.close()

# Additional example functions for different use cases
async def test_multiple_sites():
    """Test multiple websites with the same browser instance"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path=BOTBROWSER_EXEC_PATH,
            args=[
                f"--bot-profile={BOT_PROFILE_PATH}",
                "--no-sandbox",
                f"--user-data-dir={tempfile.mkdtemp()}"
            ]
        )

        # Test sites
        test_urls = [
            "https://abrahamjuliot.github.io/creepjs/",
            "https://iphey.com/",
            "https://pixelscan.net/"
        ]

        for url in test_urls:
            page = await browser.new_page()

            # Remove detection bindings
            await page.add_init_script("""
                () => {
                    delete window.__playwright__;
                    delete window.__pwInitScripts;
                }
            """)

            try:
                print(f"Testing: {url}")
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state("networkidle")

                title = await page.title()
                print(f"✅ {title}")

            except Exception as e:
                print(f"❌ Error with {url}: {e}")

            finally:
                await page.close()

        await browser.close()

async def stealth_form_interaction():
    """Example of interacting with forms in stealth mode"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Visible for demonstration
            executable_path=BOTBROWSER_EXEC_PATH,
            args=[
                f"--bot-profile={BOT_PROFILE_PATH}",
                "--no-sandbox",
                f"--user-data-dir={tempfile.mkdtemp()}"
            ]
        )

        page = await browser.new_page()

        # Stealth setup
        await page.add_init_script("""
            () => {
                delete window.__playwright__;
                delete window.__pwInitScripts;
            }
        """)

        try:
            # Example: Navigate to a form page
            await page.goto("https://httpbin.org/forms/post")

            # Fill form with human-like delays
            await page.fill('input[name="custname"]', "John Doe")
            await page.wait_for_timeout(1000)  # Human-like delay

            await page.fill('input[name="custtel"]', "123-456-7890")
            await page.wait_for_timeout(500)

            await page.fill('input[name="custemail"]', "john@example.com")
            await page.wait_for_timeout(800)

            # Select options
            await page.select_option('select[name="size"]', "medium")
            await page.wait_for_timeout(300)

            # Submit form (commented out to avoid actual submission)
            # await page.click('input[type="submit"]')

            print("Form interaction completed successfully")

        except Exception as e:
            print(f"Error in form interaction: {e}")

        finally:
            await browser.close()

# Configuration helper function
def setup_paths():
    """Helper function to set up paths based on OS"""
    import platform

    system = platform.system()

    if system == "Windows":
        return {
            "executable": "C:\\path\\to\\botbrowser\\chrome.exe",
            "profile": "C:\\path\\to\\profiles\\chrome136_win11_x64.enc"
        }
    elif system == "Darwin":  # macOS
        return {
            "executable": "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "profile": "/path/to/profiles/chrome136_win11_x64.enc"
        }
    else:  # Linux/Ubuntu
        return {
            "executable": "/usr/bin/chromium-browser",
            "profile": "/path/to/profiles/chrome136_win11_x64.enc"
        }

if __name__ == "__main__":
    # Install rebrowser-playwright instead of standard playwright:
    # pip install rebrowser-playwright
    # rebrowser-playwright install chromium

    # Update paths before running
    print("BotBrowser + Rebrowser-Playwright Python Example")
    print("This combines BotBrowser's stealth profiles with Rebrowser's anti-detection patches")
    print("Make sure to update BOTBROWSER_EXEC_PATH and BOT_PROFILE_PATH")
    print("=" * 70)

    # Run the main example
    asyncio.run(main())

    # Uncomment to run other examples:
    # asyncio.run(test_multiple_sites())
    # asyncio.run(stealth_form_interaction())