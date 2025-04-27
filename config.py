"""Configuration module for the Zomato RAG Chatbot project."""

import os
from pathlib import Path
from typing import List, Dict, Any
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the Zomato RAG Chatbot project."""
    
    # Environment
    ENV = os.getenv("APP_ENV", "development")
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    
    # Base paths
    ROOT_DIR = Path(__file__).parent
    DATA_DIR = ROOT_DIR / "data"
    RAW_DATA_DIR = DATA_DIR / "raw"
    MODELS_DIR = ROOT_DIR / "models"
    KB_INDEX_DIR = MODELS_DIR / "index"
    LOG_DIR = ROOT_DIR / "logs"
    FRONTEND_DIR = ROOT_DIR / "frontend"
    
    # Files
    RESTAURANT_DATA_FILE = RAW_DATA_DIR / "restaurant_data.json"
    
    # Web Scraper Configuration
    SCRAPER_URLS = os.getenv("SCRAPER_URLS", "").split(",") if os.getenv("SCRAPER_URLS") else [
        'https://www.eatsure.com/behrouz-biryani/lucknow/gomti-nagar',
        'https://www.eatsure.com/the-good-bowl/lucknow/gomti-nagar',
        'https://www.eatsure.com/biryani-blues/lucknow/gomti-nagar',
        'https://www.eatsure.com/ovenstory/lucknow/gomti-nagar',
        'https://www.eatsure.com/honest-bowl/lucknow/gomti-nagar',
        'https://www.eatsure.com/lunchbox/lucknow/gomti-nagar',
        'https://www.eatsure.com/slow-churn-ice-cream/lucknow/gomti-nagar',
        'https://www.eatsure.com/kwality-walls-frozen-dessert-and-ice-creme-shop-ae/lucknow/gomti-nagar',
        'https://www.eatsure.com/thalaiva-biryani/lucknow/gomti-nagar',
        'https://www.eatsure.com/firangi-bake/lucknow/gomti-nagar'
    ]
    
    # Request headers
    USER_AGENT = os.getenv("USER_AGENT", 
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
    
    # Knowledge Base Configuration
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    VECTOR_DIMENSION = 384  # Dimension of the embedding vectors
    
    # Google GenerativeAI Configuration
    GENAI_API_KEY = os.getenv("GENAI_API_KEY", "")
    GENAI_MODEL = "gemini-1.5-pro"
    MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "1024"))
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
    TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "10"))
    
    # API Configuration
    API_HOST = os.getenv("API_HOST", "127.0.0.1")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # Speech Recognition
    SPEECH_ENABLED = os.getenv("SPEECH_ENABLED", "False").lower() in ("true", "1", "t")
    
    @classmethod
    def ensure_directories(cls) -> None:
        """Ensure all necessary directories exist."""
        cls.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.KB_INDEX_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def load_restaurant_data(cls) -> List[Dict[str, Any]]:
        """Load restaurant data from the data file."""
        try:
            if not cls.RESTAURANT_DATA_FILE.exists():
                return []
            
            with open(cls.RESTAURANT_DATA_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            from src.utils.logger import app_logger
            app_logger.error(f"Error loading restaurant data: {e}")
            return []

# Create directories on import
Config.ensure_directories()
