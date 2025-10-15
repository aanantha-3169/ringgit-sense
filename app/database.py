"""
Database client for Supabase integration
Handles all database operations for the finance tracker
"""

import os
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class DatabaseClient:
    """Supabase database client for finance tracker operations"""
    
    def __init__(self):
        """Initialize Supabase client"""
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        logger.info("Supabase client initialized successfully")
    
    async def add_transaction(
        self, 
        date: str, 
        amount: float, 
        recipient: str, 
        source: str = "Manual", 
        email_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Add a new transaction to the database
        
        Args:
            date: Transaction date in YYYY-MM-DD format
            amount: Transaction amount
            recipient: Transaction recipient/description
            source: Source of transaction (Manual, GX Bank, etc.)
            email_id: Email ID for duplicate prevention
            
        Returns:
            Dict containing the created transaction or None if failed
        """
        try:
            transaction_data = {
                'date': date,
                'amount': amount,
                'recipient': recipient,
                'source': source,
                'email_id': email_id
            }
            
            result = self.supabase.table('transactions').insert(transaction_data).execute()
            
            if result.data:
                logger.info(f"Transaction added: RM {amount:.2f} to {recipient} on {date}")
                return result.data[0]
            else:
                logger.error("Failed to add transaction: No data returned")
                return None
                
        except Exception as e:
            logger.error(f"Error adding transaction: {e}")
            return None
    
    async def get_transactions(
        self, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> List[Dict]:
        """
        Get transactions from the database
        
        Args:
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            
        Returns:
            List of transaction dictionaries
        """
        try:
            query = self.supabase.table('transactions').select('*')
            
            if start_date:
                query = query.gte('date', start_date)
            if end_date:
                query = query.lte('date', end_date)
            
            result = query.order('date', desc=True).execute()
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error fetching transactions: {e}")
            return []
    
    async def get_transactions_by_date_range(
        self, 
        start_date: str, 
        end_date: str
    ) -> List[Dict]:
        """
        Get transactions within a specific date range
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of transaction dictionaries
        """
        return await self.get_transactions(start_date, end_date)
    
    async def get_transactions_by_date(self, target_date: str) -> List[Dict]:
        """
        Get transactions for a specific date
        
        Args:
            target_date: Target date (YYYY-MM-DD)
            
        Returns:
            List of transaction dictionaries
        """
        return await self.get_transactions(target_date, target_date)
    
    async def check_email_exists(self, email_id: str) -> bool:
        """
        Check if an email ID already exists in the database
        
        Args:
            email_id: Email message ID
            
        Returns:
            True if email exists, False otherwise
        """
        try:
            result = self.supabase.table('transactions').select('id').eq('email_id', email_id).execute()
            return len(result.data) > 0 if result.data else False
            
        except Exception as e:
            logger.error(f"Error checking email existence: {e}")
            return False
    
    async def get_total_spent(
        self, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> float:
        """
        Calculate total amount spent in a date range
        
        Args:
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            
        Returns:
            Total amount spent
        """
        transactions = await self.get_transactions(start_date, end_date)
        return sum(t['amount'] for t in transactions)
    
    async def get_user_settings(self, telegram_user_id: int) -> Optional[Dict]:
        """
        Get user settings by Telegram user ID
        
        Args:
            telegram_user_id: Telegram user ID
            
        Returns:
            User settings dictionary or None
        """
        try:
            result = self.supabase.table('user_settings').select('*').eq('telegram_user_id', telegram_user_id).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error fetching user settings: {e}")
            return None
    
    async def update_user_settings(
        self, 
        telegram_user_id: int, 
        settings: Dict
    ) -> Optional[Dict]:
        """
        Update user settings
        
        Args:
            telegram_user_id: Telegram user ID
            settings: Settings dictionary to update
            
        Returns:
            Updated settings dictionary or None
        """
        try:
            result = self.supabase.table('user_settings').update(settings).eq('telegram_user_id', telegram_user_id).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error updating user settings: {e}")
            return None
    
    async def create_user_settings(
        self, 
        telegram_user_id: int, 
        settings: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Create new user settings
        
        Args:
            telegram_user_id: Telegram user ID
            settings: Initial settings dictionary
            
        Returns:
            Created settings dictionary or None
        """
        try:
            default_settings = {
                'telegram_user_id': telegram_user_id,
                'gx_bank_sender': 'alerts@gxbank.my',
                'timezone': 'Asia/Kuala_Lumpur'
            }
            
            if settings:
                default_settings.update(settings)
            
            result = self.supabase.table('user_settings').insert(default_settings).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error creating user settings: {e}")
            return None

# Global database client instance
db_client = DatabaseClient()
