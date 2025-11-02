from fastapi import FastAPI, HTTPException, Depends, status, Request, Query, Header, Cookie
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
from pymongo.errors import DuplicateKeyError, PyMongoError
from bson import ObjectId
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import ValidationError, Field
import logging
import time
import json
import secrets

from database import mongodb, get_database
from models import (
    SimpleDataCreate,
    SimpleDataUpdate, 
    SimpleDataResponse,
    SimpleDataInDB,
    PlotlyDataCreate,
    PlotlyDataUpdate,
    PlotlyDataResponse,
    PlotlyDataInDB,
    ErrorResponse,
    SuccessResponse
)

# Configure logging (secure)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        # In production, use file handler with rotation
        # logging.handlers.RotatingFileHandler('app.log', maxBytes=10485760, backupCount=5)
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("="*50)
    logger.info("Starting FastAPI application...")
    logger.info("="*50)
    
    try:
        connected = await mongodb.connect()
        if connected:
            await mongodb.create_indexes()
            logger.info("✅ Database connected and indexes created")
        else:
            logger.error("❌ Failed to connect to database during startup")
    except Exception as e:
        logger.error(f"❌ Error during startup: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    yield
    
    # Shutdown
    try:
        await mongodb.disconnect()
        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

app = FastAPI(
    title="FastAPI Plotly Backend",
    description="Backend API for storing and retrieving Plotly chart data",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if __name__ == "__main__" else None,  # Only show docs in dev
    redoc_url="/redoc" if __name__ == "__main__" else None
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# CSRF Token Store (in production, use Redis or database)
csrf_tokens: Dict[str, float] = {}

# CSRF validation dependency
async def validate_csrf(
    request: Request,
    xsrf_token: Optional[str] = Cookie(None, alias="XSRF-TOKEN"),
    x_csrf_token: Optional[str] = Header(None, alias="X-CSRF-Token")
) -> None:
    """Validate CSRF token using synchronizer token pattern (double-submit)"""
    # Skip for safe methods
    if request.method in ["GET", "HEAD", "OPTIONS"]:
        return
    
    # Validate tokens exist and match
    if not xsrf_token or not x_csrf_token:
        logger.warning(f"Missing CSRF token from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(
            status_code=403,
            detail="CSRF token missing"
        )
    
    if xsrf_token != x_csrf_token:
        logger.warning(f"Invalid CSRF token from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(
            status_code=403,
            detail="Invalid CSRF token"
        )
    
    # Optional: Validate token hasn't expired (24 hours)
    current_time = time.time()
    token_timestamp = csrf_tokens.get(xsrf_token, 0)
    if current_time - token_timestamp > 86400:  # 24 hours
        logger.warning(f"Expired CSRF token from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(
            status_code=403,
            detail="CSRF token expired"
        )

# Rate Limiting Middleware (simple implementation)
request_counts = {}
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    current_time = time.time()
    
    # Clean old entries (older than 1 minute)
    cutoff_time = current_time - 60
    request_counts[client_ip] = [req_time for req_time in request_counts.get(client_ip, []) if req_time > cutoff_time]
    
    # Check rate limit (100 requests per minute)
    if len(request_counts.get(client_ip, [])) >= 100:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Add current request
    if client_ip not in request_counts:
        request_counts[client_ip] = []
    request_counts[client_ip].append(current_time)
    
    response = await call_next(request)
    return response

# CORS Configuration (restrictive)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://load-json-data.vercel.app",
        "https://load-json-data-git-main-joelmoran101s-projects.vercel.app",
        "https://load-json-data-joelmoran101s-projects.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "Authorization"],
    expose_headers=["X-Total-Count"]
)

# Trusted Host Middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=[
        "localhost",
        "127.0.0.1",
        "*.vercel.app"  # Allow all Vercel URLs (including fast-api-backend.vercel.app)
    ]
)

# Global exception handlers
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    logger.warning(f"Validation error from {request.client.host}: {exc}")
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid input data", "errors": exc.errors()}
    )

@app.exception_handler(PyMongoError)
async def pymongo_exception_handler(request: Request, exc: PyMongoError):
    logger.error(f"Database error from {request.client.host}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Database operation failed"}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP {exc.status_code} from {request.client.host}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

# CSRF Token endpoint
@app.get("/csrf-token")
async def get_csrf_token() -> JSONResponse:
    """Generate and return a CSRF token in cookie and response"""
    token = secrets.token_hex(32)
    csrf_tokens[token] = time.time()  # Store with timestamp
    
    # Clean up expired tokens (older than 24 hours)
    current_time = time.time()
    expired = [t for t, timestamp in csrf_tokens.items() if current_time - timestamp > 86400]
    for t in expired:
        del csrf_tokens[t]
    
    response = JSONResponse({"success": True})
    response.set_cookie(
        key="XSRF-TOKEN",
        value=token,
        httponly=False,  # Must be readable by JavaScript
        secure=True,     # HTTPS enabled on Vercel
        samesite="lax",
        max_age=86400    # 24 hours
    )
    return response

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "FastAPI Plotly Backend",
        "version": "1.0.0",
        "docs_url": "/docs",
        "health_check": "/health"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        logger.info("Health check: Testing database connection...")
        collection = get_database()
        # Test database connection
        collection.database.client.admin.command('ping')
        logger.info("Health check: Database connection successful")
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Health check failed: {type(e).__name__}: {str(e)}")
        logger.error(f"MongoDB URL configured: {'Yes' if mongodb.mongodb_url else 'No'}")
        logger.error(f"Database name: {mongodb.database_name}")
        logger.error(f"Client connected: {mongodb.client is not None}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {type(e).__name__}"
        )

# Input sanitization helper
def sanitize_mongodb_input(value: Any) -> Any:
    """Sanitize input to prevent NoSQL injection attacks"""
    if isinstance(value, dict):
        # Remove MongoDB operators that could be used for injection
        dangerous_keys = ['$where', '$regex', '$text', '$expr', '$jsonSchema', '$mod', '$ne']
        return {k: sanitize_mongodb_input(v) for k, v in value.items() if k not in dangerous_keys}
    elif isinstance(value, list):
        return [sanitize_mongodb_input(item) for item in value]
    return value

# Simple data endpoints (for basic dict storage)
@app.get("/data/", response_model=List[SimpleDataResponse])
async def list_all_data(
    limit: int = Query(default=100, le=1000, description="Limit results"),
    skip: int = Query(default=0, ge=0, description="Skip results"),
    collection=Depends(get_database)
):
    """Retrieve all data items with pagination"""
    try:
        # Secure query with pagination
        documents = collection.find({}).limit(limit).skip(skip)
        items = []
        for document in documents:
            # Convert ObjectId to string for response
            document["id"] = str(document["_id"])
            items.append(SimpleDataResponse(**document))
        return items
    except PyMongoError as e:
        logger.error(f"Database error in list_all_data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )

@app.get("/data/{item_id}", response_model=SimpleDataResponse)
async def read_data(item_id: int, collection=Depends(get_database)):
    """Retrieve a specific data item by ID"""
    try:
        document = collection.find_one({"item_id": item_id})
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item with ID {item_id} not found"
            )
        
        document["id"] = str(document["_id"])
        return SimpleDataResponse(**document)
    except PyMongoError as e:
        logger.error(f"Database error in read_data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )

@app.post("/data/", response_model=SuccessResponse, dependencies=[Depends(validate_csrf)])
async def create_data(data_input: SimpleDataCreate, collection=Depends(get_database)):
    """Create a new data item"""
    try:
        # Generate a unique item_id
        last_item = collection.find().sort("item_id", -1).limit(1)
        next_id = 1
        for item in last_item:
            next_id = item.get("item_id", 0) + 1
        
        # Create database document with generated item_id
        data_dict = data_input.dict()
        data_dict["item_id"] = next_id
        db_data = SimpleDataInDB(**data_dict)
        result = collection.insert_one(db_data.dict(by_alias=True))
        
        return SuccessResponse(
            message="Data created successfully",
            item_id=next_id,
            data={"database_id": str(result.inserted_id)}
        )
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item with generated ID already exists (race condition)"
        )
    except PyMongoError as e:
        logger.error(f"Database error in create_data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )

@app.put("/data/{item_id}", response_model=SuccessResponse, dependencies=[Depends(validate_csrf)])
async def update_data(item_id: int, data_input: SimpleDataUpdate, collection=Depends(get_database)):
    """Update an existing data item"""
    try:
        # Check if item exists
        existing = collection.find_one({"item_id": item_id})
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item with ID {item_id} not found"
            )
        
        # Prepare update data
        update_data = {k: v for k, v in data_input.dict().items() if v is not None}
        update_data["updated_at"] = datetime.utcnow()
        
        # Update document
        result = collection.update_one(
            {"item_id": item_id},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No changes were made"
            )
        
        return SuccessResponse(
            message="Data updated successfully",
            item_id=item_id
        )
    except PyMongoError as e:
        logger.error(f"Database error in update_data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )

@app.delete("/data/{item_id}", response_model=SuccessResponse, dependencies=[Depends(validate_csrf)])
async def delete_data(item_id: int, collection=Depends(get_database)):
    """Delete a data item"""
    try:
        result = collection.delete_one({"item_id": item_id})
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item with ID {item_id} not found"
            )
        
        return SuccessResponse(
            message="Data deleted successfully",
            item_id=item_id
        )
    except PyMongoError as e:
        logger.error(f"Database error in delete_data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )

# Plotly-specific endpoints for structured chart data
@app.get("/plotly/", response_model=List[PlotlyDataResponse])
async def list_plotly_charts(collection=Depends(get_database)):
    """Retrieve all Plotly charts"""
    try:
        documents = collection.find({"data": {"$exists": True}})  # Filter for Plotly data
        charts = []
        for document in documents:
            # Convert ObjectId to string and remove the _id field
            document["id"] = str(document.pop("_id"))
            charts.append(PlotlyDataResponse(**document))
        return charts
    except PyMongoError as e:
        logger.error(f"Database error in list_plotly_charts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )

@app.get("/plotly/{item_id}", response_model=PlotlyDataResponse)
async def read_plotly_chart(item_id: int, collection=Depends(get_database)):
    """Retrieve a specific Plotly chart by ID"""
    try:
        document = collection.find_one({"item_id": item_id})
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chart with ID {item_id} not found"
            )
        
        # Convert ObjectId to string and remove the _id field
        document["id"] = str(document.pop("_id"))
        return PlotlyDataResponse(**document)
    except PyMongoError as e:
        logger.error(f"Database error in read_plotly_chart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )

@app.post("/plotly/", response_model=SuccessResponse, dependencies=[Depends(validate_csrf)])
async def create_plotly_chart(chart_data: PlotlyDataCreate, collection=Depends(get_database)):
    """Create a new Plotly chart"""
    try:
        # Generate a unique item_id
        last_item = collection.find().sort("item_id", -1).limit(1)
        next_id = 1
        for item in last_item:
            next_id = item.get("item_id", 0) + 1
        
        # Create database document with generated item_id
        chart_dict = chart_data.dict()
        chart_dict["item_id"] = next_id
        db_data = PlotlyDataInDB(**chart_dict)
        result = collection.insert_one(db_data.dict(by_alias=True))
        
        return SuccessResponse(
            message="Plotly chart created successfully",
            item_id=next_id,
            data={"database_id": str(result.inserted_id)}
        )
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chart with generated ID already exists (race condition)"
        )
    except PyMongoError as e:
        logger.error(f"Database error in create_plotly_chart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )

@app.put("/plotly/{item_id}", response_model=SuccessResponse, dependencies=[Depends(validate_csrf)])
async def update_plotly_chart(item_id: int, chart_data: PlotlyDataUpdate, collection=Depends(get_database)):
    """Update an existing Plotly chart"""
    try:
        # Check if chart exists
        existing = collection.find_one({"item_id": item_id})
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chart with ID {item_id} not found"
            )
        
        # Prepare update data
        update_data = {k: v for k, v in chart_data.dict().items() if v is not None}
        update_data["updated_at"] = datetime.utcnow()
        
        # Update document
        result = collection.update_one(
            {"item_id": item_id},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No changes were made"
            )
        
        return SuccessResponse(
            message="Plotly chart updated successfully",
            item_id=item_id
        )
    except PyMongoError as e:
        logger.error(f"Database error in update_plotly_chart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )

@app.delete("/plotly/{item_id}", response_model=SuccessResponse, dependencies=[Depends(validate_csrf)])
async def delete_plotly_chart(item_id: int, collection=Depends(get_database)):
    """Delete a Plotly chart"""
    try:
        result = collection.delete_one({"item_id": item_id})
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chart with ID {item_id} not found"
            )
        
        return SuccessResponse(
            message="Plotly chart deleted successfully",
            item_id=item_id
        )
    except PyMongoError as e:
        logger.error(f"Database error in delete_plotly_chart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
