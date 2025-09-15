import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# --- Telegram Imports ---
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Scheduler Imports ---
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- Your Existing Logic ---
# You can import from your other files or copy the functions here
from email_fetcher import fetch_and_save_emails
from telegram_bot import authorized_only, start, add, summary, help_command, load_transactions, format_summary

# Load environment variables from a .env file for local testing
load_dotenv()

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
AUTHORIZED_USER_ID = int(os.environ.get("TELEGRAM_CHAT_ID"))
FETCH_TIME = "20:00"
SUMMARY_TIME = "20:01"

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Scheduled Job Functions ---
async def scheduled_email_fetch(context: ContextTypes.DEFAULT_TYPE):
    """Job to be run by the scheduler to fetch emails."""
    logger.info("Running scheduled email fetch job.")
    try:
        # We run this in a separate thread to avoid blocking the bot
        await context.application.create_task(fetch_and_save_emails())
    except Exception as e:
        logger.error(f"Error in scheduled_email_fetch: {e}")

async def send_daily_summary(context: ContextTypes.DEFAULT_TYPE):
    """Job to generate and send the daily summary."""
    logger.info("Running scheduled daily summary job.")
    today_str = datetime.now().strftime('%Y-%m-%d')
    transactions = load_transactions()
    
    today_transactions = [t for t in transactions if t['date'] == today_str]
    
    message = f"🔔 *Daily Summary for {today_str}* 🔔\n\n"
    message += format_summary(today_transactions, today_str, today_str)

    await context.bot.send_message(
        chat_id=AUTHORIZED_USER_ID,
        text=message,
        parse_mode='Markdown'
    )


def main():
    """Start the bot and the scheduler."""
    logger.info("Starting bot...")
    
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add command handlers from your original bot
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("help", help_command))

    # --- Scheduler Setup ---
    scheduler = AsyncIOScheduler(timezone="Asia/Kuala_Lumpur")
    scheduler.add_job(scheduled_email_fetch, 'cron', hour=20, minute=0, second=5, args=[app])
    scheduler.add_job(send_daily_summary, 'cron', hour=20, minute=1, second=5, args=[app])
    scheduler.start()
    logger.info(f"Scheduler started. Jobs will run at {FETCH_TIME} and {SUMMARY_TIME} daily.")

    # Run the bot until the user presses Ctrl-C
    app.run_polling()

if __name__ == "__main__":
    main()