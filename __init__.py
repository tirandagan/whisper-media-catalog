"""
Video Library - A tool for transcribing and organizing video files
"""

import sys
import logging
import colorlog
import os

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