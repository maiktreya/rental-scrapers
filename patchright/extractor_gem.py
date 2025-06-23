import time
from patchright.sync_api import sync_playwright, Playwright

def run(playwright: Playwright):
    """
    Launches a browser, navigates to Idealista, and extracts the Datadome cookie
    after the user solves the security challenge.
    """
    # According to the patchright documentation, using a persistent context
    # with the regular Chrome channel is the most undetectable setup.
    # A persistent context also helps in managing cookies and sessions like a real browser.
    # Replace "USER_DATA_DIR" with a path to a directory where you want to store browser data.
    context = playwright.chromium.launch_persistent_context(
        "USER_DATA_DIR",  # This creates a persistent session
        headless=False, # Better to avoid detectability, run in headful mode
        channel="chrome",  # Use the installed Chrome browser
        args=[
            '--no-first-run',
            '--no-service-autorun',
            '--password-store=basic',
            '--disable-features=IsolateOrigins,site-per-process' # Disabling site isolation might help in some cases
        ],
        no_viewport=True, # Use the browser's default viewport
    )

    page = context.new_page()

    print("Navigating to https://www.idealista.com/...")

    try:
        # Go to the website. Datadome will likely intercept this request.
        page.goto("https://www.idealista.com/inmueble/94726991/", timeout=60000)

        print("\n--- ACTION REQUIRED ---")
        print("The browser has opened. Please solve the Datadome challenge (e.g., click and hold the button).")
        print("The script will wait for you to complete it...")

        # We will wait until the datadome cookie is present.
        # This is a robust way to wait for the challenge to be solved.
        # We'll check every second for up to 2 minutes.
        datadome_cookie = None
        for _ in range(120):
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
        time.sleep(10)
        context.close()


# --- Main execution block ---
with sync_playwright() as playwright:
    run(playwright)
