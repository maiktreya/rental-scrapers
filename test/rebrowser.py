import nodriver as uc
import asyncio
import json
import time

async def extract_datadome_cookie(url, output_file="datadome_cookie.txt"):
    """
    Extract DataDome access cookie from a website and save to text file

    Args:
        url (str): Target website URL
        output_file (str): Output filename for the cookie
    """
    browser = None
    try:
        # Launch browser with nodriver
        browser = await uc.start(headless=False)  # Set to True for headless mode

        # Create a new page
        page = await browser.get(url)

        # Wait for page to load and potential DataDome challenge
        await asyncio.sleep(5)

        # Wait for DataDome cookie to be set (adjust timeout as needed)
        print("Waiting for DataDome cookie...")
        cookie_found = False
        max_attempts = 30  # 30 seconds timeout

        for attempt in range(max_attempts):
            # Get all cookies
            cookies = await page.send(uc.cdp.network.get_cookies())

            # Look for DataDome cookie
            for cookie in cookies.cookies:
                if 'datadome' in cookie.name.lower():
                    print(f"Found DataDome cookie: {cookie.name}")

                    # Format cookie data
                    cookie_data = {
                        'name': cookie.name,
                        'value': cookie.value,
                        'domain': cookie.domain,
                        'path': cookie.path,
                        'expires': cookie.expires if hasattr(cookie, 'expires') else None,
                        'httpOnly': cookie.http_only if hasattr(cookie, 'http_only') else None,
                        'secure': cookie.secure if hasattr(cookie, 'secure') else None
                    }

                    # Save to file
                    with open(output_file, 'w') as f:
                        f.write(f"Cookie Name: {cookie_data['name']}\n")
                        f.write(f"Cookie Value: {cookie_data['value']}\n")
                        f.write(f"Domain: {cookie_data['domain']}\n")
                        f.write(f"Path: {cookie_data['path']}\n")
                        f.write(f"Expires: {cookie_data['expires']}\n")
                        f.write(f"HTTP Only: {cookie_data['httpOnly']}\n")
                        f.write(f"Secure: {cookie_data['secure']}\n\n")

                        # Also save as JSON for easier parsing
                        f.write("JSON Format:\n")
                        f.write(json.dumps(cookie_data, indent=2))

                    print(f"DataDome cookie saved to {output_file}")
                    cookie_found = True
                    break

            if cookie_found:
                break

            print(f"Attempt {attempt + 1}/{max_attempts} - Cookie not found yet...")
            await asyncio.sleep(1)

        if not cookie_found:
            print("DataDome cookie not found within timeout period")
            # Save all cookies for debugging
            with open("all_cookies_debug.txt", 'w') as f:
                f.write("All cookies found:\n")
                for cookie in cookies.cookies:
                    f.write(f"Name: {cookie.name}, Value: {cookie.value}\n")
            print("All cookies saved to all_cookies_debug.txt for debugging")

    except Exception as e:
        print(f"Error occurred: {str(e)}")

    finally:
        # Clean up
        if browser:
            try:
                await browser.stop()
            except:
                pass

async def main():
    # Example usage
    target_url = input("Enter the target URL: ").strip()
    if not target_url:
        target_url = "https://idealista.com"  # Default URL

    output_filename = input("Enter output filename (default: datadome_cookie.txt): ").strip()
    if not output_filename:
        output_filename = "datadome_cookie.txt"

    print(f"Extracting DataDome cookie from: {target_url}")
    await extract_datadome_cookie(target_url, output_filename)

if __name__ == "__main__":
    # Run the async function
    asyncio.run(main())