"""
Agents package for the email processing system.
Exports all agents used in the system.
"""

from .email_categorizer import create_email_categorizer
from .notifier import create_notifier_agent

__all__ = [
    'create_email_categorizer',
    'create_notifier_agent'
]
