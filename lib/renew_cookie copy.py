# lib/renew_cookie.py
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# Define the base path for consistent file saving
# This assumes renew_cookie.py is in 'lib/' relative to the project root
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COOKIE_FILE = os.path.join(BASE_PATH, 'cookie.txt')
USER_AGENT_FILE = os.path.join(BASE_PATH, 'user_agent.txt')

def get_fresh_cookie():
    options = Options()
    options.add_argument('--headless') # Keep headless for server environments
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = None # Initialize driver to None
    try:
        driver = webdriver.Chrome(options=options)

        # Set a page load timeout for the browser (e.g., 60 seconds)
        driver.set_page_load_timeout(60)

        # IMPORTANT: Visit the main domain to get the base datadome cookie
        driver.get('https://www.idealista.com/inmueble/108387485/' )

        # Use explicit wait to ensure the 'datadome' cookie is present before trying to get it
        WebDriverWait(driver, 30).until( # Wait up to 30 seconds for the 'datadome' cookie to appear
            lambda d: d.get_cookie('datadome') is not None
        )

        datadome_cookie_obj = driver.get_cookie('datadome') #
        user_agent = driver.execute_script("return navigator.userAgent;") # Get the actual user agent from the browser

        if datadome_cookie_obj:
            full_cookie_string = f"{datadome_cookie_obj['name']}={datadome_cookie_obj['value']}"
            return full_cookie_string, user_agent # Return both the full cookie string and the user agent
        else:
            print("Error: 'datadome' cookie not found after waiting.")
            return None, None

    except TimeoutException:
        print("Timeout: Waited for page to load or datadome cookie, but timed out.")
        return None, None
    except WebDriverException as e:
        print(f"WebDriver error occurred: {e}")
        print("Ensure ChromeDriver is running and compatible with Chrome version.")
        return None, None
    except Exception as e:
        print(f"An unexpected error occurred in get_fresh_cookie: {e}")
        return None, None
    finally:
        if driver:
            driver.quit() # Ensure driver is always quit

# This block is for direct execution of renew_cookie.py (e.g., by cron)
if __name__ == '__main__':
    print("Attempting to renew cookie and user agent...")
    cookie_str, ua_str = get_fresh_cookie()

    if cookie_str and ua_str:
        try:
            with open(COOKIE_FILE, 'w') as f:
                f.write(cookie_str)
            print(f"Fresh Datadome Cookie saved to {COOKIE_FILE}")

            with open(USER_AGENT_FILE, 'w') as f:
                f.write(ua_str)
            print(f"Browser User-Agent saved to {USER_AGENT_FILE}")
        except Exception as e:
            print(f"Error saving cookie/User-Agent to files: {e}")
    else:
        print("Failed to retrieve fresh cookie or User-Agent. Files not updated.")