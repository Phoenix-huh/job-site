"""Standalone test for the Indeed / JSearch API integration."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from scraper import scrape_indeed


async def main():
    role = "Software Engineer"
    location = "India"
    print(f"[test_indeed] Running scrape_indeed('{role}', '{location}') ...")

    try:
        results = await scrape_indeed(role, location)
    except Exception as exc:
        print(f"[test_indeed] FAIL — scrape_indeed raised: {exc}")
        sys.exit(1)

    print(f"[test_indeed] Total jobs retrieved: {len(results)}")

    if not results:
        print("[test_indeed] FAIL — no jobs returned. Check RAPIDAPI_KEY and API quota.")
        sys.exit(1)

    print("\n[test_indeed] First 2 results:")
    for i, job in enumerate(results[:2]):
        print(f"  {i+1}. Title:   {job.get('title')}")
        print(f"     Company: {job.get('company')}")
        print(f"     Link:    {job.get('url')}")
        print()

    print("[test_indeed] PASS")


if __name__ == "__main__":
    asyncio.run(main())
