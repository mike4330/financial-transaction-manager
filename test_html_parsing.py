#!/usr/bin/env python3
"""
Test HTML parsing for specific email
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

def test_html_parsing():
    mail = imaplib.IMAP4_SSL(imap_server, imap_port)
    mail.login(email_address, password)
    mail.select('INBOX')
    
    # Get email b'471' specifically
    result, message_data = mail.fetch('471', '(RFC822)')
    email_message = email.message_from_bytes(message_data[0][1])
    
    print(f"Subject: {email_message.get('Subject')}")
    print(f"Date: {email_message.get('Date')}")
    
    # Test the current HTML extraction logic
    body_html = ""
    body_cleaned = ""
    
    for part in email_message.walk():
        content_type = part.get_content_type()
        content_disposition = str(part.get("Content-Disposition"))
        
        if content_type == "text/plain" and "attachment" not in content_disposition:
            print("Found text/plain part")
            try:
                body_html += part.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                pass
        elif content_type == "text/html":
            print("Found text/html part")
            try:
                html_content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                body_html = html_content  # Save raw HTML for comparison
                
                # Use BeautifulSoup for proper HTML parsing
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get text
                text = soup.get_text(separator=' ', strip=True)
                
                # Clean up text - collapse whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                body_cleaned = ' '.join(chunk for chunk in chunks if chunk)
                
            except Exception as e:
                print(f"HTML parsing failed: {e}")
    
    print(f"Raw HTML length: {len(body_html)}")
    print(f"Cleaned text length: {len(body_cleaned)}")
    
    print("\n=== Raw HTML (first 300 chars) ===")
    print(body_html[:300])
    
    print("\n=== Cleaned Text (first 300 chars) ===")
    print(body_cleaned[:300])
    
    # Test merchant patterns on cleaned text
    merchant_patterns = [
        r'Merchant\s+([A-Za-z0-9][A-Za-z0-9\s&\.,\-\'\(\)]+?)\s+Current',
        r'Merchant\s+([A-Za-z0-9][A-Za-z0-9\s&\.,\-\'\(\)]+?)\s+To\s+see',
        r'\d{4}\s+Merchant\s+([A-Za-z0-9][A-Za-z0-9\s&\.,\-\'\(\)]+?)\s+Current',
        r'Posted on [A-Za-z]+ \d{1,2}, \d{4} Merchant ([A-Za-z0-9][A-Za-z0-9\s&\.,\-\'\(\)]+?) Current',
    ]
    
    print("\n=== Testing Merchant Patterns on Cleaned Text ===")
    for i, pattern in enumerate(merchant_patterns):
        match = re.search(pattern, body_cleaned, re.IGNORECASE | re.DOTALL)
        if match:
            merchant = match.group(1).strip()
            print(f"Pattern {i} MATCHED: '{merchant}'")
        else:
            print(f"Pattern {i} failed")
    
    # Look for Banana Republic specifically
    banana_matches = re.findall(r'.{0,30}[Bb]anana.{0,30}[Rr]epublic.{0,30}', body_cleaned, re.IGNORECASE)
    print(f"\nBanana Republic context: {banana_matches}")
    
    mail.close()
    mail.logout()

if __name__ == "__main__":
    test_html_parsing()