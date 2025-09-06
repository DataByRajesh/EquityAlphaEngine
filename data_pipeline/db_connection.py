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
    """Initialize and return the SQLAlchemy engine."""
    logger.info("Creating SQLAlchemy engine with timeout.")
    connect_args = {"timeout": DEFAULT_TIMEOUT}

    # Fetch and validate the DATABASE_URL
    database_url = get_secret("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set or invalid.")

    # Create the engine
    try:
        engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
        logger.info("SQLAlchemy engine created successfully.")
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
