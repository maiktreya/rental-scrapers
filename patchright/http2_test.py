import httpx
from httpx_curl_cffi import CurlTransport
import datetime
import sys
import os
import json

# ==============================================================================
#  SETUP: IMPORT HEADERS FROM PARENT DIRECTORY
# ==============================================================================
# This block allows the script to find the 'base_headers.py' file.
try:
    # Assumes the script is in a subdirectory and base_headers.py is in the parent.
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
    from base_headers import BASE_HEADERS

    print("✅ Successfully imported headers from base_headers.py.")
except ImportError:
    print("❌ ERROR: 'base_headers.py' not found in the parent directory.")
    print("Please ensure the file exists and contains a BASE_HEADERS dictionary.")
    # As a fallback, create a default header set to allow the script to run.
    BASE_HEADERS = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    print(
        "⚠️  WARNING: Using a default User-Agent. For accurate tests, please create 'base_headers.py'."
    )


# ==============================================================================
#  STEP 1: TEST HTTP/2 FINGERPRINT
# ==============================================================================
def test_http2_fingerprint(headers):
    """
    Sends a request to the Scrapfly HTTP/2 fingerprinting service using
    httpx with CurlTransport for browser impersonation.
    """
    test_url = "https://tools.scrapfly.io/api/http2"
    impersonation_target = "chrome120"
    print(
        f"\n📡 STEP 1: Testing HTTP/2 fingerprint with httpx-curl-cffi (impersonating {impersonation_target})..."
    )
    print(f"   - Endpoint: {test_url}")

    try:
        # Use httpx.Client with the special CurlTransport to impersonate Chrome
        transport = CurlTransport(impersonate=impersonation_target)
        with httpx.Client(transport=transport, headers=headers, timeout=20) as client:
            response = client.get(test_url)

        # DEBUGGING: Print the HTTP version used for the request.
        print(f"   - HTTP Version Reported by httpx: {response.http_version}")

        if response.status_code == 200:
            fingerprint_data = response.json()
            # DEBUGGING: Print the raw JSON response from the API.
            print(f"   - Raw API Response:\n{json.dumps(fingerprint_data, indent=2)}")
            print("✅ Analysis successful. Received fingerprint data.")
            return fingerprint_data
        else:
            print(f"❌ Test failed. Status code: {response.status_code}")
            print(f"   - Response: {response.text}")
            return None

    except Exception as e:
        print(f"❌ An error occurred during the httpx-curl-cffi request: {e}")
        return None


# ==============================================================================
#  STEP 2: GENERATE REPORT
# ==============================================================================
def generate_report(headers, fingerprint_data):
    """
    Formats the collected HTTP/2 data into a report and saves it to a text file.
    """
    print("\n📄 STEP 2: Generating final HTTP/2 results report...")

    if not isinstance(fingerprint_data, dict):
        fingerprint_data = {"http2_frames": []}
        print("⚠️  Warning: Fingerprint data is missing. Report will have N/A values.")

    # --- PARSE THE NESTED FINGERPRINT DATA ---
    user_agent = headers.get("user-agent", "Not found")
    server_reported_protocol = fingerprint_data.get("http_protocol", "N/A")

    pseudo_headers = None
    stream_headers = None
    settings = None
    window_update = None
    priority_frames_found = False

    http2_frames = fingerprint_data.get("http2_frames", [])
    for frame in http2_frames:
        frame_name = frame.get("name")
        if frame_name == "SETTINGS":
            settings = frame.get("settings_map")
        elif frame_name == "WINDOW_UPDATE":
            window_update = frame.get("increment")
        elif frame_name == "HEADERS":
            all_headers = frame.get("ordered_headers_key", [])
            pseudo_headers = [h for h in all_headers if h.startswith(":")]
            stream_headers = [h for h in all_headers if not h.startswith(":")]
        elif frame_name == "PRIORITY":
            priority_frames_found = True
    # --- END PARSING LOGIC ---

    # Determine verdict based on whether we got the fingerprint data
    if (
        all([pseudo_headers, stream_headers, settings, window_update])
        and server_reported_protocol == "HTTP/2.0"
    ):
        verdict = "Success: The server confirmed an HTTP/2 connection and a valid fingerprint was retrieved."
    else:
        verdict = "Failure: The HTTP/2 fingerprint could not be fully parsed. The request may have fallen back to HTTP/1.1 or the API response was unexpected."

    report_content = f"""
# ==================================================
#  HTTP/2 Fingerprint Analysis Report
# ==================================================
#
#  Date & Time: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
#  Test Client: httpx-curl-cffi (impersonating chrome120)
#  Test Endpoint: https://tools.scrapfly.io/api/http2
#
# --------------------------------------------------
#  1. SESSION CONTEXT
# --------------------------------------------------
#
#  User-Agent Sent: {user_agent}
#  Protocol Confirmed by Server: {server_reported_protocol}
#
# --------------------------------------------------
#  2. HTTP/2 FINGERPRINT ANALYSIS
# --------------------------------------------------
#
#  Pseudo-Header Order: {pseudo_headers or 'N/A'}
#  Stream Header Order: {stream_headers or 'N/A'}
#  Settings Frame: {settings or 'N/A'}
#  Window Update Increment: {window_update or 'N/A'}
#  Priority Frames Sent: {'Yes' if priority_frames_found else 'No'}
#
# --------------------------------------------------
#  3. CONCLUSION
# --------------------------------------------------
#
#  Verdict: {verdict}
#
#  Explanation: The test uses httpx with CurlTransport to impersonate
#  the HTTP/2 negotiation of a real web browser (Chrome 120).
#  The server's protocol confirmation is the most reliable indicator
#  of a successful HTTP/2 connection.
#
# ==================================================
"""
    try:
        report_filename = "http2_fingerprint_report.txt"
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(report_content.strip())
        print(f"✅ Report saved successfully to '{report_filename}'")
    except Exception as e:
        print(f"❌ Failed to save report: {e}")


# ==============================================================================
#  MAIN EXECUTION
# ==============================================================================
def main():
    """
    Main function to run the fingerprinting test and generate a report.
    """
    # Step 1: Test the HTTP/2 fingerprint
    fingerprint_data = test_http2_fingerprint(BASE_HEADERS)

    # Step 2: Generate the final report if the test was successful
    if fingerprint_data:
        generate_report(BASE_HEADERS, fingerprint_data)
    else:
        print(
            "\nCould not generate a report because the HTTP/2 fingerprint test failed."
        )


if __name__ == "__main__":
    main()
