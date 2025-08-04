import csv
import os
import hashlib
import shutil
import re
from datetime import datetime
from typing import Dict, List, Optional
from database import TransactionDB
import logging

class CSVParser:
    def __init__(self, db: TransactionDB):
        self.db = db
        self.logger = logging.getLogger(__name__)
    
    def get_file_hash(self, filepath: str) -> str:
        """Generate hash of file contents for change detection"""
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def clean_numeric_value(self, value: str) -> Optional[float]:
        """Clean and convert numeric values, handling empty strings and commas"""
        if not value or value.strip() == '':
            return None
        try:
            # Remove commas and convert to float
            cleaned = value.replace(',', '').strip()
            return float(cleaned) if cleaned else None
        except (ValueError, AttributeError):
            return None
    
    def convert_date_to_iso(self, date_str: str) -> Optional[str]:
        """Convert MM/DD/YYYY date format to YYYY-MM-DD (ISO format)"""
        if not date_str or not date_str.strip():
            return None
        
        try:
            # Parse MM/DD/YYYY format
            date_obj = datetime.strptime(date_str.strip(), '%m/%d/%Y')
            # Return as YYYY-MM-DD
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            try:
                # Try alternative format MM/DD/YY
                date_obj = datetime.strptime(date_str.strip(), '%m/%d/%y')
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                self.logger.warning(f"Could not parse date: {date_str}")
                return None
    
    def extract_payee(self, action: str, description: str = "") -> Optional[str]:
        """Extract payee name from action column and optionally description"""
        if not action:
            return None
        
        action_upper = action.upper().strip()
        
        # Pattern 1: Direct debit patterns like "DIRECT DEBIT STATE FARM RO SFPP (Cash)"
        direct_debit_match = re.search(r'DIRECT DEBIT\s+([A-Z][A-Z0-9\s&.]+?)(?:\s+[A-Z]{2,3}\s+[A-Z0-9]+|\s*\([^)]+\)|$)', action_upper)
        if direct_debit_match:
            payee = direct_debit_match.group(1).strip()
            return self._clean_payee_name(payee)
        
        # Pattern 2: PayPal transactions like "DEBIT CARD PURCHASE PAYPAL *Roetto Julie"
        if 'PAYPAL *' in action_upper:
            paypal_match = re.search(r'PAYPAL \*([A-Z][A-Z0-9\s-]+?)(?:\s+VISA|\s+\d{3}-\d{3}-\d{4}|\s+CA\d|\s*\(|$)', action_upper)
            if paypal_match:
                payee = f"PayPal ({paypal_match.group(1).strip()})"
                return payee
        
        # Pattern 3a: POS with special codes like "DEBIT CARD PURCHASE POSNCZT UBER EATS*"
        pos_special_match = re.search(r'DEBIT CARD PURCHASE\s+POS[A-Z]+\s+([A-Z][A-Z0-9\s*&#.-]+?)(?:\s+[A-Z]{2}\d|\s+[A-Z]{2}\s+\d|$)', action_upper)
        if pos_special_match:
            payee = pos_special_match.group(1).strip()
            return self._clean_payee_name(payee)
        
        # Pattern 3b: POS transactions like "DEBIT CARD PURCHASE POS1825 WAL-MART #1825"
        pos_match = re.search(r'DEBIT CARD PURCHASE\s+POS\d+\s+([A-Z][A-Z0-9\s&#.-]+?)(?:\s+#\d+|\s+[A-Z]{2}\d|\s+[A-Z]{2}\s+\d|$)', action_upper)
        if pos_match:
            payee = pos_match.group(1).strip()
            return self._clean_payee_name(payee)
        
        # Pattern 3c: Store with phone numbers like "DEBIT CARD PURCHASE LOWES #00907* 866-483-7521"
        store_phone_match = re.search(r'DEBIT CARD PURCHASE\s+([A-Z][A-Z0-9\s&#.-]+?)\s+#?\d+\*?\s+\d{3}-\d{3}-\d{4}', action_upper)
        if store_phone_match:
            payee = store_phone_match.group(1).strip()
            return self._clean_payee_name(payee)
        
        # Pattern 4: General debit card purchases like "DEBIT CARD PURCHASE WALMART SUPERCENTER"
        debit_card_match = re.search(r'DEBIT CARD PURCHASE\s+([A-Z][A-Z0-9\s&.]+?)(?:\s+\d|\s+[A-Z]{2}\d|$)', action_upper)
        if debit_card_match:
            payee = debit_card_match.group(1).strip()
            return self._clean_payee_name(payee)
        
        # Pattern 5: ACH patterns like "ACH DEBIT NETFLIX.COM"
        ach_match = re.search(r'ACH\s+(?:DEBIT|CREDIT)\s+([A-Z][A-Z0-9\s&.]+?)(?:\s+\d|\s+[A-Z]{2}\d|$)', action_upper)
        if ach_match:
            payee = ach_match.group(1).strip()
            return self._clean_payee_name(payee)
        
        # Pattern 6: Check patterns like "CHECK #1234 TO JOHN DOE"
        check_match = re.search(r'CHECK\s+#?\d+\s+(?:TO\s+)?([A-Z][A-Z0-9\s&.]+?)(?:\s+\d|\s+[A-Z]{2}\d|$)', action_upper)
        if check_match:
            payee = check_match.group(1).strip()
            return self._clean_payee_name(payee)
        
        # Pattern 7: Wire transfer patterns
        wire_match = re.search(r'WIRE\s+(?:TRANSFER\s+)?(?:TO\s+)?([A-Z][A-Z0-9\s&.]+?)(?:\s+\d|\s+[A-Z]{2}\d|$)', action_upper)
        if wire_match:
            payee = wire_match.group(1).strip()
            return self._clean_payee_name(payee)
        
        # Pattern 8: Online transfer patterns
        transfer_match = re.search(r'(?:ONLINE\s+)?TRANSFER\s+(?:TO\s+)?([A-Z][A-Z0-9\s&.]+?)(?:\s+\d|\s+[A-Z]{2}\d|$)', action_upper)
        if transfer_match:
            payee = transfer_match.group(1).strip()
            return self._clean_payee_name(payee)
        
        # Pattern 9: General merchant patterns - look for company names
        merchant_patterns = [
            r'([A-Z][A-Z0-9\s&.]+(?:INC|CORP|LLC|CO|COMPANY))',  # Company suffixes
            r'([A-Z][A-Z0-9\s&.]+(?:BANK|CREDIT UNION|FEDERAL))',  # Financial institutions
            r'([A-Z][A-Z0-9\s&.]+(?:RESTAURANT|CAFE|STORE|MARKET|PHARMACY))',  # Business types
        ]
        
        for pattern in merchant_patterns:
            match = re.search(pattern, action_upper)
            if match:
                payee = match.group(1).strip()
                return self._clean_payee_name(payee)
        
        # Pattern 8: If description has useful info, try to extract from there
        if description:
            desc_upper = description.upper().strip()
            # Look for common payee indicators in description
            desc_match = re.search(r'(?:^|\s)([A-Z][A-Z0-9\s&.]{2,20})(?:\s|$)', desc_upper)
            if desc_match and len(desc_match.group(1).strip()) > 2:
                payee = desc_match.group(1).strip()
                return self._clean_payee_name(payee)
        
        return None
    
    def _clean_payee_name(self, payee: str) -> str:
        """Clean and standardize payee names"""
        if not payee:
            return None
        
        # Remove common suffixes and prefixes that aren't part of the business name
        payee = payee.strip()
        
        # Remove trailing location codes, numbers, etc.
        payee = re.sub(r'\s+\d{3,}$', '', payee)  # Remove trailing numbers
        payee = re.sub(r'\s+[A-Z]{2}\s*\d+$', '', payee)  # Remove state codes with numbers
        
        # Clean up common variations
        payee_mapping = {
            'STATE FARM': 'State Farm',
            'AMAZON': 'Amazon',
            'AMAZON.COM': 'Amazon', 
            'WALMART': 'Walmart',
            'WALMART SUPERCENTER': 'Walmart',
            'WAL-MART': 'Walmart',
            'WAL-MART SUPER': 'Walmart',
            'TARGET': 'Target',
            'STARBUCKS': 'Starbucks',
            'MCDONALDS': 'McDonald\'s',
            'NETFLIX': 'Netflix',
            'NETFLIX.COM': 'Netflix',
            'SPOTIFY': 'Spotify',
            'GOOGLE': 'Google',
            'MICROSOFT': 'Microsoft',
            'APPLE': 'Apple',
            'PAYPAL': 'PayPal',
            'VENMO': 'Venmo',
            'UBER': 'Uber',
            'UBER EATS': 'Uber Eats',
            'LYFT': 'Lyft',
            'CVS': 'CVS Pharmacy',
            'LOWES': 'Lowe\'s',
            'WALGREENS': 'Walgreens',
            'HOME DEPOT': 'Home Depot'
        }
        
        # Check for exact matches first
        if payee in payee_mapping:
            return payee_mapping[payee]
        
        # Check for partial matches
        for key, value in payee_mapping.items():
            if key in payee:
                return value
        
        # Convert to title case for better readability
        return payee.title()
    
    def extract_account_from_filename(self, filepath: str) -> Optional[tuple]:
        """Extract account info from filename patterns like History_for_Account_Z23693697.csv"""
        filename = os.path.basename(filepath)
        
        # Pattern: History_for_Account_Z23693697.csv
        match = re.search(r'History_for_Account_([Z]?\d+)', filename)
        if match:
            account_number = match.group(1)
            
            # Map account numbers to existing account names
            account_mapping = {
                'Z23693697': 'Cash Management (Joint WROS)',
                'Z06431462': 'Individual - TOD',
                'Z09658794': 'Uniform Transfers to Minors (UTMA)',
                'Z21438083': 'Uniform Transfers to Minors (UTMA)',
                'Z21990055': 'Declan- Youth Account',
                'Z24733398': 'Leia - Youth Account',
                'Z28391843': 'Emergency Fund',
                '239574793': 'ROTH IRA'
            }
            
            account_name = account_mapping.get(account_number, f"Unknown Account ({account_number})")
            return (account_name, account_number)
        
        return None
    
    def normalize_account_info(self, account: str, account_number: str) -> tuple:
        """Normalize account name and number to handle duplicate formats"""
        if not account:
            return account, account_number
        
        # Extract account number from account name if it's embedded
        account_num_patterns = [
            r'\(([Z]?\d+)\)',  # Match (Z23693697) or (239574793)
            r'\s+([Z]?\d+)\s+\(\)',  # Match Z06431462 ()
            r'\s+([Z]?\d+)$',  # Match trailing Z06431462
        ]
        
        extracted_number = None
        clean_account = account.strip()
        
        for pattern in account_num_patterns:
            match = re.search(pattern, account)
            if match:
                extracted_number = match.group(1)
                # Remove the matched pattern from account name
                clean_account = re.sub(pattern, '', account).strip()
                break
        
        # Use extracted number if we found one, otherwise use provided account_number
        final_account_number = extracted_number or account_number or ''
        
        # Clean up account name
        clean_account = re.sub(r'\s+', ' ', clean_account)  # Normalize whitespace
        clean_account = clean_account.strip()
        
        return clean_account, final_account_number
    
    def extract_transaction_type(self, action: str) -> str:
        """Extract transaction type from action column"""
        if not action:
            return "Unknown"
        
        action_upper = action.upper().strip()
        
        # Investment transactions
        if any(keyword in action_upper for keyword in ["YOU BOUGHT", "YOU SOLD"]):
            return "Investment Trade"
        elif "DIVIDEND RECEIVED" in action_upper:
            return "Dividend"
        elif "REINVESTMENT" in action_upper:
            return "Reinvestment"
        
        # Transfer transactions
        elif any(keyword in action_upper for keyword in ["TRANSFERRED FROM", "TRANSFERRED TO"]):
            return "Transfer"
        elif "CASH CONTRIBUTION" in action_upper:
            return "Contribution"
        
        # Direct transactions
        elif "DIRECT DEPOSIT" in action_upper:
            return "Direct Deposit"
        elif "DIRECT DEBIT" in action_upper:
            return "Direct Debit"
        
        # Card transactions
        elif "DEBIT CARD" in action_upper:
            return "Debit Card"
        elif "CREDIT CARD" in action_upper:
            return "Credit Card"
        
        # ACH transactions
        elif action_upper.startswith("ACH"):
            if "DEBIT" in action_upper:
                return "ACH Debit"
            elif "CREDIT" in action_upper:
                return "ACH Credit"
            else:
                return "ACH"
        
        # Wire transfers
        elif "WIRE" in action_upper:
            return "Wire Transfer"
        
        # Checks
        elif action_upper.startswith("CHECK"):
            return "Check"
        
        # ATM transactions
        elif "ATM" in action_upper:
            return "ATM"
        
        # Fee transactions
        elif any(keyword in action_upper for keyword in ["FEE", "CHARGE"]):
            return "Fee"
        
        # Interest
        elif "INTEREST" in action_upper:
            return "Interest"
        
        # Default fallback - try to extract from the original type column or use generic
        return "Other"
    
    
    def parse_csv_file(self, filepath: str) -> List[Dict]:
        """Parse a CSV file and return list of transaction dictionaries"""
        transactions = []
        
        with open(filepath, 'r', encoding='utf-8-sig') as file:  # utf-8-sig handles BOM
            # Skip empty lines at the beginning
            content = file.read().strip()
            if not content:
                self.logger.warning(f"Empty file: {filepath}")
                return []
            
            lines = content.split('\n')
            
            # Find the header row (first non-empty line)
            header_found = False
            csv_reader = None
            
            for i, line in enumerate(lines):
                if line.strip() and not header_found:
                    # Check if this looks like our expected header (multiple formats)
                    if ('Run Date' in line and 'Amount' in line and 
                        ('Account' in line or 'Action' in line)):
                        # Start CSV reader from this line
                        remaining_lines = lines[i:]
                        csv_reader = csv.DictReader(remaining_lines)
                        header_found = True
                        break
            
            if not header_found:
                self.logger.error(f"No valid header found in {filepath}")
                return []
            
            for row_num, row in enumerate(csv_reader, start=1):
                try:
                    # Skip empty rows
                    if not any(row.values()):
                        continue
                    
                    action = (row.get('Action') or '').strip()
                    description = (row.get('Description') or '').strip()
                    
                    # Skip transactions with 'OUTSTAND AUTH' in action field
                    if 'OUTSTAND AUTH' in action.upper():
                        self.logger.debug(f"Skipping row {row_num}: contains OUTSTAND AUTH")
                        continue
                    
                    # Normalize account information (handle missing Account columns)
                    raw_account = (row.get('Account') or '').strip()
                    raw_account_number = (row.get('Account Number') or '').strip()
                    
                    # If no account info in CSV, extract from filename
                    if not raw_account and not raw_account_number:
                        account_from_filename = self.extract_account_from_filename(filepath)
                        if account_from_filename:
                            raw_account, raw_account_number = account_from_filename
                    
                    clean_account, clean_account_number = self.normalize_account_info(raw_account, raw_account_number)
                    
                    # Extract enhanced transaction type
                    enhanced_type = self.extract_transaction_type(action)
                    symbol = (row.get('Symbol') or '').strip() or None
                    
                    # Rule: Only investment transactions should have payee as None and symbol populated
                    is_investment = enhanced_type in ["Investment Trade", "Dividend", "Reinvestment"] or symbol is not None
                    
                    # Convert dates to ISO format
                    run_date_iso = self.convert_date_to_iso((row.get('Run Date') or '').strip())
                    settlement_date_iso = self.convert_date_to_iso((row.get('Settlement Date') or '').strip()) if row.get('Settlement Date') else None
                    
                    transaction = {
                        'run_date': run_date_iso,
                        'account': clean_account,
                        'account_number': clean_account_number,
                        'action': action,
                        'symbol': symbol,
                        'description': description,
                        'type': enhanced_type,
                        'exchange_quantity': self.clean_numeric_value(row.get('Exchange Quantity', '')),
                        'exchange_currency': (row.get('Exchange Currency') or '').strip() or None,
                        'quantity': self.clean_numeric_value(row.get('Quantity', '')),
                        'currency': (row.get('Currency') or '').strip(),
                        'price': self.clean_numeric_value(row.get('Price', '') or row.get('Price ($)', '')),
                        'exchange_rate': self.clean_numeric_value(row.get('Exchange Rate', '')),
                        'commission': self.clean_numeric_value(row.get('Commission', '') or row.get('Commission ($)', '')),
                        'fees': self.clean_numeric_value(row.get('Fees', '') or row.get('Fees ($)', '')),
                        'accrued_interest': self.clean_numeric_value(row.get('Accrued Interest', '') or row.get('Accrued Interest ($)', '')),
                        'amount': self.clean_numeric_value(row.get('Amount', '') or row.get('Amount ($)', '')),
                        'settlement_date': settlement_date_iso,
                        'payee': None if is_investment else self.extract_payee(action, description)
                    }
                    
                    # Validate required fields
                    if not transaction['run_date'] or transaction['amount'] is None:
                        self.logger.warning(f"Skipping row {row_num} in {filepath}: missing required fields")
                        continue
                    
                    # Try to auto-classify using cached patterns
                    pattern_match = self.db.find_matching_pattern(
                        transaction.get('description', ''), 
                        transaction.get('action', ''),
                        transaction.get('payee', '')
                    )
                    
                    if pattern_match:
                        cat_id, sub_id, confidence, cat_name, sub_name = pattern_match
                        transaction['category_id'] = cat_id
                        transaction['subcategory_id'] = sub_id
                        transaction['note'] = f"Auto-classified from pattern (confidence: {confidence:.2f})"
                        self.logger.info(f"Auto-classified transaction as {cat_name}/{sub_name} (confidence: {confidence:.2f})")
                    
                    transactions.append(transaction)
                    
                except Exception as e:
                    self.logger.error(f"Error parsing row {row_num} in {filepath}: {e}")
                    continue
        
        return transactions
    
    def process_file(self, filepath: str) -> Dict[str, int]:
        """Process a single CSV file and return statistics"""
        filename = os.path.basename(filepath)
        file_hash = self.get_file_hash(filepath)
        
        # Check if file already processed
        if self.db.is_file_processed(filename, file_hash):
            self.logger.info(f"File {filename} already processed, skipping")
            return {'processed': 0, 'duplicates': 0, 'errors': 0}
        
        self.logger.info(f"Processing file: {filename}")
        
        try:
            transactions = self.parse_csv_file(filepath)
            
            # If parsing failed (no transactions), don't mark as processed
            if not transactions:
                self.logger.error(f"No transactions parsed from {filename}")
                return {'processed': 0, 'duplicates': 0, 'errors': 1}
            
            processed_count = 0
            duplicate_count = 0
            error_count = 0
            
            for transaction in transactions:
                try:
                    if self.db.insert_transaction(transaction, filename):
                        processed_count += 1
                    else:
                        duplicate_count += 1
                except Exception as e:
                    self.logger.error(f"Error inserting transaction: {e}")
                    error_count += 1
            
            # Only mark file as processed if we successfully processed some transactions
            # and didn't encounter any database errors
            if processed_count > 0 or (duplicate_count > 0 and error_count == 0):
                self.db.mark_file_processed(filename, file_hash, len(transactions))
                self.logger.info(f"Completed {filename}: {processed_count} new, {duplicate_count} duplicates")
                return {
                    'processed': processed_count,
                    'duplicates': duplicate_count,
                    'errors': error_count
                }
            else:
                self.logger.error(f"Failed to process any transactions from {filename}")
                return {'processed': 0, 'duplicates': 0, 'errors': error_count or 1}
            
        except Exception as e:
            self.logger.error(f"Error processing file {filename}: {e}")
            return {'processed': 0, 'duplicates': 0, 'errors': 1}
    
    def move_processed_file(self, filepath: str, processed_dir: str = "processed"):
        """Move processed file to a subdirectory"""
        try:
            # Create processed directory if it doesn't exist
            base_dir = os.path.dirname(filepath)
            processed_path = os.path.join(base_dir, processed_dir)
            os.makedirs(processed_path, exist_ok=True)
            
            # Move file
            filename = os.path.basename(filepath)
            destination = os.path.join(processed_path, filename)
            
            # If destination exists, add timestamp
            if os.path.exists(destination):
                name, ext = os.path.splitext(filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                destination = os.path.join(processed_path, f"{name}_{timestamp}{ext}")
            
            shutil.move(filepath, destination)
            self.logger.info(f"Moved {filename} to {processed_dir}/")
            
        except Exception as e:
            self.logger.error(f"Error moving file {filepath}: {e}")
    
    def scan_and_process_directory(self, directory: str, move_processed: bool = True) -> Dict[str, int]:
        """Scan directory for CSV files and process them"""
        total_stats = {'processed': 0, 'duplicates': 0, 'errors': 0, 'files': 0}
        
        if not os.path.exists(directory):
            self.logger.error(f"Directory does not exist: {directory}")
            return total_stats
        
        # Find all CSV files
        csv_files = []
        for filename in os.listdir(directory):
            if filename.lower().endswith('.csv') and os.path.isfile(os.path.join(directory, filename)):
                csv_files.append(os.path.join(directory, filename))
        
        if not csv_files:
            self.logger.info(f"No CSV files found in {directory}")
            return total_stats
        
        self.logger.info(f"Found {len(csv_files)} CSV files to process")
        
        for filepath in csv_files:
            stats = self.process_file(filepath)
            
            # Update totals
            for key in ['processed', 'duplicates', 'errors']:
                total_stats[key] += stats[key]
            total_stats['files'] += 1
            
            # Move processed file if requested and no errors
            if move_processed and stats['errors'] == 0:
                self.move_processed_file(filepath)
        
        return total_stats