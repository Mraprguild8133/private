from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Group(Base):
    __tablename__ = 'groups'
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(String(50), unique=True, nullable=False)
    title = Column(String(255))
    language = Column(String(10), default='en')
    welcome_enabled = Column(Boolean, default=True)
    goodbye_enabled = Column(Boolean, default=True)
    captcha_enabled = Column(Boolean, default=False)
    approval_mode = Column(Boolean, default=False)
    anti_flood_enabled = Column(Boolean, default=True)
    night_mode_enabled = Column(Boolean, default=False)
    night_mode_start = Column(String(5), default="23:00")
    night_mode_end = Column(String(5), default="07:00")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    users = relationship("GroupUser", back_populates="group")
    warnings = relationship("Warning", back_populates="group")
    blocked_words = relationship("BlockedWord", back_populates="group")
    media_settings = relationship("MediaSetting", back_populates="group")

class GroupUser(Base):
    __tablename__ = 'group_users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    group_id = Column(Integer, ForeignKey('groups.id'))
    is_approved = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    warnings_count = Column(Integer, default=0)
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    group = relationship("Group", back_populates="users")

class Warning(Base):
    __tablename__ = 'warnings'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), nullable=False)
    group_id = Column(Integer, ForeignKey('groups.id'))
    reason = Column(Text)
    issued_by = Column(String(50))
    issued_at = Column(DateTime, default=datetime.utcnow)
    
    group = relationship("Group", back_populates="warnings")

class BlockedWord(Base):
    __tablename__ = 'blocked_words'
    
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id'))
    word = Column(String(255), nullable=False)
    is_regex = Column(Boolean, default=False)
    
    group = relationship("Group", back_populates="blocked_words")

class MediaSetting(Base):
    __tablename__ = 'media_settings'
    
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id'))
    media_type = Column(String(20), nullable=False)  # photo, video, document, etc.
    allowed = Column(Boolean, default=True)
    admin_only = Column(Boolean, default=False)
    
    group = relationship("Group", back_populates="media_settings")
