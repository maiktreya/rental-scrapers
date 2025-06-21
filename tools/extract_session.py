# This is your adapted script to extract DataDome cookie
# Let's call it: tools/extract_datadome_cookie.py

import os
import json
from rebrowser_playwright.sync_api import sync_playwright

# --- Configuration ---
# Let's target a specific search results page now
TARGET_URL = "https://www.idealista.com/venta-viviendas/madrid-madrid/"
COOKIE_NAME = "datadome"
# This will be the file containing the extracted cookie data
OUTPUT_FILE = "datadome_cookie.json"

def extract_datadome_cookie():
    """
    Launches a stealth browser, authenticates past DataDome, and then
    extracts the DataDome cookie from the authenticated page.
    """
    with sync_playwright() as p:
        print("--- STEP 1: AUTHENTICATING ---")
        print("Launching patched browser...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        try:
            print(f"Navigating to {TARGET_URL}...")
            page.goto(TARGET_URL, timeout=90000, wait_until="domcontentloaded")

            print("Waiting for the DataDome cookie to be set...")
            page.wait_for_function(
                f"() => document.cookie.includes('{COOKIE_NAME}=')",
                timeout=45000
            )
            print("Authentication successful. The DataDome cookie is now available.")

            # --- STEP 2: EXTRACTING COOKIE AND HEADERS ---
            print("Extracting DataDome cookie and request headers...")

            # Get the user agent and other headers used by the browser
            user_agent = page.evaluate('navigator.userAgent')

            # Get additional browser/request info
            browser_info = {
                'user_agent': user_agent,
                'language': page.evaluate('navigator.language'),
                'platform': page.evaluate('navigator.platform'),
                'viewport': page.viewport_size,
                'cookies_enabled': page.evaluate('navigator.cookieEnabled'),
                'do_not_track': page.evaluate('navigator.doNotTrack'),
                'hardware_concurrency': page.evaluate('navigator.hardwareConcurrency'),
                'max_touch_points': page.evaluate('navigator.maxTouchPoints')
            }

            # Get all cookies from the page context
            cookies = context.cookies()

            # Find the DataDome cookie
            datadome_cookie = None
            for cookie in cookies:
                if cookie['name'] == COOKIE_NAME:
                    datadome_cookie = cookie
                    break

            if datadome_cookie:
                print(f"DataDome cookie found!")
                print(f"Cookie value: {datadome_cookie['value'][:50]}..." if len(datadome_cookie['value']) > 50 else f"Cookie value: {datadome_cookie['value']}")

                # Prepare comprehensive data for export
                extracted_data = {
                    # Cookie information
                    'cookie': {
                        'name': datadome_cookie['name'],
                        'value': datadome_cookie['value'],
                        'domain': datadome_cookie['domain'],
                        'path': datadome_cookie['path'],
                        'expires': datadome_cookie.get('expires', None),
                        'httpOnly': datadome_cookie.get('httpOnly', False),
                        'secure': datadome_cookie.get('secure', False),
                        'sameSite': datadome_cookie.get('sameSite', 'None')
                    },
                    # Browser/Request information
                    'headers': {
                        'User-Agent': browser_info['user_agent'],
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                        'Accept-Language': f"{browser_info['language']},en;q=0.9",
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': browser_info['do_not_track'] or '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-User': '?1',
                        'Cache-Control': 'max-age=0'
                    },
                    # Browser fingerprint information
                    'browser_info': browser_info,
                    # Metadata
                    'metadata': {
                        'extracted_from': TARGET_URL,
                        'extraction_timestamp': page.evaluate('Date.now()'),
                        'success': True
                    }
                }

                # Save comprehensive data to file
                file_path = os.path.join(os.path.dirname(__file__), OUTPUT_FILE)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(extracted_data, f, indent=2, ensure_ascii=False)

                print(f"Complete extraction data saved to {os.path.abspath(file_path)}")

                # Display key information
                print(f"\n=== EXTRACTED INFORMATION ===")
                print(f"User-Agent: {browser_info['user_agent']}")
                print(f"Platform: {browser_info['platform']}")
                print(f"Language: {browser_info['language']}")
                print(f"Viewport: {browser_info['viewport']}")

                # Also extract cookie as a simple string format for easy use
                cookie_string = f"{datadome_cookie['name']}={datadome_cookie['value']}"
                print(f"\nCookie string format: {cookie_string}")

                # Save cookie string to a separate file for convenience
                cookie_string_file = os.path.join(os.path.dirname(__file__), "datadome_cookie_string.txt")
                with open(cookie_string_file, 'w', encoding='utf-8') as f:
                    f.write(cookie_string)

                # Save full headers as a Python dict for easy copying
                headers_file = os.path.join(os.path.dirname(__file__), "request_headers.py")
                with open(headers_file, 'w', encoding='utf-8') as f:
                    f.write("# Complete headers for successful requests\n")
                    f.write("# Copy this dict and use it in your HTTP requests\n\n")
                    f.write(f"headers = {{\n")
                    for key, value in extracted_data['headers'].items():
                        f.write(f"    '{key}': '{value}',\n")
                    f.write(f"    'Cookie': 'datadome={datadome_cookie['value']}'\n")
                    f.write("}\n\n")
                    f.write("# Usage example:\n")
                    f.write("# import requests\n")
                    f.write(f"# response = requests.get('{TARGET_URL}', headers=headers)\n")

                return extracted_data
            else:
                print("DataDome cookie not found!")
                return None

        except Exception as e:
            print(f"An error occurred: {e}")
            page.screenshot(path='error_screenshot.png')
            return None
        finally:
            print("Closing browser.")
            browser.close()

def load_saved_data():
    """
    Load previously saved extraction data from file
    """
    file_path = os.path.join(os.path.dirname(__file__), OUTPUT_FILE)
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def show_usage_examples():
    """
    Show examples of how to use the extracted data
    """
    data = load_saved_data()
    if data:
        print(f"\n=== USAGE EXAMPLES ===")

        # Simple requests example
        print(f"\n1. Simple requests with cookie:")
        cookie_header = f"datadome={data['cookie']['value']}"
        print(f"   headers = {{'Cookie': '{cookie_header}'}}")
        print(f"   response = requests.get('{TARGET_URL}', headers=headers)")

        # Full headers example
        print(f"\n2. Full headers for maximum compatibility:")
        print(f"   headers = {{")
        for key, value in data['headers'].items():
            print(f"       '{key}': '{value}',")
        print(f"       'Cookie': 'datadome={data['cookie']['value']}'")
        print(f"   }}")
        print(f"   response = requests.get('{TARGET_URL}', headers=headers)")

        # Session-based example
        print(f"\n3. Using requests.Session:")
        print(f"   session = requests.Session()")
        print(f"   session.headers.update(headers)")
        print(f"   response = session.get('{TARGET_URL}')")

        return data
    return None

if __name__ == "__main__":
    print("=== DataDome Cookie & Headers Extractor ===\n")

    extracted_data = extract_datadome_cookie()
    if extracted_data:
        cookie = extracted_data['cookie']
        headers = extracted_data['headers']
        browser_info = extracted_data['browser_info']

        print(f"\n=== EXTRACTION SUCCESSFUL ===")
        print(f"Cookie Name: {cookie['name']}")
        print(f"Cookie Domain: {cookie['domain']}")
        print(f"Cookie Path: {cookie['path']}")
        print(f"Cookie Value Length: {len(cookie['value'])} characters")
        print(f"User-Agent: {headers['User-Agent']}")
        print(f"Browser Platform: {browser_info['platform']}")
        print(f"Browser Language: {browser_info['language']}")

        # Show usage examples
        show_usage_examples()

        print(f"\n=== FILES CREATED ===")
        print(f"- {OUTPUT_FILE} (complete extraction data)")
        print(f"- datadome_cookie_string.txt (simple cookie string)")
        print(f"- request_headers.py (ready-to-use headers dict)")
    else:
        print(f"\n=== EXTRACTION FAILED ===")
        print("Could not extract DataDome cookie and headers.")