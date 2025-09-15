import imaplib
import email
from email.header import decode_header
import re
import os
import json
from datetime import datetime,timedelta
from dotenv import load_dotenv

# Load environment variables from a .env file for local testing
load_dotenv()

# --- Configuration ---
EMAIL_SERVER = "imap.gmail.com"
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")
GX_BANK_SENDER = "alerts@gxbank.my"
TRANSACTIONS_FILE = "transactions.json"

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

def load_transactions():
    if not os.path.exists(TRANSACTIONS_FILE): return []
    try:
        with open(TRANSACTIONS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_transactions(transactions):
    with open(TRANSACTIONS_FILE, "w") as f:
        json.dump(transactions, f, indent=4)

# --- Main Logic ---
def fetch_and_save_emails():
    """Connects to Gmail, fetches new transactions, and saves them to the JSON file."""
    print(f"[{datetime.now()}] Starting email fetch...")
    
    try:
        mail = imaplib.IMAP4_SSL(EMAIL_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")
        
        # Search for emails from the last 2 days to avoid missing any
        search_date = (datetime.now() - timedelta(days=2)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'(FROM "{GX_BANK_SENDER}" SENTSINCE "{search_date}")')

        if status != "OK":
            print("Failed to search for emails.")
            return

        email_ids = messages[0].split()
        if not email_ids:
            print("No new emails found.")
            mail.logout()
            return
            
        print(f"Found {len(email_ids)} potential emails to process.")
        
        transactions = load_transactions()
        existing_ids = {t.get('email_id') for t in transactions}
        new_transactions_found = 0

        for email_id in email_ids:
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            if status != 'OK': continue

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    msg_id = msg.get('Message-ID')

                    # --- Prevent Duplicates ---
                    if msg_id in existing_ids:
                        continue
                    
                    email_body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() in ["text/plain", "text/html"]:
                                try:
                                    email_body += part.get_payload(decode=True).decode('utf-8', 'ignore')
                                except: pass
                    else:
                        try:
                            email_body = msg.get_payload(decode=True).decode('utf-8', 'ignore')
                        except: pass
                    
                    clean_text = clean_body(email_body)
                    amount, recipient = parse_gx_bank_email(clean_text)
                    
                    date_tuple = email.utils.parsedate_tz(msg['Date'])
                    if date_tuple:
                        local_date = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
                        date_str = local_date.strftime("%Y-%m-%d")

                        if amount and recipient:
                            new_transaction = {
                                "date": date_str,
                                "amount": amount,
                                "recipient": recipient,
                                "source": "GX Bank",
                                "email_id": msg_id # Store ID to prevent duplicates
                            }
                            transactions.append(new_transaction)
                            existing_ids.add(msg_id)
                            new_transactions_found += 1
                            print(f"  + Added: RM {amount:.2f} to {recipient} on {date_str}")
        
        if new_transactions_found > 0:
            save_transactions(transactions)
            print(f"Saved {new_transactions_found} new transaction(s).")
        else:
            print("No new transactions to save.")

        mail.logout()

    except Exception as e:
        print(f"An error occurred during email fetch: {e}")

if __name__ == '__main__':
    fetch_and_save_emails()
