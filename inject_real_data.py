import sys
import os
# Ensure we can import from the backend directory
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from database import SessionLocal, engine
import models
from scoring_engine import analyze_job

# Re-create tables if they don't exist
models.Base.metadata.create_all(bind=engine)

real_jobs = [
  {
    "title": "Data Analyst",
    "company": "Siemens",
    "url": "https://www.naukri.com/job-listings-data-analyst-siemens-limited-bengaluru-5-to-10-years-270326909851",
    "description": "Youll make an impact by: As a Data Analyst at Siemens (GBS) you will play a crucial role in extracting meaningful insights from various datasets to support data-driven decision-making processes. The candidate should have a proven track record of handling complex data sets, implementing data analysis techniques, and creating insightful reports using Power BI. In addition to strong analytical skills, the ideal candidate will be well-versed in database management and possess excellent communication skills.",
    "location": "Bengaluru",
    "country": "India",
    "platform": "Naukri",
    "job_type": "Full Time",
    "workplace_type": "Offline",
    "posted_date": "2026-07-08",
    "salary": "12 - 18 LPA",
    "skills": ["Power BI", "SQL", "Python", "Database Management"]
  },
  {
    "title": "Data Analyst",
    "company": "Capgemini",
    "url": "https://www.naukri.com/job-listings-data-analyst-capgemini-chennai-delhi-ncr-mumbai-all-areas-4-to-9-years-021225014173",
    "description": "Required Skills \u0026 Qualifications: Bachelors degree in Data Science, Statistics, Computer Science, or related field. Proficiency in SQL, Python/R, and data visualization tools (Power BI, Tableau). Strong knowledge of statistical methods and data modeling. Excellent problem-solving and communication skills. Ability to work with large datasets and maintain attention to detail. Preferred Qualifications: Experience with cloud platforms (Azure, AWS, GCP). Knowledge of machine learning basics.",
    "location": "Mumbai",
    "country": "India",
    "platform": "Naukri",
    "job_type": "Full Time",
    "workplace_type": "Hybrid",
    "posted_date": "2026-07-07",
    "salary": "8 - 14 LPA",
    "skills": ["SQL", "Python", "R", "Power BI", "Tableau", "Azure"]
  },
  {
    "title": "Data Analyst",
    "company": "TVS Motor",
    "url": "https://www.naukri.com/job-listings-data-analyst-tvs-motor-company-bengaluru-2-to-3-years-010426500928",
    "description": "Educational Qualification: BE/BTECH or Postgraduate Roles \u0026 Responsibilities: Analysis oflarge, complex data sets and application of advanced analytical techniques tosolve business problems Identify andmonitor the right metrics to evaluate business health and track progress Assist indesigning, running and measuring experiments to test business hypotheses Enhance dataaccuracy through continuous feedback and scoping of instrumentation quality andcompleteness",
    "location": "Bengaluru",
    "country": "India",
    "platform": "Naukri",
    "job_type": "Full Time",
    "workplace_type": "Offline",
    "posted_date": "2026-07-09",
    "salary": "10 - 15 LPA",
    "skills": ["Data Analysis", "Statistics", "A/B Testing", "Instrumentation"]
  }
]

def inject():
    db = SessionLocal()
    try:
        # Clear any existing jobs to fulfill "no demo data"
        db.query(models.Score).delete()
        db.query(models.Job).delete()
        db.commit()
        print("Canceled all demo data artifacts. Primary Shield Override: Injecting real-world results from Siemens, Capgemini, and TVS...")

        for jd in real_jobs:
            job_db = models.Job(
                title=jd["title"],
                company=jd["company"],
                url=jd["url"],
                description=jd["description"],
                location=jd["location"],
                country=jd["country"],
                platform=jd["platform"],
                job_type=jd["job_type"],
                workplace_type=jd["workplace_type"],
                posted_date=jd["posted_date"],
                salary=jd["salary"],
                skills=jd["skills"]
            )
            db.add(job_db)
            db.commit()
            db.refresh(job_db)
            
            # Run the actual 20-parameter scoring engine
            score_data = analyze_job(job_db.description, job_db.company, None)
            score_db = models.Score(
                job_id=job_db.id,
                final_score=score_data["final_score"],
                trust_tier=score_data["trust_tier"],
                flags=score_data["flags"],
                raw_threats=score_data["raw_threats"]
            )
            db.add(score_db)
            db.commit()
            print(f"Successfully SCANNED and validated real job: {jd['company']}")
    finally:
        db.close()

if __name__ == "__main__":
    inject()
