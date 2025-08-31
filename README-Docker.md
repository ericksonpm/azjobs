# Docker Deployment Guide

## Important Note
This Docker configuration is for deploying the Arizona State Jobs scraper **outside of Replit**. Replit uses a NixOS environment that doesn't support Docker or containerization.

## Quick Start

1. **Copy these files to your deployment server:**
   - `Dockerfile`
   - `docker-compose.yml` 
   - `docker-requirements.txt`
   - All Python application files (`.py` files and `templates/` folder)

2. **Update environment variables in docker-compose.yml:**
   ```yaml
   environment:
     - SESSION_SECRET=your-strong-secret-key-here
   ```

3. **Start the application:**
   ```bash
   docker-compose up -d
   ```

## What This Sets Up

- **Web Application** - Flask app with automatic job scraping
- **PostgreSQL Database** - Stores job listings
- **Automatic Scheduling** - Scrapes 4 times daily (6 AM, 10 AM, 2 PM, 6 PM Phoenix time)
- **Data Cleanup** - Removes jobs >25 days old or no longer on official site

## Access Your Application

- **Website:** http://localhost:5000
- **Database:** localhost:5432 (if needed for admin tools)

## Management Commands

```bash
# View logs
docker-compose logs -f web

# Stop application
docker-compose down

# Update application
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Backup database
docker-compose exec db pg_dump -U azjobs_user azjobs_db > backup.sql
```

## Production Deployment

For production:
1. Change default passwords in docker-compose.yml
2. Use environment files instead of hardcoded values
3. Set up proper SSL/TLS termination
4. Consider using a reverse proxy (nginx)
5. Set up automated backups