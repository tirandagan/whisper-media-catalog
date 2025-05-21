"""
╔════════════════════════════════════════════════════════════════════════════════╗
║                                                                                ║
║   Video Library Transcription & Management System                              ║
║                                                                                ║
║   Created by: Tiran Dagan                                                      ║
║   Copyright © 2023-2025 Tiran Dagan. All rights reserved.                      ║
║                                                                                ║
║   Database models module that defines the SQLAlchemy ORM models for the        ║
║   application. This module contains the Video, Transcription, and Keyword      ║
║   models, as well as their relationships and database initialization logic.    ║
║                                                                                ║
║   Repository: https://github.com/tirandagan/whisper-media-catalog              ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import sqlite3
import logging
import os

logger = logging.getLogger(__name__)

Base = declarative_base()

# Association table for many-to-many relationship between transcriptions and keywords
transcription_keywords = Table(
    'transcription_keywords',
    Base.metadata,
    Column('transcription_id', Integer, ForeignKey('transcriptions.id'), primary_key=True),
    Column('keyword_id', Integer, ForeignKey('keywords.id'), primary_key=True)
)

class Keyword(Base):
    __tablename__ = 'keywords'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    transcriptions = relationship("Transcription", secondary=transcription_keywords, back_populates="keywords")
    
    def __repr__(self):
        return f"<Keyword(name='{self.name}')>"

class Video(Base):
    __tablename__ = 'videos'
    
    id = Column(Integer, primary_key=True)
    filename = Column(String, unique=True, nullable=False)
    filepath = Column(String, nullable=False)
    filesize = Column(Integer)  # Size in bytes
    duration = Column(Float)    # Duration in seconds
    
    # Video characteristics
    encoding = Column(String)
    resolution = Column(String) # e.g., "1920x1080"
    width = Column(Integer)
    height = Column(Integer)
    bitrate = Column(Integer)   # Bitrate in bps
    fps = Column(Float)         # Frames per second
    
    # Status tracking - possible values: "New", "Transcribed", "Missing", "Error Transcribing"
    status = Column(String, default="New")
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    transcription = relationship("Transcription", uselist=False, back_populates="video", cascade="all, delete-orphan")

class Transcription(Base):
    __tablename__ = 'transcriptions'
    
    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey('videos.id'), nullable=False)
    
    # Transcription info
    is_transcribed = Column(Boolean, default=False)
    transcribed_at = Column(DateTime)
    transcript_text = Column(Text)
    transcript_file = Column(String)  # Path to transcript file if saved separately
    suggested_title = Column(String)
    summary = Column(Text)  # Summary of the video transcript
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    video = relationship("Video", back_populates="transcription")
    keywords = relationship("Keyword", secondary=transcription_keywords, back_populates="transcriptions")

def init_db(db_path):
    """Initialize the database and create tables if they don't exist"""
    # Check if the database file exists
    db_exists = os.path.exists(db_path)
    
    # Create engine and tables
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    
    # If database already existed, run migrations
    if db_exists:
        logger.info(f"Existing database found at {db_path}, checking for migrations")
        migrate_db(db_path)
    else:
        logger.info(f"Created new database at {db_path}")
    
    return engine

def migrate_db(db_path):
    """Apply any necessary database migrations"""
    try:
        # Connect directly to the SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check table existence
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [table[0] for table in cursor.fetchall()]
        
        # Check if summary column exists in transcriptions table
        cursor.execute("PRAGMA table_info(transcriptions)")
        columns = [col[1] for col in cursor.fetchall()]
        logger.info(f"Current columns in transcriptions table: {columns}")
        
        # Add summary column if it doesn't exist
        if 'summary' not in columns:
            logger.info("Adding 'summary' column to transcriptions table")
            cursor.execute("ALTER TABLE transcriptions ADD COLUMN summary TEXT")
            logger.info("Database migration completed successfully - added 'summary' column")
            
        # Check if status column exists in videos table
        cursor.execute("PRAGMA table_info(videos)")
        video_columns = [col[1] for col in cursor.fetchall()]
        logger.info(f"Current columns in videos table: {video_columns}")
        
        # Add status column if it doesn't exist
        if 'status' not in video_columns:
            logger.info("Adding 'status' column to videos table")
            cursor.execute("ALTER TABLE videos ADD COLUMN status TEXT DEFAULT 'New'")
            
            # Update existing records based on transcription status
            cursor.execute("""
            UPDATE videos 
            SET status = 'Transcribed' 
            WHERE id IN (
                SELECT video_id FROM transcriptions 
                WHERE is_transcribed = 1
            )
            """)
            logger.info("Database migration completed successfully - added 'status' column to videos table")
        
        # Check if keywords table exists
        if 'keywords' not in tables:
            logger.info("Creating 'keywords' table")
            cursor.execute("""
            CREATE TABLE keywords (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            logger.info("Keywords table created successfully")
        
        # Check if association table exists
        if 'transcription_keywords' not in tables:
            logger.info("Creating 'transcription_keywords' association table")
            cursor.execute("""
            CREATE TABLE transcription_keywords (
                transcription_id INTEGER NOT NULL,
                keyword_id INTEGER NOT NULL,
                PRIMARY KEY (transcription_id, keyword_id),
                FOREIGN KEY (transcription_id) REFERENCES transcriptions (id),
                FOREIGN KEY (keyword_id) REFERENCES keywords (id)
            )
            """)
            logger.info("Transcription-keywords association table created successfully")
        
        conn.commit()
        logger.info("Database schema is up to date")
        
        conn.close()
    except Exception as e:
        logger.error(f"Error during database migration: {str(e)}")
        raise  # Re-raise the exception to ensure we know there was a problem 