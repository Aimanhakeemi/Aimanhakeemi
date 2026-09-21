"""
Job Market Intelligence Platform - Backend API
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import get_db, Base, engine
from database.models import RawJob, ExtractedJob
import logging

# Create tables
Base.metadata.create_all(bind=engine)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Job Market Intelligence API",
    description="API for job market analysis and predictions",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Job Market Intelligence API is running"}

# Raw Jobs endpoints
@app.get("/api/raw-jobs")
def get_raw_jobs(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """Get raw job postings from database"""
    jobs = db.query(RawJob).offset(skip).limit(limit).all()
    return jobs

@app.get("/api/raw-jobs/count")
def count_raw_jobs(db: Session = Depends(get_db)):
    """Get total count of raw jobs"""
    count = db.query(RawJob).count()
    return {"total_jobs": count}

# Extracted Jobs endpoints
@app.get("/api/extracted-jobs")
def get_extracted_jobs(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """Get extracted and structured job data"""
    jobs = db.query(ExtractedJob).offset(skip).limit(limit).all()
    return jobs

@app.get("/api/extracted-jobs/count")
def count_extracted_jobs(db: Session = Depends(get_db)):
    """Get total count of extracted jobs"""
    count = db.query(ExtractedJob).count()
    return {"total_extracted_jobs": count}

# Health status
@app.get("/api/status")
def get_status(db: Session = Depends(get_db)):
    """Get overall platform status"""
    raw_jobs_count = db.query(RawJob).count()
    extracted_jobs_count = db.query(ExtractedJob).count()

    return {
        "raw_jobs": raw_jobs_count,
        "extracted_jobs": extracted_jobs_count,
        "extraction_progress": (extracted_jobs_count / raw_jobs_count * 100) if raw_jobs_count > 0 else 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
