#!/usr/bin/env python3
"""
Scheduler for Boardgame Bot
"""
import signal
import sys
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

from main import run_bot
from src.utils.config_loader import load_config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Global scheduler instance
scheduler = None


def job_function():
    """Job function to run bot"""
    logger.info("Scheduled job triggered - running bot...")
    try:
        success = run_bot()
        if success:
            logger.info("Scheduled job completed successfully")
        else:
            logger.error("Scheduled job failed")
    except Exception as e:
        logger.error(f"Error in scheduled job: {e}", exc_info=True)


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Shutdown signal received, stopping scheduler...")
    if scheduler:
        scheduler.shutdown()
    sys.exit(0)


def main():
    """Main scheduler entry point"""
    global scheduler
    
    # Load configuration
    logger.info("Loading scheduler configuration...")
    config = load_config()
    schedule_config = config.get('schedule', {})
    
    if not schedule_config.get('enabled', True):
        logger.info("Scheduler is disabled in config")
        return
    
    # Setup scheduler
    scheduler = BlockingScheduler()
    
    # Get schedule settings
    post_time = schedule_config.get('post_time', '19:00')
    timezone_str = schedule_config.get('timezone', 'Asia/Ho_Chi_Minh')
    frequency = schedule_config.get('frequency', 'daily')
    
    tz = timezone(timezone_str)
    
    # Parse time
    hour, minute = map(int, post_time.split(':'))
    
    # Setup trigger based on frequency
    if frequency == 'daily':
        trigger = CronTrigger(hour=hour, minute=minute, timezone=tz)
    elif frequency == 'weekly':
        # Post every Monday at specified time
        trigger = CronTrigger(day_of_week='mon', hour=hour, minute=minute, timezone=tz)
    else:
        # Default to daily
        trigger = CronTrigger(hour=hour, minute=minute, timezone=tz)
    
    # Add job
    scheduler.add_job(
        job_function,
        trigger=trigger,
        id='boardgame_bot_job',
        name='Boardgame Bot Post Job',
        replace_existing=True
    )
    
    logger.info(f"Scheduler configured: {frequency} at {post_time} ({timezone_str})")
    logger.info("Scheduler started. Press Ctrl+C to stop.")
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped by user")
        scheduler.shutdown()


if __name__ == '__main__':
    main()

