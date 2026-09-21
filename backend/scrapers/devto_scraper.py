"""
Dev.to Job Scraper
Scrapes job postings from dev.to using their public API
"""

import requests
from datetime import datetime
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class DevtoScraper:
    BASE_URL = "https://dev.to/api/articles"

    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "JobMarketIntelligence/1.0"
        }

    def scrape_jobs(self, page: int = 1, per_page: int = 30) -> List[Dict]:
        """
        Scrape job postings from dev.to

        Args:
            page: Page number (pagination)
            per_page: Number of results per page

        Returns:
            List of job postings
        """
        try:
            # Dev.to uses tags, we look for "jobs" tag
            params = {
                "tag": "jobs",
                "page": page,
                "per_page": per_page,
                "sort_by": "published_at",
                "sort_direction": "desc"
            }

            response = self.session.get(
                self.BASE_URL,
                headers=self.headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()

            articles = response.json()
            jobs = []

            for article in articles:
                job = {
                    "source": "devto",
                    "source_id": f"devto_{article['id']}",
                    "title": article.get("title", ""),
                    "company": extract_company_from_title(article.get("title", "")),
                    "location": "Not specified",  # Dev.to doesn't provide location in API
                    "raw_description": article.get("body_markdown", ""),
                    "job_url": article.get("url", ""),
                    "posted_date": datetime.fromisoformat(article.get("published_at", "").replace("Z", "+00:00")),
                }
                jobs.append(job)

            logger.info(f"Successfully scraped {len(jobs)} jobs from dev.to page {page}")
            return jobs

        except requests.RequestException as e:
            logger.error(f"Error scraping dev.to: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in dev.to scraper: {e}")
            return []

    def scrape_multiple_pages(self, num_pages: int = 5) -> List[Dict]:
        """Scrape multiple pages of jobs"""
        all_jobs = []
        for page in range(1, num_pages + 1):
            jobs = self.scrape_jobs(page=page)
            all_jobs.extend(jobs)
            if not jobs:  # Stop if no more jobs
                break

        return all_jobs

def extract_company_from_title(title: str) -> str:
    """
    Simple heuristic to extract company name from job title
    e.g., "Senior Python Developer at Google" -> "Google"
    """
    if " at " in title:
        return title.split(" at ")[-1].strip()
    return "Not specified"
