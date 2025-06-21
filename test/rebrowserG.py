# Your original script
from rebrowser_playwright.sync_api import sync_playwright

def get_cookies_with_playwright():
    with sync_playwright() as p:
        # The 'launch()' method will now use the patched browser logic
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
        )
        page = context.new_page()
        page.goto("https://www.idealista.com")
        page.wait_for_timeout(5000)

        cookies = context.cookies()
        browser.close()
        #... rest of your code
        browser.close()

        # Convert cookies to a string
        cookie_str = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])

        with open('cookie.txt', 'w') as f:
            f.write(cookie_str)

        print("Cookies saved to cookie.txt")
        return cookie_str

if __name__ == "__main__":
    cookie_str = get_cookies_with_playwright()
    print("Extracted cookies:", cookie_str)
