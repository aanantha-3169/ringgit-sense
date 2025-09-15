import os
import logging
import asyncio
import signal
from dotenv import load_dotenv

from telegram.ext import Application, CommandHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .email_fetcher import fetch_and_save_emails
from .telegram_bot import start, add, summary, help_command

load_dotenv()

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
AUTHORIZED_USER_ID = int(os.environ.get("TELEGRAM_CHAT_ID"))

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Scheduled Job Functions (These remain the same) ---
async def scheduled_email_fetch(context):
    logger.info("Running scheduled email fetch job.")
    try:
        await context.application.create_task(fetch_and_save_emails())
    except Exception as e:
        logger.error(f"Error in scheduled_email_fetch: {e}")

async def send_daily_summary(context):
    # ... (code to format and send the message)
    logger.info("Running scheduled daily summary job.")
    # ...

async def main():
    """Start the bot and the scheduler."""
    logger.info("Starting bot...")
    
    # --- Create the Application with Signal Handlers ---
    # This allows you to stop the bot gracefully with Ctrl+C
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("help", help_command))

    # --- Scheduler Setup ---
    scheduler = AsyncIOScheduler(timezone="Asia/Kuala_Lumpur")
    scheduler.add_job(scheduled_email_fetch, 'cron', hour=20, minute=0, args=[app])
    scheduler.add_job(send_daily_summary, 'cron', hour=20, minute=1, args=[app])
    
    # --- The Correct Startup Sequence ---
    # The `async with` block handles app.initialize() and app.shutdown() automatically.
    async with app:
        scheduler.start()
        logger.info("Scheduler started.")
        
        # Start the bot's internal processes
        await app.start()
        # Start listening for updates from Telegram
        await app.updater.start_polling()
        
        logger.info("Bot is running. Press Ctrl+C to stop.")
        
        # Keep the script running until a shutdown signal is received
        # This replaces the blocking `run_polling()` call
        while app.running:
            await asyncio.sleep(1)
        
        # This part will only be reached after you press Ctrl+C
        logger.info("Bot is shutting down.")
        scheduler.shutdown()
        
        # Stop the bot's internal processes
        await app.updater.stop()
        await app.stop()

if __name__ == "__main__":
    # --- The Correct Way to Handle Shutdown ---
    # We wrap the main call in a try/except block to catch Ctrl+C
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot shutdown successfully.")