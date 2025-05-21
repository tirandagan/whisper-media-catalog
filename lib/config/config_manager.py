import os
import configparser
from dotenv import load_dotenv
import logging

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
        
        # Load the configuration
        self.load_config()
    
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