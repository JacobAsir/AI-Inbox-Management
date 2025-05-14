"""
Notification agent for deciding when to send alerts.
"""

from crewai import Agent

from tools import send_telegram_notification
from config import NOTIFIER_MODEL

def create_notifier_agent() -> Agent:
    """
    Creates and returns a notification agent.

    This agent is responsible for evaluating email categorization results
    and deciding whether to notify the user via Telegram.

    Returns:
        Agent: The notification agent
    """
    return Agent(
        role="Notification Agent",
        goal="Evaluate email categorization results and ONLY notify the user via Telegram for HIGH PRIORITY emails OR emails that explicitly NEED A RESPONSE. NEVER send notifications for newsletters or promotional emails under any circumstances. Do not send notifications for low or medium priority emails unless they specifically require a response AND are not newsletters or promotional emails.",
        backstory="A very strict gatekeeper that only alerts the user about truly urgent matters. You understand that notifications should be rare and reserved only for emails that genuinely require immediate attention. You NEVER send notifications for promotional emails or newsletters, even if they need a response. You filter out all non-urgent content to prevent notification fatigue.",
        tools=[send_telegram_notification],
        verbose=True,
        llm=f"groq/{NOTIFIER_MODEL}"
    )
