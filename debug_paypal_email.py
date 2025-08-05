#!/usr/bin/env python3
"""
Debug script to examine PayPal email content
"""
import imaplib
import email
from bs4 import BeautifulSoup
import re

# Connection details
email_address = 'mike@roetto.org'
password = '$99.99Dinner'
imap_server = 'roetto.org'
imap_port = 993

def debug_email():
    # Connect to IMAP
    mail = imaplib.IMAP4_SSL(imap_server, imap_port)
    mail.login(email_address, password)
    mail.select('INBOX')
    
    # Search for PayPal Pay in 4 emails
    result, message_ids = mail.search(None, '(FROM "service@paypal.com" SUBJECT "Your PayPal Pay in 4 payment went through")')
    
    if result == 'OK' and message_ids[0]:
        ids = message_ids[0].split()
        print(f"Found {len(ids)} PayPal payment went through emails")
        
        # Get the first email
        message_id = ids[0]
        print(f"Examining email ID: {message_id}")
        
        result, message_data = mail.fetch(message_id, '(RFC822)')
        email_message = email.message_from_bytes(message_data[0][1])
        
        print(f"Subject: {email_message.get('Subject')}")
        print(f"Date: {email_message.get('Date')}")
        print(f"From: {email_message.get('From')}")
        print()
        
        # Extract body
        body = ""
        for part in email_message.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            
            if content_type == "text/html":
                html_content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get text
                text = soup.get_text()
                
                # Clean up text
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                
                body = text
                break
        
        print("=== CLEANED EMAIL BODY ===")
        print(body[:2000])
        print("\n" + "="*50)
        
        # Look for key patterns
        print("\n=== PATTERN ANALYSIS ===")
        
        # Amount patterns
        amount_matches = re.findall(r'\$([0-9,]+\.?[0-9]*)', body)
        print(f"Amount matches: {amount_matches}")
        
        # Merchant patterns - updated to match our new patterns
        merchant_patterns = [
            r'Merchant\s+([A-Za-z0-9][A-Za-z0-9\s&\.,\-\'\(\)]{2,50})(?:\s+Current|\s+To\s+see|\s*$)',
            r'for your Pay in 4 plan.*?Merchant\s+([A-Za-z0-9][A-Za-z0-9\s&\.,\-\'\(\)]{2,50})',
            r'Posted on.*?Merchant\s+([A-Za-z0-9][A-Za-z0-9\s&\.,\-\'\(\)]{2,50})',
        ]
        
        merchant_matches = []
        for pattern in merchant_patterns:
            matches = re.findall(pattern, body, re.IGNORECASE | re.DOTALL)
            if matches:
                merchant_matches.extend(matches)
        
        print(f"Merchant matches: {merchant_matches}")
        
        # Let's also look for the word "Merchant" in the text
        merchant_context = re.findall(r'.{0,50}Merchant.{0,50}', body, re.IGNORECASE)
        print(f"Merchant context: {merchant_context}")
        
        # Date patterns
        date_matches = re.findall(r'([A-Za-z]{3}\s+\d{1,2},\s+\d{4})', body)
        print(f"Date matches: {date_matches}")
        
    mail.close()
    mail.logout()

if __name__ == "__main__":
    debug_email()