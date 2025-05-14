# AI-Inbox-Management

Tired of drowning in emails?

I developed a smart AI-powered email assistant to simplify your inbox management! 

An AI Agent for your inbox management! 

# Key Features: 

- Intelligent Priority Detection (High/Medium/Low) 

- Smart Categorization (Work, Personal, GitHub, YouTube, etc.)

- Task Identification (highlights emails that need responses) 

- Instant Telegram Notifications (real-time alerts only for urgent emails)

No more missed opportunities or wasted time sorting through countless emails.

## Project Structure

```
.
├── config.py                 # Configuration and environment variables
├── main.py                   # Main execution script
├── utils.py                  # Utility functions for file operations
├── requirements.txt          # Project dependencies
├── .env                      # Environment variables (not tracked in git)
├── current_email.txt         # Temporary storage for email being processed
├── agents/                   # Agent definitions
│   ├── __init__.py           # Export agents
│   ├── email_categorizer.py  # Email categorization agent
│   └── notifier.py           # Notification agent
├── tasks/                    # Task definitions
│   ├── __init__.py           # Export task creation functions
│   └── email_tasks.py        # Email-related tasks
└── tools/                    # Tool functions
    ├── __init__.py           # Export tools
    ├── email_tools.py        # Email fetching tools
    ├── notification_tools.py # Telegram notification tools
    └── categorization_tools.py # Email categorization tools
```

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file with the following variables:
   ```
   # API Keys
   GROQ_API_KEY="your_groq_api_key"
   GEMINI_API_KEY="your_gemini_api_key"

   # Gmail Credentials
   GMAIL_USERNAME="your_gmail_username"
   GMAIL_APP_PASSWORD="your_gmail_app_password"

   # Email Processing Settings
   EMAIL_BATCH_SIZE=3

   # Telegram Notification Settings
   TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
   TELEGRAM_CHAT_ID="your_telegram_chat_id"
   ```
4. Run the application: `python main.py`

## Usage

The system will:
1. Fetch unread emails from your Gmail account
2. Process each email one at a time using a file-based approach with AI agents:
   - Write the email to a text file
   - Read the email from the file
   - Use the Email Categorizer agent with Gemini to analyze and categorize the email
   - Apply Gmail labels based on the categorization (Priority, Category, Needs Response)
   - Use the Notification agent to determine if a notification is needed
   - Send a Telegram notification if required
   - Clear the file before processing the next email
3. This approach ensures reliable processing and avoids token limit issues while leveraging AI agents for intelligent decision-making

## Notification Criteria

Notifications are only sent for:
- HIGH PRIORITY emails
- Emails that explicitly NEED A RESPONSE (regardless of priority)
- Never for newsletters or promotional emails
- Never for low or medium priority emails unless they require a response

## Model Usage

This system uses two different AI models for different purposes:

- **Google's Gemini model** (gemini-2.5-flash-preview-04-17): Used by the Email Categorizer agent for email categorization due to its strong reasoning capabilities and ability to accurately classify emails.
- **Groq's LLama model** (llama-3.3-70b-versatile): Used by the Notification agent to determine when to send alerts to the user.

## Gmail Labels

The system automatically applies the following labels to your emails in Gmail:

1. **Priority Labels**: Based on the email's priority level
   - `Priority/High`
   - `Priority/Medium`
   - `Priority/Low`

2. **Category Labels**: Based on the email's category
   - `Category/Personal`
   - `Category/Work`
   - `Category/Promotional`
   - `Category/Newsletter`
   - `Category/GitHub`
   - `Category/YouTube`
   - `Category/Receipts_Invoices`
   - `Category/Other`

3. **Response Label**: Applied if the email needs a response
   - `Needs_Response`

These labels help you quickly identify and filter emails based on their categorization.

## File-Based Processing

The system uses a file-based approach for processing emails:

1. **Reliability**: By processing one email at a time and using a text file as intermediate storage, the system is more reliable and can recover from errors.

2. **Token Limit Management**: This approach helps avoid token limit issues by ensuring only one email is being processed at a time.

3. **Debugging**: The file-based approach makes debugging easier as you can inspect the text file to see what's being processed.

4. **Memory Efficiency**: Processing one email at a time reduces memory usage and makes the system more efficient.

5. **Separation of Concerns**: The approach creates a clear separation between fetching emails and processing them, making the code more maintainable.
