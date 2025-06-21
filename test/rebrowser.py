import os
from rebrowser_playwright.sync_api import sync_playwright, Playwright

def get_datadome_cookie():
    """
    Launches a browser using the rebrowser-playwright patched engine,
    navigates to Idealista, extracts the DataDome cookie, and saves it to a file.
    """
    with sync_playwright() as p:
        print("Launching patched browser...")
        # The 'rebrowser-playwright' installation patches the standard Playwright launch.
        # No code changes are needed here to get the benefit of the patched browser.
        browser = p.chromium.launch(headless=True)

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            print("Navigating to https://www.idealista.com...")
            # Increased timeout to allow for bot detection checks to complete.
            page.goto("https://www.idealista.com", timeout=60000)

            print("Waiting for the DataDome cookie to be set...")
            # A more reliable way to wait is to check for the cookie's presence.
            # We will loop and check for the cookie with a timeout.
            datadome_cookie = None
            for _ in range(10): # Try for 10 seconds
                cookies = context.cookies()
                datadome_cookie = next((cookie for cookie in cookies if cookie['name'] == 'datadome'), None)
                if datadome_cookie:
                    break
                page.wait_for_timeout(1000)

            if not datadome_cookie:
                print("Could not find the DataDome cookie after waiting.")
                browser.close()
                return None

            cookie_value = datadome_cookie['value']
            print(f"Successfully extracted DataDome cookie.")

            # Save the cookie to a file in the same root folder
            file_path = 'datadome_cookie.txt'
            with open(file_path, 'w') as f:
                f.write(cookie_value)

            print(f"DataDome cookie saved to {os.path.abspath(file_path)}")
            return cookie_value

        except Exception as e:
            print(f"An error occurred: {e}")
            # Save a screenshot for debugging purposes if something goes wrong
            page.screenshot(path='error_screenshot.png')
            print("Saved an error screenshot to 'error_screenshot.png'")
            return None
        finally:
            print("Closing browser.")
            browser.close()

if __name__ == "__main__":
    extracted_cookie = get_datadome_cookie()
    if extracted_cookie:
        # You can now use this cookie value in other requests
        pass