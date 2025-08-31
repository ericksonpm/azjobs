# Overview

This is a Flask-based web application that automatically scrapes and tracks job postings from the Arizona State Jobs website (azstatejobs.gov). The application periodically collects job data including titles, departments, locations, salary information, and other details, storing them in a database and presenting them through a user-friendly web interface with advanced filtering and search capabilities.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Backend Architecture
- **Framework**: Flask web application with SQLAlchemy ORM for database operations
- **Database**: SQLite by default with configurable DATABASE_URL for production databases
- **Models**: Single Job model storing comprehensive job posting information including salary data, requirements, and metadata
- **Scheduled Tasks**: APScheduler background scheduler running scraping jobs 4 times daily (6 AM, 10 AM, 2 PM, 6 PM Phoenix time)

## Web Scraping System
- **Target**: Arizona State Jobs website (azstatejobs.gov)
- **Method**: BeautifulSoup HTML parsing with requests session for HTTP handling
- **Data Extraction**: Parses job tables and individual job detail pages for comprehensive information
- **Rate Limiting**: Built-in delays and session management to avoid overwhelming the target server

## Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap 5 dark theme
- **UI Components**: DataTables for advanced table functionality including sorting, filtering, and responsive design
- **Styling**: Bootstrap-based responsive design with Feather icons
- **Data Loading**: AJAX-based data loading for improved performance

## Database Schema
- **Jobs Table**: Stores job postings with fields for requisition_id, title, department, location, employment_type, salary information, job details, and metadata
- **Indexing**: Strategic indexes on frequently queried fields (requisition_id, title, department, location, scraped_at)
- **Salary Processing**: Separate fields for raw salary text and parsed min/max values

## Application Entry Points
- **Development**: Direct Flask app execution via app.py
- **Production**: main.py entry point that starts both scheduler and Flask server
- **Proxy Support**: ProxyFix middleware for deployment behind reverse proxies

# External Dependencies

## Core Framework Dependencies
- **Flask**: Web framework with SQLAlchemy extension for database operations
- **SQLAlchemy**: ORM with DeclarativeBase for modern database modeling

## Web Scraping Dependencies
- **requests**: HTTP client for web scraping with session management
- **BeautifulSoup**: HTML parsing library for extracting job data from web pages

## Scheduling Dependencies
- **APScheduler**: Background job scheduler with cron triggers
- **pytz**: Timezone handling for Phoenix time scheduling

## Frontend Dependencies
- **Bootstrap 5**: CSS framework with dark theme variant
- **DataTables**: Advanced table functionality with responsive design
- **Feather Icons**: Icon library for UI elements

## Target Website
- **Arizona State Jobs**: Primary data source at azstatejobs.gov/jobs/search
- **Data Format**: HTML tables and detail pages containing job posting information