#!/usr/bin/env python3
"""
Database Migration Script for Video Library

This script ensures that the database schema is up to date by adding any missing columns.
"""

import os
import argparse
import sqlite3
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.WARNING,  # Default to WARNING level
    format='%(levelname)s: %(message)s'  # Simplified format
)

logger = logging.getLogger("migrate_database")

def migrate_database(db_path):
    """Migrate the database to the latest schema"""
    logger.info(f"Migrating database: {db_path}")
    
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        return False
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [table[0] for table in cursor.fetchall()]
        logger.info(f"Tables in database: {tables}")
        
        # Check if transcriptions table exists
        if 'transcriptions' not in tables:
            logger.warning("Transcriptions table not found in database!")
            return False
        
        # Check columns in transcriptions table
        cursor.execute("PRAGMA table_info(transcriptions)")
        columns = [col[1] for col in cursor.fetchall()]
        logger.info(f"Columns in transcriptions table: {columns}")
        
        # Add missing columns
        missing_columns = []
        
        # Check for summary column
        if 'summary' not in columns:
            missing_columns.append(('summary', 'TEXT'))
        
        # Add missing columns
        for col_name, col_type in missing_columns:
            logger.info(f"Adding column {col_name} ({col_type}) to transcriptions table")
            cursor.execute(f"ALTER TABLE transcriptions ADD COLUMN {col_name} {col_type}")
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        if missing_columns:
            logger.info(f"Added {len(missing_columns)} columns to the database")
        else:
            logger.info("Database schema is already up to date")
        
        return True
        
    except Exception as e:
        logger.error(f"Error migrating database: {e}")
        return False

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Migrate the Video Library database to the latest schema'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to configuration file (default: config.ini)'
    )
    
    parser.add_argument(
        '--db-path',
        type=str,
        help='Direct path to database file (overrides config file)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output (INFO-level logging)'
    )
    
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Set log level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)
        logging.info("Verbose mode enabled")
    
    # Determine database path
    db_path = None
    
    if args.db_path:
        # Use provided database path
        db_path = args.db_path
    else:
        # Try to get from config
        try:
            from lib.config.config_manager import ConfigManager
            config_manager = ConfigManager(args.config)
            db_path = config_manager.get_database_path()
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            logger.error("Please provide a direct path to the database using --db-path")
            return 1
    
    if not db_path:
        logger.error("Database path not specified")
        return 1
    
    # Run migration
    success = migrate_database(db_path)
    
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    sys.exit(main()) 