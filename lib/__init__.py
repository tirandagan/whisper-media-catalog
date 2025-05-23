"""
╔════════════════════════════════════════════════════════════════════════════════╗
║                                                                                ║
║   Video Library Transcription & Management System                              ║
║                                                                                ║
║   Created by: Tiran Dagan                                                      ║
║   Copyright © 2023-2025 Tiran Dagan. All rights reserved.                      ║
║                                                                                ║
║   Main library package that contains all the core functionality modules.       ║
║   This init file imports and exposes the primary components for convenience.   ║
║                                                                                ║
║   Repository: https://github.com/tirandagan/whisper-media-catalog              ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝

Video Library - Library modules

This package contains all the library modules for the Video Library application.
"""

# Import and expose submodules
from . import database
from . import config
from . import transcriber
from . import utils
from . import video_processor

# Import specific classes for convenience
from .database.models import Video, Transcription
from .config.config_manager import ConfigManager
from .transcriber.transcriber import VideoTranscriber
from .video_processor import VideoProcessor
from .utils import export_database_to_excel
