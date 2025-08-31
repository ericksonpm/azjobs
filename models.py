from app import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Float

class Job(db.Model):
    """Model for storing job postings"""
    __tablename__ = 'jobs'
    
    id = Column(Integer, primary_key=True)
    requisition_id = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False, index=True)
    department = Column(String(100), index=True)
    location = Column(String(100), index=True)
    employment_type = Column(String(50))
    category = Column(Text)
    closing_date = Column(DateTime)
    postsecondary_required = Column(String(10))
    url = Column(Text, nullable=False)
    
    # Salary information
    salary_text = Column(String(100))  # Raw salary text from the page
    salary_min = Column(Float)  # Parsed minimum salary
    salary_max = Column(Float)  # Parsed maximum salary
    grade = Column(String(20))  # Job grade
    
    # Additional job details
    job_summary = Column(Text)
    job_duties = Column(Text)
    requirements = Column(Text)
    
    # Metadata
    scraped_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Job {self.requisition_id}: {self.title}>'
    
    def to_dict(self):
        """Convert job to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'requisition_id': self.requisition_id,
            'title': self.title,
            'department': self.department,
            'location': self.location,
            'employment_type': self.employment_type,
            'category': self.category,
            'closing_date': self.closing_date.isoformat() if self.closing_date is not None else None,
            'postsecondary_required': self.postsecondary_required,
            'url': self.url,
            'salary_text': self.salary_text,
            'salary_min': self.salary_min,
            'salary_max': self.salary_max,
            'grade': self.grade,
            'scraped_at': self.scraped_at.isoformat() if self.scraped_at is not None else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at is not None else None
        }
