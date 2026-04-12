from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional

import models
import schemas
from database import engine, get_db

# Try to import the injector script for remote execution
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from inject_real_data import inject
except ImportError:
    inject = None

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ShieldDB API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/jobs", response_model=List[schemas.JobOut])
def get_jobs(role: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Get all jobs, optionally filtered by role. Sorted by scam score (safest first)."""
    query = db.query(models.Job)
    if role:
        query = query.filter(models.Job.role == role)
    jobs = query.all()
    jobs.sort(key=lambda j: j.score.final_score if j.score else 100)
    return jobs

@app.get("/api/roles")
def get_roles(db: Session = Depends(get_db)):
    """Get all available roles in the database."""
    roles = db.query(models.Job.role).distinct().all()
    return [r[0] for r in roles if r[0]]

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Quick stats for the dashboard."""
    total = db.query(models.Job).count()
    safe = db.query(models.Job).join(models.Score).filter(models.Score.final_score < 31).count()
    caution = db.query(models.Job).join(models.Score).filter(models.Score.final_score >= 31, models.Score.final_score < 61).count()
    risky = db.query(models.Job).join(models.Score).filter(models.Score.final_score >= 61).count()
    return {"total": total, "safe": safe, "caution": caution, "risky": risky}

@app.get("/api/seed")
def seed_database():
    """Trigger the real-data injection script remotely."""
    if inject:
        # Run the injection synchronously
        inject()
        return {"status": "success", "message": "Database seeded successfully with 3 real-world jobs."}
    else:
        raise HTTPException(status_code=500, detail="Injection script not found or could not be loaded.")

@app.get("/api/jobs/{job_id}", response_model=schemas.JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
