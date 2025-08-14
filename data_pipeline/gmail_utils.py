import base64  # Gmail API requires base64 encoding for messages
from email.mime.text import MIMEText
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import logging
from typing import Optional

try:
    from . import config
except ImportError:  # pragma: no cover - fallback when running as script
    import config  # type: ignore

logger = logging.getLogger(__name__)

# If modifying these SCOPES, delete token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


def get_gmail_service(
    credentials_path: Optional[str] = None,
    token_path: Optional[str] = None,
):
    """Return an authenticated Gmail API service instance.

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

    credentials_path = credentials_path or config.GMAIL_CREDENTIALS_FILE
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
                credentials_path, SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save credentials for next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    return service

def create_message(sender, to, subject, message_text):
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes())
    return {'raw': raw.decode()}

def send_message(service, user_id, message):
    try:
        message = service.users().messages().send(userId=user_id, body=message).execute()
        logger.info(f"Message Id: {message['id']}")
        return message
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return None

'''if __name__ == '__main__':
    service = get_gmail_service()
    sender = "raj.analystdata@gmail.com"
    to = "raj.analystdata@gmail.com"
    subject = "Test email from Gmail API"
    message_text = "Hello! This is a test email sent via Gmail API with OAuth2."
    
    msg = create_message(sender, to, subject, message_text)
    send_message(service, "me", msg)''' 
