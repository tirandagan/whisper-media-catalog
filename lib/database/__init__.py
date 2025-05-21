"""
╔════════════════════════════════════════════════════════════════════════════════╗
║                                                                                ║
║   Video Library Transcription & Management System                              ║
║                                                                                ║
║   Created by: Tiran Dagan                                                      ║
║   Copyright © 2023-2025 Tiran Dagan. All rights reserved.                      ║
║                                                                                ║
║   Database package initialization module that exposes the database models      ║
║   and initialization functions.                                                ║
║                                                                                ║
║   Repository: https://github.com/tirandagan/whisper-media-catalog              ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝

Video Library - Database models
"""

from .models import Video, Transcription, init_db, migrate_db
