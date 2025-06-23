import httpx
import json
import time
import datetime
from patchright.sync_api import sync_playwright


# ==============================================================================
#  STEP 1: GET HEADERS (Unchanged)
# ==============================================================================
def get_stealth_headers_from_challenge():
    """
    Launches a robustly configured browser, asks the user to solve a security
    challenge, and then captures the complete, authentic headers.
    """
    print("🚀 STEP 1: Launching stealth browser to generate authentic headers...")

    launch_args = [
        "--disable-blink-features=AutomationControlled",
        "--no-first-run",
        "--no-service-autorun",
        "--password-store=basic",
        "--start-maximized",
    ]

    context = None
    try:
        context = (
            sync_playwright()
            .start()
            .chromium.launch_persistent_context(
                user_data_dir="./chrome_session",
                headless=False,
                channel="chrome",
                args=launch_args,
                no_viewport=True,
            )
        )
        page = context.new_page()
        page.goto("https://www.idealista.com/inmueble/94726991/", timeout=60000)

        print("\n--- ACTION REQUIRED ---")
        print("Solve the security challenge in the browser to proceed...")

        for _ in range(180):
            if any(cookie["name"] == "datadome" for cookie in context.cookies()):
                print("\n✅ Datadome challenge solved successfully!")
                break
            time.sleep(1)
        else:
            raise RuntimeError("Timed out waiting for Datadome cookie.")

        print("Capturing headers from an authenticated request...")
        captured_headers = {}

        def capture_request_headers(request):
            if request.is_navigation_request() and request.resource_type == "document":
                captured_headers.update(request.headers)

        page.on("request", capture_request_headers)
        page.reload(wait_until="networkidle")

        if not captured_headers:
            raise RuntimeError("Failed to capture headers on the second request.")

        all_cookies = context.cookies()
        captured_headers["cookie"] = "; ".join(
            [f"{c['name']}={c['value']}" for c in all_cookies]
        )
        headers_to_remove = ["host", "connection", "content-length"]
        for h in headers_to_remove:
            captured_headers.pop(h, None)

        print("✅ Headers captured.")
        return captured_headers
    finally:
        if context:
            context.close()


# ==============================================================================
#  STEP 2: TEST FINGERPRINT (Now returns data for the report)
# ==============================================================================
def test_request_fingerprint(headers):
    """
    Sends the captured headers to a fingerprinting service and returns the
    analysis data and a verdict.
    """
    test_url = "https://tls.browserleaks.com/json"
    print(f"\n📡 STEP 2: Testing request fingerprint against: {test_url}")

    try:
        with httpx.Client(
            headers=headers, http2=True, follow_redirects=True, timeout=20
        ) as client:
            response = client.get(test_url)
            if response.status_code == 200:
                fingerprint_data = response.json()
                print("✅ Analysis successful.")

                # Determine the verdict based on the JA3 string
                ja3_text = fingerprint_data.get("ja3")
                if (
                    ja3_text and "101:" in ja3_text
                ):  # Rough check for Chrome's GREASE mechanism
                    verdict = "Potentially Browser-like: The JA3 fingerprint contains GREASE values, mimicking a real browser."
                else:
                    verdict = "Likely Automated: The JA3 fingerprint does not resemble a standard Chrome browser."

                return fingerprint_data, verdict
            else:
                print(f"❌ Test failed. Status code: {response.status_code}")
                return None, "Test Failed: Received a non-200 status code."
    except Exception as e:
        print(f"❌ An error occurred during the httpx request: {e}")
        return None, f"Test Error: {e}"


# ==============================================================================
#  STEP 3: GENERATE REPORT (New Function)
# ==============================================================================
def generate_report(headers, fingerprint_data, verdict):
    """
    Formats the collected data into a report and saves it to a text file.
    """
    print("\n📄 STEP 3: Generating results report...")

    # Safely get key data for the report
    user_agent = headers.get("user-agent", "Not found")
    ja3_hash = fingerprint_data.get("ja3_hash", "N/A")
    ja3_string = fingerprint_data.get("ja3", "N/A")
    http2_fp = fingerprint_data.get("http2_fp", "N/A")

    report_content = f"""
# ==================================================
#  HTTPX Request Fingerprint Analysis Report
# ==================================================
#
#  Date & Time: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
#  Test Endpoint: https://tls.browserleaks.com/json
#
# --------------------------------------------------
#  1. SESSION CONTEXT
# --------------------------------------------------
#
#  User-Agent Sent: {user_agent}
#  Datadome Cookie: {"Obtained and sent successfully." if "datadome" in headers.get('cookie', '') else "Not found."}
#  Total Headers Sent: {len(headers)}
#
# --------------------------------------------------
#  2. FINGERPRINT ANALYSIS
# --------------------------------------------------
#
#  TLS (JA3) Hash: {ja3_hash}
#  HTTP/2 Fingerprint: {http2_fp}
#
#  Full JA3 String: {ja3_string}
#
# --------------------------------------------------
#  3. CONCLUSION
# --------------------------------------------------
#
#  Verdict: {verdict}
#
#  Explanation: This verdict is based on the JA3 fingerprint, which analyzes
#  the TLS handshake of the HTTP client (`httpx`). A mismatch between this
#  fingerprint and that of a real web browser is a primary detection vector
#  for advanced Web Application Firewalls (WAFs).
#
# ==================================================
"""
    try:
        with open("fingerprint_report.txt", "w", encoding="utf-8") as f:
            f.write(report_content.strip())
        print("✅ Report saved successfully to 'fingerprint_report.txt'")
        print(headers)
    except Exception as e:
        print(f"❌ Failed to save report: {e}")


if __name__ == "__main__":
    try:
        # Step 1: Get headers from a real browser session
        stealth_headers = get_stealth_headers_from_challenge()

        # Step 2: Use those headers in a test that analyzes the httpx client itself
        fingerprint_data, verdict = test_request_fingerprint(stealth_headers)

        # Step 3: Generate and save the final report
        if fingerprint_data:
            generate_report(stealth_headers, fingerprint_data, verdict)
        else:
            print("\nCould not generate a report because the fingerprint test failed.")

    except (RuntimeError, Exception) as e:
        print(f"\nProcess failed: {e}")
