"""
Run scrapers and store data in database
"""

import sys
import logging
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from database.models import RawJob
from scrapers.devto_scraper import DevtoScraper
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

def store_jobs_in_db(jobs: list, db: Session):
    """Store scraped jobs in database"""
    stored_count = 0
    skipped_count = 0

    for job in jobs:
        # Check if job already exists
        existing = db.query(RawJob).filter(
            RawJob.source_id == job["source_id"]
        ).first()

        if existing:
            skipped_count += 1
            continue

        # Create new job record
        db_job = RawJob(
            source=job["source"],
            source_id=job["source_id"],
            title=job["title"],
            company=job["company"],
            location=job["location"],
            raw_description=job["raw_description"],
            job_url=job["job_url"],
            posted_date=job["posted_date"]
        )

        db.add(db_job)
        stored_count += 1

    db.commit()
    return stored_count, skipped_count

def main():
    db = SessionLocal()

    try:
        logger.info("Starting job scraping...")

        # Run dev.to scraper
        logger.info("Scraping dev.to jobs...")
        devto_scraper = DevtoScraper()
        devto_jobs = devto_scraper.scrape_multiple_pages(num_pages=3)

        if devto_jobs:
            stored, skipped = store_jobs_in_db(devto_jobs, db)
            logger.info(f"Dev.to: Stored {stored} jobs, skipped {skipped} duplicates")
        else:
            logger.warning("No jobs scraped from dev.to")

        # Get statistics
        total_jobs = db.query(RawJob).count()
        logger.info(f"Total jobs in database: {total_jobs}")

    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
