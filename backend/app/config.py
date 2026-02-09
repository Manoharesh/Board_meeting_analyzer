"""
Configuration module for Board Meeting Analyzer.
Loads settings from environment variables with defaults.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration."""
    
    # API Configuration
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 8000))
    RELOAD = os.getenv('RELOAD', 'False').lower() == 'true'
    
    # Audio Configuration
    SAMPLE_RATE = int(os.getenv('SAMPLE_RATE', 16000))
    AUDIO_CHUNK_SIZE = int(os.getenv('AUDIO_CHUNK_SIZE', 1024))
    AUDIO_CHANNELS = int(os.getenv('AUDIO_CHANNELS', 1))
    
    # STT Configuration
    STT_ENGINE = os.getenv('STT_ENGINE', 'google')  # 'google', 'whisper', 'azure'
    WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'base')
    
    # LLM Configuration
    LLM_ENGINE = os.getenv('LLM_ENGINE', 'ollama')  # 'ollama', 'openai', 'azure'
    LLM_MODEL = os.getenv('LLM_MODEL', 'llama3')
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    
    # Speaker Configuration
    MIN_ENROLLMENT_DURATION = int(os.getenv('MIN_ENROLLMENT_DURATION', 10))  # seconds
    MAX_ENROLLMENT_DURATION = int(os.getenv('MAX_ENROLLMENT_DURATION', 20))  # seconds
    SPEAKER_CONFIDENCE_THRESHOLD = float(os.getenv('SPEAKER_CONFIDENCE_THRESHOLD', 0.5))
    
    # Sentiment Configuration
    SENTIMENT_EMOTIONS = [
        'confidence', 'concern', 'disagreement', 'optimism', 'enthusiasm',
        'skepticism', 'frustration', 'agreement', 'neutral', 'thoughtful'
    ]
    
    # Storage Configuration
    STORAGE_PATH = os.getenv('STORAGE_PATH', './meetings')
    MAX_MEETINGS_IN_MEMORY = int(os.getenv('MAX_MEETINGS_IN_MEMORY', 100))
    
    # Database Configuration (for future use)
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./meetings.db')
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', './logs/analyzer.log')
    
    # CORS Configuration
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    
    @classmethod
    def get_summary(cls):
        """Get configuration summary for logging."""
        return {
            'debug': cls.DEBUG,
            'host': cls.HOST,
            'port': cls.PORT,
            'stt_engine': cls.STT_ENGINE,
            'llm_engine': cls.LLM_ENGINE,
            'llm_model': cls.LLM_MODEL,
            'sample_rate': cls.SAMPLE_RATE,
            'storage_path': cls.STORAGE_PATH
        }


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    RELOAD = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    RELOAD = False
    LOG_LEVEL = 'INFO'


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    DATABASE_URL = 'sqlite:///./test.db'
    STORAGE_PATH = './test_meetings'


# Select configuration based on environment
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development').lower()
if ENVIRONMENT == 'production':
    config = ProductionConfig
elif ENVIRONMENT == 'testing':
    config = TestingConfig
else:
    config = DevelopmentConfig
