#!/usr/bin/env python3
"""
Startup script for the FastAPI Plotly Backend application.
"""

import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    # Get configuration from environment
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
    print(f"Starting FastAPI Plotly Backend on {host}:{port}")
    print(f"Debug mode: {debug}")
    print(f"MongoDB URL: {os.getenv('MONGODB_URL', 'mongodb://localhost:27017')}")
    print(f"Database: {os.getenv('DATABASE_NAME', 'fastapi_plotly_db')}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if debug else "warning"
    )