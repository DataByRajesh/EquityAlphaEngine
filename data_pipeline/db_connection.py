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

# Initialize the SQLAlchemy engine
def initialize_engine():
    """Initialize and return the SQLAlchemy engine with connection pooling."""
    logger.info("Creating SQLAlchemy engine with connection pooling and timeout.")
    
    # Connection arguments for PostgreSQL
    connect_args = {
        "timeout": DEFAULT_TIMEOUT,
        "connect_timeout": 10,
    }

    # Fetch and validate the DATABASE_URL
    database_url = get_secret("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set or invalid.")

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
    if new_database_url:
        logger.info("Reinitializing engine with a new database URL.")
        engine = create_engine(new_database_url, pool_pre_ping=True)
    else:
        logger.info("Reinitializing engine with the default database URL.")
        engine = create_engine(get_secret("DATABASE_URL"), pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
