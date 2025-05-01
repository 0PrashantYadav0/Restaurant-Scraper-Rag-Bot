from typing import Dict, Optional
import uuid
from src.chatbot.retriever import RestaurantRetriever
from src.chatbot.generator import RAGGenerator
from src.chatbot.conversation import ConversationManager
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class RestaurantRAGChatbot:
    def __init__(
        self, 
        index_path: str, 
        embeddings_path: str, 
        metadata_path: str,
        model_name: str = "gemini-1.5-flash"
    ):
        """
        Initialize the RAG chatbot.
        
        Args:
            index_path: Path to the FAISS index
            embeddings_path: Path to document embeddings
            metadata_path: Path to document metadata
            model_name: Name of the language model to use
        """
        # Initialize components
        self.retriever = RestaurantRetriever(
            index_path=index_path,
            embeddings_path=embeddings_path,
            metadata_path=metadata_path
        )
        
        self.generator = RAGGenerator(model_name=model_name)
        self.generator.set_retriever(self.retriever)
        
        self.conversation_manager = ConversationManager()
    
    def chat(self, query: str, session_id: Optional[str] = None) -> Dict:
        """
        Process a user query and generate a response.
        
        Args:
            query: User query string
            session_id: Session identifier for conversation tracking
        
        Returns:
            Response dictionary
        """
        # Create a new session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Get conversation history
        conversation_history = self.conversation_manager.get_conversation_history(session_id)
        
        # Handle edge cases
        if not query or not query.strip():
            return {
                "response": "I didn't receive a question. How can I help you with restaurant information?",
                "session_id": session_id
            }
        
        # Check for out-of-scope questions
        out_of_scope_keywords = ["booking", "reservation", "order", "deliver", "pickup", "weather", "stock", "politics"]
        if any(keyword in query.lower() for keyword in out_of_scope_keywords):
            response = {
                "response": "I'm specialized in providing information about restaurants, their menus, and features. I can't help with bookings, ordering, or topics unrelated to restaurant information. How else can I assist you with restaurant details?",
                "query_type": "out_of_scope"
            }
        else:
            # Generate response using the RAG pipeline
            try:
                response = self.generator.generate_response(query, conversation_history)
            except Exception as e:
                logger.error(f"Error generating response: {e}")
                response = {
                    "response": "I'm sorry, I encountered an error processing your request. Could you try asking in a different way?",
                    "error": str(e)
                }
        
        # Add the turn to conversation history
        self.conversation_manager.add_conversation_turn(session_id, query, response)
        
        # Add session ID to response
        response["session_id"] = session_id
        
        return response
    
    def reset_conversation(self, session_id: str):
        """
        Reset the conversation history for a session.
        
        Args:
            session_id: Session identifier
        """
        self.conversation_manager.clear_conversation(session_id)
        return {"status": "success", "message": "Conversation reset successfully"}
    