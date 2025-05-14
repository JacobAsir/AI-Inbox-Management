"""
Categorization tools for analyzing and categorizing emails.
"""

from crewai.tools import tool

from config import groq_client, gemini_model, CATEGORIZER_MODEL

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
                model=CATEGORIZER_MODEL,
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

def categorize_with_gemini_func(email_content: str) -> str:
    """
    Categorize an email using Google's Gemini model.
    Returns the categorization result as a string.
    """
    try:
        # Always truncate emails to avoid token limit issues
        if len(email_content) > 800:
            email_content = email_content[:800] + "..." # Truncate long emails

        # Check for common keywords to provide basic categorization if API fails
        lower_content = email_content.lower()

        # Try to use the Gemini API first
        try:
            if gemini_model is None:
                raise ValueError("Gemini model not initialized. Check your API key.")

            # Enhanced prompt with better instructions for Gemini's reasoning capabilities
            prompt = f"""Analyze this email and categorize it:

            {email_content}

            First, understand the intent and context of the email:
            1. Who is the sender and what is their relationship to the recipient?
            2. What is the main purpose of this email?
            3. Is there any urgency or time-sensitivity?
            4. Does it require action from the recipient?
            5. What category best describes this email?

            IMPORTANT RULES:
            - Security-related emails (password resets, security alerts, breach notifications) should ALWAYS be marked as High Priority and ALWAYS need a response
            - Financial notifications (unusual charges, payment confirmations) should be High Priority
            - Emails containing action items or requests should be marked as Needs Response: Yes
            - Emails with deadlines or time-sensitive information should be at least Medium Priority

            Based on your analysis, provide ONLY the following structured output:
            Priority: [High/Medium/Low] - Use High for urgent matters, security alerts, or financial notifications
            Category: [Personal/Work/Promotional/Newsletter/GitHub/YouTube/Receipts_Invoices/Other] - Choose the most specific category
            Needs Response: [Yes/No] - Use Yes if the sender expects a reply OR if the email contains security alerts or action items
            Contains Tasks: [Yes/No] - Use Yes if there are specific actions required
            Summary: [1-2 sentence summary of the email's main content and purpose]
            """

            try:
                # Generate a response using Gemini with reduced tokens
                response = gemini_model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.1,
                        "max_output_tokens": 250,
                        "top_p": 0.95
                    }
                )

                result = response.text.strip()

                # Validate the response format
                if not result.startswith("Priority:") or "Category:" not in result:
                    raise ValueError("Invalid response format from Gemini")

                return result
            except Exception as api_error:
                # Check specifically for rate limit errors
                error_str = str(api_error).lower()
                if "rate limit" in error_str or "quota" in error_str or "429" in error_str:
                    print(f"Gemini API rate limit reached: {str(api_error)}. Using fallback categorization.")
                else:
                    print(f"Gemini API error: {str(api_error)}. Using fallback categorization.")
                # Continue to fallback categorization
                raise

        except Exception as api_error:
            print(f"Gemini API error: {str(api_error)}. Using fallback categorization.")

            # Improved fallback categorization logic
            priority = "Low"  # Default to low priority
            category = "Other"  # Default category
            needs_response = "No"  # Default to no response needed
            contains_tasks = "No"  # Default to no tasks

            # Extract subject and sender for better categorization
            subject_line = ""
            sender = ""
            for line in email_content.split("\n"):
                if line.startswith("Subject:"):
                    subject_line = line[8:].strip().lower()
                elif line.startswith("From:"):
                    sender = line[5:].strip().lower()

            # Combine subject, sender and content for analysis
            analysis_text = f"{subject_line} {sender} {lower_content}"

            # Security-related emails detection
            if any(word in analysis_text for word in ["security", "breach", "hack", "password", "reset", "suspicious", "login", "unauthorized", "access", "alert", "warning", "fraud", "phishing", "verify", "verification"]):
                priority = "High"
                needs_response = "Yes"
                category = "Personal"  # Security emails are usually personal
            # Financial notifications detection
            elif any(word in analysis_text for word in ["charge", "transaction", "payment", "unusual", "bank", "credit card", "debit", "account", "balance", "statement"]):
                priority = "High"
                category = "Receipts_Invoices"
            # Better keyword detection for priority
            elif any(word in analysis_text for word in ["urgent", "important", "asap", "deadline", "emergency", "critical", "immediate", "priority"]):
                priority = "High"

            # Better category detection
            if "github" in analysis_text or "repository" in analysis_text or "commit" in analysis_text or "pull request" in analysis_text:
                category = "GitHub"
            elif "youtube" in analysis_text or "video" in analysis_text or "channel" in analysis_text:
                category = "YouTube"
            elif any(word in analysis_text for word in ["receipt", "invoice", "payment", "order", "purchase", "transaction", "bill"]) and priority != "High":  # Don't override security emails
                category = "Receipts_Invoices"
            elif any(word in analysis_text for word in ["newsletter", "subscribe", "update", "weekly", "monthly", "digest"]) and priority != "High":  # Don't override security emails
                category = "Newsletter"
            elif any(word in analysis_text for word in ["offer", "discount", "sale", "promotion", "deal", "limited time", "off", "save", "coupon"]) and priority != "High":  # Don't override security emails
                category = "Promotional"
            elif any(word in analysis_text for word in ["job", "interview", "application", "career", "position", "work", "project", "meeting"]) and priority != "High":  # Don't override security emails
                category = "Work"
            elif any(word in analysis_text for word in ["hi", "hello", "hey", "dear", "friend", "family", "personal"]) and priority != "High":  # Don't override security emails
                category = "Personal"

            # Better response needed detection
            if any(phrase in analysis_text for phrase in ["please respond", "let me know", "reply", "get back to me", "response", "confirm", "rsvp", "answer", "action", "required", "request", "approve", "approval"]):
                needs_response = "Yes"

            # Better task detection
            if any(word in analysis_text for word in ["task", "todo", "to-do", "action", "assignment", "complete", "finish", "due"]):
                contains_tasks = "Yes"

            # Create a better summary based on the content
            if category == "Newsletter":
                summary = f"Newsletter from {sender if sender else 'unknown sender'}"
            elif category == "Promotional":
                summary = f"Promotional email about {subject_line if subject_line else 'offers or discounts'}"
            elif category == "GitHub":
                summary = "GitHub notification or update"
            elif category == "YouTube":
                summary = "YouTube notification or update"
            elif category == "Receipts_Invoices":
                summary = f"Receipt or invoice from {sender if sender else 'a service'}"
            elif category == "Work":
                summary = f"Work-related email about {subject_line if subject_line else 'a project or task'}"
            elif category == "Personal":
                summary = f"Personal email from {sender if sender else 'someone'}"
            else:
                summary = f"Email about {subject_line if subject_line else 'unknown topic'}"

            # Create a formatted response similar to what the API would return
            return f"Priority: {priority}\nCategory: {category}\nNeeds Response: {needs_response}\nContains Tasks: {contains_tasks}\nSummary: {summary}"
    except Exception as e:
        return f"Error categorizing email with Gemini: {str(e)}"

@tool
def categorize_with_groq(email_content: str) -> str:
    """Categorize an email using Groq's LLama model."""
    return categorize_with_groq_func(email_content)

@tool
def categorize_with_gemini(email_content: str = "") -> str:
    """Categorize an email using Google's Gemini model.

    If email_content is empty, the tool will read from current_email.txt file.
    """
    # If no content is provided or it's a dictionary (which happens with CrewAI sometimes),
    # read from the file
    if not email_content or not isinstance(email_content, str) or not email_content.strip():
        try:
            with open("current_email.txt", "r", encoding="utf-8") as file:
                email_content = file.read()
        except Exception as e:
            return f"Error reading from current_email.txt: {str(e)}"

    return categorize_with_gemini_func(email_content)
