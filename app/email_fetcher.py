import imaplib
import email
from email.header import decode_header
import re
import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Try relative import first, fallback to absolute import
try:
    from .database import db_client
except ImportError:
    # For GitHub Actions and direct script execution
    import sys
    sys.path.append(os.path.dirname(__file__))
    from database import db_client

# Load environment variables from a .env file for local testing
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# --- Configuration ---
EMAIL_SERVER = "imap.gmail.com"
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")
GX_BANK_SENDER = "alerts@gxbank.my"

# --- Helper Functions ---
def clean_body(body_text):
    if not body_text: return ""
    clean = re.sub('<[^<]+?>', '', body_text)
    clean = clean.replace('&nbsp;', ' ').replace('\r\n', '\n')
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

def parse_gx_bank_email(body):
    match = re.search(r"Your transaction of RM\s*([\d,]+\.\d{2}) to (.*?) is successful", body, re.IGNORECASE)
    if match:
        try:
            amount_str = match.group(1).replace(',', '')
            amount = float(amount_str)
            recipient = match.group(2).strip()
            return amount, recipient
        except (ValueError, IndexError):
            return None, None
    return None, None

# Removed JSON file functions - now using Supabase database

# --- Main Logic ---
async def fetch_and_save_emails():
    """Connects to Gmail, fetches new transactions, and saves them to Supabase."""
    logger.info(f"Starting email fetch at {datetime.now()}")
    
    try:
        mail = imaplib.IMAP4_SSL(EMAIL_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")
        
        # Search for emails from the last 2 days to avoid missing any
        search_date = (datetime.now() - timedelta(days=2)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'(FROM "{GX_BANK_SENDER}" SENTSINCE "{search_date}")')

        if status != "OK":
            logger.error("Failed to search for emails.")
            return

        email_ids = messages[0].split()
        if not email_ids:
            logger.info("No new emails found.")
            mail.logout()
            return
            
        logger.info(f"Found {len(email_ids)} potential emails to process.")
        
        new_transactions_found = 0

        for email_id in email_ids:
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            if status != 'OK': 
                continue

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    msg_id = msg.get('Message-ID')

                    # Check if email already exists in database
                    if await db_client.check_email_exists(msg_id):
                        continue
                    
                    email_body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() in ["text/plain", "text/html"]:
                                try:
                                    email_body += part.get_payload(decode=True).decode('utf-8', 'ignore')
                                except: 
                                    pass
                    else:
                        try:
                            email_body = msg.get_payload(decode=True).decode('utf-8', 'ignore')
                        except: 
                            pass
                    
                    clean_text = clean_body(email_body)
                    amount, recipient = parse_gx_bank_email(clean_text)
                    
                    date_tuple = email.utils.parsedate_tz(msg['Date'])
                    if date_tuple:
                        local_date = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
                        date_str = local_date.strftime("%Y-%m-%d")

                        if amount and recipient:
                            # Add transaction to Supabase
                            transaction = await db_client.add_transaction(
                                date_str, 
                                amount, 
                                recipient, 
                                "GX Bank", 
                                msg_id
                            )
                            
                            if transaction:
                                new_transactions_found += 1
                                logger.info(f"Added: RM {amount:.2f} to {recipient} on {date_str}")
        
        if new_transactions_found > 0:
            logger.info(f"Successfully saved {new_transactions_found} new transaction(s) to Supabase.")
        else:
            logger.info("No new transactions to save.")

        mail.logout()

    except Exception as e:
        logger.error(f"An error occurred during email fetch: {e}")

# Synchronous wrapper for backward compatibility
def fetch_and_save_emails_sync():
    """Synchronous wrapper for the async email fetching function"""
    import asyncio
    asyncio.run(fetch_and_save_emails())

if __name__ == '__main__':
    import asyncio
    asyncio.run(fetch_and_save_emails())
