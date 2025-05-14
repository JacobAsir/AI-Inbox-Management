"""
Email tools for fetching and processing emails.
"""

from typing import List, Dict, Any, Optional
import email
from email.header import decode_header
import imaplib
import re
from crewai.tools import tool

from config import GMAIL_USERNAME, GMAIL_APP_PASSWORD

def fetch_emails_func(limit=3) -> List[Dict[str, Any]] | str:
    """
    Fetches unread emails from Gmail using IMAP.
    Returns a list of email dictionaries or an error string.
    """
    try:
        # Configuration
        if not GMAIL_USERNAME or not GMAIL_APP_PASSWORD:
            return "Error: Gmail credentials not found in environment variables"

        print(f"Connecting to Gmail with username: {GMAIL_USERNAME}")

        # Connect to Gmail
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USERNAME, GMAIL_APP_PASSWORD)
        mail.select("inbox")

        # Search for unread emails
        _, messages = mail.search(None, "UNSEEN")
        email_ids = messages[0].split()

        print(f"Found {len(email_ids)} unread emails")

        # Limit number of emails to process
        email_ids = email_ids[-limit:] if limit and len(email_ids) > limit else email_ids

        emails = []
        for e_id in email_ids:
            _, msg_data = mail.fetch(e_id, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Extract email details
            subject = decode_header(msg["Subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode()
            sender = msg.get("From")
            date_str = msg.get("Date")

            # Get body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))

                    # Skip attachments
                    if "attachment" not in content_disposition and part.get_payload(decode=True):
                        if content_type == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode('utf-8') # Try UTF-8 first
                            except UnicodeDecodeError:
                                try:
                                    # Fallback to latin-1 if utf-8 fails
                                    body = part.get_payload(decode=True).decode('latin-1')
                                except UnicodeDecodeError:
                                    body = "Unable to decode email body (tried utf-8, latin-1)" # Placeholder if both fail
                            break # Found plain text body, stop searching parts
            else:
                 # Handle non-multipart emails
                if msg.get_payload(decode=True):
                    try:
                        body = msg.get_payload(decode=True).decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            body = msg.get_payload(decode=True).decode('latin-1')
                        except UnicodeDecodeError:
                            body = "Unable to decode email body (tried utf-8, latin-1)"

            email_data = {
                "id": e_id.decode(),
                "subject": subject,
                "from": sender,
                "date": date_str,
                "body": body[:1000]  # Truncate large emails
            }

            emails.append(email_data)
            print(f"Fetched email: {subject}")

        mail.close()
        mail.logout()

        return emails
    except Exception as e:
        return f"Error fetching emails: {str(e)}"

def create_gmail_label(label_name: str) -> bool:
    """
    Creates a new label in Gmail if it doesn't exist.

    Args:
        label_name: The name of the label to create

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Connect to Gmail
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USERNAME, GMAIL_APP_PASSWORD)

        # Format label name for IMAP (replace slashes with dots)
        imap_label_name = label_name.replace('/', '.')

        # List all labels
        _, labels = mail.list()

        # Check if label already exists
        label_exists = False
        for label in labels:
            label_str = label.decode('utf-8') if isinstance(label, bytes) else str(label)
            if imap_label_name in label_str:
                label_exists = True
                print(f"Label already exists: {label_name}")
                break

        # Create label if it doesn't exist
        if not label_exists:
            try:
                result = mail.create(f'"{imap_label_name}"')
                print(f"Created label: {label_name}, Result: {result}")
            except Exception as create_error:
                # Try alternative format if the first attempt fails
                try:
                    result = mail.create(imap_label_name)
                    print(f"Created label (alt method): {label_name}, Result: {result}")
                except Exception as alt_error:
                    print(f"Both label creation methods failed: {str(create_error)} | {str(alt_error)}")
                    return False

        mail.logout()
        return True
    except Exception as e:
        print(f"Error creating label {label_name}: {str(e)}")
        return False

def apply_gmail_label(email_id: str, label_name: str) -> bool:
    """
    Applies a label to an email in Gmail.

    Args:
        email_id: The ID of the email to label
        label_name: The name of the label to apply

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Connect to Gmail
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USERNAME, GMAIL_APP_PASSWORD)
        mail.select("inbox")

        # Make sure the label exists
        create_gmail_label(label_name)

        # Format label name for IMAP (replace slashes with dots)
        imap_label_name = label_name.replace('/', '.')

        # Apply the label
        try:
            result = mail.store(email_id.encode(), '+X-GM-LABELS', f'({imap_label_name})')
            print(f"Applied label '{label_name}' to email {email_id}, Result: {result}")
        except Exception as store_error:
            # Try alternative format if the first attempt fails
            try:
                result = mail.store(email_id.encode(), '+X-GM-LABELS', imap_label_name)
                print(f"Applied label (alt method) '{label_name}' to email {email_id}, Result: {result}")
            except Exception as alt_error:
                print(f"Both label application methods failed: {str(store_error)} | {str(alt_error)}")
                return False

        mail.close()
        mail.logout()
        return True
    except Exception as e:
        print(f"Error applying label {label_name} to email {email_id}: {str(e)}")
        return False

def apply_categorization_labels(email_id: str, categorization: str) -> bool:
    """
    Applies appropriate labels based on email categorization.

    Args:
        email_id: The ID of the email
        categorization: The categorization result string

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Parse categorization
        priority = "Unknown"
        category = "Unknown"
        needs_response = "Unknown"

        for line in categorization.split('\n'):
            if line.startswith("Priority:"):
                priority = line.replace("Priority:", "").strip()
            elif line.startswith("Category:"):
                category = line.replace("Category:", "").strip()
            elif line.startswith("Needs Response:"):
                needs_response = line.replace("Needs Response:", "").strip()

        # Create and apply priority label
        priority_label = f"Priority/{priority}"
        apply_gmail_label(email_id, priority_label)

        # Create and apply category label
        category_label = f"Category/{category}"
        apply_gmail_label(email_id, category_label)

        # Create and apply response label if needed
        if needs_response.lower() == "yes":
            apply_gmail_label(email_id, "Needs_Response")

        return True
    except Exception as e:
        print(f"Error applying categorization labels to email {email_id}: {str(e)}")
        return False

@tool
def fetch_emails(limit=3) -> List[Dict[str, Any]] | str:
    """Fetches unread emails from Gmail using IMAP."""
    return fetch_emails_func(limit)

@tool
def apply_labels(email_id: str, categorization: str) -> str:
    """Applies Gmail labels based on email categorization."""
    success = apply_categorization_labels(email_id, categorization)
    if success:
        return f"Successfully applied labels to email {email_id}"
    else:
        return f"Failed to apply labels to email {email_id}"
