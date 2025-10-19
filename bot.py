#!/usr/bin/env python3
import logging
import os
import re
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

try:
    from telegram import (
        Update, 
        Chat, 
        ChatMember, 
        ChatPermissions,
        User,
        InlineKeyboardButton,
        InlineKeyboardMarkup
    )
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        CallbackQueryHandler,
        ContextTypes,
        filters
    )
    from telegram.error import TelegramError
    
    # Import config
    try:
        from config import config
    except ImportError as e:
        logging.error(f"Failed to import config: {e}")
        raise
    except ValueError as e:
        logging.error(f"Configuration error: {e}")
        raise

except ImportError as e:
    logging.error(f"Failed to import required packages: {e}")
    raise

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, config.LOG_LEVEL),
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TelegramManagerBot:
    def __init__(self):
        self.application = None
        self.user_warnings: Dict[int, List[datetime]] = {}
        self.setup_bot()
        
    def setup_bot(self):
        """Initialize the bot application."""
        try:
            if not config.BOT_TOKEN:
                raise ValueError("BOT_TOKEN is not set in configuration")
                
            self.application = Application.builder().token(config.BOT_TOKEN).build()
            self.setup_handlers()
            logger.info("Bot application initialized successfully")
        except Exception as e:
            logger.error(f"Failed to setup bot: {e}")
            raise
        
    def setup_handlers(self):
        """Setup all command and message handlers"""
        if not self.application:
            raise RuntimeError("Application not initialized")
            
        try:
            # Command handlers
            command_handlers = [
                CommandHandler("start", self.start_command),
                CommandHandler("help", self.help_command),
                CommandHandler("admin", self.admin_command),
                CommandHandler("promote", self.promote_command),
                CommandHandler("demote", self.demote_command),
                CommandHandler("ban", self.ban_command),
                CommandHandler("unban", self.unban_command),
                CommandHandler("mute", self.mute_command),
                CommandHandler("unmute", self.unmute_command),
                CommandHandler("warn", self.warn_command),
                CommandHandler("warnings", self.warnings_command),
                CommandHandler("pin", self.pin_message),
                CommandHandler("unpin", self.unpin_message),
                CommandHandler("settings", self.settings_command),
                CommandHandler("stats", self.stats_command),
                CommandHandler("broadcast", self.broadcast_command),
            ]
            
            for handler in command_handlers:
                self.application.add_handler(handler)
            
            # Callback query handlers for buttons
            self.application.add_handler(CallbackQueryHandler(self.button_handler))
            
            # Message handlers
            message_handlers = [
                MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.new_member_handler),
                MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, self.left_member_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler),
                MessageHandler(filters.ALL & ~filters.COMMAND, self.file_handler),
            ]
            
            for handler in message_handlers:
                self.application.add_handler(handler)
            
            # Error handler
            self.application.add_error_handler(self.error_handler)
            logger.info("All handlers setup successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup handlers: {e}")
            raise

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message when command /start is issued."""
        try:
            user = update.effective_user
            chat = update.effective_chat
            
            if chat.type == Chat.PRIVATE:
                welcome_text = f"""
🤖 **Welcome {user.first_name}!**

I'm a powerful Telegram management bot with the following features:

🔧 **Group Management:**
• Add/Remove admins
• Ban/Unban users
• Mute/Unmute users
• Warn system
• Auto moderation

📢 **Channel Management:**
• Post management
• User management
• Content moderation

⚙️ **Admin Commands:**
`/admin` - Manage admins
`/promote` - Promote user to admin
`/ban` - Ban a user
`/mute` - Mute a user
`/warn` - Warn a user
`/settings` - Bot settings

Add me to your group/channel and make me admin to get started!
                """
                await update.message.reply_text(welcome_text, parse_mode='Markdown')
            else:
                await update.message.reply_text("Bot is active! Use /help for commands list.")
                
        except Exception as e:
            logger.error(f"Error in start_command: {e}")
            await self.send_error_message(update, "Failed to process start command")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send help message with available commands."""
        try:
            help_text = """
🛠 **Available Commands:**

**Admin Commands:**
`/admin` - Show admin panel
`/promote @username` - Promote user to admin
`/demote @username` - Remove admin rights
`/ban @username` - Ban a user
`/unban @username` - Unban a user
`/mute @username` - Mute a user
`/unmute @username` - Unmute a user
`/warn @username` - Warn a user
`/warnings @username` - Check user warnings
`/pin` - Pin replied message
`/unpin` - Unpin current message
`/settings` - Bot settings
`/stats` - Group statistics
`/broadcast` - Broadcast message to all groups

**User Commands:**
`/start` - Start the bot
`/help` - Show this help message

**Note:** Most commands require admin privileges.
            """
            await update.message.reply_text(help_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in help_command: {e}")
            await self.send_error_message(update, "Failed to process help command")

    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin management panel."""
        try:
            if not await self.is_user_admin(update, context):
                await update.message.reply_text("❌ You need to be an admin to use this command.")
                return

            keyboard = [
                [
                    InlineKeyboardButton("👥 Manage Admins", callback_data="manage_admins"),
                    InlineKeyboardButton("🚫 Ban User", callback_data="ban_user")
                ],
                [
                    InlineKeyboardButton("🔇 Mute User", callback_data="mute_user"),
                    InlineKeyboardButton("⚠️ Warn User", callback_data="warn_user")
                ],
                [
                    InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
                    InlineKeyboardButton("📊 Stats", callback_data="group_stats")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🛠 **Admin Control Panel**\n\nSelect an option to manage your group:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in admin_command: {e}")
            await self.send_error_message(update, "Failed to show admin panel")

    async def promote_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Promote a user to admin."""
        try:
            if not await self.is_user_admin(update, context):
                await update.message.reply_text("❌ You need to be an admin to use this command.")
                return

            target_user = await self.get_user_from_message(update, context)
            if not target_user:
                await update.message.reply_text("❌ Please specify a user to promote. Usage: /promote @username")
                return

            chat_id = update.effective_chat.id
            await context.bot.promote_chat_member(
                chat_id=chat_id,
                user_id=target_user.id,
                can_change_info=True,
                can_delete_messages=True,
                can_invite_users=True,
                can_restrict_members=True,
                can_pin_messages=True,
                can_promote_members=False,
                can_manage_video_chats=True,
                can_manage_chat=True
            )
            await update.message.reply_text(f"✅ Successfully promoted {target_user.first_name} to admin!")
            
        except TelegramError as e:
            logger.error(f"Telegram error in promote_command: {e}")
            await update.message.reply_text("❌ Failed to promote user. Make sure I have admin rights.")
        except Exception as e:
            logger.error(f"Error in promote_command: {e}")
            await self.send_error_message(update, "Failed to promote user")

    async def ban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ban a user from the group."""
        try:
            if not await self.is_user_admin(update, context):
                await update.message.reply_text("❌ You need to be an admin to use this command.")
                return

            target_user = await self.get_user_from_message(update, context)
            if not target_user:
                await update.message.reply_text("❌ Please reply to a message or specify a user. Usage: /ban @username")
                return

            chat_id = update.effective_chat.id
            await context.bot.ban_chat_member(
                chat_id=chat_id, 
                user_id=target_user.id,
                until_date=datetime.now() + timedelta(seconds=config.BAN_DURATION)
            )
            await update.message.reply_text(f"✅ Successfully banned {target_user.first_name}!")
            
        except TelegramError as e:
            logger.error(f"Telegram error in ban_command: {e}")
            await update.message.reply_text("❌ Failed to ban user. Make sure I have admin rights.")
        except Exception as e:
            logger.error(f"Error in ban_command: {e}")
            await self.send_error_message(update, "Failed to ban user")

    async def mute_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mute a user in the group."""
        try:
            if not await self.is_user_admin(update, context):
                await update.message.reply_text("❌ You need to be an admin to use this command.")
                return

            target_user = await self.get_user_from_message(update, context)
            if not target_user:
                await update.message.reply_text("❌ Please reply to a message or specify a user. Usage: /mute @username")
                return

            chat_id = update.effective_chat.id
            permissions = ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_polls=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False
            )
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=target_user.id,
                permissions=permissions,
                until_date=datetime.now() + timedelta(seconds=config.MUTE_DURATION)
            )
            await update.message.reply_text(f"✅ Successfully muted {target_user.first_name} for {config.MUTE_DURATION//3600} hours!")
            
        except TelegramError as e:
            logger.error(f"Telegram error in mute_command: {e}")
            await update.message.reply_text("❌ Failed to mute user. Make sure I have admin rights.")
        except Exception as e:
            logger.error(f"Error in mute_command: {e}")
            await self.send_error_message(update, "Failed to mute user")

    # Add other command methods following the same pattern...

    async def warn_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Warn a user."""
        try:
            if not await self.is_user_admin(update, context):
                await update.message.reply_text("❌ You need to be an admin to use this command.")
                return

            target_user = await self.get_user_from_message(update, context)
            if not target_user:
                await update.message.reply_text("❌ Please reply to a message or specify a user. Usage: /warn @username")
                return

            # Store warning
            user_id = target_user.id
            if user_id not in self.user_warnings:
                self.user_warnings[user_id] = []
            
            self.user_warnings[user_id].append(datetime.now())
            
            warning_count = len(self.user_warnings[user_id])
            warning_message = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else "Please follow the group rules."
            
            warn_text = f"""
⚠️ **Warning Issued**

User: {target_user.mention_markdown()}
Warnings: {warning_count}/{config.MAX_WARNINGS}
Reason: {warning_message}

Further violations may result in a mute or ban.
            """
            
            await update.message.reply_text(warn_text, parse_mode='Markdown')
            
            # Check if user reached max warnings
            if warning_count >= config.MAX_WARNINGS:
                try:
                    chat_id = update.effective_chat.id
                    await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
                    await update.message.reply_text(f"🚨 User {target_user.first_name} has been banned for reaching maximum warnings!")
                    # Reset warnings
                    self.user_warnings[user_id] = []
                except Exception as e:
                    logger.error(f"Error auto-banning user: {e}")
                    
        except Exception as e:
            logger.error(f"Error in warn_command: {e}")
            await self.send_error_message(update, "Failed to warn user")

    async def new_member_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle new member joins."""
        try:
            if not config.WELCOME_MESSAGE_ENABLED:
                return

            for new_member in update.message.new_chat_members:
                if new_member.id == context.bot.id:
                    # Bot was added to group
                    welcome_text = """
🤖 Thanks for adding me!

To get started, make sure to:
1. Promote me to admin with all permissions
2. Use /help to see available commands
3. Use /settings to configure the bot

I'm ready to help manage your group!
                    """
                    await update.message.reply_text(welcome_text)
                else:
                    # Regular user joined
                    welcome_msg = f"""
👋 Welcome {new_member.mention_markdown()} to {update.effective_chat.title}!

Please read the group rules and enjoy your stay!
                    """
                    await update.message.reply_text(welcome_msg, parse_mode='Markdown')
                    
        except Exception as e:
            logger.error(f"Error in new_member_handler: {e}")

    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all messages for auto-moderation."""
        try:
            if not config.AUTO_MODERATION_ENABLED:
                return

            message = update.message
            user = message.from_user
            text = message.text or message.caption or ""

            # Skip if user is admin
            if await self.is_user_admin(update, context):
                return

            # Link filtering
            if config.FILTER_LINKS and await self.contains_links(text):
                await message.delete()
                warning_msg = await message.reply_text(
                    f"❌ {user.mention_markdown()}, links are not allowed in this group!",
                    parse_mode='Markdown'
                )
                # Delete warning after 5 seconds
                await asyncio.sleep(5)
                try:
                    await warning_msg.delete()
                except:
                    pass
                return

            # Bad word filtering
            if config.FILTER_BAD_WORDS and await self.contains_bad_words(text):
                await message.delete()
                warning_msg = await message.reply_text(
                    f"❌ {user.mention_markdown()}, inappropriate language is not allowed!",
                    parse_mode='Markdown'
                )
                await asyncio.sleep(5)
                try:
                    await warning_msg.delete()
                except:
                    pass
                return
                    
        except Exception as e:
            logger.error(f"Error in message_handler: {e}")

    async def contains_links(self, text: str) -> bool:
        """Check if text contains links."""
        link_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        return bool(re.search(link_pattern, text))

    async def contains_bad_words(self, text: str) -> bool:
        """Check if text contains bad words."""
        text_lower = text.lower()
        return any(bad_word in text_lower for bad_word in config.BAD_WORDS)

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button presses."""
        try:
            query = update.callback_query
            await query.answer()

            data = query.data
            
            button_handlers = {
                "manage_admins": "👥 **Admin Management**\n\nUse:\n`/promote @username` - Add admin\n`/demote @username` - Remove admin",
                "ban_user": "🚫 **Ban User**\n\nUse `/ban @username` to ban a user from the group.",
                "mute_user": "🔇 **Mute User**\n\nUse `/mute @username` to mute a user in the group.",
                "warn_user": "⚠️ **Warn User**\n\nUse `/warn @username` to warn a user.",
                "admin_settings": "⚙️ **Admin Settings**\n\nUse `/settings` to configure bot settings.",
                "group_stats": "📊 **Group Stats**\n\nUse `/stats` to view group statistics.",
            }
            
            if data in button_handlers:
                await query.edit_message_text(
                    text=button_handlers[data],
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error in button_handler: {e}")

    async def is_user_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if user is admin in the chat."""
        try:
            user = update.effective_user
            chat = update.effective_chat
            
            if chat.type == Chat.PRIVATE:
                return user.id in config.ADMIN_IDS
            
            member = await chat.get_member(user.id)
            return member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
            
        except Exception as e:
            logger.error(f"Error checking admin status: {e}")
            return False

    async def get_user_from_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[User]:
        """Extract user from command arguments or replied message."""
        try:
            if update.message.reply_to_message:
                return update.message.reply_to_message.from_user
            
            if context.args:
                username = context.args[0].lstrip('@')
                # Search in chat members
                chat_members = await update.effective_chat.get_members()
                for member in chat_members:
                    if member.user.username and member.user.username.lower() == username.lower():
                        return member.user
                    if member.user.first_name and member.user.first_name.lower() == username.lower():
                        return member.user
                        
            return None
            
        except Exception as e:
            logger.error(f"Error getting user from message: {e}")
            return None

    async def send_error_message(self, update: Update, message: str):
        """Send error message to user."""
        try:
            await update.message.reply_text(f"❌ {message}")
        except:
            pass  # Ignore errors when sending error messages

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors in the telegram bot."""
        try:
            logger.error(f"Exception while handling an update: {context.error}")
            
            # Notify user about error
            if update and update.effective_message:
                try:
                    await update.effective_message.reply_text(
                        "❌ An error occurred while processing your request. Please try again later."
                    )
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Error in error handler: {e}")

    def run(self):
        """Start the bot."""
        try:
            logger.info("🤖 Telegram Management Bot is starting...")
            print(f"Bot token: {'Set' if config.BOT_TOKEN else 'Not set'}")
            print(f"Admin IDs: {config.ADMIN_IDS}")
            print(f"Log level: {config.LOG_LEVEL}")
            
            if not self.application:
                raise RuntimeError("Bot application not initialized")
                
            self.application.run_polling()
            
        except Exception as e:
            logger.error(f"Failed to run bot: {e}")
            raise

def main():
    """Main function to start the bot."""
    try:
        # Validate essential configuration
        if not config.BOT_TOKEN:
            print("❌ Error: BOT_TOKEN is required. Please set it in environment variables.")
            return
        
        bot = TelegramManagerBot()
        bot.run()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"❌ Failed to start bot: {e}")

if __name__ == '__main__':
    main()
