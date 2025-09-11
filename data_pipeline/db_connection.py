"""
Centralized database connection module.

This module provides a reusable SQLAlchemy engine and helper functions for database operations.
"""

import logging
import os
import time
import urllib.parse

from google.cloud.sql.connector import Connector
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from data_pipeline.utils import get_secret

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Constants
DEFAULT_TIMEOUT = 60  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


def _get_driver_specific_connect_args(database_url: str) -> dict:
    """
    Get driver-specific connection arguments based on the database URL.

    Different PostgreSQL drivers support different connection parameters:
    - psycopg2: supports both 'timeout' and 'connect_timeout'
    - pg8000: supports 'timeout' but not 'connect_timeout'
    """
    connect_args = {"timeout": DEFAULT_TIMEOUT}

    # Detect driver from URL
    if "+psycopg2" in database_url or (
        "+pg" not in database_url and "postgresql://" in database_url
    ):
        # psycopg2 driver (default for postgresql://)
        connect_args["connect_timeout"] = 10
        logger.debug("Using psycopg2 driver connection arguments")
    elif "+pg8000" in database_url:
        # pg8000 driver - doesn't support connect_timeout
        logger.debug(
            "Using pg8000 driver connection arguments (no connect_timeout)")
    else:
        # Unknown driver - use safe defaults (no connect_timeout)
        logger.warning(
            "Unknown PostgreSQL driver detected, using safe connection arguments"
        )

    return connect_args


# Global connector instance
connector = Connector()


def _parse_database_url(database_url: str) -> dict:
    """Parse database URL to extract connection parameters."""
    parsed = urllib.parse.urlparse(database_url)
    return {
        "driver": (
            parsed.scheme.split(
                "+")[-1] if "+" in parsed.scheme else "postgresql"
        ),
        "user": parsed.username,
        "password": parsed.password,
        "host": parsed.hostname,
        "port": parsed.port,
        "database": parsed.path.lstrip("/"),
        "query": parsed.query,
    }


def _is_cloud_sql_host(host: str) -> bool:
    """Check if the host is a Cloud SQL public IP or instance name."""
    # Cloud SQL public IPs are in 34.x.x.x range
    if host.startswith("34."):
        return True
    # Or if it's an instance connection name (project:region:instance)
    if ":" in host and host.count(":") == 2:
        return True
    return False


def _get_cloud_sql_instance_name():
    """Get Cloud SQL instance connection name from environment or config."""
    # Try environment variable first
    instance_name = os.environ.get("CLOUD_SQL_INSTANCE_NAME")
    if instance_name:
        return instance_name

    # Fallback to constructing from config
    try:
        from data_pipeline import config

        project = config.GCP_PROJECT_ID
        region = os.environ.get("GCP_REGION", "us-central1")  # Default region
        instance = "equity-db"  # Assumed instance name
        return f"{project}:{region}:{instance}"
    except:
        logger.warning(
            "Could not determine Cloud SQL instance name, using direct connection"
        )
        return None


def _create_engine_with_retry(
    database_url: str,
    parsed: dict,
    use_connector: bool = False,
    instance_name: str = None,
):
    """Create engine with retry logic for transient failures."""
    last_exception = None

    for attempt in range(MAX_RETRIES):
        try:
            if use_connector and instance_name:

                def getconn():
                    return connector.connect(
                        instance_name,
                        "pg8000",
                        user=parsed["user"],
                        password=parsed["password"],
                        db=parsed["database"],
                    )

                engine = create_engine(
                    "postgresql+pg8000://",
                    creator=getconn,
                    pool_pre_ping=True,
                    pool_size=10,
                    max_overflow=20,
                    pool_timeout=30,
                    pool_recycle=3600,
                    echo=False,
                )
                logger.info(
                    "SQLAlchemy engine created successfully with Cloud SQL connector."
                )
                return engine
            else:
                connect_args = _get_driver_specific_connect_args(database_url)
                engine = create_engine(
                    database_url,
                    connect_args=connect_args,
                    pool_pre_ping=True,
                    pool_size=10,
                    max_overflow=20,
                    pool_timeout=30,
                    pool_recycle=3600,
                    echo=False,
                )
                logger.info(
                    "SQLAlchemy engine created successfully with direct connection."
                )
                return engine
        except Exception as e:
            last_exception = e
            if attempt < MAX_RETRIES - 1:
                logger.warning(
                    f"Engine creation attempt {attempt + 1} failed: {e}. Retrying in {RETRY_DELAY} seconds..."
                )
                time.sleep(RETRY_DELAY)
            else:
                logger.error(
                    f"All {MAX_RETRIES} engine creation attempts failed. Last error: {e}"
                )

    raise RuntimeError(
        f"Failed to create SQLAlchemy engine after {MAX_RETRIES} attempts: {last_exception}"
    )


# Initialize the SQLAlchemy engine
def initialize_engine():
    """Initialize and return the SQLAlchemy engine with connection pooling."""
    logger.info(
        "Creating SQLAlchemy engine with connection pooling and timeout.")

    # Fetch and validate the DATABASE_URL
    database_url = get_secret("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set or invalid.")

    parsed = _parse_database_url(database_url)
    host = parsed["host"]

    # Check if we should use Cloud SQL connector
    if _is_cloud_sql_host(host):
        logger.info(
            "Detected Cloud SQL host, attempting to use Cloud SQL connector")
        instance_name = _get_cloud_sql_instance_name()
        if instance_name:
            try:
                return _create_engine_with_retry(
                    database_url,
                    parsed,
                    use_connector=True,
                    instance_name=instance_name,
                )
            except Exception as e:
                logger.warning(
                    f"Failed to create engine with Cloud SQL connector: {e}. Falling back to direct connection."
                )

    # Fallback to direct connection
    logger.info("Using direct database connection")
    return _create_engine_with_retry(database_url, parsed, use_connector=False)


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
    database_url = new_database_url if new_database_url else get_secret(
        "DATABASE_URL")

    if new_database_url:
        logger.info("Reinitializing engine with a new database URL.")
    else:
        logger.info("Reinitializing engine with the default database URL.")

    parsed = _parse_database_url(database_url)
    host = parsed["host"]

    # Check if we should use Cloud SQL connector
    if _is_cloud_sql_host(host):
        logger.info(
            "Detected Cloud SQL host for reinitialization, attempting to use Cloud SQL connector"
        )
        instance_name = _get_cloud_sql_instance_name()
        if instance_name:
            try:
                engine = _create_engine_with_retry(
                    database_url,
                    parsed,
                    use_connector=True,
                    instance_name=instance_name,
                )
                SessionLocal = sessionmaker(
                    autocommit=False, autoflush=False, bind=engine
                )
                logger.info(
                    "Engine reinitialized successfully with Cloud SQL connector."
                )
                return
            except Exception as e:
                logger.warning(
                    f"Failed to reinitialize engine with Cloud SQL connector: {e}. Falling back to direct connection."
                )

    # Fallback to direct connection
    logger.info("Reinitializing with direct database connection")
    engine = _create_engine_with_retry(
        database_url, parsed, use_connector=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("Engine reinitialized successfully with direct connection.")
