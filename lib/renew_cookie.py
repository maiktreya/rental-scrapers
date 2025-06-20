from playwright.sync_api import sync_playwright

def get_cookies_with_playwright():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        )
        page = context.new_page()
        page.goto("https://www.idealista.com")
        page.wait_for_timeout(5000)  # Wait for JavaScript to execute

        # Get all cookies
        cookies = context.cookies()
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
