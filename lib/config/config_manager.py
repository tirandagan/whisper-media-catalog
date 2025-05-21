"""
╔════════════════════════════════════════════════════════════════════════════════╗
║                                                                                ║
║   Video Library Transcription & Management System                              ║
║                                                                                ║
║   Created by: Tiran Dagan                                                      ║
║   Copyright © 2023-2025 Tiran Dagan. All rights reserved.                      ║
║                                                                                ║
║   Configuration management module that handles loading and validating the      ║
║   application's settings. This module creates a template config if none        ║
║   exists and ensures all required settings are properly configured.            ║
║                                                                                ║
║   Repository: https://github.com/tirandagan/whisper-media-catalog              ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""

import os
import configparser
from dotenv import load_dotenv
import logging
import sys

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, config_path=None):
        """
        Initialize the config manager
        
        Args:
            config_path: Path to the INI configuration file
        """
        self.config_path = config_path or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.ini')
        self.config = configparser.ConfigParser()
        
        # Load environment variables from .env file if it exists
        load_dotenv()
        
        # Check if config file exists, create template if it doesn't
        if not os.path.exists(self.config_path):
            self._create_template_config()
            logger.warning(f"Created template configuration file at {self.config_path}")
            logger.warning("Please edit the configuration file and run the program again.")
            sys.exit(0)
        
        # Load the configuration
        self.load_config()
        
        # Verify that required values are set
        self._check_required_values()
    
    def _create_template_config(self):
        """Create a template configuration file"""
        # Create default sections and values
        self.config['secrets'] = {
            'openai_api_key': 'your_openai_api_key_here'
        }
        self.config['folders'] = {
            'input': '/path/to/your/videos/',
            'database': '/path/to/your/database/',
            'transcripts': '/path/to/your/transcripts/'
        }
        self.config['database'] = {
            'filename': 'video_library.db'
        }
        self.config['whisper'] = {
            'model_size': 'base',
            'language': 'en'
        }
        
        # Create parent directories if needed
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        # Write to file
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)
    
    def load_config(self):
        """Load configuration from INI file"""
        try:
            self.config.read(self.config_path)
            
            # Override config with environment variables where applicable
            self._load_env_variables()
            
            # Validate the configuration
            self._validate_config()
            
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except Exception as e:
            logger.error(f"Error parsing INI configuration: {e}")
            raise
    
    def _load_env_variables(self):
        """Override config with environment variables"""
        # Load API keys from environment variables if available
        if os.environ.get('OPENAI_API_KEY'):
            if not self.config.has_section('secrets'):
                self.config.add_section('secrets')
            self.config.set('secrets', 'openai_api_key', os.environ.get('OPENAI_API_KEY'))
    
    def _validate_config(self):
        """Validate that the required configuration parameters are present"""
        required_sections = ['folders', 'database', 'whisper']
        required_folders = ['input', 'database', 'transcripts']
        
        # Check for required sections
        for section in required_sections:
            if not self.config.has_section(section):
                logger.error(f"Missing required config section: {section}")
                raise ValueError(f"Missing required config section: {section}")
        
        # Check for required folder configurations
        for folder in required_folders:
            if not self.config.has_option('folders', folder):
                logger.error(f"Missing required folder config: {folder}")
                raise ValueError(f"Missing required folder config: {folder}")
    
    def _check_required_values(self):
        """Check if required values are properly set or are still at default values"""
        # Check OpenAI API key
        api_key = self.get_openai_api_key()
        if not api_key or api_key == 'your_openai_api_key_here':
            logger.error("OpenAI API key not configured in config.ini")
            print("ERROR: Please set your OpenAI API key in config.ini or as an environment variable OPENAI_API_KEY")
            sys.exit(1)
        
        # Check if folder paths are still default values
        for folder in ['input', 'database', 'transcripts']:
            path = self.config.get('folders', folder)
            if path.startswith('/path/to/your/'):
                logger.error(f"Folder path not configured: {folder}")
                print(f"ERROR: Please set your {folder} folder path in config.ini")
                sys.exit(1)
    
    def _create_folders(self):
        """Create the necessary folders if they don't exist"""
        for folder in ['input', 'database', 'transcripts']:
            folder_path = self.config.get('folders', folder)
            os.makedirs(folder_path, exist_ok=True)
            logger.info(f"Ensured folder exists: {folder_path}")
    
    def get_config(self):
        """Get the full configuration object"""
        return self.config
    
    def get_database_path(self):
        """Get the full path to the SQLite database file"""
        db_folder = self.config.get('folders', 'database')
        db_file = self.config.get('database', 'filename')
        return os.path.join(db_folder, db_file)
    
    def get_whisper_config(self):
        """Get the whisper model configuration"""
        return {
            'model_size': self.config.get('whisper', 'model_size', fallback='base'),
            'language': self.config.get('whisper', 'language', fallback=None)
        }
    
    def get_openai_api_key(self):
        """Get the OpenAI API key"""
        return self.config.get('secrets', 'openai_api_key', fallback=None)
    
    def get_input_folder(self):
        """Get the input folder path"""
        return self.config.get('folders', 'input')
    
    def get_transcripts_folder(self):
        """Get the transcripts folder path"""
        return self.config.get('folders', 'transcripts') 