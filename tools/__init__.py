"""
Tools package for the email processing system.
Exports all tools used by agents.
"""

from .email_tools import fetch_emails, apply_labels
from .notification_tools import send_telegram_notification
from .categorization_tools import categorize_with_groq, categorize_with_gemini

__all__ = [
    'fetch_emails',
    'send_telegram_notification',
    'categorize_with_groq',
    'categorize_with_gemini',
    'apply_labels'
]
