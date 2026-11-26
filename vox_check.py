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
TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
STATE = Path("state.json")


def notify(title, msg):
    print("NOTIFY:", title, msg)
    r = requests.post(
        f"https://ntfy.sh/{TOPIC}",
        data=msg.encode("utf-8"),
        headers={"Title": title, "Priority": "urgent", "Click": PAGE + "#showtimes"},
        timeout=15,
    )
    print("ntfy status:", r.status_code)


def get_dates():
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(
            locale="ar-EG",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()
        try:
            resp = page.goto(PAGE + "#showtimes", wait_until="domcontentloaded", timeout=45000)
            print("HTTP status:", resp.status if resp else None)
        except Exception as e:
            print("LOAD ERROR:", repr(e)[:500])
            browser.close()
            return None
        page.wait_for_timeout(10000)
        html = page.content()
        print("page title:", page.title())
        browser.close()
    print("page length:", len(html))
    return sorted(set(re.findall(r"[?&]d=(20\d{6})", html)))


def main():
    if not TOPIC:
        print("ERROR: NTFY_TOPIC secret is empty or missing. Check repo Settings > Secrets.")
        return 1
    dates = get_dates()
    if dates is None:
        print("Could not load the page (probably blocked or timeout).")
        return 1
    print("dates found:", dates)
    if not STATE.exists():
        STATE.write_text(json.dumps(dates))
        notify("Vox watcher started", f"Currently listed dates: {dates or 'none'}")
        return 0
    known = json.loads(STATE.read_text())
    new = [d for d in dates if d not in known]
    if new:
        notify("Doomsday tickets open!", "New dates: " + ", ".join(new))
    if dates != known:
        STATE.write_text(json.dumps(dates))
    return 0


if __name__ == "__main__":
    sys.exit(main())
