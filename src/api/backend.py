import os
import json
from typing import List, Dict, Optional, Any
from fastapi import FastAPI, WebSocket, HTTPException, Request, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
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


# ROUTE 1: Get list of restaurants with name and location
@app.get("/api/restaurants")
async def get_restaurants():
    """Get a list of restaurants with their names and locations."""
    restaurants = app.state.restaurant_data
    simplified_list = [
        {
            "id": restaurant.get("id"),
            "name": restaurant.get("name"),
            "location": restaurant.get("location", "Location not available")
        }
        for restaurant in restaurants
    ]
    return simplified_list

@app.get("/api/restaurant/{restaurant_id}")
async def get_restaurant(restaurant_id: str):
    """Get details of a specific restaurant."""
    restaurants = app.state.restaurant_data
    
    for restaurant in restaurants:
        if restaurant.get("id") == restaurant_id:
            return {
                "id": restaurant.get("id"),
                "name": restaurant.get("name"),
                "location": restaurant.get("location", "Location not available"),
                "menu": restaurant.get("menu", [])
            }
    
    raise HTTPException(status_code=404, detail="Restaurant not found")

# ROUTE 2: Get menu items for a specific restaurant
@app.get("/api/restaurant/menu/{restaurant_id}")
async def get_restaurant_menu(restaurant_id: str):
    """Get menu items for a specific restaurant."""
    restaurants = app.state.restaurant_data
    
    for restaurant in restaurants:
        if restaurant.get("id") == restaurant_id:
            menu_items = restaurant.get("menu", [])
            if not menu_items:
                return []
            return menu_items
    
    raise HTTPException(status_code=404, detail="Restaurant not found")


# ROUTE 3: General chat endpoint
@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest, models=Depends(get_models)):
    """
    Process a chat request and return a response.
    """
    retriever = models["retriever"]
    generator = models["generator"]
    conversation_manager = models["conversation_manager"]
    
    logger.info(f"Chat request received: '{request.message[:50]}...'" if len(request.message) > 50 else request.message)
    
    try:
        # Create or use existing session ID
        session_id = request.session_id
        if not session_id:
            session_id = conversation_manager.create_session()
            
        # Get conversation history
        conversation_history = conversation_manager.get_history(session_id)
        
        # Detect query type for better retrieval
        query_type = retriever.detect_query_type(request.message)
        logger.debug(f"Detected query type: {query_type}")
        
        # Retrieve relevant docs
        retrieved_docs = retriever.retrieve(
            request.message,
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
        
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ROUTE 4: Restaurant-specific chat endpoint
@app.post("/api/chat/{restaurant_id}")
async def chat_restaurant_endpoint(
    restaurant_id: str, 
    request: ChatRequest, 
    models=Depends(get_models)
):
    """Process a chat request for a specific restaurant."""
    retriever = models["retriever"]
    generator = models["generator"]
    conversation_manager = models["conversation_manager"]
    
    try:
        # Find restaurant context
        restaurant_context = None
        for restaurant in app.state.restaurant_data:
            if restaurant.get("id") == restaurant_id:
                restaurant_context = restaurant
                break
        
        if not restaurant_context:
            raise HTTPException(status_code=404, detail="Restaurant not found")
        
        # Enhance the user query with restaurant context
        enhanced_query = f"For the restaurant '{restaurant_context['name']}': {request.message}"
        logger.info(f"Enhanced query with restaurant context: {enhanced_query}")
        
        # Create or use existing session ID
        session_id = request.session_id or conversation_manager.create_session()
        
        # Get conversation history
        conversation_history = conversation_manager.get_history(session_id)
        
        # Retrieve relevant docs with restaurant filter
        filter_metadata = {"restaurant": restaurant_context["name"]}
        retrieved_docs = retriever.retrieve(
            enhanced_query,  # Use enhanced query
            filter_metadata=filter_metadata,
            conversation_history=conversation_history
        )
        
        # Add restaurant context to the retrieved docs to ensure the generator has the information
        if not retrieved_docs or len(retrieved_docs) == 0:
            # Create restaurant info document if no relevant docs found
            menu_info = "\n".join([f"- {item.get('name', 'Unnamed item')}: {item.get('description', 'No description')} ({item.get('food_type', 'Unknown type')})" 
                         for item in restaurant_context.get('menu', []) if item.get('name')])
            
            restaurant_doc = {
                "content": f"Restaurant: {restaurant_context['name']}\nLocation: {restaurant_context['location']}\nMenu items:\n{menu_info}",
                "metadata": {"restaurant": restaurant_context["name"], "type": "info"},
                "score": 1.0
            }
            retrieved_docs = [restaurant_doc]
        
        # Generate response with explicit context
        response = generator.generate(
            query=enhanced_query,
            retrieved_docs=retrieved_docs,
            session_id=session_id
        )
        
        # Format sources
        sources = [
            {
                "content": doc["content"][:100] + "..." if len(doc["content"]) > 100 else doc["content"],
                "restaurant": doc["metadata"].get("restaurant", "Unknown"),
                "score": float(doc.get("score", 0))
            }
            for doc in retrieved_docs
        ]
        
        # Add turn to conversation history
        conversation_manager.add_turn(
            session_id=session_id,
            query=request.message,
            response=response,
            metadata={"restaurant_id": restaurant_id}
        )
        
        return ChatResponse(
            response=response,
            sources=sources,
            session_id=session_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in restaurant-specific chat: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ROUTE 5: WebSocket for real-time chat
@app.websocket("/api/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat.
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
                client_session_id = message_data.get("session_id")
                
                # Use client session ID if provided
                if client_session_id:
                    session_id = client_session_id
                
                if not user_message.strip():
                    await websocket.send_text(json.dumps({"error": "No message provided"}))
                    continue
                
                logger.info(f"WebSocket message received: '{user_message[:50]}...'" if len(user_message) > 50 else user_message)
                
                # Get conversation history
                conversation_history = app.state.conversation_manager.get_history(session_id)
                
                # Detect query type
                query_type = app.state.retriever.detect_query_type(user_message)
                
                # Process the message
                retrieved_docs = app.state.retriever.retrieve(
                    user_message, 
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
                    "query_type": query_type
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


# ROUTE 6: Restaurant-specific WebSocket chat
@app.websocket("/api/ws/chat/{restaurant_id}")
async def websocket_restaurant_endpoint(websocket: WebSocket, restaurant_id: str):
    """
    WebSocket endpoint for real-time chat with specific restaurant context.
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
        
        # Find restaurant context
        restaurant_context = None
        for restaurant in app.state.restaurant_data:
            if restaurant.get("id") == restaurant_id:
                restaurant_context = restaurant
                break
        
        if not restaurant_context:
            await websocket.send_text(json.dumps({
                "error": "Restaurant not found"
            }))
            await websocket.close(code=1011)
            return
        
        logger.info(f"Restaurant-specific WebSocket connection established for restaurant ID {restaurant_id}")
        
        # Create a session for this connection
        session_id = app.state.conversation_manager.create_session()
        
        # Send session ID and restaurant info to client
        await websocket.send_text(json.dumps({
            "session_id": session_id,
            "restaurant": restaurant_context["name"],
            "message": "Connection established"
        }))
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                # Parse the message
                message_data = json.loads(data)
                user_message = message_data.get("message", "")
                client_session_id = message_data.get("session_id")
                
                # Use client session ID if provided
                if client_session_id:
                    session_id = client_session_id
                
                if not user_message.strip():
                    await websocket.send_text(json.dumps({"error": "No message provided"}))
                    continue
                
                logger.info(f"Restaurant WebSocket message received: '{user_message[:50]}...'" if len(user_message) > 50 else user_message)
                
                # Get conversation history
                conversation_history = app.state.conversation_manager.get_history(session_id)
                
                # Detect query type
                query_type = app.state.retriever.detect_query_type(user_message)
                
                # Process the message with restaurant filter
                filter_metadata = {"restaurant": restaurant_context["name"]}
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
                    metadata={"query_type": query_type, "restaurant_id": restaurant_id}
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
                    "restaurant": restaurant_context["name"]
                }))
                
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON format"}))
            except Exception as e:
                logger.error(f"Error processing restaurant WebSocket message: {e}")
                await websocket.send_text(json.dumps({"error": f"Error: {str(e)}"}))
            
    except Exception as e:
        logger.error(f"Restaurant WebSocket error: {e}")
    finally:
        try:
            logger.info("Closing restaurant WebSocket connection")
            await websocket.close()
        except:
            pass


# Exception handlers
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