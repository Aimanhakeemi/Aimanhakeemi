"""
Create mock job data for testing
"""

from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from database.models import RawJob
from datetime import datetime, timedelta
import random

Base.metadata.create_all(bind=engine)

# Mock job data
MOCK_JOBS = [
    {
        "title": "Senior Python Developer at Google",
        "company": "Google",
        "location": "San Francisco, CA",
        "description": """
        We're looking for a Senior Python Developer to join our Cloud team.

        Requirements:
        - 5+ years Python experience
        - Strong knowledge of Django/FastAPI
        - Experience with cloud platforms (GCP/AWS)
        - System design skills

        Nice to have:
        - Kubernetes experience
        - Machine learning knowledge
        - Open source contributions

        Salary: $180,000 - $240,000 per year
        Benefits: Health insurance, 401k, Stock options, Remote work possible
        """
    },
    {
        "title": "Machine Learning Engineer at Meta",
        "company": "Meta",
        "location": "Menlo Park, CA",
        "description": """
        Join Meta's AI Research team as a Machine Learning Engineer.

        Requirements:
        - MS/PhD in CS or related field
        - 3+ years ML experience
        - PyTorch/TensorFlow expertise
        - Strong math background

        Nice to have:
        - Large language models experience
        - Computer vision knowledge
        - Research publications

        Salary: $190,000 - $250,000 per year
        """
    },
    {
        "title": "React Frontend Developer at Stripe",
        "company": "Stripe",
        "location": "San Francisco, CA",
        "description": """
        Help us build beautiful payment interfaces.

        Requirements:
        - 3+ years React experience
        - TypeScript proficiency
        - Web performance optimization
        - UI/UX sensibility

        Nice to have:
        - Next.js experience
        - Tailwind CSS
        - A11y knowledge

        Salary: $150,000 - $200,000 per year
        """
    },
    {
        "title": "DevOps Engineer at Amazon",
        "company": "Amazon",
        "location": "Seattle, WA",
        "description": """
        Build infrastructure for AWS services.

        Requirements:
        - 4+ years DevOps experience
        - AWS expertise
        - Kubernetes and Docker
        - CI/CD pipeline design
        - Infrastructure as Code (Terraform/CloudFormation)

        Nice to have:
        - Python/Go scripting
        - Monitoring and observability tools
        - Security best practices

        Salary: $170,000 - $230,000 per year
        """
    },
    {
        "title": "Data Scientist at Airbnb",
        "company": "Airbnb",
        "location": "San Francisco, CA",
        "description": """
        Analyze user behavior and build predictive models.

        Requirements:
        - MS in Statistics/Math or equivalent
        - 3+ years data science experience
        - Python/R proficiency
        - SQL expertise
        - Statistical modeling

        Nice to have:
        - Deep learning experience
        - A/B testing expertise
        - SQL optimization

        Salary: $160,000 - $220,000 per year
        """
    },
    {
        "title": "Full-Stack Engineer at Airbnb",
        "company": "Airbnb",
        "location": "Remote",
        "description": """
        Build end-to-end features for our platform.

        Requirements:
        - 2+ years full-stack experience
        - JavaScript/TypeScript
        - React or similar framework
        - Node.js or Python backend
        - SQL database design

        Salary: $130,000 - $180,000 per year
        """
    },
]

def seed_database():
    db = SessionLocal()

    try:
        # Delete existing mock data
        db.query(RawJob).delete()
        db.commit()

        # Add mock jobs
        for i, job in enumerate(MOCK_JOBS):
            posted_date = datetime.utcnow() - timedelta(days=random.randint(1, 30))

            db_job = RawJob(
                source="mock",
                source_id=f"mock_{i}",
                title=job["title"],
                company=job["company"],
                location=job["location"],
                raw_description=job["description"],
                job_url=f"https://example.com/jobs/{i}",
                posted_date=posted_date
            )
            db.add(db_job)

        db.commit()
        print(f"✅ Successfully seeded {len(MOCK_JOBS)} mock jobs!")

        # Show summary
        total = db.query(RawJob).count()
        print(f"📊 Total jobs in database: {total}")

    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
