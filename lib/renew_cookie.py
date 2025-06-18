# lib/renew_cookie.py - Minimalist approach with curl-impersonate
import subprocess
import re
import os
import time

# Simple file paths
COOKIE_FILE = 'cookie.txt'
USER_AGENT_FILE = 'user_agent.txt'
HEADERS_FILE = 'headers.txt'
TIMESTAMP_FILE = 'cookie_timestamp.txt'

def get_fresh_cookie_with_curl():
    """Get fresh cookie using curl-impersonate (Firefox 117)"""
    try:
        # Use curl_ff117 to get headers and response
        cmd = [
            'curl_ff117',
            '-s',  # Silent
            '-D', '-',  # Dump headers to stdout
            '-o', '/dev/null',  # Discard body
            'https://www.idealista.com/inmueble/108387485/'
        ]

        print("Running curl_ff117 to get fresh cookie...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            print(f"curl_ff117 failed with return code {result.returncode}")
            print(f"stderr: {result.stderr}")
            return None, None

        headers_text = result.stdout

        # Save headers for debugging
        with open(HEADERS_FILE, 'w') as f:
            f.write(headers_text)

        # Extract datadome cookie
        cookie_match = re.search(r'set-cookie:\s*datadome=([^;]+)', headers_text, re.IGNORECASE)
        if not cookie_match:
            print("No datadome cookie found in response headers")
            print("Headers received:")
            print(headers_text)
            return None, None

        datadome_value = cookie_match.group(1)
        full_cookie = f"datadome={datadome_value}"

        # Get the user agent that curl_ff117 uses (Firefox 117 UA)
        user_agent = "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0"

        print(f"Extracted cookie: {full_cookie[:50]}...")
        print(f"Using Firefox 117 User-Agent")

        return full_cookie, user_agent

    except subprocess.TimeoutExpired:
        print("curl_ff117 timed out")
        return None, None
    except FileNotFoundError:
        print("curl_ff117 not found. Please install curl-impersonate:")
        print("https://github.com/lwthiker/curl-impersonate")
        return None, None
    except Exception as e:
        print(f"Error running curl_ff117: {e}")
        return None, None

def validate_cookie_with_curl(cookie_str, user_agent):
    """Validate cookie using curl-impersonate"""
    try:
        cmd = [
            'curl_ff117',
            '-s',
            '-o', '/dev/null',
            '-w', '%{http_code}',
            '-H', f'Cookie: {cookie_str}',
            'https://www.idealista.com/inmueble/108387485/'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

        if result.returncode == 0:
            status_code = result.stdout.strip()
            return status_code == '200'

        return False

    except Exception as e:
        print(f"Cookie validation failed: {e}")
        return False

def is_cookie_fresh(max_age_hours=1):
    """Check if cookie is fresh (shorter window for more reliability)"""
    try:
        if not os.path.exists(TIMESTAMP_FILE):
            return False

        with open(TIMESTAMP_FILE, 'r') as f:
            timestamp = float(f.read().strip())
        age_hours = (time.time() - timestamp) / 3600
        return age_hours < max_age_hours
    except:
        return False

def get_headers_for_httpx():
    """Extract the exact headers that curl_ff117 would send"""
    # These are the headers that Firefox 117 sends
    return {
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "accept-language": "en-US,en;q=0.5",
        "accept-encoding": "gzip, deflate, br",
        "dnt": "1",
        "connection": "keep-alive",
        "upgrade-insecure-requests": "1",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "te": "trailers"
    }

def renew_if_needed():
    """Only renew if needed"""
    # Check if existing cookie is still valid
    if (is_cookie_fresh() and
        os.path.exists(COOKIE_FILE) and
        os.path.exists(USER_AGENT_FILE)):

        try:
            with open(COOKIE_FILE, 'r') as f:
                cookie = f.read().strip()
            with open(USER_AGENT_FILE, 'r') as f:
                user_agent = f.read().strip()

            if validate_cookie_with_curl(cookie, user_agent):
                print("Existing cookie is still valid")
                return cookie, user_agent
        except:
            pass

    print("Getting fresh cookie with curl_ff117...")
    return get_fresh_cookie_with_curl()

if __name__ == '__main__':
    print("Checking cookie status...")
    cookie_str, ua_str = renew_if_needed()

    if cookie_str and ua_str:
        try:
            with open(COOKIE_FILE, 'w') as f:
                f.write(cookie_str)
            with open(USER_AGENT_FILE, 'w') as f:
                f.write(ua_str)
            with open(TIMESTAMP_FILE, 'w') as f:
                f.write(str(time.time()))

            print("Cookie and user agent saved successfully!")
            print(f"Cookie: {cookie_str[:50]}...")

            # Show the headers to use in your scraper
            print("\nUse these headers in your HTTPX scraper:")
            headers = get_headers_for_httpx()
            headers["cookie"] = cookie_str

            for key, value in headers.items():
                print(f'    "{key}": "{value}",')

        except Exception as e:
            print(f"Error saving files: {e}")
    else:
        print("Failed to get valid cookie.")