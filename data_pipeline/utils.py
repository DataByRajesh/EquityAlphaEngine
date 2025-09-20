# standard libraries
import logging
import os
import json
import tempfile

# third-party libraries
from google.cloud import secretmanager

# local application imports
import data_pipeline.config as config

logger = logging.getLogger(__name__)


def _setup_gcp_credentials():
    """Set up GCP credentials for different environments."""
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        logger.debug("GOOGLE_APPLICATION_CREDENTIALS already set")
        return True
    
    # Check if we're running in Cloud Run (has metadata service)
    if os.environ.get("K_SERVICE") or os.environ.get("CLOUD_RUN_SERVICE"):
        logger.debug("Running in Cloud Run, using metadata service for authentication")
        return True
    
    # Check for service account key in environment variable (from secrets)
    gcp_sa_key = os.environ.get("GCP_SA_KEY")
    if gcp_sa_key:
        try:
            # Create temporary file for service account key
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
            temp_file.write(gcp_sa_key)
            temp_file.close()
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_file.name
            logger.debug("Set GOOGLE_APPLICATION_CREDENTIALS from GCP_SA_KEY environment variable")
            return True
        except Exception as e:
            logger.warning(f"Failed to set up credentials from GCP_SA_KEY: {e}")
    
    # Look for local service account key files
    possible_paths = [
        "service-account-key.json",
        "gcp-credentials.json",
        os.path.join(os.path.dirname(__file__), "..", "service-account-key.json"),
        os.path.join(os.path.dirname(__file__), "..", "gcp-credentials.json"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(path)
            logger.debug(f"Set GOOGLE_APPLICATION_CREDENTIALS to {path}")
            return True
    
    logger.warning("No GCP service account credentials found. GCP operations may fail unless running in an authenticated environment.")
    return False


def get_secret(secret_name: str) -> str:
    """Fetch a secret value from Google Cloud Secret Manager, with fallback to environment variables."""
    # Check if GCP Secret Manager is enabled
    use_secret_manager = os.environ.get("USE_GCP_SECRET_MANAGER", "true").lower() == "true"

    # First, try to get from environment variable (for local development)
    env_value = os.environ.get(secret_name)
    if env_value:
        logger.debug(f"Using {secret_name} from environment variable")
        return env_value

    # If not in env and Secret Manager is enabled, try GCP Secret Manager
    if use_secret_manager:
        # Set up GCP credentials
        _setup_gcp_credentials()

        try:
            client = secretmanager.SecretManagerServiceClient()
            project_id = config.GCP_PROJECT_ID  # Fetch project_id from config
            logger.debug(f"Using project_id: {project_id}")
            name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            logger.debug(f"Successfully retrieved {secret_name} from GCP Secret Manager")
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.error(f"Failed to fetch secret {secret_name} from GCP Secret Manager: {e}")
            # Provide more specific error messages
            if "permission denied" in str(e).lower():
                logger.error("Permission denied. Check if the service account has Secret Manager Secret Accessor role.")
            elif "not found" in str(e).lower():
                logger.error(f"Secret {secret_name} not found in Secret Manager. Check if the secret exists.")
            elif "authentication" in str(e).lower():
                logger.error("Authentication failed. Check if GCP credentials are properly configured.")
            
            raise RuntimeError(f"Secret {secret_name} not found in environment variables or GCP Secret Manager")
    else:
        logger.info(f"GCP Secret Manager not enabled, but {secret_name} not found in environment variables")
        raise RuntimeError(f"Secret {secret_name} not found in environment variables")
