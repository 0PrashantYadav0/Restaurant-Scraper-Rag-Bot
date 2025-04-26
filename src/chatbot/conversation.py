from typing import List, Dict, Optional, Any
import time
import uuid

class ConversationManager:
    def __init__(self, max_history: int = 10):
        """
        Initialize the conversation manager.
        
        Args:
            max_history: Maximum number of conversation turns to store per session
        """
        self.conversations = {}
        self.max_history = max_history
        
    def create_session(self) -> str:
        """
        Create a new conversation session.
        
        Returns:
            New session ID
        """
        session_id = str(uuid.uuid4())
        self.conversations[session_id] = []
        return session_id
    
    def add_turn(self, session_id: str, query: str, response: str, 
                 metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a conversation turn to the history.
        
        Args:
            session_id: Session identifier
            query: User query
            response: System response
            metadata: Optional metadata to store with the turn
        """
        if session_id not in self.conversations:
            self.conversations[session_id] = []
            
        turn = {
            "query": query,
            "response": response,
            "timestamp": time.time()
        }
        
        if metadata:
            turn["metadata"] = metadata
            
        self.conversations[session_id].append(turn)
        
        # Trim history if it exceeds the maximum
        if len(self.conversations[session_id]) > self.max_history:
            self.conversations[session_id] = self.conversations[session_id][-self.max_history:]
    
    def get_history(self, session_id: str, max_turns: Optional[int] = None) -> List[Dict]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session identifier
            max_turns: Maximum number of most recent turns to return
        
        Returns:
            List of conversation turns
        """
        if session_id not in self.conversations:
            return []
            
        history = self.conversations[session_id]
        
        if max_turns is not None:
            history = history[-max_turns:]
            
        return history
    
    def clear_history(self, session_id: str) -> bool:
        """
        Clear conversation history for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if history was cleared, False if session did not exist
        """
        if session_id in self.conversations:
            del self.conversations[session_id]
            return True
        return False