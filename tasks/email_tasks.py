"""
Email task creation functions.
"""

from typing import List, Dict, Any
from crewai import Task, Agent

def create_email_tasks(emails: List[Dict[str, Any]], email_categorizer: Agent, notifier_agent: Agent) -> List[Task]:
    """
    Creates tasks for processing emails using a file-based approach.

    Args:
        emails: List of email dictionaries (only one email should be passed at a time)
        email_categorizer: Agent for categorizing emails
        notifier_agent: Agent for sending notifications

    Returns:
        List[Task]: List of tasks for processing emails
    """
    all_tasks = []
    email_details_for_notification = {}  # Store original email details for notification task

    # This function should be called with only one email at a time in the file-based approach
    for i, email_data in enumerate(emails):
        # Verify that the email file exists
        try:
            with open("current_email.txt", "r", encoding="utf-8") as file:
                # Just check if the file exists and has content
                if not file.read().strip():
                    print("Warning: current_email.txt exists but is empty")
        except Exception as e:
            print(f"Error reading from current_email.txt: {str(e)}")

        # Store details needed later
        email_details_for_notification[f"email_{i}"] = {
            "from": email_data['from'],
            "subject": email_data['subject']
        }

        # Task 1: Categorize the email
        categorize_task = Task(
            description=f"Analyze and categorize this email using the categorize_with_gemini tool. The email content is stored in the current_email.txt file. Do not pass any content to the tool, it will read from the file automatically.",
            agent=email_categorizer,
            expected_output="A structured string containing Priority, Category, Needs Response, Contains Tasks, and Summary."
        )

        # Task 2: Decide and potentially notify (depends on Task 1)
        # The context will include the result from categorize_task
        notify_task = Task(
            description=f"""Evaluate the categorization result for email (ID: email_{i}).

            Email details:
            From: {email_data['from']}
            Subject: {email_data['subject']}

            STRICT NOTIFICATION CRITERIA:
            - ONLY send a Telegram notification if the email is HIGH PRIORITY
            - OR if the email explicitly NEEDS A RESPONSE (regardless of priority)
            - NEVER send notifications for newsletters or promotional emails, even if they need a response
            - NEVER send notifications for low or medium priority emails unless they require a response AND are not newsletters or promotional emails

            If notification is needed: Construct a concise alert message using this exact format:
            "From: {email_data['from']}\nSubject: {email_data['subject']}\nPriority: [priority]\nCategory: [category]\nNeeds Response: [yes/no]\nSummary: [brief summary]"

            Then use the send_telegram_notification tool with this message.

            If no notification is needed: DO NOT use the send_telegram_notification tool at all. Simply state that no notification is needed and explain why.
            """,
            agent=notifier_agent,
            context=[categorize_task],  # Make this task dependent on the categorization task
            expected_output="A confirmation message stating whether a notification was sent or not, and why."
        )

        all_tasks.extend([categorize_task, notify_task])

    return all_tasks
