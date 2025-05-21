"""
╔════════════════════════════════════════════════════════════════════════════════╗
║                                                                                ║
║   Video Library Transcription & Management System                              ║
║                                                                                ║
║   Created by: Tiran Dagan                                                      ║
║   Copyright © 2023-2025 Tiran Dagan. All rights reserved.                      ║
║                                                                                ║
║   Root package initialization module for the application. This file provides   ║
║   version information and application metadata.                                ║
║                                                                                ║
║   Repository: https://github.com/tirandagan/whisper-media-catalog              ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""

# Application version
__version__ = '1.0.0'

# Application information
__app_name__ = 'Video Library Transcription & Management System'
__author__ = 'Tiran Dagan'
__license__ = 'MIT'
__copyright__ = 'Copyright © 2023-2025 Tiran Dagan. All rights reserved.'

# Import required libraries
import sys
import os

# Add the parent directory to the path to allow proper module imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import main components
from lib.database.models import Video, Transcription
from lib.config.config_manager import ConfigManager
from lib.video_processor import VideoProcessor
from lib.transcriber.transcriber import VideoTranscriber
from lib.utils import export_database_to_excel

def setup_logger():
    """Set up colorized logging for the entire package"""
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)s:%(name)s:%(message)s',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    ))
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = []  # Remove any existing handlers
    root_logger.addHandler(handler)
    
    return root_logger

# Initialize logger when the package is imported
logger = setup_logger()

# Make sure all modules are included in the package
from . import config
from . import database
from . import transcriber
from . import video_processor

# Expose utilities at the package level
from utils import export_database_to_excel

__version__ = "0.1.0" 