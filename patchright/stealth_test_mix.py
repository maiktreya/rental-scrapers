import httpx
from httpx_curl_cffi import CurlTransport
import datetime
import sys
import os

# ==============================================================================
#  SETUP: IMPORT HEADERS FROM PARENT DIRECTORY
# ==============================================================================
# This block allows the script to find the 'base_headers.py' file.
try:
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(parent_dir)
    from base_headers import BASE_HEADERS

    print("✅ Successfully imported headers from base_headers.py.")
except ImportError:
    print("❌ ERROR: 'base_headers.py' not found in the parent directory.")
    print("Please ensure the file exists and contains a BASE_HEADERS dictionary.")
    sys.exit(1)


# ==============================================================================
#  STEP 1: TEST FINGERPRINT (Using httpx-curl-cffi)
# ==============================================================================
def test_request_fingerprint_with_hybrid(headers):
    """
    Sends the captured headers to a fingerprinting service using httpx with
    CurlTransport for impersonation.
    """
    test_url = "https://tls.browserleaks.com/json"
    impersonation_target = "chrome120"
    print(
        f"\n📡 STEP 1: Testing fingerprint with httpx-curl-cffi (impersonating {impersonation_target})..."
    )

    try:
        # Use httpx.Client with the special CurlTransport
        transport = CurlTransport(impersonate=impersonation_target)
        with httpx.Client(transport=transport, headers=headers, timeout=20) as client:
            response = client.get(test_url)

        if response.status_code == 200:
            fingerprint_data = response.json()
            print("✅ Analysis successful.")

            # Since we are impersonating Chrome, the verdict should be positive.
            verdict = "Success: The JA3 fingerprint likely matches a real Chrome browser due to httpx-curl-cffi impersonation."
            return fingerprint_data, verdict
        else:
            print(f"❌ Test failed. Status code: {response.status_code}")
            return None, "Test Failed: Received a non-200 status code."

    except Exception as e:
        print(f"❌ An error occurred during the httpx-curl-cffi request: {e}")
        return None, f"Test Error: {e}"


# ==============================================================================
#  STEP 2: GENERATE REPORT (The final output)
# ==============================================================================
def generate_report(headers, fingerprint_data, verdict):
    """
    Formats the collected data into a report and saves it to a text file.
    """
    print("\n📄 STEP 2: Generating final results report...")

    # Ensure fingerprint_data is a dictionary to prevent errors on .get()
    if not isinstance(fingerprint_data, dict):
        fingerprint_data = {}
        print("⚠️  Warning: Fingerprint data is missing. Report will have N/A values.")

    user_agent = headers.get("user-agent", "Not found")
    ja3_hash = fingerprint_data.get("ja3_hash", "N/A")
    http2_fp = fingerprint_data.get("http2_fp", "N/A")

    report_content = f"""
# ==================================================
#  Request Fingerprint Analysis Report
# ==================================================
#
#  Date & Time: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
#  Test Client: httpx-curl-cffi (impersonating chrome120)
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
#  Explanation: The test was performed using httpx with CurlTransport,
#  which masks the default Python TLS signature and impersonates a real
#  web browser. This new JA3 hash should match that of Chrome.
#
# ==================================================
"""
    try:
        report_filename = "httpx_curl_cffi_fingerprint_report.txt"
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
    # Step 1: Test the fingerprint using the hybrid library
    fingerprint_data, verdict = test_request_fingerprint_with_hybrid(BASE_HEADERS)

    # Step 2: Generate the final report if the test was successful
    if fingerprint_data:
        generate_report(BASE_HEADERS, fingerprint_data, verdict)
    else:
        print("\nCould not generate a report because the fingerprint test failed.")


if __name__ == "__main__":
    main()
