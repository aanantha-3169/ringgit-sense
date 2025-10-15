-- Supabase Database Schema for Finance Tracker
-- Optimized for free tier usage

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Transactions table (optimized for size)
CREATE TABLE transactions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    date DATE NOT NULL,
    amount DECIMAL(8,2) NOT NULL, -- Reduced precision for space efficiency
    recipient TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'Manual',
    email_id TEXT UNIQUE, -- For duplicate prevention from email parsing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance (within free tier limits)
CREATE INDEX idx_transactions_date ON transactions(date);
CREATE INDEX idx_transactions_email_id ON transactions(email_id);
CREATE INDEX idx_transactions_created_at ON transactions(created_at);

-- Enable Row Level Security (RLS) for security
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;

-- Policy for single user (can be expanded later for multi-user support)
CREATE POLICY "Users can manage their own transactions" ON transactions
    FOR ALL USING (true); -- For now, allow all (single user setup)

-- User settings table (for future expansion)
CREATE TABLE user_settings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    telegram_user_id BIGINT UNIQUE NOT NULL,
    email_user TEXT,
    email_password TEXT, -- Will be encrypted
    gx_bank_sender TEXT DEFAULT 'alerts@gxbank.my',
    timezone TEXT DEFAULT 'Asia/Kuala_Lumpur',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for user settings
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;

-- Policy for user settings
CREATE POLICY "Users can manage their own settings" ON user_settings
    FOR ALL USING (true); -- For now, allow all (single user setup)

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
CREATE TRIGGER update_user_settings_updated_at 
    BEFORE UPDATE ON user_settings 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default user settings (you'll need to update this with your actual telegram_user_id)
-- INSERT INTO user_settings (telegram_user_id) VALUES (YOUR_TELEGRAM_USER_ID_HERE);
