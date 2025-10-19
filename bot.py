import logging
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta

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

from config import config

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
        self.application = Application.builder().token(config.BOT_TOKEN).build()
        self.user_warnings: Dict[int, List[datetime]] = {}  # user_id: list of warning timestamps
        self.setup_handlers()
        
    def setup_handlers(self):
        """Setup all command and message handlers"""
        
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
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message when command /start is issued."""
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

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send help message with available commands."""
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

    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin management panel."""
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

    async def promote_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Promote a user to admin."""
        if not await self.is_user_admin(update, context):
            await update.message.reply_text("❌ You need to be an admin to use this command.")
            return

        target_user = await self.get_user_from_message(update, context)
        if not target_user:
            await update.message.reply_text("❌ Please specify a user to promote. Usage: /promote @username")
            return

        try:
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
        except Exception as e:
            logger.error(f"Error promoting user: {e}")
            await update.message.reply_text("❌ Failed to promote user. Make sure I have admin rights.")

    async def demote_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Demote an admin to regular user."""
        if not await self.is_user_admin(update, context):
            await update.message.reply_text("❌ You need to be an admin to use this command.")
            return

        target_user = await self.get_user_from_message(update, context)
        if not target_user:
            await update.message.reply_text("❌ Please specify a user to demote. Usage: /demote @username")
            return

        try:
            chat_id = update.effective_chat.id
            await context.bot.promote_chat_member(
                chat_id=chat_id,
                user_id=target_user.id,
                can_change_info=False,
                can_delete_messages=False,
                can_invite_users=False,
                can_restrict_members=False,
                can_pin_messages=False,
                can_promote_members=False,
                can_manage_video_chats=False,
                can_manage_chat=False
            )
            await update.message.reply_text(f"✅ Successfully demoted {target_user.first_name}!")
        except Exception as e:
            logger.error(f"Error demoting user: {e}")
            await update.message.reply_text("❌ Failed to demote user.")

    async def ban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ban a user from the group."""
        if not await self.is_user_admin(update, context):
            await update.message.reply_text("❌ You need to be an admin to use this command.")
            return

        target_user = await self.get_user_from_message(update, context)
        if not target_user:
            await update.message.reply_text("❌ Please reply to a message or specify a user. Usage: /ban @username")
            return

        try:
            chat_id = update.effective_chat.id
            await context.bot.ban_chat_member(
                chat_id=chat_id, 
                user_id=target_user.id,
                until_date=datetime.now() + timedelta(seconds=config.BAN_DURATION)
            )
            await update.message.reply_text(f"✅ Successfully banned {target_user.first_name}!")
        except Exception as e:
            logger.error(f"Error banning user: {e}")
            await update.message.reply_text("❌ Failed to ban user. Make sure I have admin rights.")

    async def mute_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mute a user in the group."""
        if not await self.is_user_admin(update, context):
            await update.message.reply_text("❌ You need to be an admin to use this command.")
            return

        target_user = await self.get_user_from_message(update, context)
        if not target_user:
            await update.message.reply_text("❌ Please reply to a message or specify a user. Usage: /mute @username")
            return

        try:
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
        except Exception as e:
            logger.error(f"Error muting user: {e}")
            await update.message.reply_text("❌ Failed to mute user. Make sure I have admin rights.")

    async def warn_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Warn a user."""
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

    async def warnings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check user warnings."""
        target_user = await self.get_user_from_message(update, context)
        if not target_user:
            await update.message.reply_text("❌ Please specify a user. Usage: /warnings @username")
            return

        user_id = target_user.id
        warning_count = len(self.user_warnings.get(user_id, []))
        
        warnings_text = f"""
⚠️ **Warnings for {target_user.first_name}**

Total Warnings: {warning_count}/{config.MAX_WARNINGS}
        """
        
        await update.message.reply_text(warnings_text, parse_mode='Markdown')

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show group statistics."""
        if not await self.is_user_admin(update, context):
            await update.message.reply_text("❌ You need to be an admin to use this command.")
            return

        chat = update.effective_chat
        try:
            # Get chat member count (approximate)
            chat_member_count = await context.bot.get_chat_member_count(chat.id)
            
            stats_text = f"""
📊 **Group Statistics**

🏷 Name: {chat.title}
👥 Members: {chat_member_count}
🆔 Chat ID: `{chat.id}`
📝 Type: {chat.type}
            """
            
            await update.message.reply_text(stats_text, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            await update.message.reply_text("❌ Failed to get group statistics.")

    async def broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Broadcast message to all groups (admin only)."""
        user = update.effective_user
        
        if user.id not in config.ADMIN_IDS:
            await update.message.reply_text("❌ This command is for bot admins only.")
            return

        if not context.args:
            await update.message.reply_text("❌ Please provide a message to broadcast. Usage: /broadcast Your message")
            return

        broadcast_message = " ".join(context.args)
        
        # Note: In a real implementation, you'd need to track which chats the bot is in
        await update.message.reply_text("📢 Broadcast feature would send to all groups here.")

    async def new_member_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle new member joins."""
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

    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all messages for auto-moderation."""
        if not config.AUTO_MODERATION_ENABLED:
            return

        message = update.message
        user = message.from_user
        text = message.text or message.caption or ""

        # Link filtering
        if config.FILTER_LINKS and await self.contains_links(text):
            if not await self.is_user_admin(update, context):
                await message.delete()
                warning_msg = await message.reply_text(
                    f"❌ {user.mention_markdown()}, links are not allowed in this group!",
                    parse_mode='Markdown'
                )
                # Delete warning after 5 seconds
                await context.job_queue.run_once(
                    self.delete_message, 
                    5, 
                    data=warning_msg.chat_id, 
                    name=str(warning_msg.message_id)
                )
                return

        # Bad word filtering
        if config.FILTER_BAD_WORDS and await self.contains_bad_words(text):
            if not await self.is_user_admin(update, context):
                await message.delete()
                warning_msg = await message.reply_text(
                    f"❌ {user.mention_markdown()}, inappropriate language is not allowed!",
                    parse_mode='Markdown'
                )
                await context.job_queue.run_once(
                    self.delete_message, 
                    5, 
                    data=warning_msg.chat_id, 
                    name=str(warning_msg.message_id)
                )
                return

    async def file_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle files and media."""
        if config.FILTER_FILES and not await self.is_user_admin(update, context):
            await update.message.delete()
            warning_msg = await update.message.reply_text(
                f"❌ {update.message.from_user.mention_markdown()}, file sharing is not allowed!",
                parse_mode='Markdown'
            )
            await context.job_queue.run_once(
                self.delete_message, 
                5, 
                data=warning_msg.chat_id, 
                name=str(warning_msg.message_id)
            )

    async def contains_links(self, text: str) -> bool:
        """Check if text contains links."""
        import re
        link_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        return bool(re.search(link_pattern, text))

    async def contains_bad_words(self, text: str) -> bool:
        """Check if text contains bad words."""
        text_lower = text.lower()
        return any(bad_word in text_lower for bad_word in config.BAD_WORDS)

    async def delete_message(self, context: ContextTypes.DEFAULT_TYPE):
        """Delete a message."""
        job = context.job
        try:
            await context.bot.delete_message(chat_id=job.data, message_id=int(job.name))
        except Exception as e:
            logger.error(f"Error deleting message: {e}")

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button presses."""
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

    async def is_user_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if user is admin in the chat."""
        user = update.effective_user
        chat = update.effective_chat
        
        if chat.type == Chat.PRIVATE:
            return user.id in config.ADMIN_IDS
        
        try:
            member = await chat.get_member(user.id)
            return member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
        except Exception as e:
            logger.error(f"Error checking admin status: {e}")
            return False

    async def get_user_from_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[User]:
        """Extract user from command arguments or replied message."""
        if update.message.reply_to_message:
            return update.message.reply_to_message.from_user
        
        if context.args:
            username = context.args[0].lstrip('@')
            try:
                # Search in chat members
                chat_members = await update.effective_chat.get_members()
                for member in chat_members:
                    if member.user.username and member.user.username.lower() == username.lower():
                        return member.user
                    if member.user.first_name and member.user.first_name.lower() == username.lower():
                        return member.user
            except Exception as e:
                logger.error(f"Error finding user: {e}")
        
        return None

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors in the telegram bot."""
        logger.error(f"Exception while handling an update: {context.error}")

    def run(self):
        """Start the bot."""
        logger.info("🤖 Telegram Management Bot is starting...")
        print(f"Bot is running in {config.__class__.__name__} mode")
        print(f"Log level: {config.LOG_LEVEL}")
        self.application.run_polling()

def main():
    """Main function to start the bot."""
    if not config.BOT_TOKEN or config.BOT_TOKEN == 'your_bot_token_here':
        print("❌ Error: Please set BOT_TOKEN in environment variables or config.py")
        return
    
    bot = TelegramManagerBot()
    bot.run()

if __name__ == '__main__':
    main()
