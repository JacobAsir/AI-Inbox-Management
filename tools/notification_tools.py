"""
Notification tools for sending alerts via Telegram.
"""

import requests
from crewai.tools import tool

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def send_telegram_notification_func(message: str):
    """
    Sends a message to Telegram using a bot.
    """
    bot_token = TELEGRAM_BOT_TOKEN
    chat_id = TELEGRAM_CHAT_ID
    
    if not bot_token or not chat_id:
        return "Error: Telegram credentials not found in environment variables"
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    try:
        payload = {"chat_id": chat_id, "text": message}
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        return f"Error sending notification: {str(e)}"

@tool
def send_telegram_notification(message: str):
    """Sends a message to Telegram using a bot."""
    return send_telegram_notification_func(message)
