#!/usr/bin/env python3
"""
Daily tasks script for finance tracker
This script is run by GitHub Actions to:
1. Fetch emails from GX Bank
2. Send daily summary to Telegram
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from email_fetcher import fetch_and_save_emails
from telegram_bot import send_daily_summary

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def run_daily_tasks():
    """Run all daily tasks"""
    logger.info(f"Starting daily tasks at {datetime.now()}")
    
    try:
        # Step 1: Fetch emails from GX Bank
        logger.info("Step 1: Fetching emails from GX Bank...")
        await fetch_and_save_emails()
        logger.info("Email fetching completed successfully")
        
        # Step 2: Send daily summary
        logger.info("Step 2: Sending daily summary...")
        success = await send_daily_summary()
        
        if success:
            logger.info("Daily summary sent successfully")
        else:
            logger.error("Failed to send daily summary")
            return False
            
        logger.info("All daily tasks completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error running daily tasks: {e}")
        return False

def main():
    """Main function"""
    logger.info("Finance Tracker Daily Tasks Starting...")
    
    # Run the async tasks
    success = asyncio.run(run_daily_tasks())
    
    if success:
        logger.info("Daily tasks completed successfully")
        sys.exit(0)
    else:
        logger.error("Daily tasks failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
