from crewai import Agent, Task, Crew
from crewai.tools import BaseTool, tool
from typing import List, Dict, Any, Optional
import base64
import requests
import os
from dotenv import load_dotenv # Moved import to the top
import email
from email.header import decode_header
import imaplib
import time
from groq import Groq

# Load environment variables
load_dotenv()

# Initialize Groq client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)

# ================== TOOLS ==================

# Define our functions first
def fetch_emails_func(limit=5) -> List[Dict[str, Any]] | str:
    """
    Fetches unread emails from Gmail using IMAP.
    Returns a list of email dictionaries or an error string.
    """
    try:
        # Configuration
        GMAIL_USERNAME = os.getenv("GMAIL_USERNAME")
        GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

        if not GMAIL_USERNAME or not GMAIL_APP_PASSWORD:
            return "Error: Gmail credentials not found in environment variables"

        print(f"Connecting to Gmail with username: {GMAIL_USERNAME}")

        # Connect to Gmail
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USERNAME, GMAIL_APP_PASSWORD)
        mail.select("inbox")

        # Search for unread emails
        status, messages = mail.search(None, "UNSEEN")
        email_ids = messages[0].split()

        print(f"Found {len(email_ids)} unread emails")

        # Limit number of emails to process
        email_ids = email_ids[-limit:] if limit and len(email_ids) > limit else email_ids

        emails = []
        for e_id in email_ids:
            status, msg_data = mail.fetch(e_id, "(RFC822)")
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

def send_telegram_notification_func(message: str):
    """
    Sends a message to Telegram using a bot.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        return "Error: Telegram credentials not found in environment variables"

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    try:
        payload = {"chat_id": chat_id, "text": message}
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        return f"Error sending notification: {str(e)}"

def categorize_with_groq_func(email_content: str) -> str:
    """
    Categorize an email using Groq's LLama model.
    Returns the categorization result as a string.
    """
    try:
        # Fallback categorization in case of rate limits
        if len(email_content) > 1000:
            email_content = email_content[:1000] + "..." # Truncate long emails

        # Check for common keywords to provide basic categorization if API fails
        lower_content = email_content.lower()

        # Try to use the API first
        try:
            prompt = f"""Analyze this email and categorize it:

            {email_content}

            1. Determine the priority (High, Medium, Low)
            2. Categorize the type (Personal, Work, Promotional, Newsletter, GitHub, YouTube, Receipts_Invoices, Other)
               - Use GitHub for any GitHub-related notifications or updates
               - Use YouTube for YouTube notifications and subscriptions
               - Use Receipts_Invoices for any receipts, invoices, or financial documents
            3. Indicate if it needs a response (Yes/No)
            4. If it contains task-related content (Yes/No)
            5. Provide a 1-2 sentence summary

            Format your response as:
            Priority: [priority]
            Category: [category]
            Needs Response: [yes/no]
            Contains Tasks: [yes/no]
            Summary: [brief summary]
            """

            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # Using the more powerful model for categorization
                messages=[
                    {"role": "system", "content": "You are an email categorization assistant. Analyze emails and categorize them accurately."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Lower temperature for more consistent results
                max_tokens=500
            )

            return completion.choices[0].message.content

        except Exception as api_error:
            print(f"API error: {str(api_error)}. Using fallback categorization.")

            # Fallback categorization logic
            priority = "Low"  # Default to low priority
            category = "Other"  # Default category
            needs_response = "No"  # Default to no response needed
            contains_tasks = "No"  # Default to no tasks
            summary = "Unable to fully analyze due to API limits. Basic categorization provided."

            # Simple keyword-based categorization
            if any(word in lower_content for word in ["urgent", "important", "asap", "deadline", "emergency"]):
                priority = "High"
                needs_response = "Yes"

            if any(word in lower_content for word in ["newsletter", "subscribe", "update", "weekly", "monthly"]):
                category = "Newsletter"
            elif any(word in lower_content for word in ["github", "commit", "pull request", "issue", "repository"]):
                category = "GitHub"
            elif any(word in lower_content for word in ["youtube", "video", "channel", "subscribe"]):
                category = "YouTube"
            elif any(word in lower_content for word in ["receipt", "invoice", "payment", "order", "purchase"]):
                category = "Receipts_Invoices"
            elif any(word in lower_content for word in ["offer", "discount", "sale", "promotion", "deal"]):
                category = "Promotional"
            elif any(word in lower_content for word in ["job", "interview", "application", "career", "position"]):
                category = "Work"

            if any(word in lower_content for word in ["please respond", "let me know", "reply", "get back to me"]):
                needs_response = "Yes"

            if any(word in lower_content for word in ["task", "todo", "to-do", "action item", "assignment"]):
                contains_tasks = "Yes"

            # Create a formatted response similar to what the API would return
            return f"Priority: {priority}\nCategory: {category}\nNeeds Response: {needs_response}\nContains Tasks: {contains_tasks}\nSummary: {summary}"
    except Exception as e:
        return f"Error categorizing email with Groq: {str(e)}"

# Now create CrewAI tools using the decorator
@tool
def fetch_emails(limit=5) -> List[Dict[str, Any]] | str:
    """Fetches unread emails from Gmail using IMAP."""
    return fetch_emails_func(limit)

@tool
def categorize_with_groq(email_content: str) -> str:
    """Categorize an email using Groq's LLama model."""
    return categorize_with_groq_func(email_content)

@tool
def send_telegram_notification(message: str):
    """Sends a message to Telegram using a bot."""
    return send_telegram_notification_func(message)

# ================== AGENTS ==================

# Using the more powerful model for complex categorization tasks
email_categorizer = Agent(
    role="Email Categorizer",
    goal="Analyze email content and determine the category, priority, and required actions.",
    backstory="An LLM trained to understand emails and smartly tag them into meaningful categories with appropriate priority levels, identifying necessary responses and tasks.",
    tools=[categorize_with_groq],
    verbose=True,
    llm="groq/llama-3.3-70b-versatile"
)

# Using the lighter model for simpler notification tasks
notifier_agent = Agent(
    role="Notification Agent",
    goal="Evaluate email categorization results and ONLY notify the user via Telegram for HIGH PRIORITY emails OR emails that explicitly NEED A RESPONSE. Do not send notifications for low or medium priority emails unless they specifically require a response.",
    backstory="A strict gatekeeper that only alerts the user about truly urgent matters. You understand that notifications should be rare and reserved only for emails that genuinely require immediate attention. You never send notifications for promotional emails, newsletters, or any non-urgent content.",
    tools=[send_telegram_notification], # Tool to send notification
    verbose=True,
    llm="groq/llama-3.1-8b-instant"
)

# ================== TASKS ==================

# Task definitions remain largely the same, but we'll create them differently in the main block

# ================== MAIN EXECUTION ==================

if __name__ == "__main__":
    try:
        # Check if Groq API key is available
        if not GROQ_API_KEY:
            print("Error: GROQ_API_KEY not found in environment variables")
            exit(1)

        print("Fetching emails...")
        emails = fetch_emails_func(limit=int(os.getenv("EMAIL_BATCH_SIZE", 5))) # Use limit from env or default 5

        if isinstance(emails, str) and emails.startswith("Error"):
            print(emails)
            exit(1)
        elif not emails: # Added check for empty list
             print("No unread emails found.")
             exit(0)
        else:
            print(f"Fetched {len(emails)} emails. Starting analysis...")
            all_tasks = []
            email_details_for_notification = {} # Store original email details for notification task

            for i, email_data in enumerate(emails):
                email_content = f"""
From: {email_data['from']}
Subject: {email_data['subject']}
Date: {email_data['date']}
Body: {email_data['body']}
"""
                # Store details needed later
                email_details_for_notification[f"email_{i}"] = {
                    "from": email_data['from'],
                    "subject": email_data['subject']
                }

                # Task 1: Categorize the email
                categorize_task = Task(
                    description=f"Analyze and categorize this email (ID: email_{i}) using the categorize_with_groq tool:\n\n{email_content}",
                    agent=email_categorizer,
                    expected_output="A structured string containing Priority, Category, Needs Response, Contains Tasks, and Summary."
                )

                # Task 2: Decide and potentially notify (depends on Task 1)
                # The context will include the result from categorize_task
                notify_task = Task(
                    description=f"""Evaluate the categorization result for email (ID: email_{i}).

                    STRICT NOTIFICATION CRITERIA:
                    - ONLY send a Telegram notification if the email is HIGH PRIORITY
                    - OR if the email explicitly NEEDS A RESPONSE (regardless of priority)
                    - NEVER send notifications for newsletters or promotional emails
                    - NEVER send notifications for low or medium priority emails unless they require a response

                    If notification is needed: Construct a concise alert message including From, Subject, Priority, Category, Needs Response, and Summary, then use the send_telegram_notification tool.

                    If no notification is needed: DO NOT use the send_telegram_notification tool at all. Simply state that no notification is needed and explain why.
                    """,
                    agent=notifier_agent,
                    context=[categorize_task], # Make this task dependent on the categorization task
                    expected_output="A confirmation message stating whether a notification was sent or not, and why."
                )

                all_tasks.extend([categorize_task, notify_task])

            # Create and run the crew
            crew = Crew(
                agents=[email_categorizer, notifier_agent],
                tasks=all_tasks,
                verbose=True
            )

            try:
                print("Running Crew...")
                results = crew.kickoff()

                print("\n--- Crew Run Finished ---")
                print("Results:")
                # The results list now contains outputs from all tasks (categorization and notification decisions)
                # We can print them, but the notification action itself is handled by the notifier_agent within the crew run.
                for result in results:
                     print(result) # Print the output of each task (categorization and notification decision)
            except Exception as crew_error:
                if "rate_limit" in str(crew_error).lower():
                    print("\n--- Rate limit reached ---")
                    print("The Groq API rate limit has been reached. Please try again later or upgrade your plan.")
                    print("Some emails may not have been processed due to this limitation.")
                else:
                    print(f"\n--- Error running crew: {str(crew_error)} ---")

    except Exception as e:
        print(f"Error in email pipeline: {str(e)}")
