import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from database import SessionLocal
import models
from scoring_engine import analyze_job

scam_jobs = [
    {
        "title": "Data Entry Specialist (Remote)",
        "company": "Global Enterprises Pvt",
        "url": "https://www.naukri.com/fake-job-1",
        "email": "hr@gmail.com",
        "role": "Data Entry",
        "description": "Earn unlimited easily! We are urgently hiring for remote jobs. We will send you a check to purchase your own equipment before you start. A small registration fee is required. Pay via cryptocurrency for registration fee."
    },
    {
        "title": "Frontend Developer",
        "company": "NextGen Solutions",
        "url": "https://www.naukri.com/fake-job-2",
        "email": "recruitment@yahoo.com",
        "role": "Frontend Developer",
        "description": "100% Guaranteed Selection! Message us on telegram for your remote interview. Please send your aadhar card number and share bank details for our payroll processing system immediately before the limited time offer expires."
    },
    {
        "title": "Software Engineer",
        "company": "Google",
        "url": "https://www.naukri.com/fake-job-3",
        "email": "careers@google-careers-apply.com",
        "role": "Software Engineer",
        "description": "We are urgently hiring Software Engineers! To apply, fill this form bit.ly/google-apply and send a processed security deposit. This is a limited time offer so act now or lose. No skills required."
    },
    {
        "title": "Sales Executive",
        "company": "Unknown",
        "url": "https://www.naukri.com/fake-job-4",
        "email": "info@protonmail.com",
        "role": "Sales Executive",
        "description": "💰💰💰 EARN BIG 🔥🔥🔥 Be your own boss and earn thousands daily. Build your downline. No qualification needed, anyone can apply. Eas\u200By Mo\u200Bney guaranteed! 🚀💸🚀"
    }
]

def inject_scams():
    db = SessionLocal()
    try:
        print("Injecting 4 realistic scam jobs into the database...")
        for jd in scam_jobs:
            job_db = models.Job(
                title=jd["title"],
                company=jd["company"],
                url=jd["url"],
                email=jd["email"],
                role=jd["role"],
                description=jd["description"]
            )
            db.add(job_db)
            db.commit()
            db.refresh(job_db)
            
            # Run the scoring engine
            score_data = analyze_job(job_db.description, job_db.company, job_db.email)
            score_db = models.Score(
                job_id=job_db.id,
                final_score=score_data["final_score"],
                trust_tier=score_data["trust_tier"],
                flags=score_data["flags"],
                raw_threats=score_data["raw_threats"]
            )
            db.add(score_db)
            db.commit()
            print(f"Successfully SCANNED and injected scam job: {jd['company']} - Score: {score_data['final_score']}")
    finally:
        db.close()

if __name__ == "__main__":
    inject_scams()
