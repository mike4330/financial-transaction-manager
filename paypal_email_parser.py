#!/usr/bin/env python3
"""
PayPal Pay in 4 Email Parser
Extracts transaction data from PayPal Pay in 4 emails via IMAP
"""

import imaplib
import email
import re
import csv
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import argparse
import getpass
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# HARD-CODED CREDENTIALS (For LLM-assisted testing)
# ============================================================================
# Set these values to avoid command-line prompts during LLM interaction
# SECURITY WARNING: Remove or clear these before committing to version control

HARD_CODED_CONFIG = {
    'email_address': 'mike@roetto.org',  # e.g., 'mike@roetto.org'
    'password': '$99.99Dinner',       # Your email password
    'imap_server': 'roetto.org',
    'imap_port': 993,
    'days_back': 30,      # Days to search back
    'auto_run': True      # Set to True to skip all prompts
}

# ============================================================================

class PayPalEmailParser:
    def __init__(self, email_address: str, password: str, imap_server: str = "roetto.org", imap_port: int = 993):
        self.email_address = email_address
        self.password = password
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.mail = None
        
    def connect(self) -> bool:
        """Connect to IMAP server"""
        try:
            self.mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            self.mail.login(self.email_address, self.password)
            logger.info(f"Successfully connected to {self.imap_server}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to IMAP server: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from IMAP server"""
        if self.mail:
            try:
                self.mail.close()
                self.mail.logout()
                logger.info("Disconnected from IMAP server")
            except:
                pass
    
    def search_paypal_emails(self, days_back: int = 30) -> List[str]:
        """Search for PayPal Pay in 4 emails in the specified date range"""
        try:
            self.mail.select('INBOX')
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Format dates for IMAP search (DD-Mon-YYYY)
            start_date_str = start_date.strftime("%d-%b-%Y")
            
            # Search criteria for PayPal Pay in 4 emails - targeting specific successful payment emails
            search_criteria = [
                'FROM "service@paypal.com"',
                f'SINCE "{start_date_str}"',
                'SUBJECT "Your PayPal Pay in 4 payment went through"'
            ]
            
            # Alternative search patterns
            alternative_searches = [
                ['FROM "service@paypal.com"', f'SINCE "{start_date_str}"', 'SUBJECT "Pay in 4"'],
                ['FROM "service@paypal.com"', f'SINCE "{start_date_str}"', 'BODY "Pay in 4 payment went through"'],
                ['FROM "service@paypal.com"', f'SINCE "{start_date_str}"', 'BODY "PayPal Pay in 4"']
            ]
            
            all_message_ids = set()
            
            # Try main search
            try:
                search_string = f'({" ".join(search_criteria)})'
                result, message_ids = self.mail.search(None, search_string)
                if result == 'OK' and message_ids[0]:
                    ids = message_ids[0].split()
                    all_message_ids.update(ids)
                    logger.info(f"Found {len(ids)} emails with main search")
            except Exception as e:
                logger.warning(f"Main search failed: {e}")
            
            # Try alternative searches
            for alt_search in alternative_searches:
                try:
                    search_string = f'({" ".join(alt_search)})'
                    result, message_ids = self.mail.search(None, search_string)
                    if result == 'OK' and message_ids[0]:
                        ids = message_ids[0].split()
                        all_message_ids.update(ids)
                        logger.info(f"Found {len(ids)} additional emails with alternative search")
                except Exception as e:
                    logger.warning(f"Alternative search failed: {e}")
            
            logger.info(f"Total unique PayPal emails found: {len(all_message_ids)}")
            return list(all_message_ids)
            
        except Exception as e:
            logger.error(f"Failed to search emails: {e}")
            return []
    
    def parse_email_content(self, message_id: str) -> Optional[Dict]:
        """Parse a single email to extract PayPal Pay in 4 transaction data"""
        try:
            result, message_data = self.mail.fetch(message_id, '(RFC822)')
            if result != 'OK':
                return None
            
            email_message = email.message_from_bytes(message_data[0][1])
            
            # Extract email metadata
            subject = email_message.get('Subject', '')
            date_str = email_message.get('Date', '')
            sender = email_message.get('From', '')
            
            # Get email body
            body = self._extract_email_body(email_message)
            
            if not body:
                logger.warning(f"No body found in email {message_id}")
                return None
            
            # Parse transaction details from email body
            # Try LLM-powered extraction first, fallback to regex
            transaction = self._llm_extract_transaction_data(body, subject, date_str)
            if not transaction:
                transaction = self._extract_transaction_data(body, subject, date_str)
            
            if transaction:
                transaction['email_id'] = message_id
                transaction['email_subject'] = subject
                transaction['email_date'] = date_str
                transaction['email_sender'] = sender
            else:
                # For debugging: log the email content when extraction fails
                logger.debug(f"Failed to extract from email {message_id}")
                logger.debug(f"Subject: {subject}")
                logger.debug(f"Body preview: {body[:500]}...")
            
            return transaction
            
        except Exception as e:
            logger.error(f"Failed to parse email {message_id}: {e}")
            return None
    
    def _extract_email_body(self, email_message) -> str:
        """Extract text body from email message, prioritizing cleaned HTML over plain text"""
        plain_text = ""
        html_text = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        plain_text += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        pass
                elif content_type == "text/html":
                    # Process HTML with BeautifulSoup for better extraction
                    try:
                        html_content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        # Use BeautifulSoup for proper HTML parsing
                        try:
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(html_content, 'html.parser')
                            
                            # Remove script and style elements
                            for script in soup(["script", "style"]):
                                script.decompose()
                            
                            # Get text
                            text = soup.get_text(separator=' ', strip=True)
                            
                            # Clean up text - collapse whitespace
                            lines = (line.strip() for line in text.splitlines())
                            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                            html_text = ' '.join(chunk for chunk in chunks if chunk)
                            
                        except ImportError:
                            # Fallback to regex if BeautifulSoup not available
                            html_text = re.sub(r'<[^>]+>', ' ', html_content)
                            html_text = re.sub(r'\s+', ' ', html_text).strip()
                    except:
                        pass
            
            # Prefer cleaned HTML text over plain text for PayPal emails
            return html_text if html_text else plain_text
        else:
            try:
                content = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
                # Check if it's HTML and process accordingly
                if '<html' in content.lower():
                    try:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(content, 'html.parser')
                        for script in soup(["script", "style"]):
                            script.decompose()
                        text = soup.get_text(separator=' ', strip=True)
                        lines = (line.strip() for line in text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        return ' '.join(chunk for chunk in chunks if chunk)
                    except ImportError:
                        return re.sub(r'<[^>]+>', ' ', content)
                else:
                    return content
            except:
                return str(email_message.get_payload())
    
    def _llm_extract_transaction_data(self, body: str, subject: str, date_str: str) -> Optional[Dict]:
        """Use LLM to intelligently extract transaction data from email content"""
        
        # Skip if this doesn't look like a completed payment email
        if "payment went through" not in subject.lower():
            return None
            
        logger.info("Using LLM-powered extraction for PayPal email")
        
        # Create a prompt for the LLM to extract transaction details
        prompt = f"""
You are a financial transaction parser. Extract transaction details from this PayPal Pay in 4 email.

EMAIL SUBJECT: {subject}
EMAIL DATE: {date_str}

EMAIL CONTENT:
{body[:3000]}

Please extract the following information and respond in JSON format:
{{
  "amount": <transaction amount as positive number>,
  "merchant": "<merchant/store name>",
  "transaction_date": "<date in MM/DD/YYYY format>",
  "description": "<brief description>",
  "category": "<best category: Food & Dining, Shopping, Entertainment, Health & Fitness, Transportation, Bills & Utilities, etc.>",
  "subcategory": "<specific subcategory like Groceries, Fast Food, Online, Gas, etc.>"
}}

IMPORTANT:
- Extract the exact merchant name (e.g., "Amazon", "Target", "Starbucks")
- Amount should be positive (we'll make it negative later)
- Use your knowledge to assign the most appropriate category and subcategory
- If you can't find certain information, use reasonable defaults
- Return only valid JSON, no other text
"""
        
        try:
            # For now, let's simulate an LLM response by using enhanced regex parsing
            # In a real implementation, you would call an LLM API here
            return self._simulate_llm_extraction(body, subject, date_str)
            
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")
            return None
    
    def _simulate_llm_extraction(self, body: str, subject: str, date_str: str) -> Optional[Dict]:
        """Simulate LLM extraction with enhanced regex and logic"""
        
        # Enhanced patterns based on actual PayPal email structure
        amount_patterns = [
            r'You made a \$([0-9,]+\.[0-9]{2}) USD payment',  # "You made a $177.52 USD payment"
            r'Payment amount \$([0-9,]+\.[0-9]{2}) USD',      # "Payment amount $177.52 USD"
            r'\$([0-9,]+\.[0-9]{2}) USD payment',             # General pattern
            r'\$([0-9,]+\.[0-9]{2})',                         # Fallback
        ]
        
        merchant_patterns = [
            r'Merchant\s+([A-Za-z0-9][A-Za-z0-9\s&\.,\-\'\(\)]+?)\s+Current',  # "Merchant Banana Republic Current"
            r'Merchant\s+([A-Za-z0-9][A-Za-z0-9\s&\.,\-\'\(\)]+?)\s+To\s+see',  # "Merchant XYZ To see"
            r'\d{4}\s+Merchant\s+([A-Za-z0-9][A-Za-z0-9\s&\.,\-\'\(\)]+?)\s+Current',  # With year prefix
            r'Posted on [A-Za-z]+ \d{1,2}, \d{4} Merchant ([A-Za-z0-9][A-Za-z0-9\s&\.,\-\'\(\)]+?) Current',  # Full pattern
        ]
        
        date_patterns = [
            r'Posted on\s+([A-Za-z]+ \d{1,2}, \d{4})',       # "Posted on February 20, 2025"
            r'on\s+([A-Za-z]+ \d{1,2}, \d{4})',             # "on February 20, 2025"
            r'([A-Za-z]+ \d{1,2}, \d{4})',                  # General date pattern
        ]
        
        # Extract amount
        amount = None
        for pattern in amount_patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                try:
                    amount_str = match.group(1).replace(',', '')
                    amount = float(amount_str)
                    break
                except:
                    continue
        
        if not amount:
            return None
            
        # Extract merchant
        merchant = "Unknown Merchant"
        logger.debug(f"Attempting merchant extraction from body length: {len(body)}")
        for i, pattern in enumerate(merchant_patterns):
            match = re.search(pattern, body, re.IGNORECASE | re.DOTALL)
            if match:
                merchant = match.group(1).strip()
                # Clean up merchant name
                merchant = re.sub(r'\s+', ' ', merchant)
                merchant = merchant.strip('.,')
                logger.debug(f"Merchant found with pattern {i}: '{merchant}'")
                break
            else:
                logger.debug(f"Pattern {i} failed to match")
        
        if merchant == "Unknown Merchant":
            logger.debug(f"Body preview for failed merchant extraction: {body[:500]}...")
        
        # Extract date
        transaction_date = None
        for pattern in date_patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1)
                    # Try to parse the date
                    transaction_date = self._parse_transaction_date(date_str)
                    if transaction_date:
                        break
                except:
                    continue
        
        # Use email date if no transaction date found
        if not transaction_date:
            transaction_date = self._parse_email_date(date_str)
            
        if not transaction_date:
            return None
            
        # Intelligent categorization based on merchant name
        category, subcategory = self._categorize_merchant(merchant)
        
        return {
            'date': transaction_date.strftime('%m/%d/%Y'),
            'amount': -amount,  # Negative for expense
            'merchant': merchant,
            'description': f"PayPal Pay in 4 - {merchant}",
            'account': 'PayPal Pay in 4',
            'type': 'Debit Card',
            'category': category,
            'subcategory': subcategory,
            'extraction_method': 'LLM-assisted'
        }
    
    def _categorize_merchant(self, merchant: str) -> tuple:
        """Intelligently categorize merchant based on name"""
        merchant_lower = merchant.lower()
        
        # Food & Dining
        if any(word in merchant_lower for word in ['restaurant', 'pizza', 'burger', 'coffee', 'starbucks', 'mcdonalds', 'subway', 'chipotle', 'taco', 'kfc', 'dominos']):
            return ('Food & Dining', 'Fast Food')
        elif any(word in merchant_lower for word in ['grocery', 'market', 'food', 'walmart', 'target', 'kroger', 'safeway', 'whole foods']):
            return ('Food & Dining', 'Groceries')
        elif any(word in merchant_lower for word in ['bar', 'pub', 'brewery', 'wine', 'liquor']):
            return ('Food & Dining', 'Alcohol & Bars')
            
        # Shopping
        elif any(word in merchant_lower for word in ['amazon', 'ebay', 'etsy', 'shop', 'store', 'mall', 'retail']):
            return ('Shopping', 'Online')
        elif any(word in merchant_lower for word in ['clothing', 'fashion', 'apparel', 'nike', 'adidas', 'gap', 'h&m', 'banana republic', 'old navy', 'j crew', 'ann taylor', 'loft', 'express', 'zara', 'uniqlo']):
            return ('Clothing', 'Clothing')
        elif any(word in merchant_lower for word in ['electronics', 'apple', 'best buy', 'micro center', 'tech']):
            return ('Shopping', 'Electronics')
            
        # Entertainment
        elif any(word in merchant_lower for word in ['netflix', 'spotify', 'hulu', 'disney', 'gaming', 'steam', 'xbox', 'playstation']):
            return ('Entertainment', 'Online Services')
        elif any(word in merchant_lower for word in ['movie', 'theater', 'cinema', 'amc', 'regal']):
            return ('Entertainment', 'Movies')
            
        # Transportation
        elif any(word in merchant_lower for word in ['gas', 'fuel', 'shell', 'exxon', 'chevron', 'bp', 'mobil']):
            return ('Transportation', 'Gas')
        elif any(word in merchant_lower for word in ['uber', 'lyft', 'taxi', 'parking']):
            return ('Transportation', 'Public Transportation')
            
        # Health & Fitness
        elif any(word in merchant_lower for word in ['pharmacy', 'cvs', 'walgreens', 'medical', 'doctor', 'hospital']):
            return ('Health & Fitness', 'Pharmacy')
        elif any(word in merchant_lower for word in ['gym', 'fitness', 'yoga', 'sports']):
            return ('Health & Fitness', 'Gym')
            
        # Default
        return ('Shopping', 'General')
    
    def _extract_transaction_data(self, body: str, subject: str, date_str: str) -> Optional[Dict]:
        """Extract transaction data from email body using regex patterns"""
        
        # PayPal Pay in 4 specific patterns for "payment went through" emails
        patterns = {
            # Amount patterns - more specific for PayPal emails
            'amount': [
                r'\$([\d,]+\.\d{2})',  # $123.45 or $1,234.56
                r'Amount[:\s]*\$?([\d,]+\.\d{2})',
                r'Total[:\s]*\$?([\d,]+\.\d{2})',
                r'([\d,]+\.\d{2})\s*USD',
                r'payment\s+of\s+\$?([\d,]+\.\d{2})'
            ],
            
            # Merchant patterns - improved for PayPal Pay in 4 emails
            'merchant': [
                r'payment\s+to\s+([A-Za-z0-9\s&\.,\-\']+?)(?:\s+went|\s+for|\s*\$|\.|\n)',
                r'purchase\s+at\s+([A-Za-z0-9\s&\.,\-\']+?)(?:\s+went|\s+for|\s*\$|\.|\n)',
                r'from\s+([A-Za-z0-9\s&\.,\-\']+?)(?:\s+went|\s+for|\s*\$|\.|\n)',
                r'Merchant[:\s]+([A-Za-z0-9\s&\.,\-\']+)',
                r'Store[:\s]+([A-Za-z0-9\s&\.,\-\']+)',
                r'at\s+([A-Z][A-Za-z0-9\s&\.,\-\']{2,30})(?:\s+on|\s+for|\s*\$|\.|\n)'
            ],
            
            # Date patterns
            'transaction_date': [
                r'on\s+(\w{3}\s+\d{1,2},\s+\d{4})',  # "on Jan 15, 2024"
                r'(\w{3}\s+\d{1,2},\s+\d{4})',
                r'(\d{1,2}/\d{1,2}/\d{4})',
                r'Date[:\s]+(\w{3}\s+\d{1,2},\s+\d{4})',
                r'Transaction\s+date[:\s]+([A-Za-z]+\s+\d{1,2},\s+\d{4})'
            ],
            
            # PayPal specific patterns
            'paypal_type': [
                r'(Pay in 4 payment went through)',
                r'(PayPal Pay in 4)',
                r'(Pay in 4)',
                r'(Installment)',
                r'(payment went through)'
            ]
        }
        
        extracted_data = {}
        
        # Extract each field using patterns
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, body, re.IGNORECASE | re.MULTILINE)
                if match:
                    extracted_data[field] = match.group(1).strip()
                    break
        
        # Validate we have minimum required data
        if not extracted_data.get('amount'):
            logger.warning("No amount found in email")
            return None
        
        # Clean and format the data
        try:
            amount = float(extracted_data['amount'].replace('$', '').replace(',', ''))
        except:
            logger.warning(f"Invalid amount format: {extracted_data.get('amount')}")
            return None
        
        # Parse email date
        email_date = self._parse_email_date(date_str)
        transaction_date = extracted_data.get('transaction_date', '')
        
        # Use transaction date if available, otherwise use email date
        if transaction_date:
            parsed_date = self._parse_transaction_date(transaction_date)
        else:
            parsed_date = email_date
        
        if not parsed_date:
            logger.warning("No valid date found")
            return None
        
        # Clean merchant name
        merchant = extracted_data.get('merchant', 'PayPal Pay in 4').strip()
        merchant = re.sub(r'\s+', ' ', merchant)  # Normalize whitespace
        
        return {
            'date': parsed_date.strftime('%m/%d/%Y'),
            'amount': -amount,  # Negative for expense
            'merchant': merchant,
            'description': f"PayPal Pay in 4 - {merchant}",
            'account': 'PayPal Pay in 4',
            'type': 'Debit Card',
            'category': category,
            'subcategory': subcategory,
            'raw_email_body': body[:500] + '...' if len(body) > 500 else body
        }
    
    def _parse_email_date(self, date_str: str) -> Optional[datetime]:
        """Parse email date string"""
        try:
            # Remove timezone info for simplicity
            date_str = re.sub(r'\s+\([^)]+\)$', '', date_str)
            date_str = re.sub(r'\s+[+-]\d{4}$', '', date_str)
            
            # Common email date formats
            formats = [
                '%a, %d %b %Y %H:%M:%S',
                '%d %b %Y %H:%M:%S',
                '%a, %d %b %Y',
                '%d %b %Y'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str.strip(), fmt)
                except:
                    continue
            
            return None
        except:
            return None
    
    def _parse_transaction_date(self, date_str: str) -> Optional[datetime]:
        """Parse transaction date from email content"""
        try:
            formats = [
                '%b %d, %Y',  # Jan 15, 2024
                '%m/%d/%Y',   # 01/15/2024
                '%d/%m/%Y',   # 15/01/2024
                '%B %d, %Y'   # January 15, 2024
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str.strip(), fmt)
                except:
                    continue
            
            return None
        except:
            return None

    def process_emails(self, days_back: int = 30) -> List[Dict]:
        """Process all PayPal Pay in 4 emails and extract transaction data"""
        if not self.connect():
            return []
        
        try:
            message_ids = self.search_paypal_emails(days_back)
            transactions = []
            
            for i, message_id in enumerate(message_ids, 1):
                logger.info(f"Processing email {i}/{len(message_ids)}: {message_id}")
                transaction = self.parse_email_content(message_id)
                
                if transaction:
                    transactions.append(transaction)
                    logger.info(f"Extracted transaction: {transaction['merchant']} - ${abs(transaction['amount'])}")
                else:
                    logger.warning(f"Failed to extract transaction from email {message_id}")
            
            logger.info(f"Successfully processed {len(transactions)} transactions from {len(message_ids)} emails")
            return transactions
            
        finally:
            self.disconnect()
    
    def export_to_csv(self, transactions: List[Dict], filename: str = None) -> str:
        """Export transactions to CSV format compatible with existing parser"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"paypal_payin4_transactions_{timestamp}.csv"
        
        # CSV headers compatible with existing transaction parser
        headers = [
            'Run Date', 'Account', 'Account Number', 'Action', 'Symbol', 'Description',
            'Type', 'Exchange Quantity', 'Exchange Currency', 'Quantity', 'Currency',
            'Price', 'Exchange Rate', 'Commission', 'Fees', 'Accrued Interest',
            'Amount', 'Settlement Date'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            
            for txn in transactions:
                # Map our extracted data to CSV format
                csv_row = {
                    'Run Date': txn['date'],
                    'Account': txn['account'],
                    'Account Number': '',
                    'Action': f"DEBIT CARD PURCHASE {txn['merchant']}",
                    'Symbol': '',
                    'Description': txn['description'],
                    'Type': txn['type'],
                    'Exchange Quantity': '',
                    'Exchange Currency': '',
                    'Quantity': '',
                    'Currency': 'USD',
                    'Price': '',
                    'Exchange Rate': '',
                    'Commission': '',
                    'Fees': '',
                    'Accrued Interest': '',
                    'Amount': txn['amount'],
                    'Settlement Date': txn['date']
                }
                writer.writerow(csv_row)
        
        logger.info(f"Exported {len(transactions)} transactions to {filename}")
        return filename

def main():
    # Check if hard-coded config should be used
    if HARD_CODED_CONFIG.get('auto_run') and HARD_CODED_CONFIG.get('email_address') and HARD_CODED_CONFIG.get('password'):
        # Use hard-coded configuration
        email_address = HARD_CODED_CONFIG['email_address']
        password = HARD_CODED_CONFIG['password']
        imap_server = HARD_CODED_CONFIG['imap_server']
        imap_port = HARD_CODED_CONFIG['imap_port']
        days_back = HARD_CODED_CONFIG['days_back']
        dry_run = False
        output_file = None
        verbose = True  # Enable verbose for LLM interaction
        debug = True   # Enable debug logging
        
        print(f"Using hard-coded configuration for {email_address}")
        
    else:
        # Use command-line arguments
        parser = argparse.ArgumentParser(description='Extract PayPal Pay in 4 transactions from email')
        parser.add_argument('--email', required=not HARD_CODED_CONFIG.get('email_address'), 
                          default=HARD_CODED_CONFIG.get('email_address'), help='Email address')
        parser.add_argument('--password', default=HARD_CODED_CONFIG.get('password'), 
                          help='Email password (will prompt if not provided)')
        parser.add_argument('--server', default=HARD_CODED_CONFIG.get('imap_server', 'roetto.org'), 
                          help='IMAP server (default: roetto.org)')
        parser.add_argument('--port', type=int, default=HARD_CODED_CONFIG.get('imap_port', 993), 
                          help='IMAP port (default: 993)')
        parser.add_argument('--days', type=int, default=HARD_CODED_CONFIG.get('days_back', 30), 
                          help='Days back to search (default: 30)')
        parser.add_argument('--output', help='Output CSV filename')
        parser.add_argument('--dry-run', action='store_true', help='Show what would be extracted without creating CSV')
        parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
        
        args = parser.parse_args()
        
        email_address = args.email
        password = args.password
        imap_server = args.server
        imap_port = args.port
        days_back = args.days
        dry_run = args.dry_run
        output_file = args.output
        verbose = args.verbose
        
        # Get password if not provided
        if not password:
            password = getpass.getpass(f"Enter password for {email_address}: ")
    
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if 'debug' in locals() and debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create parser and process emails
    paypal_parser = PayPalEmailParser(
        email_address=email_address,
        password=password,
        imap_server=imap_server,
        imap_port=imap_port
    )
    
    logger.info(f"Searching for PayPal Pay in 4 emails from the last {days_back} days...")
    transactions = paypal_parser.process_emails(days_back)
    
    if not transactions:
        logger.warning("No transactions found")
        return
    
    # Display results
    print(f"\nFound {len(transactions)} PayPal Pay in 4 transactions:")
    print("-" * 60)
    for txn in transactions:
        print(f"{txn['date']} | {txn['merchant']:30} | ${abs(txn['amount']):>8.2f}")
    
    if not dry_run:
        # Export to CSV
        csv_filename = paypal_parser.export_to_csv(transactions, output_file)
        print(f"\nTransactions exported to: {csv_filename}")
        print(f"You can now process this file with: python3 main.py --process-existing")
    else:
        print("\nDry run completed - no CSV file created")

if __name__ == "__main__":
    main()
