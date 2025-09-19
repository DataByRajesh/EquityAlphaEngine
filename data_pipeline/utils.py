import logging
import os

# Set gRPC to use ares resolver for better IPv6 support
os.environ.setdefault("GRPC_DNS_RESOLVER", "ares")
os.environ.setdefault("GRPC_EXPERIMENTAL_ENABLE_ARES_DNS_RESOLVER", "true")

from google.cloud import secretmanager

import data_pipeline.config as config

logger = logging.getLogger(__name__)


def get_secret(secret_name: str) -> str:
    """Fetch a secret value from Google Cloud Secret Manager, with fallback to environment variables."""
    # First, try to get from environment variable (for local development)
    env_value = os.environ.get(secret_name)
    if env_value:
        logger.debug(f"Using {secret_name} from environment variable")
        return env_value

    # If not in env, try GCP Secret Manager
    # Set GOOGLE_APPLICATION_CREDENTIALS if not set and credentials file exists
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        creds_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "Downloads", "client_secret_2_248891289968-44j05tt7cjtfbkpc77svs3diqe8tr9fr.apps.googleusercontent.com.json")
        if os.path.exists(creds_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
            logger.debug(f"Set GOOGLE_APPLICATION_CREDENTIALS to {creds_path}")
        else:
            logger.warning("GCP credentials file not found, GCP operations may fail")

    client = secretmanager.SecretManagerServiceClient()
    try:
        project_id = config.GCP_PROJECT_ID  # Fetch project_id from config
        # Debug log for project_id
        logger.debug(f"Using project_id: {project_id}")
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error(f"Failed to fetch secret {secret_name} from GCP Secret Manager: {e}")
        raise RuntimeError(f"Secret {secret_name} not found in environment variables or GCP Secret Manager")
