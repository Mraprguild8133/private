import os
from typing import List

class Config:
    """Configuration class for the Telegram bot"""
    
    # Bot Token from @BotFather
    BOT_TOKEN = os.getenv('BOT_TOKEN', 'your_bot_token_here')
    
    # Admin user IDs (comma separated)
    ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]
    
    # Bot settings
    BOT_USERNAME = os.getenv('BOT_USERNAME', '')
    
    # Group settings
    WELCOME_MESSAGE_ENABLED = True
    GOODBYE_MESSAGE_ENABLED = True
    AUTO_MODERATION_ENABLED = True
    
    # Moderation settings
    MAX_WARNINGS = 3
    MUTE_DURATION = 3600  # 1 hour in seconds
    BAN_DURATION = 86400  # 24 hours in seconds
    
    # Filter settings
    FILTER_LINKS = True
    FILTER_BAD_WORDS = True
    FILTER_FILES = False
    
    # Bad words list (add your own)
    BAD_WORDS = [
        'badword1', 'badword2', 'inappropriate'
    ]
    
    # Allowed domains (if link filtering is enabled)
    ALLOWED_DOMAINS = [
        'telegram.org', 'github.com', 'python.org'
    ]
    
    # Database settings (if using database)
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bot.db')
    
    # Logging settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = 'bot.log'

class DevelopmentConfig(Config):
    """Development configuration"""
    LOG_LEVEL = 'DEBUG'
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    LOG_LEVEL = 'WARNING'
    DEBUG = False

# Configuration selector
def get_config():
    env = os.getenv('ENVIRONMENT', 'development')
    if env == 'production':
        return ProductionConfig()
    else:
        return DevelopmentConfig()

# Global config instance
config = get_config()
