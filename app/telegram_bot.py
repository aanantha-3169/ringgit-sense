import os
import json
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

# Load environment variables from a .env file for local testing
load_dotenv()

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TRANSACTIONS_FILE = "transactions.json"
AUTHORIZED_USER_ID = int(os.environ.get("TELEGRAM_CHAT_ID"))

# --- Data Handling ---
def load_transactions():
    """Loads transactions from the JSON file."""
    if not os.path.exists(TRANSACTIONS_FILE):
        return []
    try:
        with open(TRANSACTIONS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_transactions(transactions):
    """Saves transactions to the JSON file."""
    with open(TRANSACTIONS_FILE, "w") as f:
        json.dump(transactions, f, indent=4)

def add_transaction(date, amount, recipient, source="Manual"):
    """Adds a new transaction to our data file."""
    transactions = load_transactions()
    new_transaction = {
        "date": date,
        "amount": amount,
        "recipient": recipient,
        "source": source
    }
    transactions.append(new_transaction)
    save_transactions(transactions)
    return new_transaction

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
        
        transaction = add_transaction(today_str, amount, recipient)
        
        await update.message.reply_text(
            f"✅ Transaction Added:\n"
            f"Amount: RM {transaction['amount']:.2f}\n"
            f"To: {transaction['recipient']}"
        )
    except (ValueError, IndexError):
        await update.message.reply_text("Please use the format: `/add <amount> <description>`\nExample: `/add 15.50 Lunch`")

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
    transactions = load_transactions()
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

    filtered_transactions = [
        t for t in transactions if start_date_str <= t['date'] <= end_date_str
    ]
    
    message = format_summary(filtered_transactions, start_date_str, end_date_str)
    await update.message.reply_text(message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the help message."""
    await start(update, context) # Re-use the start message for help

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
