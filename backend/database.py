from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Supports both local SQLite and cloud PostgreSQL (Supabase / Neon)
# Set DATABASE_URL env var to your cloud DB connection string
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "sql_app.db")
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{db_path}")

# SQLAlchemy needs special args only for SQLite
connect_args = {}
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    connect_args["check_same_thread"] = False

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def post_scrape_cleanup():
    """Post-scrape housekeeping: deduplicate by URL, expire stale listings, release sessions."""
    from datetime import date, timedelta
    import models

    db = SessionLocal()
    try:
        dupes = (
            db.query(models.Job.url)
            .filter(models.Job.url != None, models.Job.url != "")
            .group_by(models.Job.url)
            .having(db.func.count(models.Job.url) > 1)
            .all()
        )
        dupe_urls = {row[0] for row in dupes}
        removed_dupes = 0
        for url in dupe_urls:
            rows = (
                db.query(models.Job)
                .filter(models.Job.url == url)
                .order_by(models.Job.id)
                .all()
            )
            keep = rows[0]
            for row in rows[1:]:
                db.query(models.Score).filter(models.Score.job_id == row.id).delete(synchronize_session="fetch")
                db.delete(row)
                removed_dupes += 1
        if removed_dupes:
            db.commit()
            print(f"[CLEANUP] Removed {removed_dupes} duplicate job rows")

        cutoff = date.today() - timedelta(days=90)
        stale = db.query(models.Job).filter(
            models.Job.posted_date != None,
            models.Job.posted_date < cutoff,
        ).all()
        if stale:
            stale_ids = [j.id for j in stale]
            db.query(models.Score).filter(models.Score.job_id.in_(stale_ids)).delete(synchronize_session="fetch")
            db.query(models.Job).filter(models.Job.id.in_(stale_ids)).delete(synchronize_session="fetch")
            db.commit()
            print(f"[CLEANUP] Expired {len(stale)} stale listings (older than {cutoff.isoformat()})")
        else:
            print("[CLEANUP] No stale listings to expire")
    except Exception as e:
        db.rollback()
        print(f"[CLEANUP] Error during post-scrape cleanup: {e}")
    finally:
        db.close()
        engine.dispose()
        print("[CLEANUP] Database sessions and connection pool released")
