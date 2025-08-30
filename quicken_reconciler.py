#!/usr/bin/env python3
"""
Quicken QIF Parser and Reconciliation Tool

This tool parses QIF (Quicken Interchange Format) files and prepares them for 
LLM-assisted reconciliation with the existing transaction database.

Usage:
    python3 quicken_reconciler.py --parse transactions.qif --batch-size 25
    python3 quicken_reconciler.py --analyze-batch batch_001.json
    python3 quicken_reconciler.py --apply-batch batch_001_decisions.json
"""

import argparse
import json
import os
import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from database import TransactionDB


class QIFTransaction:
    """Represents a single QIF transaction"""
    
    def __init__(self):
        self.date: Optional[date] = None
        self.amount: Optional[float] = None
        self.payee: Optional[str] = None
        self.memo: Optional[str] = None
        self.category: Optional[str] = None
        self.cleared_status: Optional[str] = None
        self.number: Optional[str] = None  # Check number
        self.address: Optional[str] = None
        self.raw_data: Dict[str, str] = {}  # Store original QIF fields
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary for JSON export"""
        return {
            'date': self.date.isoformat() if self.date else None,
            'amount': self.amount,
            'payee': self.payee,
            'memo': self.memo,
            'category': self.category,
            'cleared_status': self.cleared_status,
            'number': self.number,
            'address': self.address,
            'raw_data': self.raw_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QIFTransaction':
        """Create transaction from dictionary"""
        txn = cls()
        txn.date = datetime.fromisoformat(data['date']).date() if data['date'] else None
        txn.amount = data['amount']
        txn.payee = data['payee']
        txn.memo = data['memo']
        txn.category = data['category']
        txn.cleared_status = data['cleared_status']
        txn.number = data['number']
        txn.address = data['address']
        txn.raw_data = data.get('raw_data', {})
        return txn


class QIFParser:
    """Parser for QIF (Quicken Interchange Format) files"""
    
    def __init__(self):
        self.transactions: List[QIFTransaction] = []
        self.account_type: Optional[str] = None
        self.account_name: Optional[str] = None
    
    def parse_date(self, date_str: str) -> Optional[date]:
        """Parse QIF date string (various formats supported)"""
        # Common QIF date formats: 12/31/23, 12/31/2023, 9/27'23 (Quicken export format)
        date_patterns = [
            r'^(\d{1,2})/(\d{1,2})/(\d{4})$',     # MM/DD/YYYY
            r'^(\d{1,2})/(\d{1,2})/(\d{2})$',     # MM/DD/YY
            r'^(\d{1,2})/(\d{1,2})\'(\d{2})$',    # MM/DD'YY (Quicken format)
            r'^(\d{1,2})/\s*(\d{1,2})\'(\d{2})$', # MM/ D'YY (with space)
            r'^(\d{1,2})-(\d{1,2})-(\d{4})$',     # MM-DD-YYYY
            r'^(\d{1,2})-(\d{1,2})-(\d{2})$',     # MM-DD-YY
        ]
        
        for pattern in date_patterns:
            match = re.match(pattern, date_str.strip())
            if match:
                month, day, year = match.groups()
                year = int(year)
                if year < 50:  # Y2K handling for 2-digit years
                    year += 2000
                elif year < 100:
                    year += 1900
                
                try:
                    return date(year, int(month), int(day))
                except ValueError:
                    continue
        
        print(f"Warning: Could not parse date '{date_str}'")
        return None
    
    def parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse QIF amount string"""
        # Remove currency symbols and extra spaces
        amount_clean = re.sub(r'[$,\s]', '', amount_str.strip())
        try:
            return float(amount_clean)
        except ValueError:
            print(f"Warning: Could not parse amount '{amount_str}'")
            return None
    
    def parse_file(self, qif_file_path: str) -> List[QIFTransaction]:
        """Parse QIF file and return list of transactions"""
        print(f"Parsing QIF file: {qif_file_path}")
        
        with open(qif_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Split into transactions (separated by '^' on its own line)
        transaction_blocks = re.split(r'\n\^\n', content)
        
        transactions = []
        current_account_type = None
        
        for block in transaction_blocks:
            if not block.strip():
                continue
            
            lines = block.strip().split('\n')
            
            # Check for account type header
            if lines[0].startswith('!Type:'):
                current_account_type = lines[0][6:]  # Remove '!Type:'
                continue
            
            # Parse transaction
            txn = QIFTransaction()
            
            for line in lines:
                if not line.strip():
                    continue
                
                field_code = line[0]
                field_value = line[1:] if len(line) > 1 else ""
                
                # Store raw data for debugging
                txn.raw_data[field_code] = field_value
                
                # Parse standard QIF fields
                if field_code == 'D':  # Date
                    txn.date = self.parse_date(field_value)
                elif field_code == 'T':  # Amount
                    txn.amount = self.parse_amount(field_value)
                elif field_code == 'P':  # Payee
                    txn.payee = field_value.strip()
                elif field_code == 'M':  # Memo
                    txn.memo = field_value.strip()
                elif field_code == 'L':  # Category
                    txn.category = field_value.strip()
                elif field_code == 'C':  # Cleared status
                    txn.cleared_status = field_value.strip()
                elif field_code == 'N':  # Number (check number)
                    txn.number = field_value.strip()
                elif field_code == 'A':  # Address
                    txn.address = field_value.strip()
            
            # Only add transactions with required fields
            if txn.date and txn.amount is not None:
                transactions.append(txn)
            else:
                print(f"Warning: Skipping incomplete transaction: {txn.raw_data}")
        
        self.transactions = transactions
        self.account_type = current_account_type
        
        print(f"Parsed {len(transactions)} transactions from QIF file")
        return transactions
    
    def export_batch_json(self, transactions: List[QIFTransaction], batch_size: int = 25, 
                         output_dir: str = "qif_batches") -> List[str]:
        """Export transactions in reviewable JSON batches"""
        Path(output_dir).mkdir(exist_ok=True)
        
        batch_files = []
        
        for i in range(0, len(transactions), batch_size):
            batch_num = (i // batch_size) + 1
            batch = transactions[i:i + batch_size]
            
            batch_data = {
                'batch_number': batch_num,
                'total_batches': (len(transactions) + batch_size - 1) // batch_size,
                'batch_size': len(batch),
                'date_range': {
                    'start': min(txn.date for txn in batch if txn.date).isoformat(),
                    'end': max(txn.date for txn in batch if txn.date).isoformat()
                },
                'transactions': [txn.to_dict() for txn in batch]
            }
            
            batch_file = f"{output_dir}/batch_{batch_num:03d}.json"
            with open(batch_file, 'w', encoding='utf-8') as f:
                json.dump(batch_data, f, indent=2, ensure_ascii=False)
            
            batch_files.append(batch_file)
            print(f"Created {batch_file} with {len(batch)} transactions")
        
        return batch_files
    
    def create_reconciliation_report(self, transactions: List[QIFTransaction]) -> Dict[str, Any]:
        """Generate summary report for LLM review"""
        if not transactions:
            return {}
        
        dates = [txn.date for txn in transactions if txn.date]
        amounts = [txn.amount for txn in transactions if txn.amount is not None]
        payees = [txn.payee for txn in transactions if txn.payee]
        categories = [txn.category for txn in transactions if txn.category]
        
        return {
            'total_transactions': len(transactions),
            'date_range': {
                'start': min(dates).isoformat() if dates else None,
                'end': max(dates).isoformat() if dates else None
            },
            'amount_summary': {
                'total': sum(amounts),
                'min': min(amounts) if amounts else 0,
                'max': max(amounts) if amounts else 0,
                'average': sum(amounts) / len(amounts) if amounts else 0
            },
            'unique_payees': sorted(list(set(payees))),
            'quicken_categories': sorted(list(set(categories))),
            'transactions_by_month': self._group_by_month(transactions),
            'potential_issues': self._identify_issues(transactions)
        }
    
    def _group_by_month(self, transactions: List[QIFTransaction]) -> Dict[str, int]:
        """Group transactions by month for analysis"""
        monthly_counts = {}
        for txn in transactions:
            if txn.date:
                month_key = txn.date.strftime('%Y-%m')
                monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1
        return monthly_counts
    
    def _identify_issues(self, transactions: List[QIFTransaction]) -> List[str]:
        """Identify potential data quality issues"""
        issues = []
        
        # Check for missing data
        missing_payee = sum(1 for txn in transactions if not txn.payee)
        missing_category = sum(1 for txn in transactions if not txn.category)
        missing_date = sum(1 for txn in transactions if not txn.date)
        missing_amount = sum(1 for txn in transactions if txn.amount is None)
        
        if missing_payee > 0:
            issues.append(f"{missing_payee} transactions missing payee")
        if missing_category > 0:
            issues.append(f"{missing_category} transactions missing category")
        if missing_date > 0:
            issues.append(f"{missing_date} transactions missing date")
        if missing_amount > 0:
            issues.append(f"{missing_amount} transactions missing amount")
        
        # Check for unusual amounts
        amounts = [txn.amount for txn in transactions if txn.amount is not None]
        if amounts:
            very_large = [a for a in amounts if abs(a) > 10000]
            if very_large:
                issues.append(f"{len(very_large)} transactions with amounts > $10,000")
        
        return issues


class ReconciliationSession:
    """Manages LLM-assisted reconciliation workflow"""
    
    def __init__(self, db_path: str = "transactions.db"):
        self.db = TransactionDB(db_path)
    
    def analyze_batch_for_llm(self, batch_file: str) -> Dict[str, Any]:
        """Prepare batch analysis for Claude Code review"""
        with open(batch_file, 'r', encoding='utf-8') as f:
            batch_data = json.load(f)
        
        # Get context from existing database
        categories = self.db.get_all_categories()
        recent_payees = self.db.get_recent_payees(limit=200)
        
        analysis = {
            'batch_info': {
                'file': batch_file,
                'batch_number': batch_data['batch_number'],
                'transaction_count': batch_data['batch_size'],
                'date_range': batch_data['date_range']
            },
            'transactions': batch_data['transactions'],
            'existing_context': {
                'categories': categories,
                'recent_payees': recent_payees,
                'category_mappings': self._suggest_category_mappings(batch_data['transactions'], categories)
            },
            'duplicate_candidates': self._find_potential_duplicates(batch_data['transactions'])
        }
        
        return analysis
    
    def _suggest_category_mappings(self, transactions: List[Dict], existing_categories: List[Tuple]) -> Dict[str, str]:
        """Suggest mappings from Quicken categories to existing categories"""
        mappings = {}
        existing_cat_names = [cat[1].lower() for cat in existing_categories]
        
        quicken_categories = set()
        for txn in transactions:
            if txn.get('category'):
                quicken_categories.add(txn['category'])
        
        for qcat in quicken_categories:
            # Simple fuzzy matching
            qcat_lower = qcat.lower()
            best_match = None
            for existing_cat in existing_categories:
                if qcat_lower in existing_cat[1].lower() or existing_cat[1].lower() in qcat_lower:
                    best_match = existing_cat[1]
                    break
            
            mappings[qcat] = best_match or "NEEDS_MAPPING"
        
        return mappings
    
    def analyze_transaction_for_enhancement(self, qif_txn: Dict, existing_txn: Dict) -> Dict:
        """Analyze what enhancements can be made to existing transaction"""
        enhancements = {}
        
        # Payee enhancement
        qif_payee = qif_txn.get('payee', '').strip()
        existing_payee = existing_txn.get('payee', '').strip()
        
        if self._should_enhance_payee(qif_payee, existing_payee):
            enhancements['payee'] = {
                'from': existing_payee,
                'to': qif_payee,
                'reason': 'QIF payee is more descriptive'
            }
        
        # Memo enhancement
        qif_memo = (qif_txn.get('memo') or '').strip()
        existing_memo = existing_txn.get('memo') or ''
        
        if qif_memo and not existing_memo:
            enhancements['memo'] = {
                'from': existing_memo,
                'to': qif_memo,
                'reason': 'QIF provides memo, existing has none'
            }
        
        # Category enhancement (if existing is uncategorized)
        if not existing_txn.get('category_id') and qif_txn.get('category'):
            mapped_category = self._map_quicken_category(qif_txn['category'])
            if mapped_category:
                enhancements['category'] = {
                    'from': None,
                    'to': mapped_category,
                    'reason': 'QIF provides category, existing is uncategorized'
                }
        
        return enhancements
    
    def _should_enhance_payee(self, qif_payee: str, existing_payee: str) -> bool:
        """Determine if QIF payee is better than existing payee"""
        if not qif_payee:
            return False
            
        # Clear cases where QIF is better
        if existing_payee in ['No Description', '', None]:
            return True
            
        # QIF payee is significantly longer (more descriptive)
        if len(qif_payee) > len(existing_payee) * 1.5:
            return True
            
        # Check if QIF payee contains merchant name while existing is generic
        generic_patterns = ['POS', 'DEBIT CARD', 'ATM', 'CASH ADVANCE']
        if any(pattern in existing_payee.upper() for pattern in generic_patterns):
            return True
            
        return False
    
    def _map_quicken_category(self, quicken_category: str) -> Optional[Dict]:
        """Map a Quicken category to our app's category system"""
        if not quicken_category:
            return None
            
        # Check existing mappings first
        existing_mapping = self.db.get_category_mapping(quicken_category)
        if existing_mapping:
            return existing_mapping
            
        # Simple fuzzy matching against existing categories
        categories = self.db.get_all_categories()
        
        # Look for direct matches or close matches
        quicken_lower = quicken_category.lower()
        
        for cat_id, cat_name, sub_id, sub_name in categories:
            if ':' in quicken_category and sub_name:
                # Handle "Food & Dining:Groceries" format
                qif_parts = quicken_category.split(':')
                if (qif_parts[0].lower() in cat_name.lower() and 
                    qif_parts[1].lower() in sub_name.lower()):
                    return {
                        'app_category_id': cat_id,
                        'app_subcategory_id': sub_id,
                        'confidence': 0.9,
                        'mapping_type': 'fuzzy_match'
                    }
            
            # Simple category name matching
            if quicken_lower in cat_name.lower() or cat_name.lower() in quicken_lower:
                return {
                    'app_category_id': cat_id,
                    'app_subcategory_id': sub_id,
                    'confidence': 0.8,
                    'mapping_type': 'fuzzy_match'
                }
        
        return None
    
    def check_transaction_exists(self, txn: Dict) -> Dict:
        """Check if a single QIF transaction already exists and analyze enhancements"""
        import hashlib
        
        # Create hash for QIF transaction
        hash_data = f"{txn['date']}-{txn.get('payee', '')}-{txn['amount']}-{txn.get('memo', '')}"
        qif_hash = hashlib.md5(hash_data.encode()).hexdigest()
        
        # Check if already processed in QIF reconciliation
        existing_qif = self.db.check_qif_transaction_processed(qif_hash)
        if existing_qif:
            return {
                'status': 'already_processed',
                'qif_hash': qif_hash,
                'details': existing_qif,
                'reason': f'Already processed in {existing_qif["status"]} status'
            }
        
        # Check for similar transactions in main database
        similar = self.db.find_similar_transactions(
            date=txn['date'],
            amount=txn['amount'],
            payee=txn.get('payee', ''),
            tolerance_days=3
        )
        
        if similar:
            # Analyze the best match for potential enhancements
            best_match = similar[0]  # find_similar_transactions returns ordered by relevance
            enhancements = self.analyze_transaction_for_enhancement(txn, best_match)
            
            if enhancements:
                return {
                    'status': 'enhance_existing',
                    'qif_hash': qif_hash,
                    'details': best_match,
                    'enhancements': enhancements,
                    'reason': f'Found duplicate - can enhance with {len(enhancements)} improvements'
                }
            else:
                return {
                    'status': 'duplicate_no_enhancement',
                    'qif_hash': qif_hash,
                    'details': best_match,
                    'reason': 'Found duplicate - no enhancements possible'
                }
        
        return {
            'status': 'new_transaction',
            'qif_hash': qif_hash,
            'details': None,
            'reason': 'No matching transactions found'
        }
    
    def _find_potential_duplicates(self, transactions: List[Dict]) -> List[Dict]:
        """Find transactions that might already exist in database"""
        duplicates = []
        
        for txn in transactions:
            if not txn['date'] or txn['amount'] is None:
                continue
            
            duplicate_check = self.check_transaction_exists(txn)
            if duplicate_check['status'] != 'new_transaction':
                duplicates.append({
                    'qif_transaction': txn,
                    'duplicate_info': duplicate_check
                })
        
        return duplicates
    
    def apply_llm_decisions(self, decisions_file: str) -> Dict[str, Any]:
        """Apply Claude Code's reconciliation decisions to database"""
        print(f"This would apply decisions from {decisions_file}")
        print("Implementation pending - requires LLM decision format specification")
        
        return {
            'status': 'pending_implementation',
            'message': 'Decision application will be implemented after LLM review format is established'
        }


def main():
    parser = argparse.ArgumentParser(description='Quicken QIF Parser and Reconciliation Tool')
    parser.add_argument('--parse', metavar='QIF_FILE', help='Parse QIF file into batches')
    parser.add_argument('--batch-size', type=int, default=25, help='Number of transactions per batch')
    parser.add_argument('--output-dir', default='qif_batches', help='Output directory for batch files')
    parser.add_argument('--analyze-batch', metavar='BATCH_FILE', help='Analyze batch for LLM review')
    parser.add_argument('--apply-batch', metavar='DECISIONS_FILE', help='Apply LLM decisions from file')
    parser.add_argument('--report', action='store_true', help='Generate reconciliation report')
    parser.add_argument('--progress', action='store_true', help='Show reconciliation progress')
    parser.add_argument('--list-mappings', action='store_true', help='List learned category mappings')
    
    args = parser.parse_args()
    
    if args.parse:
        # Parse QIF file into batches
        qif_parser = QIFParser()
        transactions = qif_parser.parse_file(args.parse)
        
        if transactions:
            # Create batches
            batch_files = qif_parser.export_batch_json(
                transactions, 
                batch_size=args.batch_size,
                output_dir=args.output_dir
            )
            
            # Generate summary report
            report = qif_parser.create_reconciliation_report(transactions)
            report_file = f"{args.output_dir}/reconciliation_report.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            print(f"\nSummary:")
            print(f"- Created {len(batch_files)} batch files")
            print(f"- Total transactions: {len(transactions)}")
            print(f"- Date range: {report['date_range']['start']} to {report['date_range']['end']}")
            print(f"- Unique payees: {len(report['unique_payees'])}")
            print(f"- Quicken categories: {len(report['quicken_categories'])}")
            print(f"- Report saved: {report_file}")
            
            if report['potential_issues']:
                print(f"\nPotential issues found:")
                for issue in report['potential_issues']:
                    print(f"  - {issue}")
    
    elif args.analyze_batch:
        # Analyze batch for LLM review
        session = ReconciliationSession()
        analysis = session.analyze_batch_for_llm(args.analyze_batch)
        
        analysis_file = args.analyze_batch.replace('.json', '_analysis.json')
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        print(f"Batch analysis saved to: {analysis_file}")
        print("Ready for Claude Code LLM review!")
    
    elif args.apply_batch:
        # Apply LLM decisions
        session = ReconciliationSession()
        result = session.apply_llm_decisions(args.apply_batch)
        print(json.dumps(result, indent=2))
    
    elif args.progress:
        # Show reconciliation progress
        session = ReconciliationSession()
        progress = session.db.get_reconciliation_progress()
        
        print("\n=== Quicken Reconciliation Progress ===")
        print(f"Total transactions processed: {progress.get('total_transactions', 0)}")
        print(f"Completion rate: {progress.get('completion_rate', 0):.1%}")
        print(f"Category mappings learned: {progress.get('category_mappings_learned', 0)}")
        
        print("\nTransaction Status Breakdown:")
        for status, count in progress.get('transaction_counts', {}).items():
            print(f"  {status}: {count}")
    
    elif args.list_mappings:
        # List learned category mappings
        session = ReconciliationSession()
        import sqlite3
        conn = sqlite3.connect(session.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT qcm.quicken_category, qcm.quicken_subcategory,
                   c.name as app_category, s.name as app_subcategory,
                   qcm.confidence, qcm.usage_count, qcm.mapping_type
            FROM qif_category_mappings qcm
            JOIN categories c ON qcm.app_category_id = c.id
            LEFT JOIN subcategories s ON qcm.app_subcategory_id = s.id
            ORDER BY qcm.usage_count DESC, qcm.confidence DESC
        ''')
        
        mappings = cursor.fetchall()
        conn.close()
        
        print("\n=== Learned Category Mappings ===")
        print(f"{'Quicken Category':<25} {'→':<3} {'App Category':<25} {'Confidence':<10} {'Used':<5}")
        print("-" * 70)
        
        for mapping in mappings:
            quicken_cat = f"{mapping[0]}" + (f":{mapping[1]}" if mapping[1] else "")
            app_cat = f"{mapping[2]}" + (f":{mapping[3]}" if mapping[3] else "")
            print(f"{quicken_cat:<25} {'→':<3} {app_cat:<25} {mapping[4]:<10.1f} {mapping[5]:<5}")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()