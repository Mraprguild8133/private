import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from dotenv import load_dotenv

from database import db
from config import Config
from handlers.user_management import UserManagementHandler
from handlers.content_filter import ContentFilterHandler
from handlers.utilities import UtilitiesHandler

# Load environment variables
load_dotenv()

class TelegramBot:
    def __init__(self):
        self.application = Application.builder().token(Config.BOT_TOKEN).build()
        self.content_filter = ContentFilterHandler()
        self.setup_handlers()
    
    def setup_handlers(self):
        # User Management
        self.application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, UserManagementHandler.welcome_user))
        self.application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, UserManagementHandler.goodbye_user))
        self.application.add_handler(CallbackQueryHandler(UserManagementHandler.handle_captcha, pattern="^captcha_"))
        self.application.add_handler(CommandHandler("warn", UserManagementHandler.warn_user))
        self.application.add_handler(CommandHandler("info", UserManagementHandler.user_info))
        
        # Content Filtering
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.content_filter.filter_content))
        self.application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, self.content_filter.filter_media))
        self.application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, self.content_filter.check_flood))
        self.application.add_handler(CommandHandler("block", ContentFilterHandler.add_blocked_word))
        
        # Utilities
        self.application.add_handler(CommandHandler("tagall", UtilitiesHandler.tag_all))
        self.application.add_handler(CommandHandler("close", UtilitiesHandler.close_group))
        self.application.add_handler(CommandHandler("open", UtilitiesHandler.open_group))
        self.application.add_handler(CommandHandler("lang", UtilitiesHandler.set_language))
        
        # Help command
        self.application.add_handler(CommandHandler("help", self.help_command))
    
    async def help_command(self, update, context):
        """Send help message"""
        help_text = """
🤖 **Group Management Bot Commands:**

**User Management:**
/warn [reply to user] [reason] - Warn a user
/info [reply to user] - Get user information

**Content Filtering:**
/block <word> [--regex] - Add word to blocklist

**Group Utilities:**
/tagall [message] - Mention all members
/close - Close group (admins only)
/open - Open group (admins only)
/lang <code> - Set bot language

**Admin Only:** warn, block, tagall, close, open, lang
        """
        await update.message.reply_text(help_text)
    
    def run(self):
        """Start the bot"""
        print("Starting bot...")
        db.create_tables()
        self.application.run_polling()

if __name__ == "__main__":
    bot = TelegramBot()
    bot.run()
