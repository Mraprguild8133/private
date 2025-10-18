import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bot.db')
    
    # Default settings
    MAX_WARNINGS = 3
    FLOOD_LIMIT = 5  # messages
    FLOOD_WINDOW = 10  # seconds
    NIGHT_MODE_START = "23:00"
    NIGHT_MODE_END = "07:00"
    
    # Anti-spam settings
    BANNED_LINKS = ['spam.com', 'malicious.site']
    ALLOWED_MEDIA_TYPES = ['photo', 'video', 'document', 'audio', 'voice']
    
    # Language settings
    LANGUAGES = {
        'en': 'English',
        'es': 'Spanish',
        'ru': 'Russian',
        'fr': 'French'
    }
