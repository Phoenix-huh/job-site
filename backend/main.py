from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case, text
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


# ==================== DATA VIEWER ENDPOINTS ====================
@app.get("/view-data/{table_name}", response_class=HTMLResponse)
def view_data(table_name: str = "jobs", limit: int = Query(100, ge=1, le=1000), db: Session = Depends(get_db)):
    """
    View data from any table as an HTML table.
    Usage:
    - /view-data/jobs
    - /view-data/scores
    - /view-data/comments
    """
    try:
        # Validate table name (prevent SQL injection)
        valid_tables = ["jobs", "scores", "comments"]
        if table_name.lower() not in valid_tables:
            return f"<h1>Error</h1><p>Invalid table. Available tables: {', '.join(valid_tables)}</p>"
        
        # Execute raw SQL to fetch data
        result = db.execute(text(f"SELECT * FROM {table_name} LIMIT {limit}"))
        rows = result.fetchall()
        columns = result.keys()
        
        if not rows:
            return f"""
            <html>
            <head>
                <title>Database Viewer - {table_name}</title>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background: #f5f5f5; }}
                    h1 {{ color: #333; margin-bottom: 20px; }}
                    .nav {{ margin-bottom: 20px; display: flex; gap: 10px; }}
                    .nav a {{ padding: 10px 15px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; transition: background 0.3s; }}
                    .nav a:hover {{ background: #0056b3; }}
                    .info {{ padding: 10px; background: #fff3cd; border: 1px solid #ffc107; border-radius: 4px; color: #856404; }}
                </style>
            </head>
            <body>
                <h1>🗄️ Database Viewer: {table_name.upper()}</h1>
                <div class="nav">
                    <a href="/view-data/jobs">📋 View Jobs</a>
                    <a href="/view-data/scores">⭐ View Scores</a>
                    <a href="/view-data/comments">💬 View Comments</a>
                </div>
                <div class="info">
                    <strong>No data found</strong> in the {table_name} table. Try running /api/seed to populate sample data.
                </div>
            </body>
            </html>
            """
        
        # Build HTML table
        html_rows = ""
        for row in rows:
            cells = "".join([f"<td>{str(row[col])[:100]}</td>" for col in columns])
            html_rows += f"<tr>{cells}</tr>"
        
        headers = "".join([f"<th>{col}</th>" for col in columns])
        
        html = f"""
        <html>
        <head>
            <title>Database Viewer - {table_name}</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background: #f5f5f5; }}
                h1 {{ color: #333; margin-bottom: 10px; }}
                .stats {{ margin-bottom: 20px; color: #666; font-size: 14px; }}
                .nav {{ margin-bottom: 20px; display: flex; gap: 10px; flex-wrap: wrap; }}
                .nav a {{ padding: 10px 15px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; transition: background 0.3s; }}
                .nav a:hover {{ background: #0056b3; }}
                .nav a.active {{ background: #28a745; }}
                table {{ 
                    border-collapse: collapse; 
                    width: 100%; 
                    background: white; 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    border-radius: 4px;
                    overflow: hidden;
                }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background: #007bff; color: white; font-weight: 600; }}
                tr:nth-child(even) {{ background: #f9f9f9; }}
                tr:hover {{ background: #f0f0f0; }}
                td {{ word-break: break-word; max-width: 200px; }}
            </style>
        </head>
        <body>
            <h1>🗄️ Database Viewer: {table_name.upper()}</h1>
            <div class="stats">
                📊 Showing <strong>{len(rows)}</strong> record(s) from table <strong>{table_name}</strong>
            </div>
            <div class="nav">
                <a href="/view-data/jobs" {'class="active"' if table_name == 'jobs' else ''}>📋 View Jobs</a>
                <a href="/view-data/scores" {'class="active"' if table_name == 'scores' else ''}>⭐ View Scores</a>
                <a href="/view-data/comments" {'class="active"' if table_name == 'comments' else ''}>💬 View Comments</a>
            </div>
            <table>
                <thead>
                    <tr>{headers}</tr>
                </thead>
                <tbody>
                    {html_rows}
                </tbody>
            </table>
        </body>
        </html>
        """
        return html
    except Exception as e:
        return f"""
        <html>
        <head>
            <title>Error</title>
            <style>
                body {{ font-family: Arial; margin: 20px; background: #f5f5f5; }}
                .error {{ background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 15px; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <h1>❌ Error</h1>
            <div class="error">
                <strong>Error Details:</strong><br>
                {str(e)}
            </div>
        </body>
        </html>
        """


@app.get("/view-all", response_class=HTMLResponse)
def view_all(db: Session = Depends(get_db)):
    """View summary of all tables in the database"""
    try:
        stats = {
            "jobs": db.query(models.Job).count(),
            "scores": db.query(models.Score).count(),
            "comments": db.query(models.Comment).count() if hasattr(models, 'Comment') else 0,
        }
        
        table_links = "".join([
            f'<li><a href="/view-data/{table}">{table.upper()} ({count} records)</a></li>'
            for table, count in stats.items()
        ])
        
        html = f"""
        <html>
        <head>
            <title>Database Overview</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background: #f5f5f5; }}
                h1 {{ color: #333; }}
                .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); max-width: 600px; }}
                ul {{ list-style: none; padding: 0; }}
                li {{ margin: 15px 0; }}
                a {{ 
                    display: block;
                    padding: 15px 20px;
                    background: #007bff;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    transition: background 0.3s;
                    font-weight: 500;
                }}
                a:hover {{ background: #0056b3; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🗄️ Database Overview</h1>
                <p>Select a table to view its data:</p>
                <ul>
                    {table_links}
                </ul>
            </div>
        </body>
        </html>
        """
        return html
    except Exception as e:
        return f"<h1>Error</h1><p>{str(e)}</p>"
