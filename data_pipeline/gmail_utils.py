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

# If modifying these SCOPES, delete token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


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

    credentials_path = credentials_path or _get_credentials_path()
    token_path = token_path or config.GMAIL_TOKEN_FILE

    if not os.path.exists(credentials_path):
        raise FileNotFoundError(
            f"Gmail credentials file not found at {credentials_path}. "
            "Set the correct path via parameters or the GMAIL_CREDENTIALS_FILE environment variable."
        )

    creds = None
    # token.json stores user's access and refresh tokens.
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    # If there are no valid credentials, log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
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
                    creds = flow.run_local_server(port=0)
            else:
                creds = flow.run_local_server(port=0)
        # Save credentials for next run
        with open(token_path, "w") as token:
            token.write(creds.to_json())

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
    """Send ``message`` using the Gmail API service."""
    try:
        message = service.users().messages().send(
            userId=user_id, body=message).execute()
        logger.info(f"Message Id: {message['id']}")
        return message
    except Exception as e:  # pragma: no cover - network errors
        logger.error(f"An error occurred: {e}")
        return None


if __name__ == "__main__":
    service = get_gmail_service()
    sender = "raj.analystdata@gmail.com"
    to = "raj.analystdata@gmail.com"
    subject = "Test email from Gmail API"
    message_text = "Hello! This is a test email sent via Gmail API with OAuth2."

    msg = create_message(sender, to, subject, message_text)
    send_message(service, "me", msg)
