import base64  # Gmail API requires base64 encoding for messages
import logging
import os
import tempfile
from email.mime.text import MIMEText
from typing import Optional

from google.auth.transport.requests import Request
from google.cloud import storage
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

try:
    from google.cloud import secretmanager
except ImportError:
    secretmanager = None

# Updated local imports to use fallback mechanism
try:
    from . import config
except ImportError:
    import data_pipeline.config as config

logger = logging.getLogger(__name__)

# Suppress specific gRPC warnings when not running on GCP (only affects this module)
import warnings
warnings.filterwarnings("ignore", message=".*ALTS creds ignored.*")

# If modifying these SCOPES, delete token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# Gmail authentication configuration
USE_SECRET_MANAGER = os.environ.get("USE_GCP_SECRET_MANAGER", "false").lower() == "true"

def _get_secret_from_manager(secret_name: str) -> Optional[str]:
    """Get secret from Google Cloud Secret Manager."""
    if not USE_SECRET_MANAGER or not secretmanager:
        return None
    
    try:
        from data_pipeline.utils import get_secret
        return get_secret(secret_name).strip()
    except Exception as e:
        logger.warning(f"Failed to fetch {secret_name} from Secret Manager: {e}")
        return None

def _get_oauth_token_from_secret_manager() -> Optional[str]:
    """Get OAuth token from Secret Manager if available."""
    token_secret = _get_secret_from_manager("GMAIL_OAUTH_TOKEN")
    if token_secret:
        logger.info("Retrieved OAuth token from Secret Manager")
        return token_secret
    return None

def _save_oauth_token_to_secret_manager(token_json: str) -> bool:
    """Save OAuth token to Secret Manager if configured."""
    if not USE_SECRET_MANAGER or not secretmanager:
        return False
    
    try:
        client = secretmanager.SecretManagerServiceClient()
        parent = f"projects/{config.GCP_PROJECT_ID}"
        secret_id = "GMAIL_OAUTH_TOKEN"
        
        # Try to create the secret first (will fail if it exists)
        try:
            secret = {"replication": {"automatic": {}}}
            client.create_secret(
                request={"parent": parent, "secret_id": secret_id, "secret": secret}
            )
            logger.info(f"Created new secret: {secret_id}")
        except Exception:
            # Secret already exists, which is fine
            pass
        
        # Add the secret version
        secret_name = f"{parent}/secrets/{secret_id}"
        payload = token_json.encode("UTF-8")
        client.add_secret_version(
            request={"parent": secret_name, "payload": {"data": payload}}
        )
        logger.info("Saved OAuth token to Secret Manager")
        return True
    except Exception as e:
        logger.warning(f"Failed to save OAuth token to Secret Manager: {e}")
        return False


def _get_credentials_path():
    """Get the path to the Gmail credentials file, fetching from GCS or Secret Manager if configured."""
    # Check for GCS path
    gcs_path = os.environ.get("GMAIL_CREDENTIALS_GCS_PATH")
    if gcs_path:
        logger.info("Fetching Gmail credentials from GCS.")
        try:
            client = storage.Client()
            bucket_name, blob_name = gcs_path.split("/", 1)
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
            blob.download_to_file(temp_file)
            temp_file.close()
            return temp_file.name
        except Exception as e:
            logger.error(f"Failed to fetch credentials from GCS: {e}")
            raise

    # Check for Secret Manager
    secret_name = os.environ.get("GMAIL_CREDENTIALS_SECRET_NAME")
    if secret_name and secretmanager:
        logger.info("Fetching Gmail credentials from Secret Manager.")
        try:
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{config.GCP_PROJECT_ID}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            payload = response.payload.data.decode("UTF-8")
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w")
            temp_file.write(payload)
            temp_file.close()
            return temp_file.name
        except Exception as e:
            logger.error(f"Failed to fetch credentials from Secret Manager: {e}")
            raise

    # Default to local file
    return config.GMAIL_CREDENTIALS_FILE


def get_gmail_service(
    credentials_path: Optional[str] = None,
    token_path: Optional[str] = None,
):
    """Return an authenticated Gmail API service instance.

    Supports both OAuth2 and Service Account authentication.
    For Service Account, set GMAIL_SERVICE_ACCOUNT_KEY_PATH or use Secret Manager.
    Requires domain-wide delegation for service account to send emails.

    In headless environments set the ``HEADLESS`` environment variable (or
    leave ``DISPLAY`` unset) to authenticate via the console instead of
    opening a browser.

    Parameters
    ----------
    credentials_path:
        Path to the OAuth2 client secrets JSON file. Defaults to
        ``config.GMAIL_CREDENTIALS_FILE``.
    token_path:
        Path to the stored user token. Defaults to
        ``config.GMAIL_TOKEN_FILE``.

    Raises
    ------
    FileNotFoundError
        If the credentials file does not exist.
    """

    # Check for service account key
    service_account_key_path = os.environ.get("GMAIL_SERVICE_ACCOUNT_KEY_PATH")
    if service_account_key_path:
        logger.info("Using Service Account authentication for Gmail.")
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_file(
            service_account_key_path, scopes=SCOPES)
        # For domain-wide delegation, impersonate the user
        user_email = os.environ.get("GMAIL_USER_EMAIL", "raj.analystdata@gmail.com")
        creds = creds.with_subject(user_email)
        service = build("gmail", "v1", credentials=creds)
        return service

    # Check for service account from Secret Manager
    secret_name = os.environ.get("GMAIL_SERVICE_ACCOUNT_SECRET_NAME")
    if secret_name and secretmanager:
        logger.info("Fetching Service Account key from Secret Manager for Gmail.")
        try:
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{config.GCP_PROJECT_ID}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            key_data = response.payload.data.decode("UTF-8")
            from google.oauth2 import service_account
            import json
            key_dict = json.loads(key_data)
            creds = service_account.Credentials.from_service_account_info(
                key_dict, scopes=SCOPES)
            # For domain-wide delegation, impersonate the user
            user_email = os.environ.get("GMAIL_USER_EMAIL", "raj.analystdata@gmail.com")
            creds = creds.with_subject(user_email)
            service = build("gmail", "v1", credentials=creds)
            return service
        except Exception as e:
            logger.error(f"Failed to use Service Account from Secret Manager: {e}")
            raise

    # Fallback to OAuth2
    credentials_path = credentials_path or _get_credentials_path()
    token_path = token_path or config.GMAIL_TOKEN_FILE

    if not os.path.exists(credentials_path):
        raise FileNotFoundError(
            f"Gmail credentials file not found at {credentials_path}. "
            "Set the correct path via parameters or the GMAIL_CREDENTIALS_FILE environment variable."
        )

    creds = None
    
    # Try to get OAuth token from Secret Manager first
    if USE_SECRET_MANAGER:
        token_json = _get_oauth_token_from_secret_manager()
        if token_json:
            try:
                import json
                token_info = json.loads(token_json)
                creds = Credentials.from_authorized_user_info(token_info, SCOPES)
                logger.info("Loaded OAuth credentials from Secret Manager")
            except Exception as e:
                logger.warning(f"Failed to load OAuth token from Secret Manager: {e}")
    
    # Fallback to local token file if Secret Manager not available or failed
    if not creds and os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        logger.info("Loaded OAuth credentials from local file")
    
    # If there are no valid credentials, log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired OAuth credentials")
            creds.refresh(Request())
            # Save refreshed token
            token_json = creds.to_json()
            if USE_SECRET_MANAGER:
                _save_oauth_token_to_secret_manager(token_json)
            with open(token_path, "w") as token:
                token.write(token_json)
        else:
            logger.info("Starting OAuth2 authentication flow")
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES)
            headless = os.environ.get("HEADLESS", "").lower() in {
                "1", "true", "yes"}
            if headless or not os.environ.get("DISPLAY"):
                # Use run_console for headless environments
                try:
                    creds = flow.run_console()
                except AttributeError:
                    # Fallback for older versions of google-auth-oauthlib
                    logger.warning("run_console not available, using run_local_server")
                    try:
                        creds = flow.run_local_server(port=0)
                    except Exception as e:
                        if "could not locate runnable browser" in str(e).lower():
                            logger.error("No runnable browser available for Gmail authentication in headless environment. Please use Service Account authentication or provide credentials.")
                            raise RuntimeError("Browser authentication not available in headless environment") from e
                        else:
                            raise
            else:
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            token_json = creds.to_json()
            if USE_SECRET_MANAGER:
                _save_oauth_token_to_secret_manager(token_json)
            with open(token_path, "w") as token:
                token.write(token_json)
            logger.info("OAuth2 authentication completed and credentials saved")

    service = build("gmail", "v1", credentials=creds)
    return service


def create_message(sender, to, subject, message_text):
    """Create a base64-encoded email ready for the Gmail API."""
    message = MIMEText(message_text)
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes())
    return {"raw": raw.decode()}


def send_message(service, user_id, message):
    """Send ``message`` using the Gmail API service.
    
    Returns:
        dict: Message object with ID if successful, None if failed
    """
    try:
        if service is None:
            logger.error("Gmail service is None - cannot send message")
            return None
            
        if not message or not message.get('raw'):
            logger.error("Invalid message format - missing 'raw' field")
            return None
            
        result = service.users().messages().send(
            userId=user_id, body=message).execute()
        logger.info(f"Email sent successfully. Message ID: {result.get('id', 'unknown')}")
        return result
        
    except Exception as e:  # pragma: no cover - network errors
        error_msg = str(e)
        logger.error(f"Failed to send email: {error_msg}")
        
        # Log specific error types for better debugging
        if "authentication" in error_msg.lower():
            logger.error("Gmail authentication failed. Check credentials and permissions.")
        elif "quota" in error_msg.lower():
            logger.error("Gmail API quota exceeded. Try again later.")
        elif "permission" in error_msg.lower():
            logger.error("Insufficient permissions for Gmail API. Check OAuth scopes.")
        elif "network" in error_msg.lower() or "connection" in error_msg.lower():
            logger.error("Network connectivity issue. Check internet connection.")
        else:
            logger.error(f"Unexpected Gmail API error: {error_msg}")
            
        return None


if __name__ == "__main__":
    service = get_gmail_service()
    sender = "raj.analystdata@gmail.com"
    to = "raj.analystdata@gmail.com"
    subject = "Test email from Gmail API"
    message_text = "Hello! This is a test email sent via Gmail API with OAuth2."

    msg = create_message(sender, to, subject, message_text)
    send_message(service, "me", msg)
