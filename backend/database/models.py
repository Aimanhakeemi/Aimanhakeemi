from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, Boolean
from sqlalchemy.sql import func
from database import Base
from datetime import datetime

class RawJob(Base):
    """Raw job posting data from scrapers"""
    __tablename__ = "raw_jobs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), index=True)  # "devto", "indeed", "linkedin"
    source_id = Column(String(255), unique=True, index=True)  # External job ID
    title = Column(String(255), index=True)
    company = Column(String(255), index=True)
    location = Column(String(255))
    raw_description = Column(Text)
    job_url = Column(String(500))
    posted_date = Column(DateTime)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

class ExtractedJob(Base):
    """Structured job data extracted by LLM"""
    __tablename__ = "extracted_jobs"

    id = Column(Integer, primary_key=True, index=True)
    raw_job_id = Column(Integer, index=True)

    # Extracted fields
    title = Column(String(255), index=True)
    company = Column(String(255), index=True)
    location = Column(String(255))

    # LLM Extracted data
    required_skills = Column(JSON)  # List of skills
    nice_to_have_skills = Column(JSON)  # List of skills
    experience_level = Column(String(50))  # "entry", "mid", "senior"
    years_of_experience = Column(Integer)
    job_type = Column(String(50))  # "full-time", "part-time", "contract"
    salary_min = Column(Float)  # In thousands
    salary_max = Column(Float)  # In thousands
    salary_currency = Column(String(10))  # "USD", "EUR"
    employment_type = Column(String(100))
    responsibilities = Column(JSON)
    benefits = Column(JSON)

    # Metadata
    extracted_at = Column(DateTime, default=datetime.utcnow)
    extraction_quality_score = Column(Float)  # 0-1, how confident is the extraction
    created_at = Column(DateTime, default=datetime.utcnow)

class SalaryPrediction(Base):
    """ML predictions for salary"""
    __tablename__ = "salary_predictions"

    id = Column(Integer, primary_key=True, index=True)
    extracted_job_id = Column(Integer, index=True)

    predicted_salary_min = Column(Float)
    predicted_salary_max = Column(Float)
    prediction_confidence = Column(Float)  # 0-1

    created_at = Column(DateTime, default=datetime.utcnow)

class SkillDemand(Base):
    """Track skill demand over time"""
    __tablename__ = "skill_demand"

    id = Column(Integer, primary_key=True, index=True)
    skill = Column(String(100), index=True)
    count = Column(Integer)  # How many jobs mention this skill
    percentage = Column(Float)  # Percentage of all jobs
    average_salary = Column(Float)  # Average salary for jobs with this skill
    trend = Column(String(50))  # "rising", "stable", "declining"

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=func.now())
