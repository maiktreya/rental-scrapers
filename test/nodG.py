# main_script.py

import asyncio
import json
import nodriver as uc

# --- Configuration ---
# Define the target URL. This should be a page known to be protected by DataDome.
# For demonstration, a major retailer's homepage is often a good candidate.
# Replace with the actual target URL.
TARGET_URL = "https://www.idealista.com/"

# Define the name of the output file where the cookie will be saved.
OUTPUT_FILE = "cookie1b.txt"

# Define the wait time in seconds for DataDome's scripts to execute.
# This is a critical parameter. If the script fails to get a cookie,
# increasing this value is the first troubleshooting step.
WAIT_TIME_SECONDS = 20

async def main():
    """
    Main asynchronous function to control the browser, extract the cookie,
    and save it to a file.
    """
    browser = None  # Initialize browser to None for the finally block
    try:
        print("--- Starting Browser Automation ---")

        # 1. Start the browser instance.
        # nodriver handles finding the browser, creating a temporary profile,
        # and establishing a stealth connection.
        browser = await uc.start()
        print("Browser started successfully.")

        # 2. Navigate to the target URL.
        # The browser.get() method returns a 'Tab' object representing the
        # active tab.
        print(f"Navigating to: {TARGET_URL}")
        page = await browser.get(TARGET_URL)
        print("Page navigation initiated.")

        # 3. Wait for DataDome's JavaScript challenges to run.
        # This is the most crucial step. The page may appear loaded, but
        # DataDome's scripts are running in the background to fingerprint
        # the browser. A sufficient delay is required for this process
        # to complete and for the 'datadome' cookie to be set.
        print(f"Waiting for {WAIT_TIME_SECONDS} seconds for DataDome challenges to complete...")
        await page.sleep(WAIT_TIME_SECONDS)
        print("Wait complete. Attempting to retrieve cookies.")

        # 4. Retrieve all cookies from the browser session.
        # page.get_cookies() returns a list of dictionaries, where each
        # dictionary contains the details of a single cookie.
        all_cookies = await page.get_cookies()

        if not all_cookies:
            print("No cookies were found. The site may not have set any, or the request was blocked.")
            return

        # 5. Filter the list to find the 'datadome' cookie.
        print("Searching for the 'datadome' cookie...")
        datadome_cookie = None
        for cookie in all_cookies:
            if cookie.get('name') == 'datadome':
                datadome_cookie = cookie
                break  # Exit the loop once found

        # 6. Process and save the cookie.
        if datadome_cookie:
            print("Successfully found the 'datadome' cookie.")

            # Extract the value of the cookie.
            cookie_value = datadome_cookie.get('value')

            # Write the cookie value to the specified text file.
            # The 'with' statement ensures the file is properly closed.
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                f.write(cookie_value)

            print(f"DataDome cookie value has been saved to '{OUTPUT_FILE}'.")

            # --- Optional: Save the full cookie object as JSON ---
            # Uncomment the following lines to save the entire cookie dictionary
            # as a JSON object, which can be more useful for programmatic reuse.
            # with open('datadome_cookie.json', 'w', encoding='utf-8') as f:
            #     json.dump(datadome_cookie, f, indent=4)
            # print("Full DataDome cookie object saved to 'datadome_cookie.json'.")

        else:
            print("Error: The 'datadome' cookie was not found.")
            print("Possible reasons: ")
            print("1. The wait time was too short for challenges to complete.")
            print("2. The browser was detected as automated and blocked.")
            print("3. The target website does not use a cookie named 'datadome'.")
            print("4. The IP address may be flagged.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    finally:
        # 7. Ensure the browser is closed to clean up temporary files.
        if browser:
            print("Closing the browser.")
            await browser.close()

        print("--- Script Finished ---")

if __name__ == "__main__":
    # Run the main asynchronous function.
    # In some environments, uc.loop().run_until_complete(main()) may be used,
    # but asyncio.run() is the modern standard.
    asyncio.run(main())