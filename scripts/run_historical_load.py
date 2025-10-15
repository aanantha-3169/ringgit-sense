#!/usr/bin/env python3
"""
Simple historical transaction loader
Run this locally to load transactions from October 1st to yesterday
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

# Load environment variables
load_dotenv()

async def main():
    """Run the historical loader"""
    print("🔄 Loading historical transactions from October 1st to yesterday...")
    print("📧 This will fetch all GX Bank emails from the last month")
    print("⏳ Please wait...")
    
    try:
        from load_historical_transactions import load_historical_transactions
        await load_historical_transactions()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure you have:")
        print("1. Set up your .env file with EMAIL_USER and EMAIL_PASS")
        print("2. Set up Supabase and run the database schema")
        print("3. Set SUPABASE_URL and SUPABASE_KEY in your .env file")

if __name__ == "__main__":
    asyncio.run(main())
