#!/usr/bin/env python3
"""
Find and analyze specific IMAP message ID
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

def find_specific_message():
    # Connect to IMAP
    mail = imaplib.IMAP4_SSL(imap_server, imap_port)
    mail.login(email_address, password)
    mail.select('INBOX')
    
    target_message_id = '3A.85.10415.38830986@ccg13mail01'
    
    # Search for all messages
    result, message_ids = mail.search(None, 'ALL')
    
    if result == 'OK' and message_ids[0]:
        ids = message_ids[0].split()
        print(f"Searching through {len(ids)} total messages for Message-ID: {target_message_id}")
        
        found = False
        for msg_id in ids:
            result, message_data = mail.fetch(msg_id, '(RFC822)')
            if result == 'OK':
                email_message = email.message_from_bytes(message_data[0][1])
                
                # Check Message-ID header
                msg_message_id = email_message.get('Message-ID', '').strip('<>')
                
                if msg_message_id == target_message_id:
                    print(f"FOUND! IMAP ID: {msg_id}, Message-ID: {msg_message_id}")
                    print(f"Subject: {email_message.get('Subject')}")
                    print(f"Date: {email_message.get('Date')}")
                    print(f"From: {email_message.get('From')}")
                    print()
                    
                    # Extract body
                    body = ""
                    for part in email_message.walk():
                        content_type = part.get_content_type()
                        
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
                    print(body)
                    print("\n" + "="*80)
                    
                    # Look for specific patterns
                    print("\n=== PATTERN ANALYSIS ===")
                    
                    # Amount patterns
                    amount_matches = re.findall(r'\$([0-9,]+\.?[0-9]*)', body)
                    print(f"Amount matches: {amount_matches}")
                    
                    # Look for Banana Republic
                    banana_matches = re.findall(r'.{0,50}[Bb]anana.{0,50}[Rr]epublic.{0,50}', body, re.IGNORECASE)
                    print(f"Banana Republic matches: {banana_matches}")
                    
                    # Merchant patterns
                    merchant_matches = re.findall(r'Merchant\s+([A-Za-z0-9][A-Za-z0-9\s&\.,\-\'\(\)]{2,50})', body, re.IGNORECASE)
                    print(f"Merchant matches: {merchant_matches}")
                    
                    # Date patterns
                    date_matches = re.findall(r'([A-Za-z]{3,}\s+\d{1,2},\s+\d{4})', body)
                    print(f"Date matches: {date_matches}")
                    
                    found = True
                    break
        
        if not found:
            print(f"Message-ID {target_message_id} not found in INBOX")
            
            # Let's also search PayPal emails for this Message-ID
            print("\nSearching PayPal emails specifically...")
            result, paypal_ids = mail.search(None, 'FROM "service@paypal.com"')
            if result == 'OK' and paypal_ids[0]:
                paypal_list = paypal_ids[0].split()
                print(f"Found {len(paypal_list)} PayPal emails to check")
                
                for msg_id in paypal_list[-20:]:  # Check last 20 PayPal emails
                    result, message_data = mail.fetch(msg_id, '(RFC822)')
                    if result == 'OK':
                        email_message = email.message_from_bytes(message_data[0][1])
                        msg_message_id = email_message.get('Message-ID', '').strip('<>')
                        
                        print(f"PayPal email {msg_id}: Message-ID = {msg_message_id}")
                        
                        if msg_message_id == target_message_id:
                            print(f"FOUND IN PAYPAL SEARCH! IMAP ID: {msg_id}")
                            found = True
                            break
    
    mail.close()
    mail.logout()

if __name__ == "__main__":
    find_specific_message()