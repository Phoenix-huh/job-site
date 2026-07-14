import asyncio
import sys
import os

# Configure stdout to handle UTF-8 printing safely on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Ensure the backend directory is in the import path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper import scrape_naukri, scrape_indeed

async def test_scrapers():
    print("=== Testing Naukri Scraper ===")
    try:
        # Fetch 1 job
        naukri_jobs = await scrape_naukri("React Developer", max_jobs=1)
        print(f"Naukri Scraper returned {len(naukri_jobs)} jobs.")
        if naukri_jobs:
            print("First Naukri Job Sample:")
            # Safely print dictionary representation
            print(str(naukri_jobs[0]).encode('utf-8', errors='replace').decode('utf-8'))
        else:
            print("No jobs returned from Naukri.")
    except Exception as e:
        print(f"Naukri Scraper test failed: {e}")

    print("\n=== Testing Indeed Scraper ===")
    try:
        # Fetch 1 job
        indeed_jobs = await scrape_indeed("React Developer", max_jobs=1)
        print(f"Indeed Scraper returned {len(indeed_jobs)} jobs.")
        if indeed_jobs:
            print("First Indeed Job Sample:")
            # Safely print dictionary representation
            print(str(indeed_jobs[0]).encode('utf-8', errors='replace').decode('utf-8'))
        else:
            print("No jobs returned from Indeed.")
    except Exception as e:
        print(f"Indeed Scraper test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_scrapers())
