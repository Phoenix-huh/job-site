"""
Naukri Scraper — uses Playwright to bypass bot detection.
Extracts job listings from search results pages and individual JD pages.
"""
import asyncio
import random
import re
import json
import os
import urllib.parse
from datetime import datetime, timedelta
import requests as _requests

from utils import (
    infer_job_type,
    infer_workplace_type,
    normalize_base_role,
    build_scrape_query,
    title_matches_search,
    filter_cards_by_role,
    extract_city_name,
    clean_skills,
    parse_relative_date,
    parse_linkedin_date,
    CITIES_LIST,
)

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    async_playwright = None
    HAS_PLAYWRIGHT = False

try:
    from playwright_stealth import Stealth
    HAS_STEALTH = True
except ImportError:
    Stealth = None
    HAS_STEALTH = False

HEADLESS_MODE = os.getenv("CI", "").lower() == "true" or os.getenv("HEADLESS", "true").lower() == "true"

CHROMIUM_LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-gpu",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--window-size=1920,1080",
]


async def get_search_results(page, role, location="", max_jobs=10, max_pages=10, existing_urls=None):
    """Get list of job URLs + basic info from search results pages (supports pagination)."""
    if existing_urls is None:
        existing_urls = set()
    if location:
        slug = f"{role.replace(' ', '-').lower()}-jobs-in-{location.replace(' ', '-').lower()}"
    else:
        slug = f"{role.replace(' ', '-').lower()}-jobs"
    
    all_cards = []
    new_count = 0
    page_num = 1
    consecutive_empty = 0
    MAX_CONSECUTIVE_EMPTY = 10
    
    while new_count < max_jobs and page_num <= max_pages:
        url = f"https://www.naukri.com/{slug}" if page_num == 1 else f"https://www.naukri.com/{slug}-{page_num}"
        print(f"  Loading search page {page_num}: {url}")
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"  Failed to load {url}: {e}")
            page_num += 1
            continue

        # Debug: log actual page we landed on
        current_url = page.url
        current_title = await page.title()
        print(f"  Landed on: {current_url} | title: {current_title}")

        # Dismiss login/auth popups that Naukri shows
        try:
            await page.evaluate("""() => {
                const closeBtn = document.querySelector('.crossIcon, .modal-close, [class*="close"], button[aria-label="Close"]');
                if (closeBtn) closeBtn.click();
                const overlay = document.querySelector('.blackLayer, .overlay, [class*="modal-backdrop"]');
                if (overlay) overlay.remove();
            }""")
        except Exception:
            pass

        await asyncio.sleep(random.uniform(6, 10))
        
        # Wait for job cards to actually appear in DOM
        try:
            await page.wait_for_selector(
                '.cust-job-tuple, .srp-jobtuple-wrapper, .jobTuple, article.jobTuple, .srp-tuple, [class*="jobTuple"], [class*="job-tuple"]',
                timeout=20000,
            )
        except Exception:
            print(f"  [WARN] Job card selector not found within 20s on page {page_num}")
            # Debug: dump a snippet of the page HTML to diagnose
            try:
                body_text = await page.evaluate("() => document.body?.innerText?.substring(0, 500) || 'NO BODY'")
                print(f"  [DEBUG] Page body preview: {body_text[:300]}")
            except Exception:
                pass

        # Scroll to load lazy content
        for _ in range(3):
            await page.mouse.wheel(0, 500)
            await asyncio.sleep(random.uniform(1, 2))
        
        # Extract job cards
        cards = await page.evaluate('''() => {
            const results = [];
            // Try multiple known Naukri card selectors (they rotate their DOM)
            const cardSelectors = [
                '.cust-job-tuple',
                '.srp-jobtuple-wrapper',
                '.jobTuple',
                'article.jobTuple',
                '.srp-tuple',
                '[class*="jobTuple"]',
                '[class*="job-tuple"]',
                '[class*="srp-job"]',
                '.search-job-result > div',
            ];
            let allCards = [];
            for (const sel of cardSelectors) {
                const found = document.querySelectorAll(sel);
                if (found.length > 0) { allCards = found; break; }
            }

            allCards.forEach(card => {
                const titleEl = card.querySelector('a.title, a.jobTitle, .title a, a[id^="job-title"], h2 a, [class*="title"] a');
                const compEl  = card.querySelector('.comp-name, .comp-dtls-wrap a, .subTitle, .companyName, [class*="company"] a, [class*="comp-name"]');
                const descEl  = card.querySelector('.job-desc, .ellipsis, .job-description, .jobDescription, [class*="job-desc"]');

                // Location
                const locEl   = card.querySelector('.loc-wrap, .location, .loc, .locWdth, .locWdth span, [class*="loc"]');

                // Salary
                const salEl   = card.querySelector('.sal-wrap, .salary, .sal, .salaryText, [class*="sal"]');

                // Tags / skills
                const tagEls  = card.querySelectorAll('.tags-gt .tag-li, .skills-list .tag-li, .tags-gt li, .tag-li, .techSkill, [class*="skill"] li, [class*="tag"] li');

                // --- Posted date: try multiple known selectors ---
                const dateSelectors = [
                    '.job-postdate', '.posted-date', '.postedVal',
                    '.postDate', '.job-post-day', '.date', '.days-ago',
                    'span.fleft.postedDate', 'span.postedDate',
                    '.jobTuple-right-cont .postedDate',
                    '[class*="postDate"]', '[class*="posted"]', '[class*="date"]',
                ];
                let rawDate = '';
                for (const sel of dateSelectors) {
                    const el = card.querySelector(sel);
                    if (el && el.textContent.trim()) {
                        rawDate = el.textContent.trim();
                        break;
                    }
                }

                // Fallback: scan ALL spans/divs in card for any text that looks like a date
                if (!rawDate) {
                    const datePattern = /\\d+\\s*(day|week|month|hour|minute|d\\b|w\\b|m\\b)|just\\s*posted|today|yesterday|few\\s+days/i;
                    const allEls = card.querySelectorAll('span, div, time, label');
                    for (const el of allEls) {
                        const txt = el.textContent.trim();
                        if (txt && datePattern.test(txt) && txt.length < 50) {
                            rawDate = txt;
                            break;
                        }
                    }
                }

                const tags = [];
                tagEls.forEach(tag => {
                    const text = tag.textContent.trim();
                    if (text) tags.push(text);
                });

                if (titleEl) {
                    results.push({
                        title:       titleEl.textContent.trim(),
                        url:         titleEl.href,
                        company:     compEl ? compEl.textContent.trim() : 'Unknown',
                        snippet:     descEl ? descEl.textContent.trim() : '',
                        location:    locEl  ? locEl.textContent.trim()  : 'Unknown',
                        salary:      salEl  ? salEl.textContent.trim()  : 'Not disclosed',
                        posted_date: rawDate || 'Just Posted',
                        skills:      tags
                    });
                }
            });
            return results;
        }''')
        
        if not cards:
            consecutive_empty += 1
            print(f"  Page {page_num}: 0 cards extracted from DOM. Advancing to page {page_num + 1} (empty streak: {consecutive_empty})")
            if consecutive_empty >= MAX_CONSECUTIVE_EMPTY:
                print(f"  {MAX_CONSECUTIVE_EMPTY} consecutive empty pages — stopping Naukri pagination.")
                break
            page_num += 1
            await asyncio.sleep(random.uniform(4, 8))
            continue

        consecutive_empty = 0

        matched, skipped = filter_cards_by_role(cards, role)
        for card in skipped:
            print(f"  [SKIP] Not a {role} role: {card.get('title', '')}")

        page_dupes = 0
        page_new = 0
        for card in matched:
            if card.get("url") in existing_urls:
                page_dupes += 1
                print(f"  [DUP] Skipping known URL: {card.get('title', '')}")
                continue
            if not any(c.get("url") == card["url"] for c in all_cards):
                all_cards.append(card)
                new_count += 1
                page_new += 1
                if new_count >= max_jobs:
                    break
        
        print(f"  Page {page_num} summary: {len(cards)} extracted, {len(matched)} role-matched, {page_dupes} duplicates, {page_new} new → total {new_count}/{max_jobs}")

        if page_new == 0:
            print(f"  No new jobs on page {page_num} ({page_dupes} dupes, {len(skipped)} mismatches), advancing to page {page_num + 1}")

        if new_count >= max_jobs:
            break
            
        page_num += 1
        await asyncio.sleep(random.uniform(4, 8))
        
    return all_cards[:new_count]

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


async def scrape_naukri(search_query: str, location: str = "", max_jobs: int = 10, existing_urls=None, archived_urls=None):
    """Main scraping function. Returns list of job dicts."""
    if not HAS_PLAYWRIGHT:
        raise RuntimeError("Playwright is not installed in this environment. Scraper should be run in GitHub Actions.")
    if existing_urls is None:
        existing_urls = set()
    if archived_urls is None:
        archived_urls = set()
    jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS_MODE,
            args=CHROMIUM_LAUNCH_ARGS,
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.113 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            window.chrome = {runtime: {}};
        """)
        
        page = await context.new_page()

        await Stealth().apply_stealth_async(page)
        
        # Warm up session
        await page.goto("https://www.naukri.com/", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)
        
        # Get search results
        cards = await get_search_results(page, search_query, location, max_jobs, existing_urls=existing_urls)
        print(f"  Found {len(cards)} listings for {search_query} in {location or 'India'}")
        
        for i, card in enumerate(cards):
            if not title_matches_search(card.get("title", ""), search_query):
                print(f"  Skipping title mismatch: {card.get('title', '')}")
                continue

            if card["url"] in archived_urls:
                print(f"  [Archive Skip] URL in archive: {card.get('title', '')}")
                continue

            parsed_date = parse_relative_date(card.get("posted_date", "Just Posted"))
            from database import is_job_too_old
            if is_job_too_old(parsed_date, max_days=90):
                print(f"  [Archive Skip] Job URL is older than 3 months: {card['url']}")
                archived_urls.add(card["url"])
                jobs.append({
                    "title": card["title"],
                    "company": card["company"],
                    "url": card["url"],
                    "description": "",
                    "email": None,
                    "location": extract_city_name(card.get("location", ""), card.get("company", "")),
                    "country": "India",
                    "platform": "Naukri",
                    "job_type": "Archived",
                    "workplace_type": "",
                    "posted_date": parsed_date,
                    "salary": card.get("salary", "Not disclosed"),
                    "skills": [],
                    "_archived": True,
                })
                continue

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
            
            loc = extract_city_name(card.get("location", ""), card.get("company", ""))
            job_type = infer_job_type(card["title"], desc)
            workplace = infer_workplace_type(loc, desc)
            
            jobs.append({
                "title": card["title"],
                "company": card["company"],
                "url": card["url"],
                "description": desc,
                "email": email,
                "location": loc,
                "country": "India",
                "platform": "Naukri",
                "job_type": job_type,
                "workplace_type": workplace,
                "posted_date": parsed_date,
                "salary": card.get("salary", "Not disclosed"),
                "skills": clean_skills(card.get("skills", []), card["title"])
            })
            print(f"  [SUCCESS] [{i+1}/{len(cards)}] {card['company']}")
        
        await browser.close()
    
    return jobs


# ---------------------------------------------------------------------------
# Indeed Scraper — JSearch API (RapidAPI)
# ---------------------------------------------------------------------------

async def scrape_indeed(search_query: str, location: str = "", max_jobs: int = 10, existing_urls=None, archived_urls=None):
    """Fetch job listings via Indeed Scraper API (RapidAPI). Returns list of job dicts."""
    if existing_urls is None:
        existing_urls = set()
    if archived_urls is None:
        archived_urls = set()

    api_key = os.getenv("RAPIDAPI_KEY", "").strip()
    if not api_key:
        print("[Indeed API Error] RAPIDAPI_KEY is empty or missing from environment!")
        return []

    loc = location if location and location.strip() else "USA"
    country_code = "in" if "india" in loc.lower() else "us"
    payload = {
        "scraper": {
            "maxRows": 20,
            "query": search_query,
            "location": loc,
            "sort": "relevance",
            "fromDays": "14",
            "country": country_code,
        }
    }

    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": "indeed-scraper-api.p.rapidapi.com",
        "x-rapidapi-key": api_key,
    }

    print(f"[Indeed API] Querying: role='{search_query}', location='{loc}'")

    try:
        response = _requests.post(
            "https://indeed-scraper-api.p.rapidapi.com/api/job",
            headers=headers,
            json=payload,
            timeout=20,
        )
    except _requests.exceptions.RequestException as e:
        print(f"[Indeed API Error] Request failed: {e}")
        return []

    if response.status_code not in (200, 201):
        print(f"[Indeed API Error {response.status_code}]: {response.text}")
        return []

    try:
        res_json = response.json()
    except (ValueError, json.JSONDecodeError):
        print(f"[Indeed API Warning] Invalid JSON response: {response.text[:200]}")
        return []

    if isinstance(res_json, dict) and "returnvalue" in res_json:
        jobs_list = res_json.get("returnvalue", {}).get("data", [])
    elif isinstance(res_json, dict):
        jobs_list = res_json.get("data", [])
    else:
        jobs_list = []

    if not jobs_list:
        print(f"[Indeed API] No results for role='{search_query}', location='{loc}'.")
        return []

    valid_jobs = []
    batch_urls = set()
    raw_count = len(jobs_list)
    skipped_dup = 0
    skipped_mismatch = 0
    skipped_invalid = 0

    for item in jobs_list:
        if len(valid_jobs) >= max_jobs:
            break

        # ── Check 3: Required fields validation (run first — cheapest) ──
        if not isinstance(item, dict):
            skipped_invalid += 1
            continue

        title = (item.get("title") or "").strip()
        company = (item.get("companyName") or "").strip() or "Unknown"

        job_key = item.get("jobKey") or item.get("id") or ""
        raw_url = (item.get("jobUrl") or item.get("applyUrl") or "").strip()
        if not raw_url or raw_url.rstrip("/") == "https://www.indeed.com/viewjob":
            if job_key:
                apply_url = f"https://www.indeed.com/viewjob?jk={job_key}"
            else:
                apply_url = raw_url if raw_url else f"https://www.indeed.com/viewjob?ref={hash(company + title)}"
        else:
            apply_url = raw_url

        if not title or not apply_url:
            skipped_invalid += 1
            print(f"  [Skip Invalid] Missing title or URL")
            continue

        # ── Check 2: Database & batch deduplication ──
        if "linkedin.com" in apply_url.lower():
            skipped_dup += 1
            print(f"  [Skip Duplicate] LinkedIn URL (handled by LinkedIn scraper): {title}")
            continue

        if apply_url in existing_urls:
            skipped_dup += 1
            print(f"  [Skip Duplicate] Known Indeed URL in DB: {title}")
            continue

        if apply_url in batch_urls:
            skipped_dup += 1
            print(f"  [Skip Duplicate] URL already in current batch: {title}")
            continue

        # ── Check 1: Title / role relevance match ──
        if not title_matches_search(title, search_query):
            skipped_mismatch += 1
            print(f"  [Skip Mismatch] Title does not match '{search_query}': {title}")
            continue

        # ── Check: Archived URL / 3-month age exclusion ──
        if apply_url in archived_urls:
            skipped_dup += 1
            print(f"  [Archive Skip] URL in archive: {title}")
            continue

        # ── All checks passed — safe to enrich and count ──
        batch_urls.add(apply_url)

        raw_loc = item.get("location")
        if isinstance(raw_loc, dict):
            item_loc = (raw_loc.get("formattedAddressShort") or f"{raw_loc.get('city', '')}, {raw_loc.get('countryCode', '')}").strip(", ")
        else:
            item_loc = str(raw_loc or "").strip()

        description = (item.get("descriptionText") or item.get("descriptionHtml") or "").strip()

        email = None
        emails = re.findall(r'[a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+', description)
        if emails:
            email = emails[0]

        loc = extract_city_name(item_loc, company) if item_loc else "Unknown"
        job_type = infer_job_type(title, description)
        workplace = infer_workplace_type(loc, description)

        posted_raw = item.get("datePublished") or item.get("age") or ""
        if isinstance(posted_raw, str) and posted_raw:
            posted_date = parse_relative_date(posted_raw)
        elif hasattr(posted_raw, "strftime"):
            posted_date = posted_raw.strftime("%Y-%m-%d")
        else:
            posted_date = datetime.today().strftime("%Y-%m-%d")

        raw_salary = item.get("salary")
        if isinstance(raw_salary, dict):
            salary = raw_salary.get("salaryText", "Not disclosed")
        else:
            salary = raw_salary or "Not disclosed"

        from database import is_job_too_old
        if is_job_too_old(posted_date, max_days=90):
            print(f"  [Archive Skip] Job URL is older than 3 months: {apply_url}")
            archived_urls.add(apply_url)
            valid_jobs.append({
                "title": title,
                "company": company,
                "url": apply_url,
                "description": "",
                "email": None,
                "location": loc,
                "country": "India" if country_code == "in" else "US",
                "platform": "Indeed",
                "job_type": "Archived",
                "workplace_type": "",
                "posted_date": posted_date,
                "salary": salary,
                "skills": [],
                "_archived": True,
            })
            continue

        valid_jobs.append({
            "title": title,
            "company": company,
            "url": apply_url,
            "description": description or "No description available",
            "email": email,
            "location": loc,
            "country": "India" if country_code == "in" else "US",
            "platform": "Indeed",
            "job_type": job_type,
            "workplace_type": workplace,
            "posted_date": posted_date,
            "salary": salary,
            "skills": [],
        })
        print(f"  [SUCCESS] [{len(valid_jobs)}/{max_jobs}] {company} — {title}")

    skipped_total = skipped_dup + skipped_mismatch + skipped_invalid
    print(f"[Indeed API] Total NEW valid jobs retrieved: {len(valid_jobs)} (Filtered out {raw_count - len(valid_jobs)} duplicates/mismatches)")
    print(f"  Breakdown — dup={skipped_dup}, mismatch={skipped_mismatch}, invalid={skipped_invalid} for '{search_query}'")
    return valid_jobs


# ---------------------------------------------------------------------------
# LinkedIn Scraper
# ---------------------------------------------------------------------------

async def _linkedin_human_delay(lo=2.0, hi=4.5):
    await asyncio.sleep(random.uniform(lo, hi))


async def _linkedin_slow_scroll(page, times=3):
    for _ in range(times):
        await page.mouse.wheel(0, random.randint(400, 800))
        await asyncio.sleep(random.uniform(0.3, 0.6))


async def get_linkedin_search_results(page, search_query, location="", max_jobs=10, existing_urls=None, internships=False):
    if existing_urls is None:
        existing_urls = set()
    all_cards = []
    all_seen_urls = set()
    new_count = 0
    start = 0

    while new_count < max_jobs and start < 200:
        params_parts = [f"keywords={urllib.parse.quote_plus(search_query)}"]
        if location:
            params_parts.append(f"location={urllib.parse.quote_plus(location)}")
        if internships:
            params_parts.append("f_E=1")
        else:
            params_parts.append("f_E=2%2C3%2C4%2C5")
        if start > 0:
            params_parts.append(f"start={start}")

        url = f"https://www.linkedin.com/jobs/search/?{'&'.join(params_parts)}"
        print(f"  Loading LinkedIn search (start={start}): {url}")

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=40000)
        except Exception as e:
            print(f"  Failed to load LinkedIn page: {e}")
            break

        try:
            await page.wait_for_selector(
                "ul.jobs-search__results-list li, .job-search-card, .base-card",
                timeout=15000,
            )
        except Exception:
            pass

        await _linkedin_slow_scroll(page, times=2)
        await asyncio.sleep(random.uniform(1.0, 2.0))

        need_more = new_count < max_jobs
        if need_more:
            see_more = await page.query_selector(
                "button.infinite-scroller__show-more-button, button[aria-label*='more']"
            )
            if see_more:
                try:
                    await see_more.click()
                    await asyncio.sleep(random.uniform(1.0, 2.0))
                except Exception:
                    pass

        try:
            cards = await page.evaluate("""() => {
                const cards = document.querySelectorAll(
                    'ul.jobs-search__results-list li, .job-search-card, div.base-card'
                );
                return Array.from(cards).map(card => {
                    const titleEl = card.querySelector('h3, .base-search-card__title, .job-search-card__title');
                    const companyEl = card.querySelector('h4, .base-search-card__subtitle, .job-search-card__company-name');
                    const locationEl = card.querySelector('.job-search-card__location, [class*="location"]');
                    const linkEl = card.querySelector('a[href*="/jobs/view/"], a.base-card__full-link');
                    // --- Posted date: try <time> with datetime attr first, then broader selectors ---
                    let rawDate = '';
                    const timeEl = card.querySelector('time');
                    if (timeEl) {
                        const dt = timeEl.getAttribute('datetime');
                        if (dt) {
                            rawDate = dt;
                        } else {
                            rawDate = timeEl.textContent.trim();
                        }
                    }
                    if (!rawDate) {
                        const dateSelectors = [
                            '.job-search-card__listdate', '.job-search-card__listdate--new',
                            '[class*="listdate"]', '[class*="posted-date"]',
                            '[class*="date"]', '[class*="age"]',
                        ];
                        for (const sel of dateSelectors) {
                            const el = card.querySelector(sel);
                            if (el && el.textContent.trim()) {
                                rawDate = el.textContent.trim();
                                break;
                            }
                        }
                    }
                    if (!rawDate) {
                        const datePatterns = /(\d+\s*(?:hour|minute|second|day|week|month)s?\s+ago)|(\d+[hdwmy]\b)|(just now|today|yesterday|recently)/i;
                        const allEls = card.querySelectorAll('span, div, time, p');
                        for (const el of allEls) {
                            const txt = el.textContent.trim();
                            if (txt && datePatterns.test(txt) && txt.length < 60) {
                                rawDate = txt;
                                break;
                            }
                        }
                    }
                    if (!rawDate) rawDate = '';

                    const subtitleEls = card.querySelectorAll('.job-search-card__subtitle, .base-search-card__metadata');
                    let salary = '';
                    subtitleEls.forEach(el => {
                        const txt = el.textContent.trim();
                        if (txt.includes('₹') || txt.includes('$') || txt.includes('PA') || txt.includes('LPA') || /\\d{2,}/.test(txt)) {
                            salary = txt;
                        }
                    });
                    let skills = [];
                    const skillEls = card.querySelectorAll('.job-criteria__text, .job-criteria-subheader__value, [class*="skill"]');
                    skillEls.forEach(el => {
                        const t = el.textContent.trim();
                        if (t && t.length < 60) skills.push(t);
                    });
                    return {
                        title: titleEl ? titleEl.innerText.trim() : '',
                        company: companyEl ? companyEl.innerText.trim() : '',
                        location: locationEl ? locationEl.innerText.trim() : '',
                        url: linkEl ? linkEl.href.split('?')[0] : '',
                        posted_date_raw: rawDate,
                        salary: salary || 'Not disclosed',
                        skills: skills,
                    };
                }).filter(j => j.title && j.company && j.url);
            }""")
        except Exception as e:
            print(f"  LinkedIn JS eval failed: {e}")
            break

        if not cards:
            print(f"  No more LinkedIn jobs found at start={start}.")
            break

        dup_on_page = 0
        for card in cards:
            if card["url"] in existing_urls or card["url"] in all_seen_urls:
                dup_on_page += 1
                print(f"  [DUP] Skipping known LinkedIn URL: {card.get('title', '')}")
                continue
            if not title_matches_search(card.get("title", ""), search_query):
                print(f"  Skipping title mismatch: {card.get('title', '')}")
                continue
            all_seen_urls.add(card["url"])
            all_cards.append(card)
            new_count += 1
            if new_count >= max_jobs:
                break

        if cards and dup_on_page == len(cards):
            print(f"  All {len(cards)} cards on this page are duplicates — stopping LinkedIn pagination.")
            break

        print(f"  LinkedIn: {new_count} new matching jobs so far...")
        if new_count >= max_jobs:
            break

        start += 25
        await asyncio.sleep(random.uniform(2, 4))

    return all_cards[:new_count]


async def get_linkedin_job_description(page, url):
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(random.uniform(1.5, 3.0))

        result = await page.evaluate("""() => {
            const sels = [
                '.jobs-description-content__text', '.jobs-description__content',
                '.show-more-less-html__markup', '[class*="jobs-description"]',
                '.description__text',
            ];
            let el = null;
            for (const s of sels) { el = document.querySelector(s); if (el) break; }
            return { description: el ? el.innerText.trim() : '' };
        }""")
        return result.get("description", "")
    except Exception:
        return ""


async def scrape_linkedin(search_query: str, location: str = "", max_jobs: int = 10, existing_urls=None, internships: bool = False, archived_urls=None):
    """Scrape linkedin.com/jobs for listings. Returns list of job dicts matching our schema."""
    if not HAS_PLAYWRIGHT:
        raise RuntimeError("Playwright is not installed in this environment. Scraper should be run in GitHub Actions.")
    if existing_urls is None:
        existing_urls = set()
    if archived_urls is None:
        archived_urls = set()
    jobs = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS_MODE,
            args=CHROMIUM_LAUNCH_ARGS,
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.113 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            window.chrome = {runtime: {}};
        """)

        page = await context.new_page()

        await Stealth().apply_stealth_async(page)

        print("  Warming up LinkedIn session...")
        try:
            await page.goto("https://www.linkedin.com/jobs/", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(1.5)
        except Exception:
            print("  [WARN] LinkedIn warm-up failed, continuing anyway.")

        li_location = location if location else "India"
        cards = await get_linkedin_search_results(page, search_query, li_location, max_jobs, existing_urls=existing_urls, internships=internships)
        print(f"  Found {len(cards)} LinkedIn listings for '{search_query}' in '{li_location}'")

        for i, card in enumerate(cards):
            if card["url"] in existing_urls:
                print(f"  [DUP] Skipping known LinkedIn URL: {card.get('title', '')}")
                continue

            if not title_matches_search(card.get("title", ""), search_query):
                print(f"  Skipping title mismatch: {card.get('title', '')}")
                continue

            if card["url"] in archived_urls:
                print(f"  [Archive Skip] URL in archive: {card.get('title', '')}")
                continue

            if i > 0:
                await asyncio.sleep(random.uniform(1.5, 3.0))

            desc = await get_linkedin_job_description(page, card["url"])
            if not desc:
                desc = card.get("snippet", "No description available")

            email = None
            emails = re.findall(r'[a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+', desc)
            if emails:
                email = emails[0]

            loc = extract_city_name(card.get("location", ""), card.get("company", ""))
            job_type = infer_job_type(card["title"], desc)
            workplace = infer_workplace_type(loc, desc)

            raw_date = card.get("posted_date_raw", "")
            parsed_date = parse_linkedin_date(raw_date) if raw_date else parse_relative_date("Just Posted")

            from database import is_job_too_old
            if is_job_too_old(parsed_date, max_days=90):
                print(f"  [Archive Skip] Job URL is older than 3 months: {card['url']}")
                archived_urls.add(card["url"])
                jobs.append({
                    "title": card["title"],
                    "company": card["company"],
                    "url": card["url"],
                    "description": "",
                    "email": None,
                    "location": loc,
                    "country": "India",
                    "platform": "LinkedIn",
                    "job_type": "Archived",
                    "workplace_type": "",
                    "posted_date": parsed_date,
                    "salary": card.get("salary", "Not disclosed"),
                    "skills": [],
                    "_archived": True,
                })
                continue

            jobs.append({
                "title": card["title"],
                "company": card["company"],
                "url": card["url"],
                "description": desc,
                "email": email,
                "location": loc,
                "country": "India",
                "platform": "LinkedIn",
                "job_type": job_type,
                "workplace_type": workplace,
                "posted_date": parsed_date,
                "salary": card.get("salary", "Not disclosed"),
                "skills": card.get("skills", []),
            })
            print(f"  [SUCCESS] [{i+1}/{len(cards)}] {card['company']}")

        await browser.close()

    return jobs

