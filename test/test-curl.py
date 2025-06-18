# Your scraper using the curl-impersonate approach
import httpx
import os

def load_cookie_and_headers():
    """Load cookie and create Firefox 117 headers"""
    COOKIE_FILE = 'cookie.txt'

    try:
        with open(COOKIE_FILE, 'r') as f:
            cookie = f.read().strip()

        # Use the exact same headers as curl_ff117 (Firefox 117)
        headers = {
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.5",
            "accept-encoding": "gzip, deflate, br",
            "cookie": cookie
        }

        return headers

    except FileNotFoundError:
        print("Cookie file not found. Run renew_cookie.py first.")
        return None
    except Exception as e:
        print(f"Error loading cookie: {e}")
        return None

def scrape_with_fresh_cookie():
    """Scrape using the fresh cookie"""
    headers = load_cookie_and_headers()
    if not headers:
        return None

    try:
        with httpx.Client(headers=headers, timeout=30.0) as client:
            response = client.get('https://www.idealista.com/inmueble/108387485/')

            print(f"Status code: {response.status_code}")

            if response.status_code == 200:
                print("Success! Page content retrieved.")
                return response.text
            elif response.status_code == 403:
                print("403 Forbidden - Cookie may be stale, try renewing")
                return None
            else:
                print(f"Unexpected status code: {response.status_code}")
                return None

    except Exception as e:
        print(f"Request failed: {e}")
        return None

# Example usage
if __name__ == '__main__':
    content = scrape_with_fresh_cookie()
    if content:
        print(f"Retrieved {len(content)} characters of content")
    else:
        print("Failed to retrieve content")
        print(load_cookie_and_headers())