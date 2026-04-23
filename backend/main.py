from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case
from typing import List, Optional
from sse_starlette.sse import EventSourceResponse

import auth
import models
import schemas
from database import engine, get_db
from notification import manager

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

# --- Global Exception Handler (Error Handling) ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Let HTTPExceptions pass through with their proper status codes
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    # Log the actual error for debugging
    import traceback
    traceback.print_exc()
    # Only catch truly unexpected errors
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later.", "type": str(type(exc).__name__)}
    )

# --- Authentication & Authorization ---
@app.post("/api/auth/register")
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        db_user = db.query(models.User).filter(models.User.email == user_in.email).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        hashed_password = auth.get_password_hash(user_in.password)
        # the first user created is admin, others aren't by default (just for demo purposes)
        is_admin = db.query(models.User).count() == 0 
        
        user = models.User(
            email=user_in.email,
            username=user_in.username,
            hashed_password=hashed_password,
            is_admin=is_admin
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"id": user.id, "email": user.email, "username": user.username, "is_active": user.is_active, "is_admin": user.is_admin}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise

@app.post("/api/auth/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# --- Notifications (SSE) ---
@app.get("/api/notifications/stream")
async def notification_stream():
    """Subscribe to events (e.g. new jobs added) via Server-Sent Events."""
    return EventSourceResponse(manager.get_generator())

@app.post("/api/notifications/publish", status_code=202)
def publish_notification(payload: dict, db: Session = Depends(get_db)):
    """Internal endpoint to publish events from scripts."""
    # Could protect this with an internal api key instead
    manager.publish(payload)
    return {"status": "published"}

# --- RESTful endpoints for Jobs (Admin Only) ---
@app.post("/api/jobs", response_model=schemas.JobOut, status_code=201)
def create_job(job: schemas.JobCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin_user)):
    """REST: Create a new job manually (admin only)."""
    db_job = models.Job(**job.model_dump())
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    
    # Notify connected clients
    manager.publish({"event": "new_job", "job_id": db_job.id, "title": db_job.title})
    
    return db_job

@app.put("/api/jobs/{job_id}", response_model=schemas.JobOut)
def update_job(job_id: int, job_update: schemas.JobCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin_user)):
    """REST: Update a job manually (admin only)."""
    db_job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    for key, value in job_update.model_dump(exclude_unset=True).items():
        setattr(db_job, key, value)
        
    db.commit()
    db.refresh(db_job)
    return db_job

@app.delete("/api/jobs/{job_id}", status_code=204)
def delete_job(job_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin_user)):
    """REST: Delete a job manually (admin only)."""
    db_job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # Also delete the score if present
    if db_job.score:
        db.delete(db_job.score)
        
    db.delete(db_job)
    db.commit()
    return None
