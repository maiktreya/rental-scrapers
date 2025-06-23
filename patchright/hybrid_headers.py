from patchright.sync_api import sync_playwright
import httpx
import json

def get_optimized_headers():
    """Get essential headers + critical security headers"""
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir="./chrome_hybrid",
            channel="chrome",
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )

        page = browser.new_page()
        security_headers = {}
        user_agent = page.evaluate("navigator.userAgent")

        # Capture security headers only
        def capture_security_headers(request):
            if "idealista.com" in request.url:
                security_headers.update({
                    "Sec-Ch-Ua": request.headers.get("sec-ch-ua"),
                    "Sec-Ch-Ua-Mobile": request.headers.get("sec-ch-ua-mobile"),
                    "Sec-Ch-Ua-Platform": request.headers.get("sec-ch-ua-platform"),
                    "Sec-Fetch-Dest": request.headers.get("sec-fetch-dest"),
                    "Sec-Fetch-Mode": request.headers.get("sec-fetch-mode"),
                    "Sec-Fetch-Site": request.headers.get("sec-fetch-site"),
                    "Sec-Fetch-User": request.headers.get("sec-fetch-user")
                })

        page.on("request", capture_security_headers)
        page.goto("https://www.idealista.com", wait_until="networkidle")

        # Get DataDome cookie
        datadome_cookie = next(
            (c for c in browser.cookies() if c["name"] == "datadome"),
            None
        )

        browser.close()

        # Build optimized header set
        return {
            "User-Agent": user_agent,
            "Cookie": f"datadome={datadome_cookie['value']}",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            **security_headers
        }

def make_stealthy_request():
    headers = get_optimized_headers()

    with httpx.Client(
        headers=headers,
        http2=True,
        follow_redirects=True,
        timeout=30
    ) as client:
        response = client.get("https://www.idealista.com")
        return response.text

if __name__ == "__main__":
    # Save optimized headers
    headers = get_optimized_headers()
    with open("optimized_headers.json", "w") as f:
        json.dump(headers, f, indent=2)

    content = make_stealthy_request()
    print(f"Received {len(content)} bytes")