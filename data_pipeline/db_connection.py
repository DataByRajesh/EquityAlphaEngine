"""
Centralized database connection module.

This module provides a reusable SQLAlchemy engine and helper functions for database operations.
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from data_pipeline.utils import get_secret

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Constants
DEFAULT_TIMEOUT = 60  # seconds

def _get_driver_specific_connect_args(database_url: str) -> dict:
    """
    Get driver-specific connection arguments based on the database URL.
    
    Different PostgreSQL drivers support different connection parameters:
    - psycopg2: supports both 'timeout' and 'connect_timeout'
    - pg8000: supports 'timeout' but not 'connect_timeout'
    """
    connect_args = {"timeout": DEFAULT_TIMEOUT}
    
    # Detect driver from URL
    if "+psycopg2" in database_url or ("+pg" not in database_url and "postgresql://" in database_url):
        # psycopg2 driver (default for postgresql://)
        connect_args["connect_timeout"] = 10
        logger.debug("Using psycopg2 driver connection arguments")
    elif "+pg8000" in database_url:
        # pg8000 driver - doesn't support connect_timeout
        logger.debug("Using pg8000 driver connection arguments (no connect_timeout)")
    else:
        # Unknown driver - use safe defaults (no connect_timeout)
        logger.warning("Unknown PostgreSQL driver detected, using safe connection arguments")
    
    return connect_args

# Initialize the SQLAlchemy engine
def initialize_engine():
    """Initialize and return the SQLAlchemy engine with connection pooling."""
    logger.info("Creating SQLAlchemy engine with connection pooling and timeout.")
    
    # Fetch and validate the DATABASE_URL
    database_url = get_secret("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set or invalid.")

    # Get driver-specific connection arguments
    connect_args = _get_driver_specific_connect_args(database_url)
    logger.info(f"Using connection arguments: {connect_args}")

    # Create the engine with connection pooling
    try:
        engine = create_engine(
            database_url, 
            connect_args=connect_args,
            pool_pre_ping=True,
            pool_size=10,           # Number of connections to maintain in pool
            max_overflow=20,        # Additional connections beyond pool_size
            pool_timeout=30,        # Timeout when getting connection from pool
            pool_recycle=3600,      # Recycle connections after 1 hour
            echo=False              # Set to True for SQL query logging in development
        )
        logger.info("SQLAlchemy engine created successfully with connection pooling.")
        return engine
    except Exception as e:
        logger.error(f"Failed to create SQLAlchemy engine: {e}")
        raise RuntimeError("SQLAlchemy engine creation failed")

# Create a global engine instance
engine = initialize_engine()

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Provide a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def reinitialize_engine(new_database_url=None):
    """Reinitialize the engine with a new database URL."""
    global engine, SessionLocal
    
    # Determine which database URL to use
    database_url = new_database_url if new_database_url else get_secret("DATABASE_URL")
    
    if new_database_url:
        logger.info("Reinitializing engine with a new database URL.")
    else:
        logger.info("Reinitializing engine with the default database URL.")
    
    # Get driver-specific connection arguments
    connect_args = _get_driver_specific_connect_args(database_url)
    
    # Create new engine with proper connection arguments
    engine = create_engine(
        database_url, 
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=3600,
        echo=False
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
