"""
Daily Scraper: Run this to scrape Naukri and populate the database.
Usage: python3 daily_scrape.py [--roles "Data Analyst,Software Engineer"] [--max 20]

Note: Opens a visible browser window (required to bypass Naukri's bot detection).
"""
import asyncio
import sys
import os
import argparse
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine
import models
from scoring_engine import analyze_job
from scraper import scrape_naukri, scrape_indeed, clean_skills, title_matches_search, normalize_base_role, build_scrape_query

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
    db = SessionLocal()
    total_new = 0
    total_skipped = 0
    listing_type = "internships" if internships else "jobs"

    # ── Cleanup: delete jobs older than 90 days ──
    try:
        cutoff = date.today() - timedelta(days=90)
        stale_jobs = db.query(models.Job).filter(models.Job.posted_date != None, models.Job.posted_date < cutoff).all()
        if stale_jobs:
            stale_ids = [j.id for j in stale_jobs]
            db.query(models.Score).filter(models.Score.job_id.in_(stale_ids)).delete(synchronize_session="fetch")
            db.query(models.Job).filter(models.Job.id.in_(stale_ids)).delete(synchronize_session="fetch")
            db.commit()
            print(f"[CLEANUP] Deleted {len(stale_jobs)} {listing_type} older than {cutoff.isoformat()}")
        else:
            print(f"[CLEANUP] No {listing_type} older than 90 days found.")
    except Exception as e:
        db.rollback()
        print(f"[CLEANUP] Failed: {e}")

    try:
        for i, role in enumerate(roles):
            base_role = normalize_base_role(role)
            search_query = build_scrape_query(base_role, internships=internships)
            print(f"\n{'='*50}")
            print(f"[{i+1}/{len(roles)}] Scraping {listing_type}: {base_role}")
            print(f"  Search query: {search_query}")
            print(f"{'='*50}")
            
            try:
                jobs = []
                p_lower = platform.lower()
                if p_lower in ("naukri", "all"):
                    print(f"  [Scraping Naukri] query={search_query}, location={city}")
                    n_jobs = await scrape_naukri(search_query, location=city, max_jobs=max_per_role)
                    jobs.extend(n_jobs)
                if p_lower in ("indeed", "all"):
                    print(f"  [Scraping Indeed] query={search_query}, location={city}")
                    i_jobs = await scrape_indeed(search_query, location=city, max_jobs=max_per_role)
                    jobs.extend(i_jobs)
            except Exception as e:
                print(f"  [ERROR] Scrape failed for {base_role}: {e}")
                continue
            
            for jd in jobs:
                if not title_matches_search(jd.get("title", ""), search_query):
                    print(f"  [SKIP] Title mismatch: {jd.get('title', '')}")
                    total_skipped += 1
                    continue

                # Skip duplicates
                existing = db.query(models.Job).filter(models.Job.url == jd["url"]).first()
                if existing:
                    total_skipped += 1
                    continue
                
                # Save job — always store the base role name
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
                db.add(job)
                db.commit()
                db.refresh(job)
                
                # Score
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
                print(f"  [OK] {jd['company']} -> {score_data['final_score']}% scam ({len(score_data['flags'])} flags)")
                
                # Notify dashboard via API loopback
                try:
                    import requests
                    requests.post("http://localhost:8000/api/notifications/publish", 
                                  json={"event": "new_job", "title": jd["title"], "company": jd["company"]},
                                  timeout=2)
                except Exception as e:
                    pass
            
            # Delay between roles
            if i < len(roles) - 1:
                delay = 10
                print(f"  [WAIT] Waiting {delay}s before next role...")
                await asyncio.sleep(delay)
    finally:
        db.close()
    
    print(f"\n{'='*50}")
    print(f"Done! Added {total_new} new jobs, skipped {total_skipped} duplicates.")
    print(f"{'='*50}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape jobs and populate ShieldDB")
    parser.add_argument("--roles", type=str, default=None, help="Comma-separated roles to scrape (default: all)")
    parser.add_argument("--max", type=int, default=20, help="Max jobs per role (default: 20)")
    parser.add_argument("--platform", type=str, default="all", choices=["naukri", "indeed", "all"], help="Platform to scrape (naukri, indeed, all)")
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