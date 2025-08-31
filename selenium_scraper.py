
import logging
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from app import app, db
from models import Job
import pytz
from datetime import datetime, timedelta
from urllib.parse import urljoin
import re

logger = logging.getLogger(__name__)

class SeleniumAZStateJobsScraper:
    def __init__(self):
        self.base_url = "https://www.azstatejobs.gov"
        self.search_url = "https://www.azstatejobs.gov/jobs/search"
        self.driver = None
        
    def setup_driver(self):
        """Setup Chrome driver with options to avoid detection"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Execute script to remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return True
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {str(e)}")
            return False
    
    def get_job_listings(self):
        """Scrape job listings using Selenium"""
        if not self.setup_driver():
            return []
            
        try:
            logger.info("Visiting homepage with Selenium...")
            self.driver.get(self.base_url)
            time.sleep(3)
            
            logger.info("Navigating to jobs search page...")
            self.driver.get(self.search_url)
            
            # Wait for page to load and check for content
            wait = WebDriverWait(self.driver, 15)
            
            # Check if we hit the bot challenge
            page_source = self.driver.page_source
            if "JavaScript is disabled" in page_source or "verify that you're not a robot" in page_source:
                logger.warning("Still hitting bot challenge with Selenium")
                
                # Try clicking through any buttons or links that might help
                try:
                    # Look for any "Continue" or similar buttons
                    continue_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')] | //a[contains(text(), 'Continue')]")
                    continue_button.click()
                    time.sleep(5)
                except:
                    pass
                    
                # Refresh page source
                page_source = self.driver.page_source
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(page_source, 'html.parser')
            
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
            logger.error(f"Error with Selenium scraping: {str(e)}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
    
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

def scrape_jobs_selenium():
    """Alternative scraping function using Selenium"""
    with app.app_context():
        scraper = SeleniumAZStateJobsScraper()
        jobs_scraped = 0
        
        try:
            job_listings = scraper.get_job_listings()
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
            logger.info(f"Selenium scraping completed. {jobs_scraped} new jobs added.")
            
            return jobs_scraped
            
        except Exception as e:
            logger.error(f"Error during Selenium scraping: {str(e)}")
            db.session.rollback()
            return 0

if __name__ == "__main__":
    scrape_jobs_selenium()
