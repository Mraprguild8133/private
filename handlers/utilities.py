from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
from database import db
from models import Group
from config import Config

class UtilitiesHandler:
    @staticmethod
    async def tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Tag all group members"""
        if not update.effective_user.id in [admin.user.id for admin in await update.effective_chat.get_administrators()]:
            await update.message.reply_text("❌ Only admins can use this command.")
            return

        try:
            members_count = await update.effective_chat.get_member_count()
            message = "📢 Announcement from admin:\n\n"
            
            if context.args:
                message += ' '.join(context.args) + "\n\n"
            
            message += "Tagging all members..."
            await update.message.reply_text(message)
            
        except Exception as e:
            print(f"Error in tag_all: {e}")
            await update.message.reply_text("❌ Error tagging members.")

    @staticmethod
    async def close_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Close group (mute all non-admins)"""
        if not update.effective_user.id in [admin.user.id for admin in await update.effective_chat.get_administrators()]:
            await update.message.reply_text("❌ Only admins can use this command.")
            return

        try:
            # Restrict all permissions for non-admins
            permissions = ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False
            )
            
            await context.bot.set_chat_permissions(update.effective_chat.id, permissions)
            await update.message.reply_text("🔒 Group has been closed. Only admins can send messages.")
            
        except Exception as e:
            print(f"Error in close_group: {e}")
            await update.message.reply_text("❌ Error closing group.")

    @staticmethod
    async def open_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Open group (restore permissions)"""
        if not update.effective_user.id in [admin.user.id for admin in await update.effective_chat.get_administrators()]:
            await update.message.reply_text("❌ Only admins can use this command.")
            return

        try:
            # Restore default permissions
            permissions = ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False
            )
            
            await context.bot.set_chat_permissions(update.effective_chat.id, permissions)
            await update.message.reply_text("🔓 Group has been opened. Everyone can send messages now.")
            
        except Exception as e:
            print(f"Error in open_group: {e}")
            await update.message.reply_text("❌ Error opening group.")

    @staticmethod
    async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set bot language for the group"""
        if not update.effective_user.id in [admin.user.id for admin in await update.effective_chat.get_administrators()]:
            await update.message.reply_text("❌ Only admins can use this command.")
            return

        if not context.args or context.args[0] not in Config.LANGUAGES:
            languages = ", ".join([f"{code} ({name})" for code, name in Config.LANGUAGES.items()])
            await update.message.reply_text(f"❌ Available languages: {languages}")
            return
        
        session = db.get_session()
        try:
            language = context.args[0]
            group = session.query(Group).filter_by(chat_id=str(update.effective_chat.id)).first()
            
            if not group:
                group = Group(chat_id=str(update.effective_chat.id), title=update.effective_chat.title)
                session.add(group)
            
            group.language = language
            session.commit()
            
            await update.message.reply_text(f"✅ Language set to {Config.LANGUAGES[language]}")
            
        except Exception as e:
            print(f"Error in set_language: {e}")
            await update.message.reply_text("❌ Error setting language.")
        finally:
            session.close()
