import time
from patchright.sync_api import sync_playwright, Playwright

def run(playwright: Playwright):
    """
    Launches a browser, navigates to Idealista, and extracts the Datadome cookie
    after the user solves the security challenge.
    """
    # Launch a persistent context with Chrome for stealth and session management
    # Replace "USER_DATA_DIR" with an actual path (e.g., "/path/to/user/data")
    context = playwright.chromium.launch_persistent_context(
        "USER_DATA_DIR",
        headless=False,           # Visible browser for manual interaction
        channel="chrome",         # Use installed Chrome browser
        args=[
            '--no-first-run',     # Skip first-run prompts
            '--no-service-autorun',  # Prevent service autoruns
            '--password-store=basic',  # Simplify password storage
            '--disable-features=IsolateOrigins,site-per-process'  # Reduce isolation flags
        ],
        no_viewport=True          # Use default browser viewport
    )

    page = context.new_page()

    print("Navigating to https://www.idealista.com/...")

    try:
        # Navigate to Idealista; Datadome may intercept this request
        page.goto("https://www.idealista.com/", timeout=60000)

        print("\n--- ACTION REQUIRED ---")
        print("The browser has opened. Please solve the Datadome challenge (e.g., click and hold the button).")
        print("The script will wait for you to complete it...")

        # Wait for the Datadome cookie to appear (up to 2 minutes)
        datadome_cookie = None
        for _ in range(120):  # 120 seconds = 2 minutes
            cookies = context.cookies()
            for cookie in cookies:
                if cookie['name'] == 'datadome':
                    datadome_cookie = cookie
                    break
            if datadome_cookie:
                break
            time.sleep(1)

        if datadome_cookie:
            print("\n✅ Datadome challenge solved successfully!")
            print("Datadome Cookie Found:")
            print(f"   Value: {datadome_cookie['value']}")
        else:
            print("\n❌ Timed out waiting for the Datadome cookie. Please try running the script again.")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        print("\nClosing the browser in 10 seconds...")
        time.sleep(10)  # Give time to view the result
        context.close()

# Main execution
with sync_playwright() as playwright:
    run(playwright)