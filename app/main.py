import os
import logging
import asyncio
from aiohttp import web
from dotenv import load_dotenv

from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update

from .email_fetcher import fetch_and_save_emails
from .telegram_bot import start, add, summary, help_command, send_daily_summary, search_transactions, delete_transaction, confirm_delete

load_dotenv()

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
AUTHORIZED_USER_ID = int(os.environ.get("TELEGRAM_CHAT_ID"))
WEBHOOK_PORT = int(os.environ.get("PORT", 8000))

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global application instance
app = None

async def webhook_handler(request):
    """Handle incoming webhook requests from Telegram"""
    try:
        data = await request.json()
        update = Update.de_json(data, app.bot)
        
        if update:
            await app.process_update(update)
            logger.info(f"Processed update: {update.update_id}")
        
        return web.Response(text="OK")
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return web.Response(text="Error", status=500)

async def health_check(request):
    """Health check endpoint for Render"""
    return web.Response(text="Bot is running", status=200)

async def manual_email_fetch(request):
    """Manual endpoint to trigger email fetching (for testing)"""
    try:
        await fetch_and_save_emails()
        return web.Response(text="Email fetch completed", status=200)
    except Exception as e:
        logger.error(f"Error in manual email fetch: {e}")
        return web.Response(text="Error", status=500)

async def manual_summary(request):
    """Manual endpoint to trigger daily summary (for testing)"""
    try:
        success = await send_daily_summary()
        if success:
            return web.Response(text="Daily summary sent", status=200)
        else:
            return web.Response(text="Failed to send summary", status=500)
    except Exception as e:
        logger.error(f"Error in manual summary: {e}")
        return web.Response(text="Error", status=500)

async def init_app():
    """Initialize the Telegram bot application"""
    global app
    
    logger.info("Initializing Telegram bot application...")
    
    # Create the Application
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("search", search_transactions))
    app.add_handler(CommandHandler("delete", delete_transaction))
    
    # Add message handler for delete confirmation
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_delete))

    # Initialize the application
    await app.initialize()
    
    logger.info("Telegram bot application initialized successfully")
    return app

async def create_web_app():
    """Create the web application with routes"""
    # Initialize Telegram bot
    await init_app()
    
    # Create web application
    web_app = web.Application()
    
    # Add routes
    web_app.router.add_post('/webhook', webhook_handler)
    web_app.router.add_get('/health', health_check)
    web_app.router.add_post('/fetch-emails', manual_email_fetch)
    web_app.router.add_post('/send-summary', manual_summary)
    
    logger.info(f"Web application created with webhook endpoint at /webhook")
    return web_app

async def main():
    """Main function to start the webhook server"""
    logger.info("Starting webhook server...")
    
    # Create web application
    web_app = await create_web_app()
    
    # Start the web server
    runner = web.AppRunner(web_app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', WEBHOOK_PORT)
    await site.start()
    
    logger.info(f"Webhook server started on port {WEBHOOK_PORT}")
    logger.info("Bot is ready to receive webhook requests")
    
    # Keep the server running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down webhook server...")
        await runner.cleanup()
        if app:
            await app.shutdown()
        logger.info("Webhook server shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Application shutdown successfully.")