from urllib.parse import quote_plus
from playwright.async_api import Browser
from models import Job, SearchFilters
from scrapers.base import BaseScraper, retry

_EXP_MAP = {"Fresher": "1", "Junior": "2", "Mid": "3", "Senior": "4", "Lead": "5"}
_TYPE_MAP = {"Full-time": "F", "Part-time": "P", "Contract": "C", "Internship": "I"}


class LinkedInScraper(BaseScraper):
    name = "LinkedIn"

    def __init__(self, browser: Browser):
        super().__init__(browser)

    @retry(max_attempts=3)
    async def scrape(self, filters: SearchFilters) -> list[Job]:
        all_jobs: list[Job] = []
        seen = set()
        for location in filters.locations:
            jobs = await self._scrape_location(filters, location)
            for j in jobs:
                key = (j.title.lower(), j.company.lower())
                if key not in seen:
                    seen.add(key)
                    all_jobs.append(j)
        return all_jobs

    async def _scrape_location(self, filters: SearchFilters, location: str) -> list[Job]:
        jobs: list[Job] = []
        page = await self.new_page()
        try:
            field = quote_plus(filters.job_field)
            loc = quote_plus(location)
            url = f"https://www.linkedin.com/jobs/search/?keywords={field}&location={loc}&position=1&pageNum=0"

            if filters.days_posted:
                url += f"&f_TPR=r{filters.days_posted * 86400}"

            exp_code = _EXP_MAP.get(filters.experience_level)
            if exp_code:
                url += f"&f_E={exp_code}"
            type_code = _TYPE_MAP.get(filters.job_type)
            if type_code:
                url += f"&f_JT={type_code}"

            await page.goto(url, wait_until="domcontentloaded", timeout=40000)
            await self.human_delay(2.0, 3.5)

            try:
                await page.wait_for_selector(
                    "ul.jobs-search__results-list li, .job-search-card, .base-card",
                    timeout=15000
                )
            except Exception:
                pass

            for _ in range(6):
                await self.scroll_to_bottom(page, times=2)
                await self.human_delay(1.0, 2.0)
                see_more = await page.query_selector(
                    "button.infinite-scroller__show-more-button, button[aria-label*='more']"
                )
                if see_more:
                    try:
                        await see_more.click()
                        await self.human_delay(1.5, 2.5)
                    except Exception:
                        pass

            raw = await page.evaluate("""
                () => {
                    const cards = document.querySelectorAll(
                        'ul.jobs-search__results-list li, .job-search-card, div.base-card'
                    );
                    return Array.from(cards).map(card => {
                        const titleEl = card.querySelector('h3, .base-search-card__title, .job-search-card__title');
                        const companyEl = card.querySelector('h4, .base-search-card__subtitle, .job-search-card__company-name');
                        const locationEl = card.querySelector('.job-search-card__location, [class*="location"]');
                        const linkEl = card.querySelector('a[href*="/jobs/view/"], a.base-card__full-link');
                        return {
                            title: titleEl ? titleEl.innerText.trim() : '',
                            company: companyEl ? companyEl.innerText.trim() : '',
                            location: locationEl ? locationEl.innerText.trim() : '',
                            url: linkEl ? linkEl.href.split('?')[0] : ''
                        };
                    }).filter(j => j.title && j.company);
                }
            """)

            for item in raw:
                jobs.append(Job(
                    title=item["title"],
                    company=item["company"],
                    location=item["location"] or location,
                    experience=filters.experience_level if filters.experience_level != "Any" else "",
                    job_type=filters.job_type if filters.job_type != "Any" else "",
                    salary="",
                    url=item["url"] or url,
                    source=self.name,
                ))
        finally:
            await page.context.close()
        return jobs
