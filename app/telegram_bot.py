import os
import logging
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from dotenv import load_dotenv
from .database import db_client

# Load environment variables from a .env file for local testing
load_dotenv()

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
AUTHORIZED_USER_ID = int(os.environ.get("TELEGRAM_CHAT_ID"))

# Set up logging
logger = logging.getLogger(__name__)

# --- Bot Command Handlers ---

# State for the conversation handler
GET_SUMMARY_DATES = range(1)

# Security decorator to ensure only you can use the bot
def authorized_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        # print(update.effective_user.id)
        # print(AUTHORIZED_USER_ID)
        # print(type(update.effective_user.id))
        # print(type(AUTHORIZED_USER_ID))
        if update.effective_user.id != AUTHORIZED_USER_ID:
            await update.message.reply_text("Sorry, you are not authorized to use this bot.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

@authorized_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /start command."""
    await update.message.reply_text(
        "Welcome to your Expense Tracker Bot!\n\n"
        "Here's what you can do:\n"
        "- `/add 12.50 Coffee` - Add a manual transaction.\n"
        "- `/summary` - Get today's expense summary.\n"
        "- `/summary YYYY-MM-DD` - Summary for a specific day.\n"
        "- `/summary YYYY-MM-DD YYYY-MM-DD` - Summary for a date range.\n"
        "- `/help` - Show this message again."
    )

@authorized_only
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adds a manual transaction. Format: /add <amount> <description>"""
    try:
        parts = context.args
        if len(parts) < 2:
            raise ValueError("Invalid format.")
        
        amount = float(parts[0])
        recipient = " ".join(parts[1:])
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # Add transaction to Supabase
        transaction = await db_client.add_transaction(today_str, amount, recipient, "Manual")
        
        if transaction:
            await update.message.reply_text(
                f"✅ Transaction Added:\n"
                f"Amount: RM {transaction['amount']:.2f}\n"
                f"To: {transaction['recipient']}"
            )
        else:
            await update.message.reply_text("❌ Failed to add transaction. Please try again.")
            
    except (ValueError, IndexError):
        await update.message.reply_text("Please use the format: `/add <amount> <description>`\nExample: `/add 15.50 Lunch`")
    except Exception as e:
        logger.error(f"Error in add command: {e}")
        await update.message.reply_text("❌ An error occurred while adding the transaction.")

def format_summary(transactions, start_date_str, end_date_str):
    """Helper function to create the summary message text."""
    if not transactions:
        return f"No expenses found for the selected period ({start_date_str} to {end_date_str})."
    
    total_spend = sum(t['amount'] for t in transactions)
    
    date_header = start_date_str if start_date_str == end_date_str else f"{start_date_str} to {end_date_str}"
    
    message = f"*{'Expense Summary'}*\n_{date_header}_\n\n"
    
    # Group transactions by date
    transactions_by_date = {}
    for t in transactions:
        transactions_by_date.setdefault(t['date'], []).append(t)

    for date, trans in sorted(transactions_by_date.items()):
        message += f"*{date}*\n"
        for t in trans:
            source_emoji = "📧" if t['source'] == 'GX Bank' else "✍️"
            message += f"{source_emoji} `RM {t['amount']:>7.2f}` - {t['recipient']}\n"
    
    message += f"\n---------------------------\n"
    message += f"*Total Spend:* `RM {total_spend:.2f}`"
    
    return message

@authorized_only
async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provides a summary of expenses."""
    try:
        today = datetime.now()
        
        # Default: Today's summary
        start_date = end_date = today

        try:
            if len(context.args) == 1:
                # Single date summary
                start_date = end_date = datetime.strptime(context.args[0], "%Y-%m-%d")
            elif len(context.args) == 2:
                # Date range summary
                start_date = datetime.strptime(context.args[0], "%Y-%m-%d")
                end_date = datetime.strptime(context.args[1], "%Y-%m-%d")
        except ValueError:
            await update.message.reply_text("Invalid date format. Please use YYYY-MM-DD.")
            return

        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        # Get transactions from Supabase
        transactions = await db_client.get_transactions_by_date_range(start_date_str, end_date_str)
        
        message = format_summary(transactions, start_date_str, end_date_str)
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in summary command: {e}")
        await update.message.reply_text("❌ An error occurred while fetching the summary.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the help message."""
    await start(update, context) # Re-use the start message for help

async def send_daily_summary():
    """
    Send daily summary via Telegram API (for external cron jobs)
    This function can be called by GitHub Actions or other external services
    """
    try:
        import requests
        
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        # Get today's transactions from Supabase
        transactions = await db_client.get_transactions_by_date(today_str)
        
        if not transactions:
            message = f"🔔 *Daily Expense Summary for {today_str}* 🔔\n\nNo expenses recorded for today. ✨"
        else:
            total_spend = sum(t['amount'] for t in transactions)
            message = f"🔔 *Daily Expense Summary for {today_str}* 🔔\n\n"
            message += "*Today's Expenses:*\n"
            
            for t in transactions:
                source_emoji = "📧" if t['source'] == 'GX Bank' else "✍️"
                message += f"{source_emoji} `RM {t['amount']:>7.2f}` - {t['recipient']}\n"
            
            message += f"\n*Total:* `RM {total_spend:.2f}`"
        
        # Send message via Telegram API
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': AUTHORIZED_USER_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            logger.info("Daily summary message sent successfully!")
            return True
        else:
            logger.error(f"Failed to send summary message: {response.json()}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending daily summary: {e}")
        return False

def main():
    """Start the bot."""
    print("Starting bot...")
    
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("help", help_command))

    print("Bot is running. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
