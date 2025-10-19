import os
import logging
from typing import List

class Config:
    """Configuration class for the Telegram bot"""
    
    def __init__(self):
        # Bot Token from @BotFather
        self.BOT_TOKEN = os.getenv('BOT_TOKEN', '').strip()
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable is required")
        
        # Admin user IDs (comma separated)
        admin_ids = os.getenv('ADMIN_IDS', '')
        self.ADMIN_IDS = []
        if admin_ids:
            for admin_id in admin_ids.split(','):
                try:
                    self.ADMIN_IDS.append(int(admin_id.strip()))
                except ValueError:
                    logging.warning(f"Invalid admin ID: {admin_id}")
        
        # Bot settings
        self.BOT_USERNAME = os.getenv('BOT_USERNAME', '')
        
        # Group settings
        self.WELCOME_MESSAGE_ENABLED = os.getenv('WELCOME_MESSAGE_ENABLED', 'true').lower() == 'true'
        self.GOODBYE_MESSAGE_ENABLED = os.getenv('GOODBYE_MESSAGE_ENABLED', 'true').lower() == 'true'
        self.AUTO_MODERATION_ENABLED = os.getenv('AUTO_MODERATION_ENABLED', 'true').lower() == 'true'
        
        # Moderation settings
        try:
            self.MAX_WARNINGS = int(os.getenv('MAX_WARNINGS', '3'))
            self.MUTE_DURATION = int(os.getenv('MUTE_DURATION', '3600'))
            self.BAN_DURATION = int(os.getenv('BAN_DURATION', '86400'))
        except ValueError as e:
            logging.warning(f"Invalid number in environment variables: {e}")
            self.MAX_WARNINGS = 3
            self.MUTE_DURATION = 3600
            self.BAN_DURATION = 86400
        
        # Filter settings
        self.FILTER_LINKS = os.getenv('FILTER_LINKS', 'true').lower() == 'true'
        self.FILTER_BAD_WORDS = os.getenv('FILTER_BAD_WORDS', 'true').lower() == 'true'
        self.FILTER_FILES = os.getenv('FILTER_FILES', 'false').lower() == 'true'
        
        # Bad words list (add your own)
        bad_words_env = os.getenv('BAD_WORDS', '')
        self.BAD_WORDS = [word.strip().lower() for word in bad_words_env.split(',')] if bad_words_env else [
            'badword1', 'badword2', 'inappropriate'
        ]
        
        # Allowed domains (if link filtering is enabled)
        allowed_domains_env = os.getenv('ALLOWED_DOMAINS', '')
        self.ALLOWED_DOMAINS = [domain.strip() for domain in allowed_domains_env.split(',')] if allowed_domains_env else [
            'telegram.org', 'github.com', 'python.org'
        ]
        
        # Database settings
        self.DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bot.db')
        
        # Logging settings
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_FILE = os.getenv('LOG_FILE', 'bot.log')

# Create global config instance
try:
    config = Config()
except ValueError as e:
    logging.error(f"Configuration error: {e}")
    raise
