# Job Market Intelligence - Backend

Python FastAPI backend for scraping jobs, extracting data with LLMs, and running ML predictions.

## Setup

### 1. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup Database
```bash
# Make sure PostgreSQL is running
# Create database
createdb job_market_db

# (Optional) Use existing PostgreSQL instance and update .env
```

### 4. Configure Environment
```bash
cp .env.example .env
# Edit .env and add your database URL and API keys
```

### 5. Initialize Database
```bash
python -c "from database import Base, engine; Base.metadata.create_all(bind=engine)"
```

## Running the Project

### Run Scraper
```bash
python run_scraper.py
```

This will:
1. Scrape jobs from dev.to
2. Store raw job data in PostgreSQL
3. Show statistics

### Run API Server
```bash
python main.py
# Or with hot reload:
uvicorn main:app --reload
```

API will be available at `http://localhost:8000`

### API Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure
```
backend/
├── database/          # Database models and setup
│   ├── __init__.py
│   └── models.py
├── scrapers/          # Web scrapers
│   ├── devto_scraper.py
│   └── (more scrapers)
├── extractors/        # LLM extraction logic
├── models/            # ML models
├── api/               # API routes
├── main.py            # FastAPI app
├── run_scraper.py     # Scraper runner
└── requirements.txt
```

## API Endpoints

### Health Check
- `GET /health` - Check if API is running
- `GET /api/status` - Get platform status

### Raw Jobs
- `GET /api/raw-jobs` - Get raw job postings
- `GET /api/raw-jobs/count` - Count total raw jobs

### Extracted Jobs
- `GET /api/extracted-jobs` - Get extracted job data
- `GET /api/extracted-jobs/count` - Count extracted jobs

## Phase 1 Progress

- [x] Project structure
- [x] Database schema (RawJob, ExtractedJob, SalaryPrediction, SkillDemand)
- [x] Dev.to scraper
- [x] FastAPI app
- [ ] Test scraper
- [ ] Data validation
- [ ] Add more scrapers (Indeed, LinkedIn)

## Next Steps

Phase 2: LLM Data Extraction
- Set up Claude/OpenAI API integration
- Build extraction prompts for skills, salary, requirements
- Extract and validate data
