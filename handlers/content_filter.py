import re
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from database import db
from models import Group, BlockedWord, MediaSetting
from config import Config

class ContentFilterHandler:
    def __init__(self):
        self.user_message_count = {}
        self.last_reset_time = datetime.now()

    async def check_flood(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check for message flooding"""
        if not update.message or not update.effective_user:
            return
        
        current_time = datetime.now()
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Reset counts if window has passed
        if (current_time - self.last_reset_time).seconds > Config.FLOOD_WINDOW:
            self.user_message_count = {}
            self.last_reset_time = current_time
        
        # Initialize user count
        if user_id not in self.user_message_count:
            self.user_message_count[user_id] = {'count': 0, 'first_message_time': current_time}
        
        self.user_message_count[user_id]['count'] += 1
        
        session = db.get_session()
        try:
            group = session.query(Group).filter_by(chat_id=str(chat_id)).first()
            if group and group.anti_flood_enabled:
                user_data = self.user_message_count[user_id]
                time_diff = (current_time - user_data['first_message_time']).seconds
                
                if user_data['count'] >= Config.FLOOD_LIMIT and time_diff <= Config.FLOOD_WINDOW:
                    # User is flooding, mute them
                    mute_time = timedelta(minutes=30)
                    try:
                        await context.bot.restrict_chat_member(
                            chat_id=chat_id,
                            user_id=user_id,
                            permissions=ChatPermissions(
                                can_send_messages=False,
                                can_send_media_messages=False,
                                can_send_other_messages=False,
                                can_add_web_page_previews=False
                            ),
                            until_date=current_time + mute_time
                        )
                        await update.message.reply_text(
                            f"🚫 {update.effective_user.mention_markdown_v2()} has been muted for 30 minutes due to flooding\."
                        )
                        # Reset count after mute
                        self.user_message_count[user_id] = {'count': 0, 'first_message_time': current_time}
                    except Exception as e:
                        print(f"Error muting user: {e}")
                        
        except Exception as e:
            print(f"Error in check_flood: {e}")
        finally:
            session.close()

    async def filter_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Filter blocked words and content"""
        if not update.message or not update.message.text:
            return
        
        session = db.get_session()
        try:
            group = session.query(Group).filter_by(chat_id=str(update.effective_chat.id)).first()
            if not group:
                return
            
            # Check blocked words
            blocked_words = session.query(BlockedWord).filter_by(group_id=group.id).all()
            message_text = update.message.text.lower()
            
            for blocked_word in blocked_words:
                if blocked_word.is_regex:
                    if re.search(blocked_word.word, message_text, re.IGNORECASE):
                        await update.message.delete()
                        await update.message.reply_text(
                            f"🚫 {update.effective_user.mention_markdown_v2()}, your message contained blocked content\."
                        )
                        return
                else:
                    if blocked_word.word.lower() in message_text:
                        await update.message.delete()
                        await update.message.reply_text(
                            f"🚫 {update.effective_user.mention_markdown_v2()}, your message contained blocked content\."
                        )
                        return
            
            # Check links
            if any(link in message_text for link in Config.BANNED_LINKS):
                await update.message.delete()
                await update.message.reply_text(
                    f"🚫 {update.effective_user.mention_markdown_v2()}, banned links are not allowed\."
                )
                return
                
        except Exception as e:
            print(f"Error in filter_content: {e}")
        finally:
            session.close()

    async def filter_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Filter media based on group settings"""
        if not update.message:
            return
        
        session = db.get_session()
        try:
            group = session.query(Group).filter_by(chat_id=str(update.effective_chat.id)).first()
            if not group:
                return
            
            # Check if user is admin
            is_admin = update.effective_user.id in [admin.user.id for admin in await update.effective_chat.get_administrators()]
            
            media_type = None
            if update.message.photo:
                media_type = 'photo'
            elif update.message.video:
                media_type = 'video'
            elif update.message.document:
                media_type = 'document'
            elif update.message.audio:
                media_type = 'audio'
            elif update.message.voice:
                media_type = 'voice'
            elif update.message.sticker:
                media_type = 'sticker'
            elif update.message.animation:
                media_type = 'gif'
            
            if media_type:
                media_setting = session.query(MediaSetting).filter_by(group_id=group.id, media_type=media_type).first()
                if media_setting:
                    if not media_setting.allowed or (media_setting.admin_only and not is_admin):
                        await update.message.delete()
                        await update.message.reply_text(
                            f"🚫 {update.effective_user.mention_markdown_v2()}, this type of media is not allowed\."
                        )
                        return
                        
        except Exception as e:
            print(f"Error in filter_media: {e}")
        finally:
            session.close()

    async def add_blocked_word(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add a word to blocklist"""
        if not update.effective_user.id in [admin.user.id for admin in await update.effective_chat.get_administrators()]:
            await update.message.reply_text("❌ Only admins can use this command.")
            return

        if not context.args:
            await update.message.reply_text("❌ Usage: /block <word> [--regex]")
            return
        
        session = db.get_session()
        try:
            group = session.query(Group).filter_by(chat_id=str(update.effective_chat.id)).first()
            if not group:
                group = Group(chat_id=str(update.effective_chat.id), title=update.effective_chat.title)
                session.add(group)
                session.commit()
            
            word = ' '.join(context.args)
            is_regex = False
            
            if '--regex' in context.args:
                word = ' '.join([arg for arg in context.args if arg != '--regex'])
                is_regex = True
                # Validate regex
                try:
                    re.compile(word)
                except re.error:
                    await update.message.reply_text("❌ Invalid regex pattern.")
                    return
            
            # Check if word already exists
            existing = session.query(BlockedWord).filter_by(group_id=group.id, word=word).first()
            if existing:
                await update.message.reply_text("❌ This word is already blocked.")
                return
            
            blocked_word = BlockedWord(group_id=group.id, word=word, is_regex=is_regex)
            session.add(blocked_word)
            session.commit()
            
            await update.message.reply_text(f"✅ Word '{word}' added to blocklist.")
            
        except Exception as e:
            print(f"Error in add_blocked_word: {e}")
            await update.message.reply_text("❌ Error adding word to blocklist.")
        finally:
            session.close()
