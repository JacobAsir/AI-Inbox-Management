"""
Main execution script for the email processing system.
"""

import os
import time
import imaplib
from crewai import Crew, Task

from config import GROQ_API_KEY, EMAIL_BATCH_SIZE, GMAIL_USERNAME, GMAIL_APP_PASSWORD
from tools.email_tools import fetch_emails_func
from agents import create_email_categorizer, create_notifier_agent
from tasks import create_email_tasks
from utils import write_email_to_file, read_email_from_file, clear_email_file, extract_email_details

def main():
    """
    Main execution function for the email processing system.
    """
    try:
        # Initialize stats dictionary
        stats = {
            "total": 0,
            "priority": {"High": 0, "Medium": 0, "Low": 0, "Unknown": 0},
            "category": {"Personal": 0, "Work": 0, "Promotional": 0, "Newsletter": 0,
                        "GitHub": 0, "YouTube": 0, "Receipts_Invoices": 0, "Other": 0, "Unknown": 0},
            "needs_response": {"Yes": 0, "No": 0, "Unknown": 0},
            "direct_categorization": []
        }

        # Check if API keys are available
        if not GROQ_API_KEY:
            print("Error: GROQ_API_KEY not found in environment variables")
            exit(1)

        from config import GEMINI_API_KEY
        if not GEMINI_API_KEY:
            print("Error: GEMINI_API_KEY not found in environment variables")
            exit(1)

        # Check if email file exists and clear it
        email_file_path = "current_email.txt"
        clear_email_file(email_file_path)

        # Create agents
        email_categorizer = create_email_categorizer()
        notifier_agent = create_notifier_agent()

        print("Fetching emails...")
        emails = fetch_emails_func(limit=EMAIL_BATCH_SIZE)

        if isinstance(emails, str) and emails.startswith("Error"):
            print(emails)
            exit(1)
        elif not emails:  # Added check for empty list
            print("No unread emails found.")
            exit(0)
        else:
            print(f"Fetched {len(emails)} emails. Starting analysis...")

            # Process one email at a time using file-based approach with agents
            for i, email_data in enumerate(emails):
                print(f"\nProcessing email {i+1} of {len(emails)}...")
                print(f"Subject: {email_data['subject']}")

                # Step 1: Write email to file
                print(f"Writing email {i+1} to file...")
                if not write_email_to_file(email_data, email_file_path):
                    print(f"Error writing email {i+1} to file. Skipping.")
                    continue

                # Step 2: Read email from file
                email_content = read_email_from_file(email_file_path)
                if not email_content:
                    print(f"Error reading email {i+1} from file. Skipping.")
                    continue

                # Step 3: Create tasks for this email
                print(f"Creating tasks for email {i+1}...")
                single_email_tasks = create_email_tasks([email_data], email_categorizer, notifier_agent)

                # Step 4: Create and run the crew for this email
                crew = Crew(
                    agents=[email_categorizer, notifier_agent],
                    tasks=single_email_tasks,
                    verbose=True
                )

                try:
                    print(f"Running Crew for email {i+1}...")
                    results = crew.kickoff()

                    print(f"\n--- Email {i+1} Processing Finished ---")
                    print(f"Email {i+1} processed successfully.")

                    # Print a summary of the results and apply labels
                    for j, result in enumerate(results):
                        if j == 0:  # First result is categorization
                            print(f"Categorization result:\n{result}")

                            # Store categorization for statistics
                            stats["direct_categorization"].append({
                                "subject": email_data['subject'],
                                "result": result
                            })

                            # Apply labels based on categorization
                            from tools.email_tools import apply_categorization_labels
                            # Convert tuple to string if needed
                            if isinstance(result, tuple):
                                result_str = result[1] if len(result) > 1 and result[1] is not None else str(result[0])
                            else:
                                result_str = str(result)

                            label_result = apply_categorization_labels(email_data['id'], result_str)
                            print(f"Label application result: {label_result}")

                        elif j == 1:  # Second result is notification decision
                            print(f"Notification decision:\n{result}")

                except Exception as crew_error:
                    error_msg = str(crew_error).lower()
                    if "rate_limit" in error_msg or "quota" in error_msg or "429" in error_msg:
                        print(f"\n--- Rate limit reached on email {i+1} ---")
                        print("The API rate limit has been reached. Please try again later.")
                        print("Using fallback categorization...")

                        # Read the email content from file
                        email_content = read_email_from_file(email_file_path)
                        if email_content:
                            # Extract basic info
                            from tools.categorization_tools import categorize_with_gemini_func
                            result = categorize_with_gemini_func(email_content)
                            print(f"Fallback categorization result:\n{result}")

                            # Check if notification is needed based on fallback categorization
                            priority = "Low"
                            category = "Other"
                            needs_response = "No"
                            summary = ""

                            for line in result.split('\n'):
                                if line.startswith("Priority:"):
                                    priority = line.replace("Priority:", "").strip()
                                elif line.startswith("Category:"):
                                    category = line.replace("Category:", "").strip()
                                elif line.startswith("Needs Response:"):
                                    needs_response = line.replace("Needs Response:", "").strip()
                                elif line.startswith("Summary:"):
                                    summary = line.replace("Summary:", "").strip()

                            # Store categorization for statistics
                            stats["direct_categorization"].append({
                                "subject": email_data['subject'],
                                "result": result
                            })

                            # Apply labels based on categorization
                            from tools.email_tools import apply_categorization_labels
                            # Convert tuple to string if needed
                            if isinstance(result, tuple):
                                result_str = result[1] if len(result) > 1 and result[1] is not None else str(result[0])
                            else:
                                result_str = str(result)

                            label_result = apply_categorization_labels(email_data['id'], result_str)
                            print(f"Label application result: {label_result}")

                            # Apply notification criteria
                            should_notify = False
                            if priority.upper() == "HIGH":
                                should_notify = True
                            elif needs_response.upper() == "YES" and category.upper() not in ["NEWSLETTER", "PROMOTIONAL"]:
                                should_notify = True

                            if should_notify:
                                from tools.notification_tools import send_telegram_notification_func
                                notification_message = f"From: {email_data['from']}\nSubject: {email_data['subject']}\nPriority: {priority}\nCategory: {category}\nNeeds Response: {needs_response}\nSummary: {summary}"
                                send_telegram_notification_func(notification_message)
                                print(f"Notification sent for email {i+1} using fallback mechanism")
                    elif "token" in error_msg:
                        print(f"\n--- Token limit reached on email {i+1} ---")
                        print("The email content was too large. Try with a smaller email.")
                    else:
                        print(f"\n--- Error processing email {i+1}: {str(crew_error)} ---")

                # Step 5: Clear the file for the next email
                clear_email_file(email_file_path)

                # Add a delay between emails to avoid rate limits
                if i < len(emails) - 1:  # Don't sleep after the last email
                    print(f"Waiting 2 seconds before processing next email...")
                    time.sleep(2)  # 2 second delay between emails

            # Update total emails in statistics
            stats["total"] = len(emails)

            # Print summary statistics
            print("\n--- Email Processing Summary ---")
            print(f"Total emails processed: {stats['total']}")

            # Print statistics for processed emails
            for email_data in emails:
                email_id = email_data['id']
                # Try to get the labels applied to this email
                try:
                    mail = imaplib.IMAP4_SSL("imap.gmail.com")
                    mail.login(GMAIL_USERNAME, GMAIL_APP_PASSWORD)
                    mail.select("inbox")

                    # Get the labels for this email
                    _, msg_data = mail.fetch(email_id.encode(), '(X-GM-LABELS)')
                    if msg_data and msg_data[0]:
                        labels_str = msg_data[0].decode()

                        # Extract priority
                        if any(f"Priority/{priority}" in labels_str or f"Priority.{priority}" in labels_str for priority in ["High", "Medium", "Low"]):
                            for priority in ["High", "Medium", "Low"]:
                                if f"Priority/{priority}" in labels_str or f"Priority.{priority}" in labels_str:
                                    stats["priority"][priority] += 1
                                    break
                        else:
                            stats["priority"]["Unknown"] += 1

                        # Extract category
                        category_found = False
                        for category in ["Personal", "Work", "Promotional", "Newsletter", "GitHub", "YouTube", "Receipts_Invoices", "Other"]:
                            if f"Category/{category}" in labels_str or f"Category.{category}" in labels_str:
                                stats["category"][category] += 1
                                category_found = True
                                break
                        if not category_found:
                            stats["category"]["Unknown"] += 1

                        # Extract needs response
                        if "Needs_Response" in labels_str:
                            stats["needs_response"]["Yes"] += 1
                        else:
                            stats["needs_response"]["No"] += 1
                    else:
                        stats["priority"]["Unknown"] += 1
                        stats["category"]["Unknown"] += 1
                        stats["needs_response"]["Unknown"] += 1

                    mail.close()
                    mail.logout()
                except Exception as e:
                    print(f"Error getting labels for email {email_id}: {str(e)}")
                    stats["priority"]["Unknown"] += 1
                    stats["category"]["Unknown"] += 1
                    stats["needs_response"]["Unknown"] += 1

            # Print the statistics
            print("\nPriority Breakdown:")
            for priority, count in stats["priority"].items():
                if count > 0:
                    print(f"  {priority}: {count}")

            print("\nCategory Breakdown:")
            for category, count in stats["category"].items():
                if count > 0:
                    print(f"  {category}: {count}")

            print("\nNeeds Response Breakdown:")
            for response, count in stats["needs_response"].items():
                if count > 0:
                    print(f"  {response}: {count}")

            # Print direct categorization results
            print("\nDirect Categorization Results:")
            for item in stats["direct_categorization"]:
                print(f"\nSubject: {item['subject']}")
                result = item['result']

                # Parse the categorization result
                priority = "Unknown"
                category = "Unknown"
                needs_response = "Unknown"

                # Convert tuple to string if needed
                if isinstance(result, tuple):
                    result_str = result[1] if len(result) > 1 and result[1] is not None else str(result[0])
                else:
                    result_str = str(result)

                # Try to extract structured data
                for line in result_str.split('\n'):
                    if line.startswith("Priority:"):
                        priority = line.replace("Priority:", "").strip()
                    elif line.startswith("Category:"):
                        category = line.replace("Category:", "").strip()
                    elif line.startswith("Needs Response:"):
                        needs_response = line.replace("Needs Response:", "").strip()

                print(f"  Priority: {priority}")
                print(f"  Category: {category}")
                print(f"  Needs Response: {needs_response}")

            print("\n--- All emails processed ---")

    except Exception as e:
        print(f"Error in email pipeline: {str(e)}")

if __name__ == "__main__":
    main()
