import os
import logging
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///azstatejobs.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Import models to create tables
    import models
    db.create_all()

@app.route('/')
def index():
    """Main page displaying job listings"""
    try:
        # Get filter parameters
        search_query = request.args.get('search', '')
        department_filter = request.args.get('department', '')
        location_filter = request.args.get('location', '')
        salary_min = request.args.get('salary_min', type=int)
        salary_max = request.args.get('salary_max', type=int)
        
        # Query jobs with filters
        query = models.Job.query
        
        if search_query:
            query = query.filter(models.Job.title.contains(search_query))
        
        if department_filter:
            query = query.filter(models.Job.department == department_filter)
            
        if location_filter:
            query = query.filter(models.Job.location.contains(location_filter))
            
        if salary_min is not None:
            query = query.filter(models.Job.salary_min >= salary_min)
            
        if salary_max is not None:
            query = query.filter(models.Job.salary_max <= salary_max)
        
        # Order by newest first
        jobs = query.order_by(models.Job.scraped_at.desc()).all()
        
        # Get unique departments and locations for filters
        departments = db.session.query(models.Job.department).distinct().order_by(models.Job.department).all()
        departments = [d[0] for d in departments if d[0]]
        
        locations = db.session.query(models.Job.location).distinct().order_by(models.Job.location).all()
        locations = [l[0] for l in locations if l[0]]
        
        return render_template('index.html', 
                             jobs=jobs, 
                             departments=departments,
                             locations=locations,
                             current_search=search_query,
                             current_department=department_filter,
                             current_location=location_filter,
                             current_salary_min=salary_min,
                             current_salary_max=salary_max)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return render_template('index.html', jobs=[], departments=[], locations=[], error="Error loading jobs")

@app.route('/api/jobs')
def api_jobs():
    """API endpoint for DataTables AJAX"""
    try:
        # Get DataTables parameters
        draw = request.args.get('draw', type=int, default=1)
        start = request.args.get('start', type=int, default=0)
        length = request.args.get('length', type=int, default=10)
        search_value = request.args.get('search[value]', default='')
        
        # Base query
        query = models.Job.query
        
        # Apply search filter
        if search_value:
            query = query.filter(
                models.Job.title.contains(search_value) |
                models.Job.department.contains(search_value) |
                models.Job.location.contains(search_value)
            )
        
        # Get total count before pagination
        total_records = models.Job.query.count()
        filtered_records = query.count()
        
        # Apply ordering
        query = query.order_by(models.Job.scraped_at.desc())
        
        # Apply pagination
        jobs = query.offset(start).limit(length).all()
        
        # Format data for DataTables
        data = []
        for job in jobs:
            salary_display = ""
            if job.salary_min and job.salary_max:
                salary_display = f"${job.salary_min:,} - ${job.salary_max:,}"
            elif job.salary_text:
                salary_display = job.salary_text
            
            data.append({
                'title': f'<a href="{job.url}" target="_blank" class="text-decoration-none">{job.title}</a>',
                'department': job.department or '',
                'location': job.location or '',
                'employment_type': job.employment_type or '',
                'salary': salary_display,
                'closing_date': job.closing_date.strftime('%b %d, %Y') if job.closing_date else '',
                'scraped_at': job.scraped_at.strftime('%b %d, %Y %I:%M %p')
            })
        
        return jsonify({
            'draw': draw,
            'recordsTotal': total_records,
            'recordsFiltered': filtered_records,
            'data': data
        })
    except Exception as e:
        logger.error(f"Error in API jobs endpoint: {str(e)}")
        return jsonify({'error': 'Error loading jobs'}), 500

@app.route('/scrape')
def manual_scrape():
    """Manual trigger for scraping (for testing)"""
    try:
        from scraper import scrape_jobs
        jobs_scraped = scrape_jobs()
        return jsonify({'success': True, 'jobs_scraped': jobs_scraped})
    except Exception as e:
        logger.error(f"Error in manual scrape: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Start the scheduler
    from scheduler import start_scheduler
    start_scheduler()
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
