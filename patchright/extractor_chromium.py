from patchright.sync_api import sync_playwright
import time

def extract_datadome_cookie():
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir="/tmp/patchright-profile",  # Change path as needed
            channel="chrome",  # Must have chrome installed
            headless=False,
            no_viewport=True,
            args=[
                "--disable-blink-features=AutomationControlled"
            ]
        )
        page = browser.pages[0] if browser.pages else browser.new_page()

        # Navigate to idealista
        page.goto("https://www.idealista.com/", wait_until="networkidle")

        # Give DataDome time to evaluate browser
        time.sleep(10)

        # Extract cookies
        cookies = browser.cookies()
        datadome_cookie = next((cookie for cookie in cookies if cookie['name'] == 'datadome'), None)

        browser.close()

        if datadome_cookie:
            print("[+] Successfully extracted DataDome cookie:")
            print(datadome_cookie)
            return datadome_cookie
        else:
            print("[-] Failed to retrieve DataDome cookie.")
            return None

if __name__ == "__main__":
    extract_datadome_cookie()
