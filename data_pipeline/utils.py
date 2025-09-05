import logging
from google.cloud import secretmanager
import data_pipeline.config as config

logger = logging.getLogger(__name__)

def get_secret(secret_name: str) -> str:
    """Fetch a secret value from Google Cloud Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    try:
        project_id = config.GCP_PROJECT_ID  # Fetch project_id from config
        logger.debug(f"Using project_id: {project_id}")  # Debug log for project_id
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error(f"Failed to fetch secret {secret_name}: {e}")
        raise
