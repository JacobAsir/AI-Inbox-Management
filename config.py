"""
Configuration module for the email processing system.
Handles environment variables and global settings.
"""

import os
from dotenv import load_dotenv
from groq import Groq
import google.generativeai as genai

# Load environment variables
load_dotenv()

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Groq client
groq_client = Groq(api_key=GROQ_API_KEY)

# Initialize Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # Initialize the Gemini model
    gemini_model = genai.GenerativeModel(model_name="gemini-2.5-flash-preview-04-17")
else:
    gemini_model = None

# Email Settings
GMAIL_USERNAME = os.getenv("GMAIL_USERNAME")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
EMAIL_BATCH_SIZE = int(os.getenv("EMAIL_BATCH_SIZE", 3))

# Telegram Settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Model Settings
CATEGORIZER_MODEL = "gemini-2.5-flash-preview-04-17"  # Using Gemini for categorization
NOTIFIER_MODEL = "llama-3.3-70b-versatile"  # Still using Groq for notifications

# Notification Settings
# Define criteria for when to send notifications
NOTIFICATION_CRITERIA = {
    "high_priority": True,  # Always notify for high priority
    "needs_response": True,  # Always notify if response needed
    "medium_priority_needs_response": True,  # Notify for medium priority if response needed
    "low_priority_needs_response": False,  # Don't notify for low priority even if response needed
}
