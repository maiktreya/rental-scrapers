import time
import tempfile
import shutil
from patchright.sync_api import sync_playwright, Playwright


def run(playwright: Playwright):
    """
    Launches a browser using patchright, solves the Datadome challenge,
    captures headers, and exports them to a Python file (base_headers.py),
    using a fresh temporary user data directory each run.
    """
    # --- Create a temporary user data directory ---
    user_data_dir = tempfile.mkdtemp()

    print(f"✅ Using temporary user data directory: {user_data_dir}")

    # --- Launch persistent context with temp user data ---
    context = playwright.chromium.launch_persistent_context(
        user_data_dir,
        headless=False,
        channel="chrome",
        args=[
            "--no-first-run",
            "--no-service-autorun",
            "--password-store=basic",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
        no_viewport=True,
    )

    page = context.new_page()

    print("Navigating to https://www.idealista.com/...")

    try:
        page.goto(
            "https://www.idealista.com/alquiler-viviendas/madrid-madrid/", timeout=60000
        )

        print("\n--- ACTION REQUIRED ---")
        print("Please solve the Datadome challenge manually in the opened browser.")
        print("The script is waiting for the datadome cookie...")

        datadome_cookie = None
        for _ in range(120):  # Wait up to 120 seconds
            cookies = context.cookies()
            for cookie in cookies:
                if cookie["name"] == "datadome":
                    datadome_cookie = cookie
                    break
            if datadome_cookie:
                break
            time.sleep(1)

        if datadome_cookie:
            print("\n✅ Datadome challenge solved successfully!")
            print(f"Datadome Cookie Value: {datadome_cookie['value']}")

            print("\nCapturing headers from an authenticated request...")
            captured_headers = {}

            def capture_request_headers(request):
                if (
                    request.is_navigation_request()
                    and request.resource_type == "document"
                ):
                    captured_headers.update(request.headers)

            page.on("request", capture_request_headers)
            page.reload(wait_until="networkidle")
            page.remove_listener("request", capture_request_headers)

            if not captured_headers:
                raise RuntimeError("Failed to capture headers on the second request.")

            # Add cookies to headers
            all_cookies = context.cookies()
            captured_headers["cookie"] = "; ".join(
                [f"{c['name']}={c['value']}" for c in all_cookies]
            )

            # Remove unwanted headers
            for header in ["host", "connection", "content-length"]:
                captured_headers.pop(header, None)

            print("✅ Headers captured.")

            # --- Export headers to Python file ---
            try:
                with open("base_headers.py", "w", encoding="utf-8") as f:
                    f.write("# Auto-generated browser headers for HTTPX scraping.\n\n")
                    f.write("BASE_HEADERS = {\n")
                    for key, value in captured_headers.items():
                        f.write(f'    "{key}": {repr(value)},\n')
                    f.write("}\n")
                    f.write("\n# Note: This file is updated on each run.\n")

                print("✅ Headers saved to base_headers.py.")
            except Exception as e:
                print(f"❌ Failed to save headers: {e}")

        else:
            print("\n❌ Timed out waiting for the Datadome cookie. Please try again.")

    except Exception as e:
        print(f"\n❌ An error occurred: {e}")

    finally:
        print("\nClosing the browser and cleaning up temporary user data...")
        time.sleep(10)
        try:
            context.close()
        except Exception as e:
            print(f"Warning: Error while closing context: {e}")

        # --- Clean up temporary user data directory ---
        try:
            shutil.rmtree(user_data_dir)
            print(f"✅ Temp directory {user_data_dir} deleted.")
        except Exception as e:
            print(f"⚠️ Failed to delete temp directory: {e}")


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
