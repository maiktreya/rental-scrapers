#!/usr/bin/env python3
import json
import subprocess
import time
import requests
import os
from urllib.parse import urlparse

class DataDomeCookieExtractor:
    def __init__(self, user_data_dir, bot_profile_path):
        self.user_data_dir = user_data_dir
        self.bot_profile_path = bot_profile_path
        self.chrome_process = None

    def launch_chrome_with_remote_debugging(self, url="https://www.idealista.com", debug_port=9222):
        """Launch Chrome with remote debugging enabled"""
        cmd = [
            "chromium-browser",
            "--no-sandbox",
            f"--user-data-dir={self.user_data_dir}",
            f"--bot-profile={self.bot_profile_path}",
            f"--remote-debugging-port={debug_port}",
            "--headless=new",  # Use new headless mode
            url
        ]

        print(f"Launching Chrome with command: {' '.join(cmd)}")
        self.chrome_process = subprocess.Popen(cmd)

        # Wait for Chrome to start
        time.sleep(3)
        return debug_port

    def get_cookies_via_cdp(self, debug_port=9222):
        """Extract cookies using Chrome DevTools Protocol"""
        try:
            # Get list of tabs
            tabs_response = requests.get(f"http://localhost:{debug_port}/json")
            tabs = tabs_response.json()

            if not tabs:
                print("No tabs found")
                return []

            # Use the first tab
            tab_id = tabs[0]['id']
            websocket_url = tabs[0]['webSocketDebuggerUrl']

            # Alternative: Use HTTP endpoints for cookies
            # Send command to get cookies
            cookies_cmd = {
                "id": 1,
                "method": "Network.getAllCookies"
            }

            # For HTTP-based approach, we'll read from the user data directory
            return self.read_cookies_from_profile()

        except Exception as e:
            print(f"Error getting cookies via CDP: {e}")
            return []

    def read_cookies_from_profile(self):
        """Read cookies directly from Chrome profile"""
        cookies_file = os.path.join(self.user_data_dir, "Default", "Cookies")

        if not os.path.exists(cookies_file):
            print(f"Cookies file not found at {cookies_file}")
            return []

        try:
            # Note: Chrome stores cookies in SQLite format
            # You'll need sqlite3 for this
            import sqlite3

            conn = sqlite3.connect(cookies_file)
            cursor = conn.cursor()

            # Query for DataDome cookies specifically
            query = """
            SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly
            FROM cookies
            WHERE name LIKE '%datadome%' OR host_key LIKE '%idealista%'
            """

            cursor.execute(query)
            cookies = cursor.fetchall()
            conn.close()

            datadome_cookies = []
            for cookie in cookies:
                cookie_dict = {
                    'name': cookie[0],
                    'value': cookie[1],
                    'domain': cookie[2],
                    'path': cookie[3],
                    'expires': cookie[4],
                    'secure': bool(cookie[5]),
                    'httpOnly': bool(cookie[6])
                }
                datadome_cookies.append(cookie_dict)

            return datadome_cookies

        except Exception as e:
            print(f"Error reading cookies from profile: {e}")
            return []

    def extract_datadome_cookies(self, wait_time=10):
        """Main method to extract DataDome cookies"""
        print("Starting DataDome cookie extraction...")

        # Launch Chrome
        debug_port = self.launch_chrome_with_remote_debugging()

        # Wait for page to load and DataDome to initialize
        print(f"Waiting {wait_time} seconds for page to load...")
        time.sleep(wait_time)

        # Extract cookies
        cookies = self.get_cookies_via_cdp(debug_port)

        # Filter DataDome specific cookies
        datadome_cookies = [
            cookie for cookie in cookies
            if 'datadome' in cookie.get('name', '').lower()
        ]

        # Cleanup
        self.cleanup()

        return datadome_cookies

    def format_cookies_for_requests(self, cookies):
        """Format cookies for use with requests library"""
        cookie_dict = {}
        for cookie in cookies:
            cookie_dict[cookie['name']] = cookie['value']
        return cookie_dict

    def format_cookies_for_curl(self, cookies):
        """Format cookies for use with curl"""
        cookie_strings = []
        for cookie in cookies:
            cookie_strings.append(f"{cookie['name']}={cookie['value']}")
        return "; ".join(cookie_strings)

    def cleanup(self):
        """Clean up Chrome process"""
        if self.chrome_process:
            self.chrome_process.terminate()
            self.chrome_process.wait()

# Usage example
if __name__ == "__main__":
    # Your paths
    user_data_dir = os.path.expanduser("~/idealista_session")
    bot_profile_path = "/home/other/Downloads/BotBrowser-main/profiles/v137/chrome137_win10_x64.enc"

    # Create extractor
    extractor = DataDomeCookieExtractor(user_data_dir, bot_profile_path)

    # Extract cookies
    cookies = extractor.extract_datadome_cookies(wait_time=15)

    if cookies:
        print(f"\nFound {len(cookies)} DataDome cookies:")
        for cookie in cookies:
            print(f"  {cookie['name']}: {cookie['value'][:50]}...")

        # Format for different uses
        print("\n--- For Python requests ---")
        requests_cookies = extractor.format_cookies_for_requests(cookies)
        print(requests_cookies)

        print("\n--- For curl ---")
        curl_cookies = extractor.format_cookies_for_curl(cookies)
        print(f'--cookie "{curl_cookies}"')

    else:
        print("No DataDome cookies found")