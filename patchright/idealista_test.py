import httpx
from curl_cffi import requests as curl_cffi_requests
from httpx_curl_cffi import CurlTransport  # Correct import based on documentation
import sys
import os
import datetime

# ==============================================================================
#  SETUP: IMPORT HEADERS FROM PARENT DIRECTORY
# ==============================================================================
# This block allows the script to find the 'base_headers.py' file
# located one level up in the directory structure.
try:
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(parent_dir)
    from base_headers import BASE_HEADERS

    print("✅ Successfully imported headers.")
except ImportError:
    print(
        "❌ Error: Could not import BASE_HEADERS. Make sure 'base_headers.py' exists in the parent directory."
    )
    sys.exit(1)


# ==============================================================================
#  TEST 1: STANDARD HTTPX REQUEST
# ==============================================================================
def test_with_httpx(headers, url):
    """
    Attempts to connect to the URL using the standard httpx library.
    This request will likely be blocked by bot detection due to its default
    Python TLS fingerprint (JA3).
    """
    print("\n" + "=" * 50)
    print("🔬 TEST 1: Standard request with HTTPX")
    print("=" * 50)
    try:
        with httpx.Client(headers=headers, timeout=20, http2=True) as client:
            response = client.get(url)
            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                print("✅ Verdict: SUCCESS - The request was not blocked.")
            elif response.status_code == 403:
                print(
                    "❌ Verdict: BLOCKED - Received a 403 Forbidden. This is expected as bot detection likely identified the Python TLS signature."
                )
            else:
                print(
                    f"⚠️ Verdict: UNEXPECTED STATUS - Received status code {response.status_code}."
                )

    except Exception as e:
        print(f"❌ An error occurred during the httpx request: {e}")


# ==============================================================================
#  TEST 2: PURE CURL-CFFI REQUEST
# ==============================================================================
def test_with_curl_cffi(headers, url):
    """
    Connects to the URL using the pure curl-cffi library to impersonate.
    This has a high chance of success by matching the browser's TLS fingerprint.
    """
    impersonation_target = "chrome120"
    print("\n" + "=" * 50)
    print(
        f"🎭 TEST 2: Impersonated request with pure curl-cffi (as {impersonation_target})"
    )
    print("=" * 50)
    try:
        response = curl_cffi_requests.get(
            url,
            headers=headers,
            impersonate=impersonation_target,  # The key to mimicking a real browser
            timeout=20,
        )
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            print(
                "✅ Verdict: SUCCESS - The request was accepted. The browser impersonation successfully bypassed TLS fingerprinting."
            )
        elif response.status_code == 403:
            print(
                "❌ Verdict: BLOCKED - Even with impersonation, the request was denied."
            )
        else:
            print(
                f"⚠️ Verdict: UNEXPECTED STATUS - Received status code {response.status_code}."
            )

    except Exception as e:
        print(f"❌ An error occurred during the curl-cffi request: {e}")


# ==============================================================================
#  TEST 3: HTTX-CURL-CFFI REQUEST (The Corrected Hybrid Approach)
# ==============================================================================
def test_with_httpx_curl_cffi(headers, url):
    """
    Uses httpx with CurlTransport from httpx-curl-cffi.
    This provides the familiar httpx API with curl-cffi's impersonation engine.
    """
    impersonation_target = "chrome120"
    print("\n" + "=" * 50)
    print(f"🧬 TEST 3: Hybrid request with httpx-curl-cffi (as {impersonation_target})")
    print("=" * 50)
    try:
        # Correct Usage: Pass a CurlTransport instance to a standard httpx.Client
        transport = CurlTransport(impersonate=impersonation_target)
        with httpx.Client(transport=transport, headers=headers, timeout=20) as client:
            response = client.get(url)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            print(
                "✅ Verdict: SUCCESS - The request was accepted. The hybrid library works as expected."
            )
        elif response.status_code == 403:
            print(
                "❌ Verdict: BLOCKED - The request was denied, which is unexpected for this library."
            )
        else:
            print(
                f"⚠️ Verdict: UNEXPECTED STATUS - Received status code {response.status_code}."
            )

    except Exception as e:
        print(f"❌ An error occurred during the httpx-curl-cffi request: {e}")


# ==============================================================================
#  MAIN EXECUTION
# ==============================================================================
def main():
    """
    Main function to run the series of tests against Idealista.
    """
    target_url = "https://www.idealista.com/alquiler-viviendas/madrid-madrid/"
    print(f"🚀 Starting tests for: {target_url}")
    print(f"🕒 Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Run Test 1
    test_with_httpx(BASE_HEADERS, target_url)

    # Run Test 2
    test_with_curl_cffi(BASE_HEADERS, target_url)

    # Run Test 3
    test_with_httpx_curl_cffi(BASE_HEADERS, target_url)

    print("\n🏁 All tests complete.")


if __name__ == "__main__":
    main()
