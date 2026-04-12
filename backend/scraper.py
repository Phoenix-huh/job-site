"""
Naukri Scraper — uses non-headless Playwright to bypass bot detection.
Extracts job listings from search results pages and individual JD pages.
"""
import asyncio
import random
import re
import json
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def get_search_results(page, role, max_jobs=10):
    """Get list of job URLs + basic info from search results pages (supports pagination)."""
    slug = role.replace(' ', '-').lower()
    
    all_cards = []
    page_num = 1
    
    while len(all_cards) < max_jobs:
        url = f"https://www.naukri.com/{slug}-jobs" if page_num == 1 else f"https://www.naukri.com/{slug}-jobs-{page_num}"
        print(f"  Loading search page {page_num}: {url}")
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"  Failed to load {url}: {e}")
            break
            
        await asyncio.sleep(random.uniform(6, 10))
        
        # Scroll to load lazy content
        for _ in range(3):
            await page.mouse.wheel(0, 500)
            await asyncio.sleep(random.uniform(1, 2))
        
        # Extract job cards
        cards = await page.evaluate('''() => {
            const results = [];
            document.querySelectorAll('.cust-job-tuple, .srp-jobtuple-wrapper').forEach(card => {
                const titleEl = card.querySelector('a.title');
                const compEl = card.querySelector('.comp-name, .comp-dtls-wrap a, .subTitle');
                const descEl = card.querySelector('.job-desc, .ellipsis, .job-description');
                
                if (titleEl) {
                    results.push({
                        title: titleEl.textContent.trim(),
                        url: titleEl.href,
                        company: compEl ? compEl.textContent.trim() : 'Unknown',
                        snippet: descEl ? descEl.textContent.trim() : '',
                    });
                }
            });
            return results;
        }''')
        
        if not cards:
            print(f"  No more jobs found on page {page_num}.")
            break
            
        # Append unique cards
        for card in cards:
            if not any(c.get("url") == card["url"] for c in all_cards):
                all_cards.append(card)
                if len(all_cards) >= max_jobs:
                    break
        
        if len(all_cards) >= max_jobs:
            break
            
        page_num += 1
        await asyncio.sleep(random.uniform(4, 8))
        
    return all_cards[:max_jobs]

async def get_job_description(page, url):
    """Load individual job page and extract full description."""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(random.uniform(4, 7))
        
        result = await page.evaluate('''() => {
            const descEl = document.querySelector('.styles_JDC__dang-inner-html__h0K4t, .job-desc, .dang-inner-html, [class*="job-desc"]');
            const compEl = document.querySelector('.styles_jd-header-comp-name__MvqAI, .jd-header-comp-name, [class*="comp-name"]');
            return {
                description: descEl ? descEl.innerText.trim() : '',
                company: compEl ? compEl.textContent.trim() : '',
            };
        }''')
        
        return result.get("description", "")
    except:
        return ""

async def scrape_naukri(search_query: str, max_jobs: int = 10):
    """Main scraping function. Returns list of job dicts."""
    jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--window-size=1440,900",
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.128 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            locale="en-US",
        )
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            window.chrome = {runtime: {}};
        """)
        
        page = await context.new_page()
        
        # Warm up session
        await page.goto("https://www.naukri.com/", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)
        
        # Get search results
        cards = await get_search_results(page, search_query, max_jobs)
        print(f"  Found {len(cards)} listings for {search_query}")
        
        for i, card in enumerate(cards):
            # Visit each job page to get full description
            if i > 0:
                await asyncio.sleep(random.uniform(3, 6))
            
            desc = await get_job_description(page, card["url"])
            if not desc:
                desc = card.get("snippet", "No description available")
            
            email = None
            emails = re.findall(r'[a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+', desc)
            if emails:
                email = emails[0]
            
            jobs.append({
                "title": card["title"],
                "company": card["company"],
                "url": card["url"],
                "description": desc,
                "email": email,
            })
            print(f"  ✅ [{i+1}/{len(cards)}] {card['company']}")
        
        await browser.close()
    
    return jobs
