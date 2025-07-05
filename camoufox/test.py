# working code snippet

from camoufox.sync_api import Camoufox
from browserforge.fingerprints import Screen

screen = Screen(max_width=1920, max_height=1080)
with Camoufox(os=["windows", "macos", "linux"],
              humanize=True,
              headless=False,
              screen=screen) as browser:
    page = browser.new_page()
    page.goto("https://bot.sannysoft.com/")
