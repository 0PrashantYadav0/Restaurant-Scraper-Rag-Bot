"""Custom exceptions for the Zomato RAG Chatbot."""

class ZomatoBotError(Exception):
    """Base exception for all Zomato chatbot errors."""
    pass

class ScraperError(ZomatoBotError):
    """Raised when there's an error in the web scraping process."""
    pass

class KnowledgeBaseError(ZomatoBotError):
    """Raised when there's an error in the knowledge base operations."""
    pass

class RetrieverError(ZomatoBotError):
    """Raised when there's an error in retrieving documents."""
    pass

class GeneratorError(ZomatoBotError):
    """Raised when there's an error in generating responses."""
    pass

class ConfigError(ZomatoBotError):
    """Raised when there's an error in configuration."""
    pass

class APIError(ZomatoBotError):
    """Raised when there's an error in the API."""
    pass