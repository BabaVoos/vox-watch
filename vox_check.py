"""
One-shot check: loads the Vox page, finds all bookable dates (links like ?d=20261216),
compares with the last run (state.json) and sends a phone notification via ntfy if new.
"""
import json
import os
import re
import sys
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

PAGE = "https://egy.voxcinemas.com/ar/movies/avengers-doomsday"
TOPIC = os.environ["NTFY_TOPIC"]
STATE = Path("state.json")


def notify(title, msg):
    print("NOTIFY:", title, msg)
    requests.post(
        f"https://ntfy.sh/{TOPIC}",
        data=msg.encode("utf-8"),
        headers={"Title": title, "Priority": "urgent", "Click": PAGE + "#showtimes"},
        timeout=15,
    )


def get_dates():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(locale="ar-EG")
        page.goto(PAGE + "#showtimes", wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)
        html = page.content()
        browser.close()
    print("page length:", len(html))
    if re.search(r"just a moment|access denied|captcha", html, re.I) and len(html) < 20000:
        print("WARNING: looks like the site blocked the request")
    return sorted(set(re.findall(r"[?&]d=(20\d{6})", html)))


def main():
    dates = get_dates()
    print("dates found:", dates)
    if not STATE.exists():
        STATE.write_text(json.dumps(dates))
        notify("Vox watcher started", f"Currently listed dates: {dates or 'none'}")
        return
    known = json.loads(STATE.read_text())
    new = [d for d in dates if d not in known]
    if new:
        notify("Doomsday tickets open!", "New dates: " + ", ".join(new))
    if dates != known:
        STATE.write_text(json.dumps(dates))


if __name__ == "__main__":
    sys.exit(main())
