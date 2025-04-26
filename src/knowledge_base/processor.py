import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

from config import Config
from src.utils.logger import setup_logger
from src.utils.exceptions import KnowledgeBaseError

# Set up logger for this module
logger = setup_logger(__name__)

class RestaurantKnowledgeBase:
    """Knowledge base for restaurant data using vector embeddings for retrieval."""
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the knowledge base with an embedding model.
        
        Args:
            model_name: Name of the sentence transformer model to use for embeddings.
                        If None, uses the model specified in Config.
        """
        self.model_name = model_name or Config.EMBEDDING_MODEL
        logger.info(f"Initializing knowledge base with model: {self.model_name}")
        
        try:
            self.embedding_model = SentenceTransformer(self.model_name)
            self.documents: List[Dict[str, Any]] = []
            self.document_embeddings: Optional[np.ndarray] = None
            self.document_ids: List[int] = []
            self.index = None
            logger.info("Knowledge base initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize knowledge base: {e}")
            raise KnowledgeBaseError(f"Failed to initialize knowledge base: {str(e)}")
    
    def load_data(self, data_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """
        Load restaurant data from JSON file.
        
        Args:
            data_path: Path to the JSON file containing restaurant data
            
        Returns:
            List of restaurant data dictionaries
            
        Raises:
            KnowledgeBaseError: If the file cannot be loaded or is invalid
        """
        data_path = Path(data_path)
        logger.info(f"Loading data from {data_path}")
        
        try:
            if not data_path.exists():
                logger.error(f"Data file not found: {data_path}")
                raise KnowledgeBaseError(f"Data file not found: {data_path}")
                
            with open(data_path, 'r') as f:
                data = json.load(f)
                
            # Validate the data structure
            if not isinstance(data, list):
                logger.error("Invalid data format: root element must be a list")
                raise KnowledgeBaseError("Invalid data format: root element must be a list")
                
            for i, item in enumerate(data):
                if not isinstance(item, dict):
                    logger.error(f"Invalid item at index {i}: must be a dictionary")
                    raise KnowledgeBaseError(f"Invalid item at index {i}: must be a dictionary")
                
                # Check for required fields
                required_fields = ["name"]
                for field in required_fields:
                    if field not in item:
                        logger.error(f"Missing required field '{field}' in item at index {i}")
                        raise KnowledgeBaseError(f"Missing required field '{field}' in item at index {i}")
            
            logger.info(f"Successfully loaded {len(data)} restaurant records")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in data file: {e}")
            raise KnowledgeBaseError(f"Invalid JSON in data file: {str(e)}")
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise KnowledgeBaseError(f"Error loading data: {str(e)}")
    
    def process_restaurant_data(self, restaurant_data: List[Dict]) -> List[Dict]:
        """
        Process restaurant data into chunks suitable for retrieval.
        
        Args:
            restaurant_data: List of restaurant data dictionaries
            
        Returns:
            List of document chunks with metadata
        """
        logger.info(f"Processing {len(restaurant_data)} restaurants into document chunks")
        documents = []
        
        for restaurant in restaurant_data:
            # Basic restaurant info
            restaurant_info = (
                f"Restaurant: {restaurant.get('name', 'Unknown')}\n"
                f"Location: {restaurant.get('location', 'Location not available')}\n"
                f"Hours: {restaurant.get('operating_hours', '')}\n"
                f"Contact: {restaurant.get('contact_info', '')}\n"
            )
            
            documents.append({
                "content": restaurant_info,
                "metadata": {
                    "restaurant": restaurant.get('name', 'Unknown'),
                    "type": "info"
                }
            })
            
            # Special features
            features = restaurant.get('special_features', [])
            if features:
                features_text = f"Restaurant {restaurant.get('name', 'Unknown')} features: {', '.join(features)}"
                documents.append({
                    "content": features_text,
                    "metadata": {
                        "restaurant": restaurant.get('name', 'Unknown'),
                        "type": "features"
                    }
                })
            
            # Menu items - process each menu item separately
            for item in restaurant.get('menu', []):
                menu_text = (
                    f"Restaurant: {restaurant.get('name', 'Unknown')}\n"
                    f"Menu Item: {item.get('name', 'Unnamed item')}\n"
                    f"Description: {item.get('description', 'No description available')}\n"
                    f"Price: {item.get('price', 'Price not listed')}"
                )
                documents.append({
                    "content": menu_text,
                    "metadata": {
                        "restaurant": restaurant.get('name', 'Unknown'),
                        "type": "menu_item",
                        "item_name": item.get('name', 'Unnamed item'),
                        "price": item.get('price', 'Price not listed')
                    }
                })
        
        logger.info(f"Created {len(documents)} document chunks")
        return documents
    
    def create_embeddings(self, documents: List[Dict]) -> None:
        """
        Create embeddings for all documents.
        
        Args:
            documents: List of document dictionaries with 'content' field
            
        Raises:
            KnowledgeBaseError: If embeddings creation fails
        """
        if not documents:
            logger.warning("No documents provided for embedding creation")
            return
            
        logger.info(f"Creating embeddings for {len(documents)} documents")
        try:
            texts = [doc["content"] for doc in documents]
            self.documents = documents
            self.document_ids = list(range(len(documents)))
            
            # Create embeddings
            logger.info("Generating embeddings...")
            embeddings = self.embedding_model.encode(texts)
            self.document_embeddings = np.array(embeddings).astype('float32')
            
            # Create FAISS index for fast retrieval
            dimension = self.document_embeddings.shape[1]
            logger.info(f"Creating FAISS index with dimension {dimension}")
            self.index = faiss.IndexFlatL2(dimension)
            self.index.add(self.document_embeddings)
            logger.info("Embeddings and index created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create embeddings: {e}")
            raise KnowledgeBaseError(f"Failed to create embeddings: {str(e)}")
    
    def save_knowledge_base(self, output_dir: Union[str, Path]) -> None:
        """
        Save the knowledge base to disk.
        
        Args:
            output_dir: Directory where to save the knowledge base files
            
        Raises:
            KnowledgeBaseError: If saving fails
        """
        output_dir = Path(output_dir)
        logger.info(f"Saving knowledge base to {output_dir}")
        
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Validate state before saving
            if not self.documents or self.document_embeddings is None or self.index is None:
                raise KnowledgeBaseError("Knowledge base not initialized properly before saving")
            
            # Save documents
            with open(output_dir / "documents.json", "w") as f:
                json.dump(self.documents, f, indent=2)
            
            # Save document IDs
            with open(output_dir / "document_ids.json", "w") as f:
                json.dump(self.document_ids, f, indent=2)
            
            # Save embeddings
            np.save(output_dir / "embeddings.npy", self.document_embeddings)
            
            # Save FAISS index
            faiss.write_index(self.index, str(output_dir / "faiss_index.bin"))
            logger.info("Knowledge base saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save knowledge base: {e}")
            raise KnowledgeBaseError(f"Failed to save knowledge base: {str(e)}")
    
    def load_knowledge_base(self, input_dir: Union[str, Path]) -> None:
        """
        Load the knowledge base from disk.
        
        Args:
            input_dir: Directory containing the knowledge base files
            
        Raises:
            KnowledgeBaseError: If loading fails
        """
        input_dir = Path(input_dir)
        logger.info(f"Loading knowledge base from {input_dir}")
        
        if not input_dir.exists():
            logger.error(f"Knowledge base directory not found: {input_dir}")
            raise KnowledgeBaseError(f"Knowledge base directory not found: {input_dir}")
        
        try:
            # Load documents
            docs_path = input_dir / "documents.json"
            if not docs_path.exists():
                logger.error(f"Documents file not found: {docs_path}")
                raise KnowledgeBaseError(f"Documents file not found: {docs_path}")
                
            with open(docs_path, "r") as f:
                self.documents = json.load(f)
            
            # Load document IDs
            ids_path = input_dir / "document_ids.json"
            if not ids_path.exists():
                logger.error(f"Document IDs file not found: {ids_path}")
                raise KnowledgeBaseError(f"Document IDs file not found: {ids_path}")
                
            with open(ids_path, "r") as f:
                self.document_ids = json.load(f)
            
            # Load embeddings
            emb_path = input_dir / "embeddings.npy"
            if not emb_path.exists():
                logger.error(f"Embeddings file not found: {emb_path}")
                raise KnowledgeBaseError(f"Embeddings file not found: {emb_path}")
                
            self.document_embeddings = np.load(emb_path)
            
            # Load FAISS index
            index_path = input_dir / "faiss_index.bin"
            if not index_path.exists():
                logger.error(f"FAISS index file not found: {index_path}")
                raise KnowledgeBaseError(f"FAISS index file not found: {index_path}")
                
            self.index = faiss.read_index(str(index_path))
            
            if len(self.documents) == 0:
                logger.warning("Loaded knowledge base contains no documents")
                
            logger.info(f"Knowledge base loaded successfully with {len(self.documents)} documents")
                
        except KnowledgeBaseError:
            raise
        except Exception as e:
            logger.error(f"Failed to load knowledge base: {e}")
            raise KnowledgeBaseError(f"Failed to load knowledge base: {str(e)}")
    
    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: The search query
            top_k: Number of results to return
            
        Returns:
            List of retrieved documents with scores
            
        Raises:
            KnowledgeBaseError: If retrieval fails
        """
        logger.info(f"Retrieving documents for query: '{query}' (top_k={top_k})")
        
        if not query.strip():
            logger.warning("Empty query received")
            return []
            
        if not self.index or not self.documents:
            logger.error("Knowledge base not loaded properly")
            raise KnowledgeBaseError("Knowledge base not loaded properly")
            
        try:
            # Encode the query
            query_embedding = self.embedding_model.encode([query])
            
            # Search the index
            distances, indices = self.index.search(query_embedding.astype('float32'), top_k)
            
            # Get the retrieved documents
            retrieved_docs = []
            for i, idx in enumerate(indices[0]):
                if 0 <= idx < len(self.documents):  # Check if index is valid
                    doc = self.documents[idx].copy()
                    doc["score"] = float(1.0 / (1.0 + distances[0][i]))  # Convert distance to similarity score
                    retrieved_docs.append(doc)
            
            logger.info(f"Retrieved {len(retrieved_docs)} documents")
            return retrieved_docs
            
        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            raise KnowledgeBaseError(f"Error during retrieval: {str(e)}")

    def get_all_documents(self) -> List[Dict]:
        """
        Get all documents in the knowledge base.
        
        Returns:
            List of all documents
        """
        return self.documents
    
    def similarity_search(self, query: str, top_k: int = 5, filter_metadata: Optional[Dict] = None, **kwargs) -> List[Dict]:
        """
        Perform a similarity search for a query.
        
        Args:
            query: The search query
            top_k: Number of results to return
            filter_metadata: Optional metadata to filter results
            **kwargs: Additional arguments (ignored)
            
        Returns:
            List of similar documents
        """
        # First retrieve based on similarity
        results = self.retrieve(query, top_k * 2)  # Get more results to account for filtering
        
        # Then filter by metadata if needed
        if filter_metadata:
            filtered_results = []
            for doc in results:
                if all(doc["metadata"].get(k) == v for k, v in filter_metadata.items()):
                    filtered_results.append(doc)
            results = filtered_results[:top_k]  # Limit to top_k after filtering
        else:
            results = results[:top_k]  # Limit to top_k
        
        return results

def create_knowledge_base(input_file: Union[str, Path], output_dir: Union[str, Path]) -> None:
    """
    Create a knowledge base from restaurant data.
    
    Args:
        input_file: Path to the JSON file containing restaurant data
        output_dir: Directory to save the knowledge base
    """
    logger.info(f"Creating knowledge base from {input_file} to {output_dir}")
    
    try:
        # Create the knowledge base
        kb = RestaurantKnowledgeBase()
        
        # Load and process the restaurant data
        restaurant_data = kb.load_data(input_file)
        documents = kb.process_restaurant_data(restaurant_data)
        
        # Create embeddings
        kb.create_embeddings(documents)
        
        # Save the knowledge base
        kb.save_knowledge_base(output_dir)
        
        logger.info(f"Knowledge base created and saved to {output_dir}")
        logger.info(f"Processed {len(documents)} document chunks")
    except Exception as e:
        logger.error(f"Failed to create knowledge base: {e}")
        raise


if __name__ == "__main__":
    # Example usage
    try:
        create_knowledge_base(
            input_file=Config.RESTAURANT_DATA_FILE,
            output_dir=Config.KB_INDEX_DIR
        )
    except Exception as e:
        logger.error(f"Knowledge base creation failed: {e}")
        raise