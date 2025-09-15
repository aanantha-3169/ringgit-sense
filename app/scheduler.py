import schedule
import time
import subprocess
import os
import requests
import json
from datetime import datetime

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "6985833874:AAHS6rDw7ntPnq9F4txdL15dhdFKvmxD5UU")
AUTHORIZED_USER_ID = os.environ.get("TELEGRAM_CHAT_ID", 5997427916)
FETCH_TIME = "20:00" # 8:00 PM
SUMMARY_TIME = "20:01" # 8:01 PM

def run_email_fetcher():
    """Executes the email_fetcher.py script."""
    print(f"[{datetime.now()}] Running email fetcher job...")
    try:
        # Use subprocess to run the script in a separate process
        subprocess.run(["python", "email_fetcher.py"], check=True)
        print("Email fetcher job completed.")
    except subprocess.CalledProcessError as e:
        print(f"Error running email_fetcher.py: {e}")
    except FileNotFoundError:
        print("Error: 'python' command not found. Make sure Python is in your system's PATH.")

def send_daily_summary():
    """Sends a request to the bot to generate and send the daily summary."""
    print(f"[{datetime.now()}] Sending daily summary notification...")
    today_str = datetime.now().strftime('%Y-%m-%d')
    message = (
        f"🔔 *Daily Expense Summary for {today_str}* 🔔\n\n"
        "Here are your transactions for today. I've automatically fetched the latest from your email."
    )
    
    # We will manually craft a summary here to avoid complexity of bot communication
    # For a more advanced setup, the bot would have an API endpoint
    
    # Load transactions and filter for today
    try:
        with open("transactions.json", "r") as f:
            transactions = json.load(f)
        
        today_transactions = [t for t in transactions if t['date'] == today_str]
        
        if not today_transactions:
            message += "\n\nNo expenses recorded for today. ✨"
        else:
            total_spend = sum(t['amount'] for t in today_transactions)
            message += "\n\n*Today's Expenses:*\n"
            for t in today_transactions:
                source_emoji = "📧" if t['source'] == 'GX Bank' else "✍️"
                message += f"{source_emoji} `RM {t['amount']:>7.2f}` - {t['recipient']}\n"
            message += f"\n*Total:* `RM {total_spend:.2f}`"

    except (FileNotFoundError, json.JSONDecodeError):
        message += "\n\nCould not load transaction data."

    # Use the requests library to send the message via the Telegram API
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': AUTHORIZED_USER_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Daily summary message sent successfully!")
        else:
            print(f"Failed to send summary message: {response.json()}")
    except Exception as e:
        print(f"An error occurred sending summary message: {e}")


if __name__ == "__main__":
    print("Starting expense tracker scheduler.")
    print(f"Email fetch will run daily at {FETCH_TIME}.")
    print(f"Daily summary will be sent at {SUMMARY_TIME}.")

    # Schedule the jobs
    # schedule.every().day.do(run_email_fetcher)

    schedule.every().day.at(FETCH_TIME).do(run_email_fetcher)
    schedule.every().day.at(SUMMARY_TIME).do(send_daily_summary)

    # Initial run for testing purposes (optional)
    run_email_fetcher()
    send_daily_summary()

    while True:
        schedule.run_pending()
        time.sleep(60) # check every minute
