"""
Backfill posted_date for existing jobs by revisiting each Naukri job page.

Usage:
    python backfill_dates.py               # process all jobs with wrong dates
    python backfill_dates.py --limit 100   # process only first 100 jobs
    python backfill_dates.py --all         # force re-process all Naukri jobs
    python backfill_dates.py --dry-run     # show what would change without saving

Note: Opens a visible browser (required to bypass Naukri's bot detection).
      Processes ~3-5 jobs/minute to avoid rate limiting.
"""

import asyncio
import sys
import os
import argparse
import random
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
import models
from utils import parse_relative_date

# ── Selectors to try on the Naukri job DETAIL page ──────────────────────────
DATE_SELECTORS_DETAIL = [
    ".styles_jhc__stat-items__lqNbx time",
    ".styles_jhc__stat-items__lqNbx span",
    "time[datetime]",
    "[class*='postDate']",
    "[class*='posted-date']",
    "[class*='postedDate']",
    "[class*='PostedDate']",
    "[class*='job-post']",
    ".job-post-day",
    ".date",
    ".posted-date",
    ".postedVal",
    "span.fleft.postedDate",
]

DATE_PATTERN_JS = r"""/\d+\s*(day|week|month|hour|minute|d\b|w\b|m\b)|just\s*posted|today|yesterday|few\s+days/i"""


async def extract_date_from_page(page) -> str:
    """Try all selectors and a text-scan fallback to find the posting date."""
    for sel in DATE_SELECTORS_DETAIL:
        try:
            el = await page.query_selector(sel)
            if el:
                txt = (await el.text_content() or "").strip()
                if txt and len(txt) < 60:
                    return txt
        except Exception:
            continue

    # Fallback: scan all visible text nodes for date-like strings
    try:
        result = await page.evaluate(f"""() => {{
            const pat = {DATE_PATTERN_JS};
            const allEls = document.querySelectorAll('span, div, time, label, p');
            for (const el of allEls) {{
                const txt = (el.textContent || '').trim();
                if (txt && pat.test(txt) && txt.length < 60 &&
                    el.children.length === 0) {{  // leaf nodes only
                    return txt;
                }}
            }}
            return '';
        }}""")
        if result:
            return result
    except Exception:
        pass

    return ""


async def backfill(limit: int, force_all: bool, dry_run: bool):
    db = SessionLocal()
    today_str = date.today().isoformat()

    try:
        query = db.query(models.Job).filter(
            models.Job.platform == "Naukri",
            models.Job.url.isnot(None),
        )

        if not force_all:
            # Only target jobs whose stored date equals the scrape date (wrong ones)
            query = query.filter(
                models.Job.posted_date == today_str
            )

        jobs = query.order_by(models.Job.id).limit(limit).all()
        total = len(jobs)

        if total == 0:
            print("✅ No jobs need date backfilling.")
            return

        print(f"{'[DRY RUN] ' if dry_run else ''}Backfilling dates for {total} Naukri jobs...")
        print("  Opening browser (visible, to bypass bot detection)...\n")

        from playwright.async_api import async_playwright

        updated = 0
        skipped = 0
        failed = 0

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=os.getenv("CI", "").lower() == "true" or os.getenv("HEADLESS", "true").lower() == "true",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--window-size=1280,800",
                ]
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.6261.128 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
                locale="en-US",
            )
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                window.chrome = {runtime: {}};
            """)

            page = await context.new_page()

            # Warm-up: visit Naukri homepage first
            print("  Warming up session on Naukri...")
            await page.goto("https://www.naukri.com/", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            for i, job in enumerate(jobs):
                print(f"  [{i+1}/{total}] {job.company} — {job.title[:50]}")

                try:
                    await page.goto(job.url, wait_until="domcontentloaded", timeout=25000)
                    await asyncio.sleep(random.uniform(2, 4))

                    raw_date = await extract_date_from_page(page)

                    if not raw_date:
                        print(f"    ⚠ No date found on page — skipping")
                        skipped += 1
                    else:
                        new_date = parse_relative_date(raw_date)
                        print(f"    raw={repr(raw_date)} → {new_date}", end="")

                        if new_date == today_str:
                            print(" (unchanged — likely 'Just Posted')")
                            skipped += 1
                        elif dry_run:
                            print(f" [DRY RUN — would update from {job.posted_date}]")
                            updated += 1
                        else:
                            old = job.posted_date
                            job.posted_date = new_date
                            print(f" ✓ (was {old})")
                            updated += 1

                except Exception as e:
                    print(f"    ✗ Error: {e}")
                    failed += 1

                # Commit in batches of 20
                if not dry_run and updated % 20 == 0 and updated > 0:
                    db.commit()

                # Polite delay between jobs
                if i < total - 1:
                    delay = random.uniform(3, 6)
                    await asyncio.sleep(delay)

            await browser.close()

        if not dry_run:
            db.commit()

        print(f"\n{'='*50}")
        print(f"Done!")
        print(f"  ✅ Updated : {updated}")
        print(f"  ⏭ Skipped : {skipped} (no date found or already 'Just Posted')")
        print(f"  ✗  Failed  : {failed}")
        print(f"{'='*50}")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill posted_date for existing Naukri jobs")
    parser.add_argument(
        "--limit", type=int, default=500,
        help="Max number of jobs to process (default: 500)"
    )
    parser.add_argument(
        "--all", action="store_true", dest="force_all",
        help="Re-process ALL Naukri jobs, not just ones with today's date"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be changed without writing to DB"
    )
    args = parser.parse_args()

    print("ShieldDB — Date Backfill")
    print(f"Mode   : {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"Target : {'All Naukri jobs' if args.force_all else 'Jobs with wrong date (today)'}")
    print(f"Limit  : {args.limit}")
    print()

    asyncio.run(backfill(args.limit, args.force_all, args.dry_run))
