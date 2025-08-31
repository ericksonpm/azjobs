import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from scraper import scrape_jobs

logger = logging.getLogger(__name__)

def start_scheduler():
    """Start the background scheduler for automatic scraping"""
    scheduler = BackgroundScheduler()
    
    # Phoenix timezone
    phoenix_tz = pytz.timezone('America/Phoenix')
    
    # Schedule scraping 4 times a day: 6 AM, 10 AM, 2 PM, 6 PM Phoenix time
    scraping_times = [
        {'hour': 6, 'minute': 0},   # 6:00 AM
        {'hour': 10, 'minute': 0},  # 10:00 AM
        {'hour': 14, 'minute': 0},  # 2:00 PM
        {'hour': 18, 'minute': 0}   # 6:00 PM
    ]
    
    for time_config in scraping_times:
        trigger = CronTrigger(
            hour=time_config['hour'],
            minute=time_config['minute'],
            timezone=phoenix_tz
        )
        
        scheduler.add_job(
            func=scheduled_scrape,
            trigger=trigger,
            id=f"scrape_{time_config['hour']}_{time_config['minute']}",
            name=f"Scrape jobs at {time_config['hour']}:{time_config['minute']:02d} Phoenix time",
            replace_existing=True,
            max_instances=1
        )
        
        logger.info(f"Scheduled scraping at {time_config['hour']}:{time_config['minute']:02d} Phoenix time")
    
    # Start the scheduler
    scheduler.start()
    logger.info("Job scheduler started successfully")
    
    return scheduler

def scheduled_scrape():
    """Function called by scheduler to scrape jobs"""
    try:
        logger.info("Starting scheduled job scraping...")
        jobs_scraped = scrape_jobs()
        logger.info(f"Scheduled scraping completed. {jobs_scraped} new jobs added.")
    except Exception as e:
        logger.error(f"Error during scheduled scraping: {str(e)}")

if __name__ == "__main__":
    # For testing the scheduler
    import time
    scheduler = start_scheduler()
    
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()
