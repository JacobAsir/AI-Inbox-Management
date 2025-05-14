"""
Email categorizer agent for analyzing and categorizing emails.
"""

from crewai import Agent

from tools import categorize_with_gemini
from config import CATEGORIZER_MODEL

def create_email_categorizer() -> Agent:
    """
    Creates and returns an email categorizer agent.

    This agent is responsible for analyzing email content and determining
    the category, priority, and required actions.

    Returns:
        Agent: The email categorizer agent
    """
    return Agent(
        role="Email Categorizer",
        goal="Analyze email content and determine the category, priority, and required actions.",
        backstory="An LLM trained to understand emails and smartly tag them into meaningful categories with appropriate priority levels, identifying necessary responses and tasks.",
        tools=[categorize_with_gemini],
        verbose=True,
        # Using Gemini model for categorization
        llm=f"gemini/{CATEGORIZER_MODEL}"
    )
