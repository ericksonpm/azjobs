import requests
from bs4 import BeautifulSoup
import re
import time
import logging
import pytz
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
from app import app, db
from models import Job

logger = logging.getLogger(__name__)

class AZStateJobsScraper:
    def __init__(self):
        self.base_url = "https://www.azstatejobs.gov"
        self.search_url = "https://www.azstatejobs.gov/jobs/search"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def get_job_listings(self):
        """Scrape the main job search page to get job listings"""
        try:
            logger.info("Fetching job listings from main search page...")
            response = self.session.get(self.search_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the jobs table
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
                    
                    # Extract job information
                    title_cell = cells[0]
                    title_link = title_cell.find('a')
                    if not title_link:
                        continue
                    
                    # Clean category text by replacing newlines and extra spaces
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
            logger.error(f"Error fetching job listings: {str(e)}")
            return []
    
    def get_job_details(self, job_url):
        """Scrape individual job page for salary and other details"""
        try:
            logger.debug(f"Fetching job details from: {job_url}")
            response = self.session.get(job_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            details = {}
            
            # Extract salary information
            salary_text = self.extract_salary(soup)
            if salary_text:
                details['salary_text'] = salary_text
                salary_min, salary_max = self.parse_salary_range(salary_text)
                details['salary_min'] = salary_min
                details['salary_max'] = salary_max
            
            # Extract grade
            grade_text = self.extract_grade(soup)
            if grade_text:
                details['grade'] = grade_text
            
            # Extract job summary
            job_summary = self.extract_job_summary(soup)
            if job_summary:
                details['job_summary'] = job_summary
            
            # Extract job duties
            job_duties = self.extract_job_duties(soup)
            if job_duties:
                details['job_duties'] = job_duties
            
            # Extract requirements
            requirements = self.extract_requirements(soup)
            if requirements:
                details['requirements'] = requirements
            
            return details
            
        except Exception as e:
            logger.error(f"Error fetching job details from {job_url}: {str(e)}")
            return {}
    
    def extract_salary(self, soup):
        """Extract salary information from job page"""
        text = soup.get_text()
        
        # Look for salary in Posting Details section specifically
        # Pattern 1: Single salary amount "Salary: $40,207.02"
        single_salary_match = re.search(r'Salary:\s*\$?([\d,]+(?:\.\d{2})?)\s*(?:\n|$)', text, re.IGNORECASE)
        if single_salary_match:
            salary_val = single_salary_match.group(1).replace(',', '')
            return f"${salary_val}"
        
        # Pattern 2: Salary range "Salary: $40,207.02 - $45,000"
        range_patterns = [
            r'Salary:\s*\$?([\d,]+(?:\.\d{2})?)\s*-\s*\$?([\d,]+(?:\.\d{2})?)',
            r'(\$[\d,]+(?:\.\d{2})?)\s*-\s*(\$[\d,]+(?:\.\d{2})?)',
        ]
        
        for pattern in range_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    min_sal = match.group(1).replace('$', '').replace(',', '')
                    max_sal = match.group(2).replace('$', '').replace(',', '')
                    return f"${min_sal} - ${max_sal}"
        
        # Pattern 3: Look for salary after "Posting Details:" heading
        posting_details_idx = text.find('Posting Details:')
        if posting_details_idx != -1:
            # Get text after "Posting Details:" up to next major section
            details_section = text[posting_details_idx:posting_details_idx + 500]
            
            # Look for salary in this section
            salary_match = re.search(r'Salary:\s*\$?([\d,]+(?:\.\d{2})?)', details_section, re.IGNORECASE)
            if salary_match:
                salary_val = salary_match.group(1).replace(',', '')
                return f"${salary_val}"
        
        return None
    
    def extract_grade(self, soup):
        """Extract job grade from job page"""
        grade_match = re.search(r'Grade:\s*(\d+)', soup.get_text(), re.IGNORECASE)
        return grade_match.group(1) if grade_match else None
    
    def extract_job_summary(self, soup):
        """Extract job summary"""
        summary_heading = soup.find(text=re.compile(r'Job Summary:', re.IGNORECASE))
        if summary_heading:
            parent = summary_heading.parent
            if parent:
                next_element = parent.find_next_sibling()
                if next_element:
                    return next_element.get_text(strip=True)[:1000]  # Limit length
        return None
    
    def extract_job_duties(self, soup):
        """Extract job duties"""
        duties_heading = soup.find(text=re.compile(r'Job Duties:', re.IGNORECASE))
        if duties_heading:
            parent = duties_heading.parent
            if parent:
                next_element = parent.find_next_sibling()
                if next_element:
                    return next_element.get_text(strip=True)[:2000]  # Limit length
        return None
    
    def extract_requirements(self, soup):
        """Extract job requirements"""
        req_heading = soup.find(text=re.compile(r'Knowledge, Skills|Requirements:', re.IGNORECASE))
        if req_heading:
            parent = req_heading.parent
            if parent:
                next_element = parent.find_next_sibling()
                if next_element:
                    return next_element.get_text(strip=True)[:2000]  # Limit length
        return None
    
    def parse_salary_range(self, salary_text):
        """Parse salary range from text"""
        if not salary_text:
            return None, None
        
        # Remove $ and commas, extract numbers
        numbers = re.findall(r'[\d,]+(?:\.\d{2})?', salary_text.replace('$', '').replace(',', ''))
        
        if len(numbers) >= 2:
            try:
                salary_min = float(numbers[0].replace(',', ''))
                salary_max = float(numbers[1].replace(',', ''))
                return salary_min, salary_max
            except ValueError:
                pass
        
        return None, None
    
    def parse_date(self, date_text):
        """Parse date string to datetime object"""
        if not date_text or date_text.strip() == '':
            return None
        
        try:
            # Try different date formats
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
            
            # If no format worked, try to extract just the date part
            date_match = re.search(r'(\w{3} \d{1,2} \d{4})', date_text)
            if date_match:
                return datetime.strptime(date_match.group(1), '%b %d %Y')
                
        except Exception as e:
            logger.error(f"Error parsing date '{date_text}': {str(e)}")
        
        return None

def scrape_jobs():
    """Main function to scrape jobs and store in database"""
    with app.app_context():
        scraper = AZStateJobsScraper()
        jobs_scraped = 0
        
        try:
            # Get job listings from main page
            job_listings = scraper.get_job_listings()
            
            for job_data in job_listings:
                try:
                    # Check if job already exists
                    existing_job = Job.query.filter_by(requisition_id=job_data['requisition_id']).first()
                    
                    if existing_job:
                        # Update existing job
                        phoenix_tz = pytz.timezone('America/Phoenix')
                        existing_job.updated_at = datetime.now(phoenix_tz)
                        logger.debug(f"Updated existing job: {job_data['requisition_id']}")
                    else:
                        # Get detailed information from individual job page
                        job_details = scraper.get_job_details(job_data['url'])
                        
                        # Merge job data with details
                        job_data.update(job_details)
                        
                        # Create new job record
                        new_job = Job(
                            requisition_id=job_data['requisition_id'],
                            title=job_data['title'],
                            department=job_data['department'],
                            location=job_data['location'],
                            employment_type=job_data['employment_type'],
                            category=job_data['category'],
                            closing_date=job_data['closing_date'],
                            postsecondary_required=job_data['postsecondary_required'],
                            url=job_data['url'],
                            salary_text=job_data.get('salary_text'),
                            salary_min=job_data.get('salary_min'),
                            salary_max=job_data.get('salary_max'),
                            grade=job_data.get('grade'),
                            job_summary=job_data.get('job_summary'),
                            job_duties=job_data.get('job_duties'),
                            requirements=job_data.get('requirements')
                        )
                        
                        db.session.add(new_job)
                        jobs_scraped += 1
                        logger.info(f"Added new job: {job_data['requisition_id']} - {job_data['title']}")
                    
                    # Rate limiting - be respectful
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error processing job {job_data.get('requisition_id', 'unknown')}: {str(e)}")
                    continue
            
            # Commit all changes
            db.session.commit()
            logger.info(f"Scraping completed. {jobs_scraped} new jobs added.")
            
            return jobs_scraped
            
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            db.session.rollback()
            return 0

if __name__ == "__main__":
    scrape_jobs()
