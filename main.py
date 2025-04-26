from pathlib import Path
from src.scraper.scraper import RestaurantScraper
from src.knowledge_base.processor import create_knowledge_base
from src.utils.logger import setup_logger
from src.api.backend import app
from config import Config
import argparse
import uvicorn

logger = setup_logger(__name__)

def setup_directories():
    """Set up the necessary directories"""
    Path("data/raw").mkdir(parents=True, exist_ok=True)
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    Path("models").mkdir(exist_ok=True)
    Path("models/index").mkdir(exist_ok=True)

def scrape_data():
    """Run the scraper to collect restaurant data"""
    logger.info("Starting data scraping...")
    scraper = RestaurantScraper(urls=Config.SCRAPER_URLS)
    scraper.scrape()
    scraper.save_data(Config.RESTAURANT_DATA_FILE)
    logger.info("Data scraping completed!")

def build_knowledge_base():
    """Process the scraped data and build the knowledge base"""
    logger.info("Processing data and building knowledge base...")
    create_knowledge_base(
        input_file=Config.RESTAURANT_DATA_FILE,
        output_dir=Config.KB_INDEX_DIR
    )
    logger.info("Knowledge base built successfully!")

def start_backend_server():
    """Start the FastAPI backend server"""
    logger.info("Starting backend API server...")
    # Import here to avoid circular imports
    uvicorn.run(app, host=Config.API_HOST, port=Config.API_PORT)

def main():
    parser = argparse.ArgumentParser(description="Zomato Restaurant Data Scraper & RAG Chatbot")
    parser.add_argument("--scrape", action="store_true", help="Scrape restaurant data")
    parser.add_argument("--build-kb", action="store_true", help="Build knowledge base")
    parser.add_argument("--backend", action="store_true", help="Start the backend API server")
    
    args = parser.parse_args()
    
    setup_directories()
    
    if args.scrape:
        scrape_data()
    elif args.build_kb:
        build_knowledge_base()
    elif args.backend:
        start_backend_server()
    else:
        scrape_data()
        build_knowledge_base()
        logger.info("Pipeline completed. Run 'python main.py --backend' to start the API server.")

if __name__ == "__main__":
    main()