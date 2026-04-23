"""
Daily Scraper: Run this to scrape Naukri and populate the database.
Usage: python3 daily_scrape.py [--roles "Data Analyst,Software Engineer"] [--max 20]

Note: Opens a visible browser window (required to bypass Naukri's bot detection).
"""
import asyncio
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine
import models
from scoring_engine import analyze_job
from scraper import scrape_naukri

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
    "Cybersecurity Engineer"
]

async def run(roles, max_per_role):
    db = SessionLocal()
    total_new = 0
    total_skipped = 0
    
    try:
        for i, role in enumerate(roles):
            print(f"\n{'='*50}")
            print(f"[{i+1}/{len(roles)}] Scraping: {role}")
            print(f"{'='*50}")
            
            try:
                jobs = await scrape_naukri(role, max_jobs=max_per_role)
            except Exception as e:
                print(f"  ❌ Scrape failed for {role}: {e}")
                continue
            
            for jd in jobs:
                # Skip duplicates
                existing = db.query(models.Job).filter(models.Job.url == jd["url"]).first()
                if existing:
                    total_skipped += 1
                    continue
                
                # Save job
                job = models.Job(
                    title=jd["title"],
                    company=jd["company"],
                    email=jd.get("email"),
                    url=jd["url"],
                    description=jd["description"],
                    role=role,
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
                print(f"  ✅ {jd['company']} → {score_data['final_score']}% scam ({len(score_data['flags'])} flags)")
                
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
                print(f"  ⏳ Waiting {delay}s before next role...")
                await asyncio.sleep(delay)
    finally:
        db.close()
    
    print(f"\n{'='*50}")
    print(f"✅ Done! Added {total_new} new jobs, skipped {total_skipped} duplicates.")
    print(f"{'='*50}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Naukri and populate ShieldDB")
    parser.add_argument("--roles", type=str, default=None, help="Comma-separated roles to scrape (default: all)")
    parser.add_argument("--max", type=int, default=20, help="Max jobs per role (default: 20)")
    args = parser.parse_args()
    
    roles = args.roles.split(",") if args.roles else ALL_ROLES
    roles = [r.strip() for r in roles]
    
    print(f"ShieldDB Daily Scrape")
    print(f"Roles: {len(roles)}")
    print(f"Max per role: {args.max}")
    
    asyncio.run(run(roles, args.max))