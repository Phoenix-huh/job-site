from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case
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
def get_jobs(
    role: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get jobs with eager-loaded scores. Sorted by scam score (safest first)."""
    query = (
        db.query(models.Job)
        .options(joinedload(models.Job.score))  # Eager load scores in 1 query
        .outerjoin(models.Score)                 # JOIN for ORDER BY
    )
    if role:
        query = query.filter(models.Job.role == role)
    if location:
        query = query.filter(models.Job.location == location)
    # Sort in SQL: jobs with no score go last (treated as 100)
    query = query.order_by(
        case((models.Score.final_score == None, 100), else_=models.Score.final_score).asc()
    )
    jobs = query.offset(offset).limit(limit).all()
    return jobs

@app.get("/api/roles")
def get_roles(db: Session = Depends(get_db)):
    """Get all available roles in the database."""
    roles = db.query(models.Job.role).distinct().all()
    return [r[0] for r in roles if r[0]]

@app.get("/api/locations")
def get_locations(db: Session = Depends(get_db)):
    """Get all available locations in the database."""
    locations = db.query(models.Job.location).distinct().all()
    return sorted([loc[0] for loc in locations if loc[0]])

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
