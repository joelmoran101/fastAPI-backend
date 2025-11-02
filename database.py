import os
import logging
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MongoDB:
    """MongoDB connection and operations manager"""
    
    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.database: Optional[Database] = None
        self.collection: Optional[Collection] = None
        
        # Configuration from environment variables
        self.mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        self.database_name = os.getenv("DATABASE_NAME", "fastapi_plotly_db")
        self.collection_name = os.getenv("COLLECTION_NAME", "plotly_data")
        
        # Determine if using Atlas (cloud) or local MongoDB
        self.is_atlas = "mongodb+srv://" in self.mongodb_url
        
    async def connect(self) -> bool:
        """Establish connection to MongoDB"""
        try:
            logger.info(f"Attempting MongoDB connection...")
            logger.info(f"MongoDB URL: {self.mongodb_url[:20]}...")
            logger.info(f"Database: {self.database_name}")
            logger.info(f"Collection: {self.collection_name}")
            logger.info(f"Is Atlas: {self.is_atlas}")
            
            # Configure connection parameters based on environment
            if self.is_atlas:
                # Atlas (cloud) optimized settings
                logger.info("Using Atlas (cloud) connection settings")
                self.client = MongoClient(
                    self.mongodb_url,
                    serverSelectionTimeoutMS=10000,  # 10 second timeout for cloud
                    connectTimeoutMS=20000,  # 20 second timeout for cloud
                    socketTimeoutMS=30000,   # 30 second timeout for cloud
                    maxPoolSize=50,  # Connection pool size
                    retryWrites=True,  # Enable retry writes
                )
            else:
                # Local MongoDB settings
                self.client = MongoClient(
                    self.mongodb_url,
                    serverSelectionTimeoutMS=5000,  # 5 second timeout
                    connectTimeoutMS=10000,  # 10 second timeout
                    socketTimeoutMS=20000,   # 20 second timeout
                )
            
            # Test the connection
            self.client.admin.command('ping')
            
            # Get database and collection
            self.database = self.client[self.database_name]
            self.collection = self.database[self.collection_name]
            
            environment = "Atlas (cloud)" if self.is_atlas else "Local"
            logger.info(f"Successfully connected to {environment} MongoDB: {self.database_name}.{self.collection_name}")
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"❌ Failed to connect to MongoDB: {type(e).__name__}")
            logger.error(f"Error details: {str(e)}")
            logger.error(f"Check: 1) MongoDB Atlas IP whitelist, 2) Credentials, 3) Network access")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error connecting to MongoDB: {type(e).__name__}")
            logger.error(f"Error details: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    def get_collection(self) -> Collection:
        """Get the MongoDB collection"""
        if self.collection is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.collection
    
    async def create_indexes(self):
        """Create database indexes for better performance"""
        if self.collection is None:
            return
            
        try:
            # Create index on item_id for faster queries
            self.collection.create_index("item_id", unique=True)
            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")

# Global MongoDB instance
mongodb = MongoDB()

async def get_database() -> Collection:
    """Dependency to get MongoDB collection - connects if needed"""
    # Lazy connection for serverless environments
    if mongodb.client is None or mongodb.collection is None:
        logger.info("Database not connected, attempting connection...")
        await mongodb.connect()
        if mongodb.collection is None:
            raise RuntimeError("Failed to connect to database")
    return mongodb.get_collection()
