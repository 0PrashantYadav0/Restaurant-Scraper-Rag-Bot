import re
from typing import List, Dict, Any, Optional

from src.utils.logger import setup_logger
from src.utils.exceptions import RetrieverError
from src.knowledge_base.processor import RestaurantKnowledgeBase

logger = setup_logger(__name__)

class Retriever:
    def __init__(self, knowledge_base: RestaurantKnowledgeBase, top_k: int = 5):
        """
        Initialize the retriever with the restaurant knowledge base
        
        Args:
            knowledge_base: The knowledge base containing restaurant data
            top_k: Number of documents to retrieve (default: 5)
        """
        self.knowledge_base = knowledge_base
        self.top_k = top_k
        
    def detect_query_type(self, query: str) -> str:
        """
        Detect the type of restaurant query to better target retrieval.
        
        Args:
            query: User query string
            
        Returns:
            Query type as a string
        """
        query = query.lower()
        
        if re.search(r'(vegan|vegetarian|gluten.?free|dairy.?free|allergies|dietary|halal|jain)', query):
            return "dietary_restrictions"
        elif re.search(r'(menu|dish|serve|offer|have.*?items?|food|eat)', query):
            return "menu_availability"
        elif re.search(r'(price|cost|expensive|cheap|affordable|range|budget)', query):
            return "price_range"
        elif re.search(r'(compare|difference|versus|vs\.?|better|between)', query):
            return "comparison"
        elif re.search(r'(location|address|where|area|direction|situated)', query):
            return "location"
        elif re.search(r'(time|open|hours|close|available|when)', query):
            return "opening_hours"
        elif re.search(r'(ambiance|atmosphere|environment|setting|decor)', query):
            return "ambiance"
        elif re.search(r'(rating|stars|review|popular|recommend)', query):
            return "rating"
        else:
            return "general"
    
    def extract_entities(self, query: str) -> Dict[str, List[str]]:
        """
        Extract restaurant names, menu items and other entities from the query
        
        Args:
            query: User query string
            
        Returns:
            Dictionary of extracted entities
        """
        entities = {
            "restaurants": [],
            "menu_items": [],
            "dietary_terms": [],
            "cuisines": []
        }
        
        # Extract restaurant names from knowledge base
        all_restaurants = set()
        for doc in self.knowledge_base.get_all_documents():
            if "restaurant" in doc["metadata"]:
                all_restaurants.add(doc["metadata"]["restaurant"].lower())
        
        # Check if any restaurant name appears in the query
        query_lower = query.lower()
        for restaurant in all_restaurants:
            if restaurant.lower() in query_lower:
                entities["restaurants"].append(restaurant)
        
        # Extract dietary terms
        dietary_terms = ["vegetarian", "vegan", "gluten-free", "dairy-free", "nut-free", "halal", "jain"]
        for term in dietary_terms:
            if term.lower() in query_lower:
                entities["dietary_terms"].append(term)
        
        # Extract cuisines
        cuisine_types = ["indian", "italian", "chinese", "mexican", "thai", "japanese", 
                         "mediterranean", "american", "french", "spanish", "middle eastern"]
        for cuisine in cuisine_types:
            if cuisine.lower() in query_lower:
                entities["cuisines"].append(cuisine)
                
        # Extract potential menu items (using quotes or specific patterns)
        menu_item_patterns = [r'"([^"]+)"', r'\'([^\']+)\'']
        for pattern in menu_item_patterns:
            matches = re.findall(pattern, query)
            entities["menu_items"].extend(matches)
        
        # Look for dish patterns without quotes
        dish_patterns = [
            r'(serve|have|offer|get|find|any|the|their|for)\s+([a-z\s]+?)\s+(dish|meal|food|plate|item)',
            r'(looking for|want|like|about|tried)\s+([a-z\s]+?)\s+(dish|meal|food|plate|item)',
        ]
        
        for pattern in dish_patterns:
            matches = re.findall(pattern, query_lower)
            for match in matches:
                if len(match) >= 2:
                    potential_dish = match[1].strip()
                    if potential_dish and len(potential_dish.split()) <= 5:  # Limit phrase length
                        entities["menu_items"].append(potential_dish)
        
        return entities
    
    def enhance_query(self, query: str, query_type: str, entities: Dict[str, List[str]]) -> str:
        """
        Enhance the query with additional context based on query type.
        
        Args:
            query: Original user query
            query_type: Detected query type
            entities: Extracted entities
            
        Returns:
            Enhanced query string for better retrieval
        """
        if query_type == "dietary_restrictions" and entities["dietary_terms"]:
            terms = " ".join(entities["dietary_terms"])
            return f"{query} {terms} options menu restrictions dietary"
        
        elif query_type == "menu_availability" and entities["menu_items"]:
            items = " ".join(entities["menu_items"])
            return f"{query} {items} menu items dishes food"
        
        elif query_type == "price_range":
            return f"{query} price cost menu prices range budget"
        
        elif query_type == "comparison" and len(entities["restaurants"]) >= 2:
            restaurants = " ".join(entities["restaurants"])
            return f"{query} {restaurants} compare comparison differences"
            
        elif query_type == "location":
            return f"{query} location address area directions map"
            
        elif query_type == "opening_hours":
            return f"{query} hours open close timing schedule"
            
        elif query_type == "ambiance":
            return f"{query} ambiance atmosphere environment setting decor"
            
        elif query_type == "rating":
            return f"{query} rating review stars popular feedback"
            
        return query
    
    def retrieve(self, query: str, filter_metadata: Optional[Dict[str, str]] = None, 
                 conversation_history: Optional[List[Dict]] = None) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents based on the user query.
        
        Args:
            query: User query
            filter_metadata: Optional metadata to filter results (e.g., by restaurant)
            conversation_history: Previous conversation context
            
        Returns:
            List of relevant documents
        """
        try:
            # Detect query type and extract entities
            query_type = self.detect_query_type(query)
            entities = self.extract_entities(query)
            
            logger.debug(f"Query type: {query_type}, Entities: {entities}")
            
            # Add context from conversation history if available
            if conversation_history:
                for turn in reversed(conversation_history[-3:]):  # Look at last 3 turns
                    # Extract context from previous user messages or system responses
                    if "query" in turn and not entities["restaurants"]:
                        prev_entities = self.extract_entities(turn["query"])
                        if prev_entities["restaurants"]:
                            entities["restaurants"].extend(prev_entities["restaurants"])
                            break
            
            # Enhance the query for better retrieval
            enhanced_query = self.enhance_query(query, query_type, entities)
            logger.debug(f"Enhanced query: '{enhanced_query}'")
            
            # If specific restaurants were mentioned but no filter is provided, filter by them
            if entities["restaurants"] and not filter_metadata:
                results = []
                for restaurant in entities["restaurants"]:
                    rest_filter = {"restaurant": restaurant}
                    restaurant_docs = self.knowledge_base.similarity_search(
                        enhanced_query, 
                        self.top_k, 
                        filter_metadata=rest_filter
                    )
                    results.extend(restaurant_docs)
                
                # Sort by score and take top k
                if results:
                    results.sort(key=lambda x: x.get("score", 0), reverse=True)
                    results = results[:self.top_k]
            else:
                # Standard search with optional restaurant filter
                results = self.knowledge_base.similarity_search(
                    enhanced_query,
                    self.top_k,
                    filter_metadata=filter_metadata
                )
            
            # Attach query type to metadata to assist the generator
            for doc in results:
                if "metadata" not in doc:
                    doc["metadata"] = {}
                doc["metadata"]["query_type"] = query_type
                
            return results
        
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            raise RetrieverError(f"Failed to retrieve relevant documents: {str(e)}")
        