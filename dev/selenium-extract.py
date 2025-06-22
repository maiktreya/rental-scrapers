#!/usr/bin/env python3
"""
Optimized DataDome Cookie Extractor for Idealista
Based on your successful Selenium test results
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import json
import os
import sys

class OptimizedDataDomeExtractor:
    def __init__(self, user_data_dir=None, bot_profile_path=None):
        self.user_data_dir = user_data_dir or os.path.expanduser("~/idealista_session")
        self.bot_profile_path = bot_profile_path or "/home/other/Downloads/BotBrowser-main/profiles/v137/chrome137_win10_x64.enc"
        self.driver = None

    def setup_driver(self, headless=True):
        """Setup Chrome driver with optimized configuration"""
        chrome_options = Options()

        # Your working configuration
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument(f"--user-data-dir={self.user_data_dir}")
        chrome_options.add_argument(f"--bot-profile={self.bot_profile_path}")

        # Headless mode (set to False if you want to see the browser)
        if headless:
            chrome_options.add_argument("--headless=new")

        # Additional optimization
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-first-run")

        self.driver = webdriver.Chrome(options=chrome_options)

        # Remove webdriver property
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def extract_datadome_cookie(self, url="https://www.idealista.com", wait_time=20):
        """Extract DataDome cookie - main method"""
        try:
            if not self.driver:
                self.setup_driver()

            print(f"🌐 Navigating to {url}...")
            self.driver.get(url)

            print(f"⏳ Waiting {wait_time} seconds for DataDome to initialize...")
            time.sleep(wait_time)

            # Get all cookies
            all_cookies = self.driver.get_cookies()

            # Find DataDome cookie
            datadome_cookie = None
            for cookie in all_cookies:
                if cookie['name'].lower() == 'datadome':
                    datadome_cookie = cookie
                    break

            if datadome_cookie:
                print(f"✅ DataDome cookie found!")
                print(f"   Value: {datadome_cookie['value'][:50]}...")
                print(f"   Domain: {datadome_cookie['domain']}")
                print(f"   Full length: {len(datadome_cookie['value'])} characters")
                return datadome_cookie
            else:
                print("❌ DataDome cookie not found")
                return None

        except Exception as e:
            print(f"❌ Error during extraction: {e}")
            return None
        finally:
            if self.driver:
                self.driver.quit()

    def get_cookie_for_requests(self, cookie_data):
        """Format cookie for Python requests library"""
        if not cookie_data:
            return {}
        return {cookie_data['name']: cookie_data['value']}

    def get_cookie_for_curl(self, cookie_data):
        """Format cookie for curl command"""
        if not cookie_data:
            return ""
        return f"--cookie \"{cookie_data['name']}={cookie_data['value']}\""

    def get_cookie_header(self, cookie_data):
        """Format cookie as HTTP header"""
        if not cookie_data:
            return {}
        return {"Cookie": f"{cookie_data['name']}={cookie_data['value']}"}

    def save_cookie_to_file(self, cookie_data, filename="datadome_cookie.json"):
        """Save cookie to JSON file"""
        if not cookie_data:
            print("❌ No cookie data to save")
            return False

        with open(filename, 'w') as f:
            json.dump(cookie_data, f, indent=2)
        print(f"💾 Cookie saved to {filename}")
        return True

    def quick_extract(self, url="https://www.idealista.com", wait_time=20, save_to_file=True):
        """Quick extraction with all formats"""
        print("🚀 Starting DataDome cookie extraction...")

        cookie_data = self.extract_datadome_cookie(url, wait_time)

        if not cookie_data:
            return None

        # Prepare all formats
        result = {
            'raw_cookie': cookie_data,
            'formats': {
                'requests': self.get_cookie_for_requests(cookie_data),
                'curl': self.get_cookie_for_curl(cookie_data),
                'header': self.get_cookie_header(cookie_data)
            }
        }

        # Display results
        print("\n" + "="*50)
        print("📋 EXTRACTION RESULTS")
        print("="*50)

        print(f"\n🍪 DataDome Cookie:")
        print(f"   Name: {cookie_data['name']}")
        print(f"   Value: {cookie_data['value']}")
        print(f"   Domain: {cookie_data['domain']}")
        print(f"   Path: {cookie_data['path']}")
        print(f"   Secure: {cookie_data['secure']}")
        print(f"   HttpOnly: {cookie_data['httpOnly']}")

        print(f"\n🐍 For Python requests:")
        print(f"   cookies = {result['formats']['requests']}")

        print(f"\n🌐 For curl:")
        print(f"   {result['formats']['curl']}")

        print(f"\n📡 For HTTP headers:")
        print(f"   headers = {result['formats']['header']}")

        # Save to file
        if save_to_file:
            self.save_cookie_to_file(cookie_data)

        return result

def main():
    """Main function for command line usage"""
    import argparse

    parser = argparse.ArgumentParser(description='Extract DataDome cookies from Idealista')
    parser.add_argument('--url', default='https://www.idealista.com', help='URL to extract cookies from')
    parser.add_argument('--wait', type=int, default=20, help='Wait time for DataDome initialization (seconds)')
    parser.add_argument('--user-data-dir', help='Chrome user data directory')
    parser.add_argument('--bot-profile', help='Bot profile path')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--no-save', action='store_true', help='Don\'t save cookie to file')

    args = parser.parse_args()

    # Create extractor
    extractor = OptimizedDataDomeExtractor(args.user_data_dir, args.bot_profile)

    # Run extraction
    try:
        result = extractor.quick_extract(
            url=args.url,
            wait_time=args.wait,
            save_to_file=not args.no_save
        )

        if result:
            print("\n✅ Extraction completed successfully!")
            return 0
        else:
            print("\n❌ Extraction failed!")
            return 1

    except KeyboardInterrupt:
        print("\n⚠️  Extraction interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    # You can run this script directly or import it as a module

    # Direct usage example:
    if len(sys.argv) == 1:  # No command line arguments
        print("🔧 Running with default configuration...")
        extractor = OptimizedDataDomeExtractor()
        result = extractor.quick_extract()
    else:
        # Command line usage
        exit(main())