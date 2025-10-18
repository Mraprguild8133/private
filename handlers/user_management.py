import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from database import db
from models import Group, GroupUser, Warning
from config import Config

class UserManagementHandler:
    @staticmethod
    async def welcome_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Welcome new users with optional captcha"""
        session = db.get_session()
        try:
            for new_member in update.message.new_chat_members:
                # Get group settings
                group = session.query(Group).filter_by(chat_id=str(update.effective_chat.id)).first()
                
                if not group:
                    group = Group(chat_id=str(update.effective_chat.id), title=update.effective_chat.title)
                    session.add(group)
                    session.commit()
                
                # Add user to database
                user = GroupUser(
                    user_id=str(new_member.id),
                    username=new_member.username,
                    first_name=new_member.first_name,
                    last_name=new_member.last_name,
                    group_id=group.id,
                    is_approved=not group.approval_mode
                )
                session.add(user)
                
                # Send welcome message
                if group.welcome_enabled:
                    welcome_text = f"Welcome {new_member.mention_markdown_v2()} to the group\!"
                    
                    if group.captcha_enabled and not group.approval_mode:
                        # Add captcha button
                        keyboard = [[InlineKeyboardButton("I'm human!", callback_data=f"captcha_{new_member.id}")]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await update.message.reply_text(
                            f"{welcome_text}\n\nPlease verify you're human by clicking the button below:",
                            reply_markup=reply_markup
                        )
                    elif group.approval_mode:
                        await update.message.reply_text(
                            f"{welcome_text}\n\nYou're in approval mode\. An admin will need to approve you before you can chat\."
                        )
                    else:
                        await update.message.reply_text(welcome_text)
                
                session.commit()
                
        except Exception as e:
            print(f"Error in welcome_user: {e}")
        finally:
            session.close()

    @staticmethod
    async def goodbye_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Say goodbye to leaving users"""
        session = db.get_session()
        try:
            left_member = update.message.left_chat_member
            group = session.query(Group).filter_by(chat_id=str(update.effective_chat.id)).first()
            
            if group and group.goodbye_enabled:
                goodbye_text = f"Goodbye {left_member.mention_markdown_v2()}\! We'll miss you\!"
                await update.message.reply_text(goodbye_text)
                
        except Exception as e:
            print(f"Error in goodbye_user: {e}")
        finally:
            session.close()

    @staticmethod
    async def handle_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle captcha verification"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.data.split('_')[1]
        session = db.get_session()
        
        try:
            user = session.query(GroupUser).filter_by(user_id=user_id).first()
            if user:
                user.is_approved = True
                session.commit()
                await query.edit_message_text("✅ Verification successful! You can now chat in the group.")
            else:
                await query.edit_message_text("❌ User not found.")
                
        except Exception as e:
            print(f"Error in handle_captcha: {e}")
        finally:
            session.close()

    @staticmethod
    async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Warn a user"""
        if not update.effective_user.id in [admin.user.id for admin in await update.effective_chat.get_administrators()]:
            await update.message.reply_text("❌ Only admins can use this command.")
            return

        session = db.get_session()
        try:
            target_user = update.message.reply_to_message.from_user if update.message.reply_to_message else None
            reason = ' '.join(context.args) if context.args else "No reason provided"
            
            if not target_user:
                await update.message.reply_text("❌ Please reply to the user's message to warn them.")
                return
            
            group = session.query(Group).filter_by(chat_id=str(update.effective_chat.id)).first()
            if not group:
                group = Group(chat_id=str(update.effective_chat.id), title=update.effective_chat.title)
                session.add(group)
                session.commit()
            
            # Add warning
            warning = Warning(
                user_id=str(target_user.id),
                group_id=group.id,
                reason=reason,
                issued_by=str(update.effective_user.id)
            )
            session.add(warning)
            
            # Update user warning count
            user = session.query(GroupUser).filter_by(user_id=str(target_user.id), group_id=group.id).first()
            if user:
                user.warnings_count += 1
                warnings_left = Config.MAX_WARNINGS - user.warnings_count
                
                if user.warnings_count >= Config.MAX_WARNINGS:
                    # Auto-ban user
                    try:
                        await context.bot.ban_chat_member(update.effective_chat.id, target_user.id)
                        await update.message.reply_text(
                            f"🚫 User {target_user.mention_markdown_v2()} has been banned for reaching {Config.MAX_WARNINGS} warnings\."
                        )
                    except Exception as e:
                        print(f"Error banning user: {e}")
                else:
                    await update.message.reply_text(
                        f"⚠️ Warning issued to {target_user.mention_markdown_v2()}\.\n"
                        f"Reason: {reason}\n"
                        f"Warnings: {user.warnings_count}/{Config.MAX_WARNINGS}\n"
                        f"{warnings_left} warnings left before ban\."
                    )
            else:
                await update.message.reply_text("❌ User not found in database.")
            
            session.commit()
            
        except Exception as e:
            print(f"Error in warn_user: {e}")
        finally:
            session.close()

    @staticmethod
    async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get user information"""
        session = db.get_session()
        try:
            target_user = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
            
            group = session.query(Group).filter_by(chat_id=str(update.effective_chat.id)).first()
            if not group:
                await update.message.reply_text("❌ Group not found in database.")
                return
            
            user = session.query(GroupUser).filter_by(user_id=str(target_user.id), group_id=group.id).first()
            
            if user:
                info_text = (
                    f"👤 User Info:\n"
                    f"Name: {target_user.first_name} {target_user.last_name or ''}\n"
                    f"Username: @{target_user.username or 'N/A'}\n"
                    f"User ID: {target_user.id}\n"
                    f"Warnings: {user.warnings_count}/{Config.MAX_WARNINGS}\n"
                    f"Joined: {user.joined_at.strftime('%Y-%m-%d %H:%M')}\n"
                    f"Status: {'Approved' if user.is_approved else 'Pending Approval'}"
                )
            else:
                info_text = "❌ User not found in database."
            
            await update.message.reply_text(info_text)
            
        except Exception as e:
            print(f"Error in user_info: {e}")
        finally:
            session.close()
