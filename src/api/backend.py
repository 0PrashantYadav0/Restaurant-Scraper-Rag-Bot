import os
import json
from typing import List, Dict, Optional, Any
from fastapi import FastAPI, WebSocket, HTTPException,Request, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import io
from pathlib import Path
import traceback
from contextlib import asynccontextmanager

from config import Config
from src.utils.logger import setup_logger
from src.utils.exceptions import ZomatoBotError, RetrieverError, GeneratorError
from src.chatbot.retriever import Retriever
from src.chatbot.generator import GoogleAIGenerator
from src.chatbot.conversation import ConversationManager
from src.knowledge_base.processor import RestaurantKnowledgeBase

# Set up logger
logger = setup_logger(__name__)

# Define startup and shutdown logic
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic: load models and data
    try:
        logger.info("Starting API server - loading models...")
        app.state.kb = RestaurantKnowledgeBase()
        app.state.kb.load_knowledge_base(Config.KB_INDEX_DIR)
        app.state.retriever = Retriever(app.state.kb)
        
        # Use Google GenerativeAI
        app.state.generator = GoogleAIGenerator(
            api_key=Config.GENAI_API_KEY,
            model_name=Config.GENAI_MODEL,
            max_output_tokens=Config.MAX_OUTPUT_TOKENS,
            temperature=Config.TEMPERATURE
        )
        logger.info(f"Using Google GenerativeAI with model: {Config.GENAI_MODEL}")
        
        # Initialize conversation manager
        app.state.conversation_manager = ConversationManager()
        logger.info("Initialized conversation manager")
        
        # Load restaurant data for display
        try:
            app.state.restaurant_data = Config.load_restaurant_data()
            logger.info(f"Loaded data for {len(app.state.restaurant_data)} restaurants")
        except Exception as e:
            logger.error(f"Error loading restaurant data: {e}")
            app.state.restaurant_data = []
            
        logger.info("API server startup complete")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        logger.error(traceback.format_exc())
        raise
    
    yield
    
    # Shutdown logic: clean up resources
    logger.info("Shutting down API server")


# Initialize FastAPI app
app = FastAPI(
    title="Zomato Restaurant Assistant API",
    description="API for the Zomato Restaurant RAG Chatbot",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_path = Path(__file__).parent / "static"
static_path.mkdir(exist_ok=True)

assets_path = static_path / "assets"
if assets_path.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")

# Serve static files
@app.get("/", response_class=FileResponse)
async def serve_index():
    """Serve the index.html file."""
    index_path = static_path / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Index file not found")
    return FileResponse(index_path)


# Models for API requests/responses
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    restaurant_id: Optional[str] = None
    session_id: Optional[str] = None
    
    @validator('message')
    def message_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v
    
class ChatResponse(BaseModel):
    response: str
    sources: Optional[List[Dict[str, Any]]] = None
    session_id: str
    query_type: Optional[str] = None
    
class SourceInfo(BaseModel):
    content: str
    restaurant: str
    score: float


# Dependency to check if models are loaded
async def get_models():
    """Dependency to check if models are loaded correctly."""
    if not hasattr(app.state, "kb") or not hasattr(app.state, "retriever") or not hasattr(app.state, "generator"):
        logger.error("API endpoint called before models were initialized")
        raise HTTPException(status_code=503, detail="Service not fully initialized")
    return {
        "kb": app.state.kb,
        "retriever": app.state.retriever,
        "generator": app.state.generator,
        "conversation_manager": app.state.conversation_manager
    }


# Routes
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, models=Depends(get_models)):
    """
    Process a chat request and return a response.
    
    Args:
        request: Chat request containing the user message and optional restaurant_id
        models: Dependency injection of required models
    
    Returns:
        ChatResponse with the generated response and sources
    """
    retriever = models["retriever"]
    generator = models["generator"]
    conversation_manager = models["conversation_manager"]
    
    logger.info(f"Chat request received: '{request.message[:50]}...' if len(request.message) > 50 else request.message")
    
    try:
        # Create or use existing session ID
        session_id = request.session_id
        if not session_id:
            session_id = conversation_manager.create_session()
            
        # Get conversation history
        conversation_history = conversation_manager.get_history(session_id)
        
        # Get restaurant context if provided
        restaurant_context = None
        if request.restaurant_id:
            for restaurant in app.state.restaurant_data:
                if restaurant.get("id") == request.restaurant_id:
                    restaurant_context = restaurant
                    break
        
        # Detect query type for better retrieval
        query_type = retriever.detect_query_type(request.message)
        logger.debug(f"Detected query type: {query_type}")
        
        # Retrieve relevant docs with restaurant context filter if available
        filter_metadata = {"restaurant": restaurant_context["name"]} if restaurant_context else None
        retrieved_docs = retriever.retrieve(
            request.message, 
            filter_metadata=filter_metadata,
            conversation_history=conversation_history
        )
        
        # Generate response
        response = generator.generate(
            query=request.message, 
            retrieved_docs=retrieved_docs,
            session_id=session_id
        )
        
        # Format source information
        sources = [
            {
                "content": doc["content"][:100] + "..." if len(doc["content"]) > 100 else doc["content"],
                "restaurant": doc["metadata"].get("restaurant", "Unknown"),
                "score": float(doc.get("score", 0)),
                "url": doc["metadata"].get("url", None)
            }
            for doc in retrieved_docs
        ]
        
        # Add turn to conversation history
        conversation_manager.add_turn(
            session_id=session_id,
            query=request.message,
            response=response,
            metadata={"query_type": query_type}
        )
        
        logger.info(f"Generated response: '{response[:50]}...' if len(response) > 50 else response")
        return ChatResponse(
            response=response, 
            sources=sources,
            session_id=session_id,
            query_type=query_type
        )
        
    except RetrieverError as e:
        logger.error(f"Retrieval error: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving information: {str(e)}")
    except GeneratorError as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")
    except ZomatoBotError as e:
        logger.error(f"Application error: {e}")
        raise HTTPException(status_code=500, detail=f"Application error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


# WebSocket for real-time chat with conversation history
@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat.
    
    Args:
        websocket: WebSocket connection
    """
    await websocket.accept()
    
    try:
        # Check if models are loaded
        if not hasattr(app.state, "retriever") or not hasattr(app.state, "generator") or not hasattr(app.state, "conversation_manager"):
            await websocket.send_text(json.dumps({
                "error": "Service not fully initialized"
            }))
            await websocket.close(code=1011)
            return
        
        logger.info("WebSocket connection established")
        
        # Create a session for this connection
        session_id = app.state.conversation_manager.create_session()
        
        # Send session ID to client
        await websocket.send_text(json.dumps({
            "session_id": session_id,
            "message": "Connection established"
        }))
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                # Parse the message
                message_data = json.loads(data)
                user_message = message_data.get("message", "")
                restaurant_id = message_data.get("restaurant_id")
                client_session_id = message_data.get("session_id")
                
                # Use client session ID if provided
                if client_session_id:
                    session_id = client_session_id
                
                if not user_message.strip():
                    await websocket.send_text(json.dumps({"error": "No message provided"}))
                    continue
                
                logger.info(f"WebSocket message received: '{user_message[:50]}...' if len(user_message) > 50 else user_message")
                
                # Get conversation history
                conversation_history = app.state.conversation_manager.get_history(session_id)
                
                # Get restaurant context if provided
                restaurant_context = None
                if restaurant_id:
                    for restaurant in app.state.restaurant_data:
                        if restaurant.get("id") == restaurant_id:
                            restaurant_context = restaurant
                            break
                
                # Detect query type
                query_type = app.state.retriever.detect_query_type(user_message)
                
                # Process the message with context filter if available
                filter_metadata = {"restaurant": restaurant_context["name"]} if restaurant_context else None
                retrieved_docs = app.state.retriever.retrieve(
                    user_message, 
                    filter_metadata=filter_metadata,
                    conversation_history=conversation_history
                )
                
                response = app.state.generator.generate(
                    query=user_message, 
                    retrieved_docs=retrieved_docs,
                    session_id=session_id
                )
                
                # Add turn to conversation history
                app.state.conversation_manager.add_turn(
                    session_id=session_id,
                    query=user_message,
                    response=response,
                    metadata={"query_type": query_type}
                )
                
                # Format source information
                sources = [
                    {
                        "content": doc["content"][:100] + "..." if len(doc["content"]) > 100 else doc["content"],
                        "restaurant": doc["metadata"].get("restaurant", "Unknown"),
                        "score": float(doc.get("score", 0)),
                        "url": doc["metadata"].get("url", None)
                    }
                    for doc in retrieved_docs
                ]
                
                # Send response
                await websocket.send_text(json.dumps({
                    "response": response,
                    "sources": sources,
                    "session_id": session_id,
                    "query_type": query_type,
                    "restaurant_context": restaurant_context["name"] if restaurant_context else None
                }))
                
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON format"}))
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                await websocket.send_text(json.dumps({"error": f"Error: {str(e)}"}))
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        try:
            logger.info("Closing WebSocket connection")
            await websocket.close()
        except:
            pass

@app.post("/api/conversation/reset")
async def reset_conversation(session_id: str, models=Depends(get_models)):
    """Reset conversation history for a session"""
    conversation_manager = models["conversation_manager"]
    
    result = conversation_manager.clear_history(session_id)
    if result:
        return {"status": "success", "message": "Conversation history cleared"}
    else:
        return {"status": "not_found", "message": "Session ID not found"}


@app.get("/api/conversation/history")
async def get_conversation_history(session_id: str, limit: Optional[int] = None, models=Depends(get_models)):
    """Get conversation history for a session"""
    conversation_manager = models["conversation_manager"]
    
    history = conversation_manager.get_history(session_id, limit)
    return {"history": history, "count": len(history)}


# Keep existing endpoints
@app.get("/api/health")
async def health_check():
    """Health check endpoint to verify API is functioning."""
    try:
        # Basic component checks
        kb_status = "available" if os.path.exists(str(Config.KB_INDEX_DIR)) else "missing"
        data_status = "available" if os.path.exists(str(Config.RESTAURANT_DATA_FILE)) else "missing"
        
        return {
            "status": "healthy",
            "version": "1.0.0",
            "environment": Config.ENV,
            "components": {
                "knowledge_base": kb_status,
                "restaurant_data": data_status,
                "api_server": "running"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during health check")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom exception handler for HTTP exceptions."""
    logger.error(f"HTTP error: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected error occurred"}
    )

# Keep existing restaurant endpoints
@app.get("/api/restaurants")
async def get_restaurants(
    cuisine: Optional[str] = None,
    location: Optional[str] = None,
    min_rating: Optional[float] = None,
    sort_by: Optional[str] = None
):
    """Get filtered restaurant information."""
    restaurants = app.state.restaurant_data
    
    # Apply filters
    if cuisine:
        restaurants = [r for r in restaurants if cuisine.lower() in r.get("cuisine", "").lower()]
    if location:
        restaurants = [r for r in restaurants if location.lower() in r.get("location", "").lower()]
    if min_rating is not None:
        restaurants = [r for r in restaurants if r.get("rating", 0) >= min_rating]
    
    # Apply sorting
    if sort_by:
        if sort_by == "rating":
            restaurants = sorted(restaurants, key=lambda r: r.get("rating", 0), reverse=True)
        elif sort_by == "name":
            restaurants = sorted(restaurants, key=lambda r: r.get("name", ""))
        elif sort_by == "popularity":
            restaurants = sorted(restaurants, key=lambda r: r.get("popularity", 0), reverse=True)
    
    return restaurants

@app.get("/api/restaurants/{restaurant_id}")
async def get_restaurant_by_id(restaurant_id: str):
    """Get detailed information about a specific restaurant."""
    restaurants = app.state.restaurant_data
    
    for restaurant in restaurants:
        if restaurant.get("id") == restaurant_id:
            return restaurant
    
    raise HTTPException(status_code=404, detail="Restaurant not found")

@app.get("/api/cuisines")
async def get_cuisines():
    """Get list of all available cuisines."""
    restaurants = app.state.restaurant_data
    cuisines = set()
    
    for restaurant in restaurants:
        if "cuisine" in restaurant:
            for cuisine in restaurant["cuisine"].split(","):
                cuisines.add(cuisine.strip())
    
    return sorted(list(cuisines))

@app.get("/api/locations")
async def get_locations():
    """Get list of all available restaurant locations."""
    restaurants = app.state.restaurant_data
    locations = set()
    
    for restaurant in restaurants:
        if "location" in restaurant:
            locations.add(restaurant["location"].strip())
    
    return sorted(list(locations))

@app.get("/api/restaurant")
async def get_all_restaurants():
    """Get a simplified list of all restaurants with just ID and name."""
    restaurants = app.state.restaurant_data
    simplified_list = [
        {
            "id": restaurant.get("id"),
            "name": restaurant.get("name")
        }
        for restaurant in restaurants
    ]
    return simplified_list

@app.get("/api/restaurant/menu/{restaurant_id}")
async def get_restaurant_menu(restaurant_id: str):
    """Get menu items for a specific restaurant."""
    restaurants = app.state.restaurant_data
    
    for restaurant in restaurants:
        if restaurant.get("id") == restaurant_id:
            # Check if the restaurant has menu items
            menu_items = restaurant.get("menu", [])
            if not menu_items:
                # If no dedicated "menu" field, create a basic menu structure
                # from other available data
                menu_items = []
                
                # Add popular dishes if available
                if "popular_dishes" in restaurant:
                    for dish in restaurant.get("popular_dishes", []):
                        menu_items.append({
                            "name": dish.get("name", "Unknown dish"),
                            "description": dish.get("description", ""),
                            "price": dish.get("price", "N/A"),
                            "vegetarian": dish.get("vegetarian", False),
                            "category": "Popular Dishes"
                        })
            
            return menu_items
    
    # If restaurant not found
    raise HTTPException(status_code=404, detail="Restaurant or menu not found")