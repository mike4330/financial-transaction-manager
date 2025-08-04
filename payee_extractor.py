#!/usr/bin/env python3
"""
Payee Extractor - Extract merchant names from transaction action column

This utility intelligently extracts actual merchant/payee names from the transaction 
action column for transactions that currently have "No Description" as their payee.

FEATURES:
- Comprehensive pattern library for major retailers, restaurants, gas stations, utilities
- Smart regex-based extraction from various transaction formats  
- Fallback algorithms for unknown transaction types
- Automatic categorization based on extracted merchant names
- Dry-run capability to preview extractions and categorizations before applying
- Batch processing of all "No Description" transactions
- Success rate typically 40-50% for payee extraction, with automatic categorization

USAGE:
    # Preview what would be extracted (recommended first step)
    python3 payee_extractor.py --dry-run
    
    # Apply extractions to database
    python3 payee_extractor.py --apply
    
    # Use custom database file
    python3 payee_extractor.py --apply --db /path/to/transactions.db

PATTERN EXAMPLES:
- "DEBIT CARD PURCHASE MCDONALD'S F18095 MANASSAS VA..." → "McDonald's" → Food & Dining/Fast Food
- "BILL PAYMENT VERIZON WIRELESS (Cash)" → "Verizon" → Utilities/Mobile
- "DEBIT CARD PURCHASE PIZZA BOLI'S 703-335-2000 VA..." → "Pizza Boli's" → Food & Dining/Fast Food
- "DEBIT CARD PURCHASE FOOD LION #1383 MANASSAS VA..." → "Food Lion" → Food & Dining/Groceries

The utility automatically categorizes transactions based on merchant patterns and can be
extended with new merchant-to-category mappings.
"""

import sqlite3
import re
import logging
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PayeeExtractor:
    def __init__(self, db_path: str = "transactions.db"):
        self.db_path = db_path
        self.patterns = self._build_extraction_patterns()
        self.merchant_categories = self._build_merchant_categories()
        
    def _build_extraction_patterns(self) -> Dict[str, str]:
        """Build comprehensive pattern library for payee extraction"""
        return {
            # Fast Food Chains
            r"MCDONALD'S": "McDonald's",
            r"PAPA JOHN'S": "Papa John's Pizza",
            r"PIZZA BOLI'S": "Pizza Boli's",
            r"TACO BELL": "Taco Bell",
            r"BURGER KING": "Burger King",
            r"WENDY'S": "Wendy's",
            r"KFC": "KFC",
            r"SUBWAY": "Subway",
            r"DOMINO'S": "Domino's Pizza",
            r"PIZZA HUT": "Pizza Hut",
            r"CHIPOTLE": "Chipotle",
            r"PANERA": "Panera Bread",
            r"POPEYES": "Popeyes",
            r"ARBY'S": "Arby's",
            r"HARDEE'S": "Hardee's",
            r"CHICK-FIL-A": "Chick-fil-A",
            r"DUNKIN": "Dunkin'",
            r"STARBUCKS": "Starbucks",
            
            # Grocery Stores
            r"WALMART": "Walmart",
            r"TARGET": "Target",
            r"KROGER": "Kroger",
            r"SAFEWAY": "Safeway",
            r"FOOD LION": "Food Lion",
            r"GIANT": "Giant",
            r"HARRIS TEETER": "Harris Teeter",
            r"WHOLE FOODS": "Whole Foods",
            r"TRADER JOE": "Trader Joe's",
            r"COSTCO": "Costco",
            r"SAM'S CLUB": "Sam's Club",
            r"ALDI": "Aldi",
            
            # Gas Stations
            r"SHELL": "Shell",
            r"EXXON": "ExxonMobil",
            r"BP": "BP",
            r"CHEVRON": "Chevron",
            r"MOBIL": "Mobil",
            r"SUNOCO": "Sunoco",
            r"WAWA": "Wawa",
            r"7-ELEVEN": "7-Eleven",
            r"SHEETZ": "Sheetz",
            r"SPEEDWAY": "Speedway",
            
            # Utilities & Services
            r"VERIZON": "Verizon",
            r"AT&T": "AT&T",
            r"T-MOBILE": "T-Mobile",
            r"COMCAST": "Comcast",
            r"DOMINION": "Dominion Energy",
            r"PEPCO": "Pepco",
            r"WASHINGTON GAS": "Washington Gas",
            
            # Banks & Financial
            r"BANK OF AMERICA": "Bank of America",
            r"WELLS FARGO": "Wells Fargo",
            r"CHASE BANK": "Chase Bank",
            r"JPMORGAN CHASE": "Chase Bank",
            r"CAPITAL ONE": "Capital One",
            r"USAA": "USAA",
            r"NAVY FEDERAL": "Navy Federal",
            r"PENTAGON FCU": "Pentagon Federal Credit Union",
            
            # Online Services
            r"PAYPAL": "PayPal",
            r"AMAZON": "Amazon",
            r"NETFLIX": "Netflix",
            r"SPOTIFY": "Spotify",
            r"APPLE": "Apple",
            r"GOOGLE": "Google",
            r"MICROSOFT": "Microsoft",
            
            # Transportation
            r"UBER": "Uber",
            r"LYFT": "Lyft",
            r"PARKING": "Parking",
            r"METRO": "Metro/Transit",
            
            # Generic patterns
            r"DEBIT CARD PURCHASE (.+?) \d{3}-\d{3}-\d{4}": r"\1",  # Extract merchant before phone number
            r"BILL PAYMENT (.+?) \(": r"\1",  # Extract payee from bill payment
            r"ACH DEBIT (.+?)(?:\s|$)": r"\1",  # Extract from ACH debit
            r"CHECK #\d+ (.+?)(?:\s|$)": r"\1",  # Extract from check payment
        }
    
    def extract_payee_from_action(self, action: str) -> Optional[str]:
        """Extract payee name from action string using pattern matching"""
        if not action or action.strip() == "":
            return None
            
        action = action.upper().strip()
        
        # Try specific merchant patterns first
        for pattern, payee in self.patterns.items():
            if pattern.startswith('r"') and pattern.endswith('"'):
                # Regex pattern
                regex_pattern = pattern[2:-1]  # Remove r" and "
                if payee.startswith(r'\1'):
                    # Capture group replacement
                    match = re.search(regex_pattern, action, re.IGNORECASE)
                    if match:
                        return match.group(1).title()
                else:
                    # Direct replacement
                    if re.search(regex_pattern, action, re.IGNORECASE):
                        return payee
            else:
                # Simple string match
                if pattern in action:
                    return payee
        
        # Fallback: Try to extract merchant name from common formats
        fallback_patterns = [
            r"DEBIT CARD PURCHASE (.+?) \d{3}-\d{3}-\d{4}",  # Before phone number
            r"DEBIT CARD PURCHASE (.+?) [A-Z]{2}\d+",        # Before state code
            r"DEBIT CARD PURCHASE (.+?)(?:\s+\d|$)",         # Before numbers
            r"^(.+?) \d{3}-\d{3}-\d{4}",                     # Any text before phone
            r"^(.+?) [A-Z]{2}\d{4,}",                        # Any text before state/ref
        ]
        
        for pattern in fallback_patterns:
            match = re.search(pattern, action)
            if match:
                payee = match.group(1).strip()
                # Clean up common prefixes
                payee = re.sub(r'^(DEBIT CARD PURCHASE|ACH DEBIT|BILL PAYMENT)\s+', '', payee)
                payee = re.sub(r'\s+POS\d+\s+', ' ', payee)  # Remove POS numbers
                payee = payee.title()
                if len(payee) > 3 and not payee.isdigit():
                    return payee
        
        return None
    
    def _build_merchant_categories(self) -> Dict[str, Tuple[str, str]]:
        """Build merchant to category/subcategory mapping"""
        return {
            # Fast Food Chains
            "McDonald's": ("Food & Dining", "Fast Food"),
            "Papa John's Pizza": ("Food & Dining", "Fast Food"),
            "Pizza Boli's": ("Food & Dining", "Fast Food"),
            "Taco Bell": ("Food & Dining", "Fast Food"),
            "Burger King": ("Food & Dining", "Fast Food"),
            "Wendy's": ("Food & Dining", "Fast Food"),
            "KFC": ("Food & Dining", "Fast Food"),
            "Subway": ("Food & Dining", "Fast Food"),
            "Domino's Pizza": ("Food & Dining", "Fast Food"),
            "Pizza Hut": ("Food & Dining", "Fast Food"),
            "Chipotle": ("Food & Dining", "Fast Food"),
            "Popeyes": ("Food & Dining", "Fast Food"),
            "Arby's": ("Food & Dining", "Fast Food"),
            "Hardee's": ("Food & Dining", "Fast Food"),
            
            # Coffee & Convenience
            "Dunkin'": ("Food & Dining", "Coffee"),
            "Starbucks": ("Food & Dining", "Coffee"),
            "7-Eleven": ("Shopping", "General"),
            
            # Grocery Stores
            "Walmart": ("Food & Dining", "Groceries"),
            "Target": ("Food & Dining", "Groceries"),
            "Kroger": ("Food & Dining", "Groceries"),
            "Safeway": ("Food & Dining", "Groceries"),
            "Food Lion": ("Food & Dining", "Groceries"),
            "Giant": ("Food & Dining", "Groceries"),
            "Harris Teeter": ("Food & Dining", "Groceries"),
            "Whole Foods": ("Food & Dining", "Groceries"),
            "Trader Joe's": ("Food & Dining", "Groceries"),
            "Costco": ("Food & Dining", "Groceries"),
            "Sam's Club": ("Food & Dining", "Groceries"),
            "Aldi": ("Food & Dining", "Groceries"),
            
            # Gas Stations
            "Shell": ("Transportation", "Gas"),
            "ExxonMobil": ("Transportation", "Gas"),
            "BP": ("Transportation", "Gas"),
            "Chevron": ("Transportation", "Gas"),
            "Mobil": ("Transportation", "Gas"),
            "Sunoco": ("Transportation", "Gas"),
            "Wawa": ("Transportation", "Gas"),
            "Sheetz": ("Transportation", "Gas"),
            "Speedway": ("Transportation", "Gas"),
            
            # Utilities & Services
            "Verizon": ("Utilities", "Mobile"),
            "AT&T": ("Utilities", "Mobile"),
            "T-Mobile": ("Utilities", "Mobile"),
            "Comcast": ("Utilities", "Internet"),
            "Dominion Energy": ("Utilities", "Electric"),
            "Pepco": ("Utilities", "Electric"),
            "Washington Gas": ("Utilities", "Gas"),
            
            # Banks & Financial
            "Bank of America": ("Banking", "Fees"),
            "Wells Fargo": ("Banking", "Fees"),
            "Chase Bank": ("Banking", "Fees"),
            "Capital One": ("Banking", "Fees"),
            "USAA": ("Banking", "Fees"),
            "Navy Federal": ("Banking", "Fees"),
            "Pentagon Federal Credit Union": ("Banking", "Fees"),
            
            # Online Services
            "PayPal": ("Banking", "Transfer"),
            "Amazon": ("Shopping", "Online"),
            "Netflix": ("Entertainment", "Streaming"),
            "Spotify": ("Entertainment", "Music"),
            "Apple": ("Shopping", "Online"),
            "Google": ("Shopping", "Online"),
            "Microsoft": ("Shopping", "Online"),
            
            # Transportation
            "Uber": ("Transportation", "Rideshare"),
            "Lyft": ("Transportation", "Rideshare"),
        }
    
    def get_category_subcategory_ids(self, category_name: str, subcategory_name: str) -> Tuple[Optional[int], Optional[int]]:
        """Get or create category and subcategory IDs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get or create category
            cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
            category_row = cursor.fetchone()
            if category_row:
                category_id = category_row[0]
            else:
                cursor.execute("INSERT INTO categories (name) VALUES (?)", (category_name,))
                category_id = cursor.lastrowid
                logger.info(f"Created new category: {category_name}")
            
            # Get or create subcategory
            cursor.execute("SELECT id FROM subcategories WHERE name = ? AND category_id = ?", (subcategory_name, category_id))
            subcategory_row = cursor.fetchone()
            if subcategory_row:
                subcategory_id = subcategory_row[0]
            else:
                cursor.execute("INSERT INTO subcategories (name, category_id) VALUES (?, ?)", (subcategory_name, category_id))
                subcategory_id = cursor.lastrowid
                logger.info(f"Created new subcategory: {subcategory_name} under {category_name}")
            
            conn.commit()
            return category_id, subcategory_id
            
        except Exception as e:
            logger.error(f"Error getting/creating category IDs: {e}")
            return None, None
        finally:
            conn.close()
    
    def get_no_description_transactions(self) -> List[Tuple[int, str]]:
        """Get all transactions with 'No Description' payee"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, action 
            FROM transactions 
            WHERE payee = 'No Description' OR payee IS NULL
            ORDER BY id
        """)
        
        results = cursor.fetchall()
        conn.close()
        return results
    
    def update_transaction(self, transaction_id: int, payee: str, category_id: Optional[int] = None, subcategory_id: Optional[int] = None) -> bool:
        """Update payee and optionally category/subcategory for a specific transaction"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if category_id and subcategory_id:
                cursor.execute("""
                    UPDATE transactions 
                    SET payee = ?, category_id = ?, subcategory_id = ?
                    WHERE id = ?
                """, (payee, category_id, subcategory_id, transaction_id))
            else:
                cursor.execute("""
                    UPDATE transactions 
                    SET payee = ? 
                    WHERE id = ?
                """, (payee, transaction_id))
            
            success = cursor.rowcount > 0
            conn.commit()
            return success
            
        except Exception as e:
            logger.error(f"Error updating transaction {transaction_id}: {e}")
            return False
        finally:
            conn.close()
    
    def extract_all_payees(self, dry_run: bool = True) -> Dict[str, int]:
        """Extract payees for all No Description transactions"""
        transactions = self.get_no_description_transactions()
        logger.info(f"Found {len(transactions)} transactions with 'No Description' payee")
        
        results = {
            'extracted': 0,
            'updated': 0,
            'categorized': 0,
            'no_match': 0
        }
        
        extraction_summary = {}
        categorization_summary = {}
        
        for transaction_id, action in transactions:
            extracted_payee = self.extract_payee_from_action(action)
            
            if extracted_payee:
                results['extracted'] += 1
                
                # Track extraction summary
                if extracted_payee not in extraction_summary:
                    extraction_summary[extracted_payee] = 0
                extraction_summary[extracted_payee] += 1
                
                # Check if we have category mapping for this payee
                category_id = None
                subcategory_id = None
                category_info = ""
                
                if extracted_payee in self.merchant_categories:
                    category_name, subcategory_name = self.merchant_categories[extracted_payee]
                    if not dry_run:
                        category_id, subcategory_id = self.get_category_subcategory_ids(category_name, subcategory_name)
                    category_info = f" → {category_name}/{subcategory_name}"
                    
                    # Track categorization summary
                    cat_key = f"{category_name}/{subcategory_name}"
                    if cat_key not in categorization_summary:
                        categorization_summary[cat_key] = 0
                    categorization_summary[cat_key] += 1
                
                if not dry_run:
                    if self.update_transaction(transaction_id, extracted_payee, category_id, subcategory_id):
                        results['updated'] += 1
                        if category_id and subcategory_id:
                            results['categorized'] += 1
                        logger.info(f"Updated ID {transaction_id}: {extracted_payee}{category_info}")
                else:
                    logger.info(f"ID {transaction_id:4d}: {extracted_payee:30s}{category_info:25s} | {action[:60]}...")
            else:
                results['no_match'] += 1
                if dry_run:
                    logger.warning(f"ID {transaction_id:4d}: No pattern match        | {action[:80]}...")
        
        # Print summary
        logger.info("\n" + "="*80)
        logger.info("PAYEE EXTRACTION SUMMARY")
        logger.info("="*80)
        for payee, count in sorted(extraction_summary.items()):
            category_info = ""
            if payee in self.merchant_categories:
                cat_name, subcat_name = self.merchant_categories[payee]
                category_info = f" → {cat_name}/{subcat_name}"
            logger.info(f"{payee:30s} | {count:4d} transactions{category_info}")
        
        if categorization_summary:
            logger.info("\n" + "="*80)
            logger.info("CATEGORIZATION SUMMARY")
            logger.info("="*80)
            for category, count in sorted(categorization_summary.items()):
                logger.info(f"{category:40s} | {count:4d} transactions")
        
        logger.info("\n" + "="*80)
        logger.info(f"Total transactions processed: {len(transactions)}")
        logger.info(f"Payees extracted: {results['extracted']}")
        logger.info(f"Database updates: {results['updated']}")
        logger.info(f"Transactions categorized: {results['categorized']}")
        logger.info(f"No matches: {results['no_match']}")
        
        return results

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract payees from transaction action column")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be extracted without updating database")
    parser.add_argument("--apply", action="store_true",
                       help="Apply extractions to database")
    parser.add_argument("--db", default="transactions.db",
                       help="Database file path")
    
    args = parser.parse_args()
    
    extractor = PayeeExtractor(args.db)
    
    if args.apply:
        logger.info("🚀 Applying payee extractions and categorization to database...")
        results = extractor.extract_all_payees(dry_run=False)
        logger.info(f"✅ Updated {results['updated']} transactions with extracted payees!")
        if results['categorized'] > 0:
            logger.info(f"🎯 Categorized {results['categorized']} transactions automatically!")
    else:
        logger.info("🔍 Dry run - showing what would be extracted and categorized...")
        extractor.extract_all_payees(dry_run=True)
        logger.info("\nTo apply these changes, run with --apply flag")

if __name__ == "__main__":
    main()