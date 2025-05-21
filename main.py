#!/usr/bin/env python3
"""
╔════════════════════════════════════════════════════════════════════════════════╗
║                                                                                ║
║   Video Library Transcription & Management System                              ║
║                                                                                ║
║   Created by: Tiran Dagan                                                      ║
║   Copyright © 2023-2025 Tiran Dagan. All rights reserved.                      ║
║                                                                                ║
║   Main script that serves as the entry point for the application. This file    ║
║   handles command-line arguments, initializes the application components,      ║
║   and orchestrates the video processing and transcription workflow.            ║
║                                                                                ║
║   Repository: https://github.com/tirandagan/whisper-media-catalog              ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import argparse
import logging
import subprocess
from datetime import datetime

# Set up logging
import colorlog

def setup_logger(verbose=False):
    """Set up colorized logging"""
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)s:%(message)s',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    ))
    
    root_logger = logging.getLogger()
    
    # Set default level to WARNING unless verbose mode is enabled
    root_logger.setLevel(logging.INFO if verbose else logging.WARNING)
    root_logger.handlers = []  # Remove any existing handlers
    root_logger.addHandler(handler)
    
    # Silence specific loggers
    logging.getLogger('httpx').setLevel(logging.WARNING)
    
    return root_logger

# Logger will be initialized in main() with verbose flag

# Import from lib
from lib.config.config_manager import ConfigManager
from lib.database.models import init_db, Video, Transcription
from lib.video_processor import VideoProcessor
from lib.transcriber.transcriber import VideoTranscriber
from lib.utils import export_database_to_excel

def check_ffmpeg_installed():
    """Check if ffmpeg and ffprobe are installed"""
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        subprocess.run(['ffprobe', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.error("FFmpeg or ffprobe is not installed or not in PATH. Please install FFmpeg.")
        logger.error("Ubuntu/Debian: sudo apt install ffmpeg")
        logger.error("Windows: Download from https://www.ffmpeg.org/download.html and add to PATH")
        logger.error("macOS: brew install ffmpeg")
        return False

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Process and transcribe video files'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to configuration file (default: config.ini)'
    )
    
    parser.add_argument(
        '--scan-only', 
        action='store_true',
        help='Only scan for videos and extract metadata, skip transcription'
    )
    
    parser.add_argument(
        '--transcribe-only',
        action='store_true',
        help='Only transcribe videos that have been scanned but not transcribed'
    )
    
    parser.add_argument(
        '--single_file',
        action='store_true',
        help='Process only one new file and then exit'
    )
    
    parser.add_argument(
        '--no-excel',
        action='store_true',
        help='Skip exporting database to Excel at the end'
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
    
    # Initialize logger with verbose flag
    global logger
    logger = setup_logger(args.verbose)
    
    db_path = None
    
    # Check if ffmpeg is installed before continuing
    if not check_ffmpeg_installed():
        return 1
    
    try:
        # Initialize the configuration manager
        try:
            config_manager = ConfigManager(args.config)
            logger.info("Configuration loaded successfully")
        except FileNotFoundError:
            # This should not happen now since we create a template, but just in case
            print(f"Configuration file not found. A template has been created at '{os.path.abspath('config.ini')}'")
            print("Please edit the configuration file and run the program again.")
            return 1
        except ValueError as ve:
            # Handle missing required configuration
            print(f"Configuration error: {str(ve)}")
            print("Please check your configuration file and try again.")
            return 1
        
        # Initialize the database
        db_path = config_manager.get_database_path()
        engine = init_db(db_path)
        logger.info(f"Database initialized at {db_path}")
        
        # Verify that folders exist (but don't create them)
        input_folder = config_manager.get_input_folder()
        transcripts_folder = config_manager.get_transcripts_folder()
        
        missing_folders = []
        
        if not os.path.exists(input_folder):
            missing_folders.append(f"Input folder: {input_folder}")
            logger.warning(f"Input folder does not exist: {input_folder}")
        
        if not os.path.exists(transcripts_folder):
            missing_folders.append(f"Transcripts folder: {transcripts_folder}")
            logger.warning(f"Transcripts folder does not exist: {transcripts_folder}")
        
        if missing_folders:
            print("The following configured folders don't exist:")
            for folder in missing_folders:
                print(f"  - {folder}")
            create_folders = input("Would you like to create these folders? (y/n): ").lower().strip()
            if create_folders == 'y':
                # Create the folders
                for folder_path in [input_folder, transcripts_folder]:
                    if not os.path.exists(folder_path):
                        os.makedirs(folder_path, exist_ok=True)
                        print(f"Created folder: {folder_path}")
            else:
                print("Please create the folders manually and run the program again.")
                return 1
        
        # Initialize video processor
        video_processor = VideoProcessor(config_manager)
        
        # Track the total number of transcribed videos
        total_transcribed = 0
        
        # Always scan for new videos first unless explicitly in transcribe-only mode
        # This ensures any new files are added to the database
        if not args.transcribe_only:
            logger.info(f"Scanning for videos in {config_manager.get_input_folder()}")
            new_video_ids = video_processor.scan_input_folder()
            logger.info(f"Found {len(new_video_ids)} new videos")
        else:
            new_video_ids = []
        
        # Process untranscribed videos if not in scan-only mode
        if not args.scan_only:
            transcriber = VideoTranscriber(config_manager)
            
            # Single file mode logic
            if args.single_file:
                # First try to use a new video if available
                if new_video_ids:
                    video_id = new_video_ids[0]
                    logger.info(f"Single file mode: Transcribing one new video")
                else:
                    # Otherwise get any untranscribed video
                    untranscribed_ids = video_processor.get_untranscribed_videos()
                    if untranscribed_ids:
                        video_id = untranscribed_ids[0]
                        logger.info(f"Single file mode: Transcribing one untranscribed video")
                    else:
                        logger.info("No untranscribed videos found")
                        video_id = None
                
                # Process the single video if we found one
                if video_id:
                    video = video_processor.get_video_by_id(video_id)
                    if video:
                        logger.info(f"Processing video: {video.filename}")
                        transcribed_count = transcriber.transcribe_videos(video_ids=[video_id])
                        total_transcribed += transcribed_count
                        
                        if transcribed_count > 0:
                            if args.verbose:
                                logger.info(f"Transcribed 1 video: {video.filename}")
                            else:
                                print(f"Transcribed: {video.filename}")
                        else:
                            logger.warning("No videos were transcribed")
                    else:
                        logger.error(f"Could not find video with ID {video_id} in database")
            else:
                # Process all untranscribed videos (default behavior)
                logger.info("Starting video transcription")
                untranscribed_ids = video_processor.get_untranscribed_videos()
                
                if untranscribed_ids:
                    logger.info(f"Found {len(untranscribed_ids)} untranscribed videos")
                    transcribed_count = transcriber.transcribe_videos(video_ids=untranscribed_ids)
                    total_transcribed += transcribed_count
                    logger.info(f"Transcribed {transcribed_count} videos")
                else:
                    logger.info("No untranscribed videos found")
        
        logger.info(f"Processing complete. Total transcribed: {total_transcribed}")
        
        # Always export database to Excel unless specifically disabled
        # This ensures the Excel file is updated after any processing
        if not args.no_excel and db_path:
            db_folder = os.path.dirname(db_path)
            excel_path = export_database_to_excel(db_path, db_folder)
            if excel_path:
                if args.verbose:
                    logger.info(f"Database exported to Excel: {excel_path}")
                else:
                    print(f"Excel export: {excel_path}")
        
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 