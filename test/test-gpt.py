import asyncio
import os
from playwright.async_api import async_playwright
import subprocess
import random

COOKIE_FILE = "cookie.txt"
TARGET_URL = "https://www.idealista.com"

async def simulate_human_activity(page):
    print("[*] Simulating human activity...")
    width = 1024
    height = 768

    # Move mouse in a random pattern
    for _ in range(5):
        x = random.randint(0, width)
        y = random.randint(0, height)
        await page.mouse.move(x, y, steps=random.randint(5, 15))
        await asyncio.sleep(random.uniform(0.5, 1.5))

    # Scroll a bit down
    for _ in range(3):
        scroll_y = random.randint(100, 400)
        await page.evaluate(f"window.scrollBy(0, {scroll_y})")
        await asyncio.sleep(random.uniform(0.5, 1.2))

    print("[*] Activity simulation complete.")

async def get_datadome_cookie():
    # Start virtual display (Xvfb)
    xvfb = subprocess.Popen(['Xvfb', ':99', '-screen', '0', '1024x768x24'])
    os.environ['DISPLAY'] = ':99'

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--no-sandbox"])
        context = await browser.new_context()
        page = await context.new_page()

        print(f"[+] Navigating to {TARGET_URL}")
        await page.goto(TARGET_URL, wait_until='networkidle')

        # Simulate user activity
        await simulate_human_activity(page)

        # Wait for any async JS or bot checks to finish
        await asyncio.sleep(5)

        # Retrieve cookies
        cookies = await context.cookies()
        await browser.close()
        xvfb.terminate()

        # Save to file
        with open(COOKIE_FILE, 'w') as f:
            for cookie in cookies:
                f.write(f"{cookie['name']}={cookie['value']}; domain={cookie['domain']}; path={cookie['path']}\n")

        print(f"[+] Cookies saved to {COOKIE_FILE}")

        # Optional: Print DataDome cookie
        datadome = next((c for c in cookies if 'datadome' in c['name']), None)
        if datadome:
            print(f"[+] Found DataDome cookie: {datadome['name']} = {datadome['value']}")
        else:
            print("[-] DataDome cookie not found. Possibly blocked or challenge failed.")

if __name__ == "__main__":
    asyncio.run(get_datadome_cookie())
