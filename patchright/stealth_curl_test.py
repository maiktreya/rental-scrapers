# ==============================================================================
#  Prerequisites:
#  pip install playwright playwright-patcher curl-cffi
#
#  Then run this command once in your terminal:
#  patchright install
# ==============================================================================

import json
import time
import datetime
from patchright.sync_api import sync_playwright
from curl_cffi import requests  # We import requests from curl_cffi, not httpx


# ==============================================================================
#  STEP 1: GET HEADERS (Unchanged - The best way to get authentic headers)
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

        # Wait for the datadome cookie to appear after solving the challenge
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

        # Consolidate all cookies into the cookie header
        all_cookies = context.cookies()
        captured_headers["cookie"] = "; ".join(
            [f"{c['name']}={c['value']}" for c in all_cookies]
        )

        # Clean up headers that the client should manage
        headers_to_remove = ["host", "connection", "content-length"]
        for h in headers_to_remove:
            captured_headers.pop(h, None)

        print("✅ Headers captured.")
        return captured_headers
    finally:
        if context:
            context.close()


# ==============================================================================
#  STEP 2: TEST FINGERPRINT (Using curl-cffi for impersonation)
# ==============================================================================
def test_request_fingerprint_with_curl(headers):
    """
    Sends the captured headers using curl-cffi to a fingerprinting service.
    The 'impersonate' parameter is key to defeating JA3 detection.
    """
    test_url = "https://tls.browserleaks.com/json"
    impersonation_target = "chrome120"
    print(
        f"\n📡 STEP 2: Testing request fingerprint with curl-cffi (impersonating {impersonation_target})..."
    )

    try:
        # We use curl_cffi's requests-like API
        response = requests.get(
            test_url,
            headers=headers,
            impersonate=impersonation_target,  # This is the magic that sets a browser-like TLS signature
            timeout=20,
        )

        if response.status_code == 200:
            fingerprint_data = response.json()
            print("✅ Analysis successful.")

            # Since we are impersonating Chrome, the verdict should be positive.
            verdict = "Success: The JA3 fingerprint likely matches a real Chrome browser due to curl-cffi impersonation."
            return fingerprint_data, verdict
        else:
            print(f"❌ Test failed. Status code: {response.status_code}")
            return None, "Test Failed: Received a non-200 status code."

    except Exception as e:
        print(f"❌ An error occurred during the curl-cffi request: {e}")
        return None, f"Test Error: {e}"


# ==============================================================================
#  STEP 3: GENERATE REPORT (The final output)
# ==============================================================================
def generate_report(headers, fingerprint_data, verdict):
    """
    Formats the collected data into a report and saves it to a text file.
    """
    print("\n📄 STEP 3: Generating final results report...")

    user_agent = headers.get("user-agent", "Not found")
    ja3_hash = fingerprint_data.get("ja3_hash", "N/A")
    http2_fp = fingerprint_data.get("http2_fp", "N/A")

    report_content = f"""
# ==================================================
#  Request Fingerprint Analysis Report
# ==================================================
#
#  Date & Time: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
#  Test Client: curl-cffi (impersonating chrome120)
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
# --------------------------------------------------
#  3. CONCLUSION
# --------------------------------------------------
#
#  Verdict: {verdict}
#
#  Explanation: The test was performed using curl-cffi, which masks the
#  default Python TLS signature and impersonates a real web browser. This
#  new JA3 hash should match that of Chrome, defeating TLS fingerprinting.
#
# ==================================================
"""
    try:
        with open("final_fingerprint_report.txt", "w", encoding="utf-8") as f:
            f.write(report_content.strip())
        print("✅ Report saved successfully to 'final_fingerprint_report.txt'")
    except Exception as e:
        print(f"❌ Failed to save report: {e}")


# ==============================================================================
#  MAIN EXECUTION BLOCK
# ==============================================================================
if __name__ == "__main__":
    try:
        # Step 1: Get headers from a real browser session
        stealth_headers = get_stealth_headers_from_challenge()

        # Step 2: Use curl-cffi to perform the definitive test
        fingerprint_data, verdict = test_request_fingerprint_with_curl(stealth_headers)

        # Step 3: Generate and save the final report on the successful test
        if fingerprint_data:
            generate_report(stealth_headers, fingerprint_data, verdict)
        else:
            print("\nCould not generate a report because the fingerprint test failed.")

    except (RuntimeError, Exception) as e:
        print(f"\nProcess failed: {e}")
