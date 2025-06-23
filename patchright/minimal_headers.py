from patchright.sync_api import sync_playwright
import json
import time

def capture_patchright_headers():
    """Capture EXACT headers used by Patchright including DataDome cookie"""
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir="./chrome_exact",
            channel="chrome",
            headless=True,
            no_viewport=True,
            args=["--disable-blink-features=AutomationControlled"]
        )

        page = browser.new_page()
        captured_headers = {}

        # Capture the EXACT request headers
        def record_headers(request):
            if "www.idealista.com" in request.url:
                captured_headers.clear()
                captured_headers.update(dict(request.headers))

        page.on("request", record_headers)
        page.goto("https://www.idealista.com", wait_until="networkidle")
        time.sleep(1)  # Ensure final headers are captured

        # Get the DataDome cookie separately
        datadome_cookie = next(
            (c for c in browser.cookies() if c["name"] == "datadome"),
            None
        )

        browser.close()
        return captured_headers, datadome_cookie["value"] if datadome_cookie else None

if __name__ == "__main__":
    # Save exact headers for inspection
    headers, cookie = capture_patchright_headers()
    with open("exact_headers.json", "w") as f:
        result = json.dump({
            "headers": dict(headers),
            "datadome_cookie": cookie
        }, f, indent=2)

    # Test the request
    print(result)