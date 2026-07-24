"""
Daily Scraper: Run this to scrape Naukri and populate the database.
Usage: python3 daily_scrape.py [--roles "Data Analyst,Software Engineer"] [--max 20]

Note: Runs Playwright in non-headless mode by default.
"""
import asyncio
import sys
import os
import argparse
import time as _time
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine, post_scrape_cleanup, load_archived_urls, archive_job_url
import models
from scoring_engine import analyze_job
from scraper import scrape_naukri, scrape_indeed, scrape_linkedin, clean_skills, title_matches_search, normalize_base_role, build_scrape_query
from sqlalchemy.exc import IntegrityError

models.Base.metadata.create_all(bind=engine)

ALL_ROLES = [
    "Data Analyst",
    "Software Engineer",
    "Product Manager",
    "Cybersecurity Analyst",
    "UI UX Designer",
    "Customer Support",
    "Sales Executive",
    "DevOps Engineer",
    "Business Analyst",
    "Marketing Manager",
    "Human Resources",
    "Content Writer",
    "Full Stack Developer",
    "Cloud Engineer",
    "Machine Learning Engineer",
    "Backend Developer",
    "Frontend Developer",
    "Data Scientist",
    "Project Manager",
    "Quality Analyst",
    "Data Entry",
    "Virtual Assistant",
    "Graphic Designer",
    "Digital Marketing",
    "Freelance Writer",
    "Online Tutor",
    "SEO Specialist",
    "Accountant",
    "Web Developer",
    "System Administrator",
    "Network Engineer",
    "HR Recruiter",
    "Executive Assistant",
    "Translator",
    "Social Media Manager",
    "Call Center Executive",
    "Operations Manager",
    "Video Editor",
    "Mobile App Developer",
    "Cybersecurity Engineer","UX Researcher",
    "Data Engineer",
    "NLP Engineer",
    "Game Developer",
    "Technical Product Manager",
    "IT Analyst"
]

async def run(roles, max_per_role, platform="all", city="", internships=False):
    total_new = 0
    total_skipped = 0
    total_archived = 0
    listing_type = "internships" if internships else "jobs"
    run_start = _time.time()

    archived_urls = load_archived_urls()

    for i, role in enumerate(roles):
        base_role = normalize_base_role(role)
        search_query = build_scrape_query(base_role, internships=internships)
        pct = round((i / len(roles)) * 100)
        elapsed_min = round((_time.time() - run_start) / 60, 1)
        print(f"\n{'='*60}")
        print(f"[PROGRESS] Starting role {i+1}/{len(roles)}: {base_role} — {pct}% complete ({elapsed_min}m elapsed)")
        print(f"  Search query: {search_query}")
        print(f"{'='*60}")

        # Fresh session per role to prevent connection pool exhaustion over long runs
        db = SessionLocal()

        try:
            existing_urls = set(row[0] for row in db.query(models.Job.url).all() if row[0])
            print(f"  [DB] {len(existing_urls)} existing job URLs in database")
            
            try:
                jobs = []
                p_lower = platform.lower()
                if p_lower in ("naukri", "all"):
                    print(f"  [Scraping Naukri] query={search_query}, location={city}")
                    n_jobs = await scrape_naukri(search_query, location=city, max_jobs=max_per_role, existing_urls=existing_urls, archived_urls=archived_urls)
                    jobs.extend(n_jobs)
                    for j in n_jobs:
                        existing_urls.add(j["url"])
                if p_lower in ("indeed", "all"):
                    print(f"  [Scraping Indeed] query={search_query}, location={city}")
                    i_jobs = await scrape_indeed(search_query, location=city, max_jobs=max_per_role, existing_urls=existing_urls, archived_urls=archived_urls)
                    jobs.extend(i_jobs)
                    for j in i_jobs:
                        existing_urls.add(j["url"])
                if p_lower in ("linkedin", "all"):
                    print(f"  [Scraping LinkedIn] query={search_query}, location={city}")
                    li_jobs = await scrape_linkedin(search_query, location=city, max_jobs=max_per_role, existing_urls=existing_urls, internships=internships, archived_urls=archived_urls)
                    jobs.extend(li_jobs)
                    for j in li_jobs:
                        existing_urls.add(j["url"])
            except Exception as e:
                print(f"  [ERROR] Scrape failed for {base_role}: {e}")
                continue
            
            role_new = 0
            for jd in jobs:
                if jd.get("_archived"):
                    archive_job_url(jd["url"], jd.get("posted_date"))
                    total_archived += 1
                    continue

                if not title_matches_search(jd.get("title", ""), search_query):
                    print(f"  [SKIP] Title mismatch: {jd.get('title', '')}")
                    total_skipped += 1
                    continue

                stored_job_type = jd.get("job_type")
                if internships:
                    stored_job_type = "Internship"

                job = models.Job(
                    title=jd["title"],
                    company=jd["company"],
                    email=jd.get("email"),
                    url=jd["url"],
                    description=jd["description"],
                    role=base_role,
                    location=jd.get("location"),
                    country=jd.get("country"),
                    platform=jd.get("platform"),
                    job_type=stored_job_type,
                    workplace_type=jd.get("workplace_type"),
                    posted_date=jd.get("posted_date"),
                    salary=jd.get("salary"),
                    skills=clean_skills(jd.get("skills") or [], jd.get("title", ""), base_role)
                )
                try:
                    db.add(job)
                    db.commit()
                    db.refresh(job)
                except IntegrityError:
                    db.rollback()
                    print(f"[DB Skip] Job already exists with URL: {jd['url']}")
                    total_skipped += 1
                    continue
                
                score_data = analyze_job(job.description, job.company, job.email)
                score = models.Score(
                    job_id=job.id,
                    final_score=score_data["final_score"],
                    trust_tier=score_data["trust_tier"],
                    flags=score_data["flags"],
                    raw_threats=score_data["raw_threats"],
                )
                db.add(score)
                db.commit()
                total_new += 1
                role_new += 1
                print(f"  [OK] {jd['company']} -> {score_data['final_score']}% scam ({len(score_data['flags'])} flags)")
                
                try:
                    import requests
                    requests.post("http://localhost:8000/api/notifications/publish", 
                                  json={"event": "new_job", "title": jd["title"], "company": jd["company"]},
                                  timeout=2)
                except Exception:
                    pass

            print(f"  [ROLE DONE] {base_role}: {role_new} new {listing_type} added this round (total: {total_new})")
        except Exception as e:
            db.rollback()
            print(f"  [ERROR] DB error for {base_role}: {e}")
        finally:
            db.close()
            
        # Delay between roles
        if i < len(roles) - 1:
            delay = 10
            print(f"  [WAIT] Waiting {delay}s before next role...")
            await asyncio.sleep(delay)

    post_scrape_cleanup()

    total_min = round((_time.time() - run_start) / 60, 1)
    print(f"\n{'='*60}")
    print(f"DONE! Added {total_new} new {listing_type}, skipped {total_skipped} mismatches, archived {total_archived} old listings.")
    print(f"Total runtime: {total_min} minutes")
    print(f"{'='*60}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape jobs and populate ShieldDB")
    parser.add_argument("--roles", type=str, default=None, help="Comma-separated roles to scrape (default: all)")
    parser.add_argument("--max", type=int, default=20, help="Max jobs per role (default: 20)")
    parser.add_argument("--platform", type=str, default="all", choices=["naukri", "indeed", "linkedin", "all"], help="Platform to scrape (naukri, indeed, linkedin, all)")
    parser.add_argument("--city", type=str, default="", help="City/location filter (e.g. Mumbai, Bangalore)")
    parser.add_argument("--internships", action="store_true", help="Scrape internship listings for each role (stored under the base role name)")
    args = parser.parse_args()
    
    roles = args.roles.split(",") if args.roles else ALL_ROLES
    roles = [normalize_base_role(r.strip()) for r in roles]
    
    print(f"ShieldDB Daily Scrape")
    print(f"Platform: {args.platform}")
    print(f"City: {args.city or 'Any'}")
    print(f"Listing type: {'Internships' if args.internships else 'Jobs'}")
    print(f"Roles: {len(roles)}")
    print(f"Max per role: {args.max}")
    
    asyncio.run(run(roles, args.max, args.platform, args.city, args.internships))