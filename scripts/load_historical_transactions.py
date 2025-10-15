#!/usr/bin/env python3
"""
Manual email transaction loader for finance tracker
Loads all transactions from emails for the last month (October 1st to yesterday)
"""

import asyncio
import imaplib
import email
from email.header import decode_header
import re
import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sys

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from database import db_client

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Configuration ---
EMAIL_SERVER = "imap.gmail.com"
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")
GX_BANK_SENDER = "alerts@gxbank.my"

# Date range: October 1st to yesterday
START_DATE = datetime(2024, 10, 1)
END_DATE = datetime.now() - timedelta(days=1)

def clean_body(body_text):
    """Clean HTML and formatting from email body"""
    if not body_text: 
        return ""
    clean = re.sub('<[^<]+?>', '', body_text)
    clean = clean.replace('&nbsp;', ' ').replace('\r\n', '\n')
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

def parse_gx_bank_email(body):
    """Parse GX Bank transaction from email body"""
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

async def load_historical_transactions():
    """Load all transactions from emails for the specified date range"""
    logger.info(f"Starting historical email load from {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")
    
    try:
        # Connect to Gmail
        mail = imaplib.IMAP4_SSL(EMAIL_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")
        
        # Search for emails from GX Bank in the date range
        start_date_str = START_DATE.strftime("%d-%b-%Y")
        end_date_str = END_DATE.strftime("%d-%b-%Y")
        
        search_query = f'(FROM "{GX_BANK_SENDER}" SENTSINCE "{start_date_str}" SENTBEFORE "{end_date_str}")'
        logger.info(f"Searching with query: {search_query}")
        
        status, messages = mail.search(None, search_query)
        
        if status != "OK":
            logger.error("Failed to search for emails.")
            return

        email_ids = messages[0].split()
        logger.info(f"Found {len(email_ids)} emails to process")
        
        if not email_ids:
            logger.info("No emails found in the specified date range.")
            mail.logout()
            return
        
        transactions_loaded = 0
        duplicates_skipped = 0
        errors = 0

        for i, email_id in enumerate(email_ids):
            try:
                logger.info(f"Processing email {i+1}/{len(email_ids)}")
                
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                if status != 'OK': 
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        msg_id = msg.get('Message-ID')

                        # Check if email already exists in database
                        if await db_client.check_email_exists(msg_id):
                            logger.info(f"  Skipping duplicate email: {msg_id}")
                            duplicates_skipped += 1
                            continue
                        
                        # Extract email body
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
                        
                        # Parse transaction
                        clean_text = clean_body(email_body)
                        amount, recipient = parse_gx_bank_email(clean_text)
                        
                        # Extract date
                        date_tuple = email.utils.parsedate_tz(msg['Date'])
                        if date_tuple:
                            local_date = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
                            date_str = local_date.strftime("%Y-%m-%d")

                            # Check if date is within our range
                            if START_DATE.date() <= local_date.date() <= END_DATE.date():
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
                                        transactions_loaded += 1
                                        logger.info(f"  ✅ Loaded: RM {amount:.2f} to {recipient} on {date_str}")
                                    else:
                                        errors += 1
                                        logger.error(f"  ❌ Failed to save transaction")
                                else:
                                    logger.info(f"  ⚠️  Could not parse transaction from email")
                            else:
                                logger.info(f"  ⏭️  Email date {date_str} outside range, skipping")
                        else:
                            logger.warning(f"  ⚠️  Could not parse email date")
                            
            except Exception as e:
                logger.error(f"Error processing email {email_id}: {e}")
                errors += 1
                continue
        
        # Summary
        logger.info("=" * 50)
        logger.info("HISTORICAL LOAD SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Date range: {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")
        logger.info(f"Emails processed: {len(email_ids)}")
        logger.info(f"Transactions loaded: {transactions_loaded}")
        logger.info(f"Duplicates skipped: {duplicates_skipped}")
        logger.info(f"Errors: {errors}")
        logger.info("=" * 50)
        
        mail.logout()
        
        if transactions_loaded > 0:
            logger.info("✅ Historical load completed successfully!")
        else:
            logger.warning("⚠️  No transactions were loaded. Check your date range and email filters.")
            
    except Exception as e:
        logger.error(f"Error during historical load: {e}")

async def main():
    """Main function"""
    logger.info("Starting historical transaction loader...")
    
    # Verify environment variables
    if not EMAIL_USER or not EMAIL_PASS:
        logger.error("EMAIL_USER and EMAIL_PASS must be set in environment variables")
        return
    
    # Run the historical load
    await load_historical_transactions()

if __name__ == "__main__":
    asyncio.run(main())
