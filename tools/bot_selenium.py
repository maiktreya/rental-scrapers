import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# --- Configuration ---
# Path to the BotBrowser executable you installed
BOTBROWSER_BINARY_PATH = "/usr/bin/chromium-browser"

# Path to the BotBrowser profile you downloaded
BOTBROWSER_PROFILE_PATH = "/home/other/Downloads/BotBrowser-main/profiles/v137/chrome137_win10_x64.enc"

# Path for the session data (can be temporary, but a fixed path is good for debugging)
USER_DATA_DIR = "/home/other/idealista_session"

# The target URL
URL = "https://www.idealista.com"

# --- Automation Logic ---
chrome_options = Options()
chrome_options.binary_location = BOTBROWSER_BINARY_PATH

# Add all the necessary arguments
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument(f"--user-data-dir={USER_DATA_DIR}")
chrome_options.add_argument(f"--bot-profile={BOTBROWSER_PROFILE_PATH}")

# This argument allows Selenium to connect to a browser that's already running
# but Selenium for Python handles this implicitly when it launches the browser.

print("Launching BotBrowser...")
# There's no separate "driver" for BotBrowser, so we let Selenium use the binary directly
# We pass an empty service object because the binary location is set in options
service = Service(executable_path=None)
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    print(f"Navigating to {URL}...")
    driver.get(URL)

    # Wait for the page to load and potentially for the DataDome challenge to be solved.
    # You might need to increase this wait time if the site is slow.
    print("Waiting for DataDome cookie...")
    time.sleep(15)

    # Retrieve the datadome cookie
    datadome_cookie = driver.get_cookie('datadome')

    if datadome_cookie:
        print("\n--- SUCCESS ---")
        print("DataDome Cookie Found!")
        print(datadome_cookie['value'])
        print("--- END ---")
    else:
        print("\n--- FAILURE ---")
        print("DataDome cookie not found after 15 seconds.")
        print("Try increasing the sleep time or check if the page loaded correctly.")

finally:
    # Close the browser
    driver.quit()
    print("\nBrowser closed.")