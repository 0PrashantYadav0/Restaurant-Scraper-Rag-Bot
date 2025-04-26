from typing import List, Dict, Any, Optional
import json
import os
import re
import google.generativeai as genai

from src.utils.logger import setup_logger
from src.utils.exceptions import GeneratorError

logger = setup_logger(__name__)

class GoogleAIGenerator:
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-pro", 
                 max_output_tokens: int = 1024, temperature: float = 0.2):
        """
        Initialize the generator with Google's Generative AI.
        
        Args:
            api_key: Google API key
            model_name: Model name to use
            max_output_tokens: Maximum number of tokens for output
            temperature: Temperature parameter for generation (0.0-1.0)
        """
        self.api_key = api_key
        self.model_name = model_name
        self.max_output_tokens = max_output_tokens
        self.temperature = temperature
        self.conversation_history = {}
        
        # Configure the Google GenerativeAI client
        genai.configure(api_key=api_key)
        
        # Initialize model
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "max_output_tokens": max_output_tokens,
                "temperature": temperature,
            }
        )
        
        logger.info(f"Initialized GoogleAI Generator with model {model_name}")

    def _format_retrieved_context(self, retrieved_docs: List[Dict]) -> str:
        """
        Format retrieved documents into a context string for the LLM.
        
        Args:
            retrieved_docs: List of retrieved documents
            
        Returns:
            Formatted context string
        """
        if not retrieved_docs:
            return "No relevant information found."
        
        context = "RESTAURANT INFORMATION:\n\n"
        
        # Group documents by restaurant
        restaurant_docs = {}
        for i, doc in enumerate(retrieved_docs):
            restaurant_name = doc.get("metadata", {}).get("restaurant", f"Restaurant {i+1}")
            
            if restaurant_name not in restaurant_docs:
                restaurant_docs[restaurant_name] = []
                
            restaurant_docs[restaurant_name].append(doc)
        
        # Format information by restaurant
        for restaurant, docs in restaurant_docs.items():
            context += f"## {restaurant}\n"
            
            for doc in docs:
                # Add document content
                content = doc.get("content", "").strip()
                if content:
                    context += f"{content}\n\n"
                    
                # Add metadata if available
                metadata = doc.get("metadata", {})
                if "category" in metadata:
                    context += f"Category: {metadata['category']}\n"
                if "cuisine" in metadata:
                    context += f"Cuisine: {metadata['cuisine']}\n"
                if "price_range" in metadata:
                    context += f"Price Range: {metadata['price_range']}\n"
                if "location" in metadata:
                    context += f"Location: {metadata['location']}\n"
                if "rating" in metadata:
                    context += f"Rating: {metadata['rating']}\n"
                
            context += "\n"
            
        return context
    
    def _create_prompt(self, query: str, context: str, query_type: str, 
                       conversation_history: List[Dict] = None) -> str:
        """
        Create a prompt for the LLM based on the query, context, and conversation history.
        
        Args:
            query: User query
            context: Formatted context from retrieved documents
            query_type: Type of query detected
            conversation_history: Previous conversation turns
            
        Returns:
            Formatted prompt for the LLM
        """
        # Add conversation history context
        history_context = ""
        if conversation_history and len(conversation_history) > 0:
            history_context = "PREVIOUS CONVERSATION:\n"
            # Include last 3 turns at most
            for turn in conversation_history[-3:]:
                history_context += f"User: {turn['query']}\n"
                if "response" in turn:
                    history_context += f"Assistant: {turn['response']}\n"
            history_context += "\n"
        
        # Customize instructions based on query type
        type_instructions = ""
        if query_type == "menu_availability":
            type_instructions = """For menu queries:
- List available dishes with brief descriptions when available
- Mention prices if available
- Note any special features of dishes (signature, popular, etc.)"""
        elif query_type == "price_range":
            type_instructions = """For price range queries:
- Be specific about price points when available
- Mention price ranges for different categories (appetizers, mains, etc.)
- Compare to other restaurants if this information is available"""
        elif query_type == "dietary_restrictions":
            type_instructions = """For dietary restriction queries:
- Clearly identify which items meet the dietary requirements
- Mention if modifications are possible for other items
- Be explicit about ingredients that may violate restrictions"""
        elif query_type == "comparison":
            type_instructions = """For restaurant comparison queries:
- Compare on multiple factors: food, price, ambiance, etc.
- Highlight unique strengths of each restaurant
- Be balanced in your assessment"""
            
        prompt = f"""You are a helpful and knowledgeable restaurant information assistant. Answer the user's question based ONLY on the provided restaurant information. Be conversational, accurate, and helpful.

{history_context}

{context}

USER QUESTION: {query}

QUERY TYPE: {query_type}

INSTRUCTIONS:
1. Answer ONLY based on the information provided above.
2. Be conversational, friendly, and natural in your response.
3. If information is not available, acknowledge what you can answer and what information is missing.
4. Keep your response concise (2-4 sentences for most questions).
5. Don't apologize for or mention "the provided information/context" - simply present what you know naturally.
6. Don't make up information not present in the context.
{type_instructions}

RESPONSE:"""

        return prompt

    def _get_conversation_history(self, session_id: str, max_turns: int = 5) -> List[Dict]:
        """Get conversation history for a specific session"""
        if session_id not in self.conversation_history:
            return []
        
        return self.conversation_history[session_id][-max_turns:]
    
    def _update_conversation_history(self, session_id: str, query: str, response: str):
        """Update the conversation history with a new turn"""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
            
        self.conversation_history[session_id].append({
            "query": query,
            "response": response
        })
        
        # Keep only the last 10 turns
        if len(self.conversation_history[session_id]) > 10:
            self.conversation_history[session_id] = self.conversation_history[session_id][-10:]

    def generate(self, query: str, retrieved_docs: List[Dict], 
                 session_id: str = None) -> str:
        """
        Generate a response based on the user query and retrieved documents.
        
        Args:
            query: User query
            retrieved_docs: Retrieved documents from the knowledge base
            session_id: Session identifier for conversation tracking
            
        Returns:
            Generated response text
        """
        try:
            # Use a default session ID if none provided
            if not session_id:
                session_id = "default"
                
            # Get conversation history
            conversation_history = self._get_conversation_history(session_id)
                
            # Detect query type from metadata if available
            query_type = "general"
            if retrieved_docs and len(retrieved_docs) > 0:
                if "metadata" in retrieved_docs[0] and "query_type" in retrieved_docs[0]["metadata"]:
                    query_type = retrieved_docs[0]["metadata"]["query_type"]
            
            # Format the context from retrieved documents
            context = self._format_retrieved_context(retrieved_docs)
            
            # Create the prompt
            prompt = self._create_prompt(
                query=query,
                context=context,
                query_type=query_type,
                conversation_history=conversation_history
            )
            
            logger.debug(f"Generated prompt: {prompt[:200]}...")
            
            # Generate the response
            generation = self.model.generate_content(prompt)
            response = generation.text.strip()
            
            # Improve response quality with post-processing
            response = self._post_process_response(response, query_type)
            
            # Update conversation history
            self._update_conversation_history(session_id, query, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise GeneratorError(f"Failed to generate response: {str(e)}")
    
    def _post_process_response(self, response: str, query_type: str) -> str:
        """
        Post-process the generated response to improve quality.
        
        Args:
            response: Generated response text
            query_type: Type of query
            
        Returns:
            Improved response text
        """
        # Remove phrases like "Based on the provided information"
        response = re.sub(r'(?i)based on the (provided|given|available) (information|context|data)', '', response)
        response = re.sub(r'(?i)according to the (provided|given|available) (information|context|data)', '', response)
        
        # Remove phrases like "I don't have information beyond what's provided"
        response = re.sub(r'(?i)I (don\'t|do not) have (information|details) (beyond|outside) (what\'s|what is) provided', 
                         "I don't have that information", response)
        
        # Fix double spaces and cleanup
        response = re.sub(r'\s+', ' ', response).strip()
        
        return response
    
    def clear_conversation_history(self, session_id: str):
        """Clear conversation history for a specific session"""
        if session_id in self.conversation_history:
            del self.conversation_history[session_id]