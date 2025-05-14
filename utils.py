"""
Utility functions for the email processing system.
"""

import os

def write_email_to_file(email_data, file_path="current_email.txt"):
    """
    Write email data to a text file.
    
    Args:
        email_data (dict): Dictionary containing email details
        file_path (str): Path to the output file
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            content = f"""From: {email_data.get('from', 'Unknown')}
Subject: {email_data.get('subject', 'Unknown')}
Date: {email_data.get('date', 'Unknown')}
ID: {email_data.get('id', 'Unknown')}
Body:
{email_data.get('body', 'No content')}
"""
            file.write(content)
        return True
    except Exception as e:
        print(f"Error writing email to file: {str(e)}")
        return False

def read_email_from_file(file_path="current_email.txt"):
    """
    Read email data from a text file.
    
    Args:
        file_path (str): Path to the input file
        
    Returns:
        str: Email content as a string
    """
    try:
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    except Exception as e:
        print(f"Error reading email from file: {str(e)}")
        return None

def clear_email_file(file_path="current_email.txt"):
    """
    Clear the content of the email file.
    
    Args:
        file_path (str): Path to the file to clear
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write("")
        return True
    except Exception as e:
        print(f"Error clearing email file: {str(e)}")
        return False

def extract_email_details(email_content):
    """
    Extract email details from the content string.
    
    Args:
        email_content (str): Email content as a string
        
    Returns:
        dict: Dictionary with email details
    """
    if not email_content:
        return {}
        
    lines = email_content.split('\n')
    email_data = {}
    
    # Extract headers
    for line in lines[:4]:  # First 4 lines should be headers
        if ': ' in line:
            key, value = line.split(': ', 1)
            email_data[key.lower()] = value
    
    # Extract body (everything after "Body:")
    body_start = email_content.find("Body:")
    if body_start != -1:
        email_data['body'] = email_content[body_start + 5:].strip()
    
    return email_data
