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


def load_archived_urls():
    """Load all URLs from archived_job_links for fast pre-scrape exclusion."""
    import models
    db = SessionLocal()
    try:
        urls = set(row[0] for row in db.query(models.ArchivedJobLink.url).all() if row[0])
        print(f"[ARCHIVE] Loaded {len(urls)} archived job URLs for exclusion")
        return urls
    finally:
        db.close()


def archive_job_url(url, posted_date):
    """Insert a URL into archived_job_links (ON CONFLICT DO NOTHING)."""
    import models
    db = SessionLocal()
    try:
        existing = db.query(models.ArchivedJobLink).filter(models.ArchivedJobLink.url == url).first()
        if not existing:
            db.add(models.ArchivedJobLink(url=url, posted_date=posted_date))
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def is_job_too_old(posted_date_str, max_days=90):
    """Return True if posted_date is older than max_days from today."""
    from datetime import date, timedelta
    if not posted_date_str:
        return False
    try:
        if isinstance(posted_date_str, date):
            posted = posted_date_str
        else:
            posted = date.fromisoformat(str(posted_date_str)[:10])
        return posted < (date.today() - timedelta(days=max_days))
    except (ValueError, TypeError):
        return False


def archive_old_jobs(max_days=90):
    """Archive all jobs older than max_days into archived_job_links, then delete them from jobs table."""
    from datetime import date, timedelta
    import models

    db = SessionLocal()
    try:
        cutoff = date.today() - timedelta(days=max_days)
        stale = db.query(models.Job).filter(
            models.Job.posted_date != None,
            models.Job.posted_date < cutoff,
        ).all()
        if not stale:
            print(f"[ARCHIVE] No jobs older than {cutoff.isoformat()} found")
            return 0

        newly_archived = 0
        for job in stale:
            if job.url:
                existing = db.query(models.ArchivedJobLink).filter(models.ArchivedJobLink.url == job.url).first()
                if not existing:
                    db.add(models.ArchivedJobLink(url=job.url, posted_date=job.posted_date))
                    newly_archived += 1

        db.commit()

        stale_ids = [j.id for j in stale]
        db.query(models.Score).filter(models.Score.job_id.in_(stale_ids)).delete(synchronize_session="fetch")
        db.query(models.Job).filter(models.Job.id.in_(stale_ids)).delete(synchronize_session="fetch")
        db.commit()

        print(f"[ARCHIVE] Archived {newly_archived} URLs and deleted {len(stale)} jobs older than {cutoff.isoformat()}")
        return len(stale)
    except Exception as e:
        db.rollback()
        print(f"[ARCHIVE] Error: {e}")
        return 0
    finally:
        db.close()


def post_scrape_cleanup():
    """Post-scrape housekeeping: deduplicate, expire stale listings, 6-month purge, release sessions."""
    from datetime import date, timedelta
    import models

    db = SessionLocal()
    try:
        contaminated = db.query(models.Job).filter(
            db.func.lower(db.func.trim(models.Job.location)) == db.func.lower(db.func.trim(models.Job.company))
        ).all()
        if contaminated:
            for job in contaminated:
                job.location = "Unknown"
            db.commit()
            print(f"[CLEANUP] Fixed {len(contaminated)} jobs where location matched company name")

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
            for row in rows[1:]:
                db.query(models.Score).filter(models.Score.job_id == row.id).delete(synchronize_session="fetch")
                db.delete(row)
                removed_dupes += 1
        if removed_dupes:
            db.commit()
            print(f"[CLEANUP] Removed {removed_dupes} duplicate job rows")

        cutoff_90 = date.today() - timedelta(days=90)
        stale = db.query(models.Job).filter(
            models.Job.posted_date != None,
            models.Job.posted_date < cutoff_90,
        ).all()
        if stale:
            newly_archived = 0
            for job in stale:
                if job.url:
                    existing = db.query(models.ArchivedJobLink).filter(models.ArchivedJobLink.url == job.url).first()
                    if not existing:
                        db.add(models.ArchivedJobLink(url=job.url, posted_date=job.posted_date))
                        newly_archived += 1
            if newly_archived:
                db.commit()
                print(f"[CLEANUP] Archived {newly_archived} stale job URLs before deletion")
            stale_ids = [j.id for j in stale]
            db.query(models.Score).filter(models.Score.job_id.in_(stale_ids)).delete(synchronize_session="fetch")
            db.query(models.Job).filter(models.Job.id.in_(stale_ids)).delete(synchronize_session="fetch")
            db.commit()
            print(f"[CLEANUP] Expired {len(stale)} stale listings (older than {cutoff_90.isoformat()})")
        else:
            print("[CLEANUP] No stale listings to expire")

        cutoff_180 = date.today() - timedelta(days=180)
        purged_archive = db.query(models.ArchivedJobLink).filter(
            models.ArchivedJobLink.posted_date != None,
            models.ArchivedJobLink.posted_date < cutoff_180,
        ).delete(synchronize_session="fetch")
        purged_jobs = db.query(models.Job).filter(
            models.Job.posted_date != None,
            models.Job.posted_date < cutoff_180,
        ).all()
        if purged_jobs:
            purged_job_ids = [j.id for j in purged_jobs]
            db.query(models.Score).filter(models.Score.job_id.in_(purged_job_ids)).delete(synchronize_session="fetch")
            db.query(models.Job).filter(models.Job.id.in_(purged_job_ids)).delete(synchronize_session="fetch")
        db.commit()
        total_purged = purged_archive + len(purged_jobs)
        if total_purged:
            print(f"[Cleanup] Purged {purged_archive} archived URLs and {len(purged_jobs)} stale jobs older than 6 months.")
        else:
            print("[Cleanup] No archived URLs or stale jobs older than 6 months to purge.")
    except Exception as e:
        db.rollback()
        print(f"[CLEANUP] Error during post-scrape cleanup: {e}")
    finally:
        db.close()
        engine.dispose()
        print("[CLEANUP] Database sessions and connection pool released")


if __name__ == "__main__":
    import argparse
    import models
    models.Base.metadata.create_all(bind=engine)

    parser = argparse.ArgumentParser(description="Archive old jobs from the database")
    parser.add_argument("--days", type=int, default=90, help="Archive jobs older than N days (default: 90)")
    args = parser.parse_args()

    count = archive_old_jobs(max_days=args.days)
    print(f"Done. {count} jobs archived.")
