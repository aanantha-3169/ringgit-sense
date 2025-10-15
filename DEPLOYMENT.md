# Finance Tracker Cloud Deployment Guide

This guide will help you deploy your finance tracker to the cloud using Supabase for data storage and Render for hosting the Telegram bot.

## Prerequisites

1. **Supabase Account**: Sign up at [supabase.com](https://supabase.com)
2. **Render Account**: Sign up at [render.com](https://render.com)
3. **GitHub Account**: For GitHub Actions (free tier)
4. **Telegram Bot Token**: From [@BotFather](https://t.me/botfather)

## Step 1: Supabase Setup

### 1.1 Create Supabase Project
1. Go to [supabase.com](https://supabase.com) and create a new project
2. Choose a project name (e.g., "finance-tracker")
3. Set a database password (save this securely)
4. Choose a region close to you

### 1.2 Set Up Database Schema
1. Go to the SQL Editor in your Supabase dashboard
2. Copy and paste the contents of `supabase/schema.sql`
3. Click "Run" to execute the SQL

### 1.3 Get API Keys
1. Go to Settings → API
2. Copy the following values:
   - **Project URL** (SUPABASE_URL)
   - **anon public** key (SUPABASE_KEY)

## Step 2: Render Deployment

### 2.1 Connect GitHub Repository
1. Go to [render.com](https://render.com) and sign in
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Select the `ringgit-sense` repository

### 2.2 Configure Service
- **Name**: `finance-tracker-bot`
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python -m app.main`
- **Plan**: Free

### 2.3 Set Environment Variables
In the Render dashboard, add these environment variables:

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_app_password_here
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_key_here
PORT=8000
```

### 2.4 Deploy
1. Click "Create Web Service"
2. Wait for deployment to complete
3. Note your service URL (e.g., `https://finance-tracker-bot.onrender.com`)

## Step 3: Set Up Telegram Webhook

### 3.1 Set Webhook URL
Replace `YOUR_BOT_TOKEN` and `YOUR_SERVICE_URL` with your actual values:

```bash
curl -X POST "https://api.telegram.org/botYOUR_BOT_TOKEN/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "YOUR_SERVICE_URL/webhook"}'
```

Example:
```bash
curl -X POST "https://api.telegram.org/bot1234567890:ABCdefGHIjklMNOpqrsTUVwxyz/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://finance-tracker-bot.onrender.com/webhook"}'
```

### 3.2 Test Webhook
Send a message to your bot to test if it's working.

## Step 4: GitHub Actions Setup

### 4.1 Add Repository Secrets
In your GitHub repository, go to Settings → Secrets and variables → Actions, and add:

- `EMAIL_USER`: Your Gmail address
- `EMAIL_PASS`: Your Gmail app password
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anon key
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `TELEGRAM_CHAT_ID`: Your Telegram chat ID

### 4.2 Test GitHub Actions
1. Go to Actions tab in your GitHub repository
2. Find "Daily Finance Tasks" workflow
3. Click "Run workflow" to test manually

## Step 5: Testing

### 5.1 Test Bot Commands
Send these commands to your bot:
- `/start` - Should show welcome message
- `/add 10.50 Coffee` - Should add a transaction
- `/summary` - Should show today's summary

### 5.2 Test Manual Endpoints
Visit these URLs (replace with your service URL):
- `https://your-service.onrender.com/health` - Should return "Bot is running"
- `https://your-service.onrender.com/fetch-emails` - Should fetch emails (POST request)

### 5.3 Test Scheduled Tasks
1. Wait for the scheduled time (8 PM Malaysia time)
2. Or manually trigger the GitHub Actions workflow
3. Check if you receive the daily summary

## Troubleshooting

### Common Issues

1. **Bot not responding**
   - Check if webhook is set correctly
   - Verify environment variables in Render
   - Check Render logs for errors

2. **Database connection errors**
   - Verify Supabase URL and key
   - Check if database schema is created
   - Ensure RLS policies are set correctly

3. **Email fetching not working**
   - Verify Gmail app password (not regular password)
   - Check if 2FA is enabled on Gmail
   - Ensure IMAP is enabled

4. **GitHub Actions failing**
   - Check repository secrets are set correctly
   - Verify the workflow file is in `.github/workflows/`
   - Check Actions logs for specific errors

### Logs and Monitoring

- **Render Logs**: Available in the Render dashboard
- **GitHub Actions Logs**: Available in the Actions tab
- **Supabase Logs**: Available in the Supabase dashboard

## Cost Breakdown (Free Tier)

- **Render**: $0/month (webhook only, sleeps after 15 min inactivity)
- **Supabase**: $0/month (500MB database, 2GB bandwidth)
- **GitHub Actions**: $0/month (2000 minutes/month)
- **Total**: **$0/month** 🎉

## Next Steps

1. **Monitor Performance**: Check logs regularly
2. **Backup Data**: Supabase provides automatic backups
3. **Scale Up**: Upgrade to paid tiers if needed
4. **Add Features**: Extend functionality as needed

## Support

If you encounter issues:
1. Check the logs first
2. Verify all environment variables
3. Test each component individually
4. Check the troubleshooting section above

Happy tracking! 📊💰
