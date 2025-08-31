
import logging
import time
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from app import app, db
from models import Job
import pytz
from datetime import datetime, timedelta
from urllib.parse import urljoin
import re

logger = logging.getLogger(__name__)

class PlaywrightAZStateJobsScraper:
    def __init__(self):
        self.base_url = "https://www.azstatejobs.gov"
        self.search_url = "https://www.azstatejobs.gov/jobs/search"
        
    async def get_job_listings(self):
        """Scrape job listings using Playwright"""
        async with async_playwright() as p:
            # Launch browser with stealth settings
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            try:
                # Create context with realistic settings
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080},
                    locale='en-US',
                    timezone_id='America/Phoenix'
                )
                
                page = await context.new_page()
                
                # Block images and unnecessary resources to speed up loading
                await page.route("**/*.{png,jpg,jpeg,gif,webp,svg,ico}", lambda route: route.abort())
                await page.route("**/*.{css,woff,woff2,ttf}", lambda route: route.abort())
                
                logger.info("Visiting homepage with Playwright...")
                await page.goto(self.base_url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(2000)
                
                logger.info("Navigating to jobs search page...")
                await page.goto(self.search_url, wait_until='domcontentloaded', timeout=30000)
                
                # Wait for content to load
                await page.wait_for_timeout(3000)
                
                # Get page content
                content = await page.content()
                
                # Check for bot detection
                if "JavaScript is disabled" in content or "verify that you're not a robot" in content:
                    logger.warning("Still hitting bot challenge with Playwright")
                    # Try waiting longer and refreshing
                    await page.wait_for_timeout(5000)
                    await page.reload(wait_until='domcontentloaded')
                    await page.wait_for_timeout(3000)
                    content = await page.content()
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')
                
                # Log page content for debugging
                page_text = soup.get_text()[:500]
                logger.info(f"Page content preview: {page_text}")
                
                # Look for jobs table
                jobs_table = soup.find('table')
                if not jobs_table:
                    logger.error("Could not find jobs table on the page")
                    return []
                
                jobs = []
                tbody = jobs_table.find('tbody')
                rows = tbody.find_all('tr') if tbody else []
                
                for row in rows:
                    try:
                        cells = row.find_all('td')
                        if len(cells) < 7:
                            continue
                        
                        title_cell = cells[0]
                        title_link = title_cell.find('a')
                        if not title_link:
                            continue
                        
                        category_text = cells[2].get_text(strip=True).replace('\n', ' ').replace('  ', ' ')
                        
                        job_data = {
                            'title': title_link.get_text(strip=True),
                            'url': urljoin(self.base_url, title_link.get('href')),
                            'requisition_id': cells[1].get_text(strip=True),
                            'category': category_text,
                            'department': cells[3].get_text(strip=True),
                            'employment_type': cells[4].get_text(strip=True),
                            'location': cells[5].get_text(strip=True),
                            'closing_date': self.parse_date(cells[6].get_text(strip=True)),
                            'postsecondary_required': cells[7].get_text(strip=True) if len(cells) > 7 else None
                        }
                        
                        jobs.append(job_data)
                        
                    except Exception as e:
                        logger.error(f"Error parsing job row: {str(e)}")
                        continue
                
                logger.info(f"Found {len(jobs)} job listings")
                return jobs
                
            except Exception as e:
                logger.error(f"Error with Playwright scraping: {str(e)}")
                return []
            finally:
                await browser.close()
    
    def parse_date(self, date_text):
        """Parse date string to datetime object"""
        if not date_text or date_text.strip() == '':
            return None
        
        try:
            formats = [
                '%b %d %Y - %H:%M %Z',
                '%b %d %Y',
                '%m/%d/%Y',
                '%Y-%m-%d'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_text.strip(), fmt)
                except ValueError:
                    continue
            
            date_match = re.search(r'(\w{3} \d{1,2} \d{4})', date_text)
            if date_match:
                return datetime.strptime(date_match.group(1), '%b %d %Y')
                
        except Exception as e:
            logger.error(f"Error parsing date '{date_text}': {str(e)}")
        
        return None

def scrape_jobs_playwright():
    """Scraping function using Playwright"""
    with app.app_context():
        scraper = PlaywrightAZStateJobsScraper()
        jobs_scraped = 0
        
        try:
            # Run async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            job_listings = loop.run_until_complete(scraper.get_job_listings())
            loop.close()
            
            current_requisition_ids = {job['requisition_id'] for job in job_listings}
            
            for job_data in job_listings:
                try:
                    existing_job = Job.query.filter_by(requisition_id=job_data['requisition_id']).first()
                    
                    if existing_job:
                        phoenix_tz = pytz.timezone('America/Phoenix')
                        existing_job.updated_at = datetime.now(phoenix_tz)
                        logger.debug(f"Updated existing job: {job_data['requisition_id']}")
                    else:
                        new_job = Job(
                            requisition_id=job_data['requisition_id'],
                            title=job_data['title'],
                            department=job_data['department'],
                            location=job_data['location'],
                            employment_type=job_data['employment_type'],
                            category=job_data['category'],
                            closing_date=job_data['closing_date'],
                            postsecondary_required=job_data['postsecondary_required'],
                            url=job_data['url']
                        )
                        
                        db.session.add(new_job)
                        jobs_scraped += 1
                        logger.info(f"Added new job: {job_data['requisition_id']} - {job_data['title']}")
                        
                except Exception as e:
                    logger.error(f"Error processing job {job_data.get('requisition_id', 'unknown')}: {str(e)}")
                    continue
            
            db.session.commit()
            logger.info(f"Playwright scraping completed. {jobs_scraped} new jobs added.")
            
            return jobs_scraped
            
        except Exception as e:
            logger.error(f"Error during Playwright scraping: {str(e)}")
            db.session.rollback()
            return 0

if __name__ == "__main__":
    scrape_jobs_playwright()
