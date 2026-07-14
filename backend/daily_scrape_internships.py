"""
Daily Internship Scraper — scrape internship listings for every role.

Usage:
  python daily_scrape_internships.py
  python daily_scrape_internships.py --max 15 --city Mumbai
  python daily_scrape_internships.py --roles "Data Analyst,Software Engineer" --max 10
  python daily_scrape_internships.py --platform naukri

Listings are stored under the base role name (e.g. "Data Analyst") with job_type=Internship,
so they appear when you select that role and switch to the Internships tab in the app.

Note: Opens a visible browser window (required to bypass Naukri's bot detection).
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from daily_scrape import ALL_ROLES, run
from scraper import normalize_base_role


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape internship listings for all roles and populate ShieldDB"
    )
    parser.add_argument(
        "--roles",
        type=str,
        default=None,
        help="Comma-separated base roles to scrape (default: all roles in ALL_ROLES)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=20,
        help="Max internship listings per role (default: 20)",
    )
    parser.add_argument(
        "--platform",
        type=str,
        default="all",
        choices=["naukri", "indeed", "all"],
        help="Platform to scrape (default: all)",
    )
    parser.add_argument(
        "--city",
        type=str,
        default="",
        help="City/location filter (e.g. Mumbai, Bangalore)",
    )
    args = parser.parse_args()

    roles = args.roles.split(",") if args.roles else ALL_ROLES
    roles = [normalize_base_role(r.strip()) for r in roles if r.strip()]

    print("ShieldDB Daily Internship Scrape")
    print(f"Platform: {args.platform}")
    print(f"City: {args.city or 'Any'}")
    print(f"Roles: {len(roles)}")
    print(f"Max per role: {args.max}")

    asyncio.run(run(roles, args.max, args.platform, args.city, internships=True))
