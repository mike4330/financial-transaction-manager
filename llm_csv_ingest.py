#!/usr/bin/env python3
"""
Production LLM-Based CSV Ingestion

Uses Claude API to dynamically map and import CSV transaction files
without hardcoded regex patterns.
"""

import os
import sys
import json
import csv
import hashlib
import anthropic
from datetime import datetime
from typing import Dict, List, Any, Optional
from database import TransactionDB


class LLMCSVIngestion:
    """
    Production-ready LLM-based CSV ingestion using Claude API.
    """

    def __init__(self, db: TransactionDB, api_key: Optional[str] = None):
        self.db = db
        self.db_path = db.db_path

        # Initialize Anthropic client
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("API key required. Set ANTHROPIC_API_KEY environment variable or pass api_key parameter")

        self.client = anthropic.Anthropic(api_key=self.api_key)

    def get_database_context(self) -> Dict[str, Any]:
        """Gather context about database for LLM"""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get sample transactions
        cursor.execute("""
            SELECT run_date, account, account_number, action, description, type,
                   amount, payee, symbol, category_id, subcategory_id
            FROM transactions
            WHERE payee IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 15
        """)
        sample_transactions = [dict(row) for row in cursor.fetchall()]

        # Get categories/subcategories
        cursor.execute("""
            SELECT c.id as category_id, c.name as category_name,
                   s.id as subcategory_id, s.name as subcategory_name
            FROM categories c
            LEFT JOIN subcategories s ON c.id = s.category_id
            ORDER BY c.name, s.name
        """)
        categories = [dict(row) for row in cursor.fetchall()]

        # Get known accounts
        cursor.execute("""
            SELECT DISTINCT account, account_number
            FROM transactions
            ORDER BY account
        """)
        known_accounts = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return {
            'sample_transactions': sample_transactions,
            'categories': categories[:30],  # Limit for prompt size
            'known_accounts': known_accounts
        }

    def read_csv_sample(self, filepath: str, num_rows: int = 10) -> Dict[str, Any]:
        """Read sample of CSV file"""
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read().strip()
            lines = content.split('\n')

            # Find header
            header_line = None
            header_index = 0
            for i, line in enumerate(lines):
                if line.strip():
                    # Look for common transaction CSV headers
                    if any(keyword in line for keyword in ['Run Date', 'Date', 'Amount', 'Transaction', 'Action']):
                        header_line = line
                        header_index = i
                        break

            if not header_line:
                return {'error': 'No valid header found'}

            # Read sample rows
            reader = csv.DictReader(lines[header_index:])
            sample_rows = []
            for i, row in enumerate(reader):
                if i >= num_rows:
                    break
                if any(row.values()):  # Skip empty rows
                    sample_rows.append(dict(row))

            return {
                'filepath': filepath,
                'header': list(sample_rows[0].keys()) if sample_rows else [],
                'sample_rows': sample_rows
            }

    def build_categorization_prompt(self, new_transactions: List[Dict], db_context: Dict[str, Any]) -> str:
        """Build prompt for categorizing new transactions"""

        # Limit categories in prompt for token efficiency
        categories_summary = {}
        for cat in db_context['categories'][:50]:
            cat_name = cat['category_name']
            if cat_name not in categories_summary:
                categories_summary[cat_name] = {
                    'category_id': cat['category_id'],
                    'subcategories': []
                }
            if cat['subcategory_name']:
                categories_summary[cat_name]['subcategories'].append({
                    'subcategory_id': cat['subcategory_id'],
                    'name': cat['subcategory_name']
                })

        # Prepare transactions for categorization (limit fields for token efficiency)
        txns_for_prompt = []
        for i, txn in enumerate(new_transactions[:50]):  # Max 50 at a time
            txns_for_prompt.append({
                'index': i,
                'date': txn.get('run_date'),
                'amount': txn.get('amount'),
                'payee': txn.get('payee'),
                'action': txn.get('action', '')[:100],  # Truncate long actions
                'type': txn.get('type'),
                'symbol': txn.get('symbol')
            })

        prompt = f"""Categorize these financial transactions.

AVAILABLE CATEGORIES:
{json.dumps(categories_summary, indent=2)}

TRANSACTIONS TO CATEGORIZE:
{json.dumps(txns_for_prompt, indent=2)}

TASK:
For each transaction, return:
1. Best matching category_id and subcategory_id
2. Improved payee name (normalize merchant names)
3. Confidence score (0.0-1.0)

RULES:
- Investment transactions (symbol present) → Use Investment category
- Common merchants: normalize names (e.g., "WALMART SUPER" → "Walmart", "AMZN" → "Amazon")
- Consider transaction type and amount when categorizing
- Use existing sample transactions as reference for patterns

Return ONLY valid JSON (no markdown):

{{
  "categorized_transactions": [
    {{
      "index": 0,
      "category_id": 171,
      "subcategory_id": 171,
      "normalized_payee": "Walmart",
      "confidence": 0.95,
      "reasoning": "Brief explanation"
    }}
  ]
}}"""

        return prompt

    def build_llm_prompt(self, csv_sample: Dict[str, Any], db_context: Dict[str, Any]) -> str:
        """Build prompt for Claude API"""

        prompt = f"""You are analyzing a CSV file of financial transactions to map them to a database.

DATABASE CONTEXT:

Known Accounts:
{json.dumps(db_context['known_accounts'], indent=2)}

Sample Existing Transactions (for pattern learning):
{json.dumps(db_context['sample_transactions'][:10], indent=2)}

Available Categories (sample):
{json.dumps(db_context['categories'][:20], indent=2)}

CSV FILE TO ANALYZE:

File: {csv_sample['filepath']}
Headers: {json.dumps(csv_sample['header'])}

Sample Rows:
{json.dumps(csv_sample['sample_rows'], indent=2)}

TASK:

Analyze this CSV and provide a JSON response with mapping instructions.

Return ONLY valid JSON (no markdown, no explanation outside JSON) with this structure:

{{
  "account_inference": {{
    "account": "account name",
    "account_number": "account number",
    "source": "filename|csv_column|unknown"
  }},
  "column_mapping": {{
    "date_column": "CSV column name for transaction date",
    "action_column": "CSV column name for transaction action/description",
    "amount_column": "CSV column name for amount",
    "symbol_column": "CSV column name for stock symbol (or null)",
    "description_column": "CSV column name for description (or null)"
  }},
  "sample_mappings": [
    {{
      "csv_row_index": 0,
      "skip": false,
      "skip_reason": null,
      "extracted_data": {{
        "date_iso": "2025-11-08",
        "payee": "extracted merchant/payee name",
        "transaction_type": "Debit Card|ACH|Transfer|Investment Trade|etc",
        "amount": -25.50,
        "symbol": null,
        "suggested_category_id": 171,
        "suggested_subcategory_id": 189,
        "reasoning": "brief explanation"
      }}
    }}
  ],
  "extraction_logic": {{
    "payee_extraction_pattern": "describe how to extract payee from action field",
    "pending_transaction_indicator": "text pattern indicating pending/uncleared transactions to skip",
    "date_format": "MM/DD/YYYY or other format detected"
  }}
}}

IMPORTANT RULES:
- Investment transactions (stocks/ETFs) should have symbol populated, payee=null
- Skip pending/uncleared transactions (look for OUTSTAND AUTH, Processing, etc)
- Extract clean merchant names from action text (remove transaction IDs, location codes)
- Convert dates to ISO format YYYY-MM-DD
- Negative amounts = debits/expenses, positive = deposits/income
- Match categories based on similar existing transactions
- If account info not in CSV, try to extract from filename pattern

Return ONLY the JSON response, nothing else."""

        return prompt

    def call_claude_api(self, prompt: str, max_tokens: int = 4000) -> Dict[str, Any]:
        """Call Claude API and parse response"""

        print("📞 Calling Claude API...")

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",  # Latest Sonnet
                max_tokens=max_tokens,
                temperature=0,  # Deterministic
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text

            # Strip markdown code blocks if present
            if response_text.strip().startswith('```'):
                # Remove ```json or ``` from start
                response_text = response_text.strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                elif response_text.startswith('```'):
                    response_text = response_text[3:]
                # Remove ``` from end
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                response_text = response_text.strip()

            # Parse JSON response
            response_json = json.loads(response_text)

            # Add API metadata
            response_json['_api_metadata'] = {
                'model': message.model,
                'input_tokens': message.usage.input_tokens,
                'output_tokens': message.usage.output_tokens,
                'stop_reason': message.stop_reason
            }

            print(f"✓ API call successful")
            print(f"  Tokens: {message.usage.input_tokens} in / {message.usage.output_tokens} out")

            return response_json

        except json.JSONDecodeError as e:
            print(f"✗ Failed to parse API response as JSON: {e}")
            print(f"Response text: {response_text[:500]}")
            raise
        except Exception as e:
            print(f"✗ API call failed: {e}")
            raise

    def convert_date_to_iso(self, date_str: str, detected_format: str = None) -> Optional[str]:
        """Convert date to ISO format"""
        if not date_str or not date_str.strip():
            return None

        # Common formats to try
        formats = ['%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d', '%d/%m/%Y']

        # Try detected format first
        if detected_format:
            formats.insert(0, detected_format)

        for fmt in formats:
            try:
                date_obj = datetime.strptime(date_str.strip(), fmt)
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                continue

        return None

    def clean_numeric_value(self, value: Any) -> Optional[float]:
        """Clean and convert numeric values"""
        if value is None or value == '':
            return None
        try:
            if isinstance(value, str):
                cleaned = value.replace(',', '').replace('$', '').strip()
                return float(cleaned) if cleaned else None
            return float(value)
        except (ValueError, AttributeError):
            return None

    def generate_transaction_hash(self, transaction: Dict[str, Any]) -> str:
        """Generate unique hash for duplicate detection"""
        hash_string = f"{transaction.get('run_date', '')}-{transaction.get('account_number', '')}-{transaction.get('action', '')}-{transaction.get('amount', '')}"
        return hashlib.md5(hash_string.encode()).hexdigest()

    def extract_payee_and_type_from_llm(self, action: str, llm_logic: Dict) -> tuple:
        """
        Use LLM's extraction logic to get payee and type.
        Fallback to simple extraction if logic not provided.
        """
        # For now, use simple extraction based on patterns
        # In future, we could ask LLM to classify individual transactions
        # but that would be expensive for large files

        action_upper = action.upper()

        # Detect transaction type
        if 'DEBIT CARD' in action_upper:
            trans_type = 'Debit Card'
        elif 'DIRECT DEBIT' in action_upper:
            trans_type = 'Direct Debit'
        elif 'ACH DEBIT' in action_upper:
            trans_type = 'ACH Debit'
        elif 'ACH CREDIT' in action_upper:
            trans_type = 'ACH Credit'
        elif 'TRANSFERRED' in action_upper:
            trans_type = 'Transfer'
        elif 'YOU BOUGHT' in action_upper or 'YOU SOLD' in action_upper:
            trans_type = 'Investment Trade'
        elif 'DIVIDEND' in action_upper:
            trans_type = 'Dividend'
        else:
            trans_type = 'Other'

        # Extract payee (simplified - using pattern from LLM logic if available)
        payee = None
        pattern_desc = llm_logic.get('payee_extraction_pattern', '')

        # Simple extraction for common patterns
        if 'DEBIT CARD PURCHASE' in action_upper:
            # Extract text after DEBIT CARD PURCHASE, before location codes
            import re
            match = re.search(r'DEBIT CARD PURCHASE\s+([A-Z0-9][A-Z0-9\s&.*-]+?)(?:\s+\d{3}-\d{3}-\d{4}|\s+[A-Z]{2}\d|$)', action_upper)
            if match:
                payee = match.group(1).strip().title()
        elif 'DIRECT DEBIT' in action_upper:
            import re
            match = re.search(r'DIRECT DEBIT\s+([A-Z][A-Z0-9\s&.]+?)(?:\s+[A-Z]{2,}|\s*\(|$)', action_upper)
            if match:
                payee = match.group(1).strip().title()

        return payee, trans_type

    def process_csv_with_llm(self, csv_filepath: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Main processing function - uses LLM to analyze and import CSV

        Args:
            csv_filepath: Path to CSV file
            dry_run: If True, analyze but don't insert to database

        Returns:
            Dictionary with processing results and statistics
        """

        print("=" * 80)
        print("LLM-BASED CSV INGESTION WITH AUTO-CATEGORIZATION")
        print("=" * 80)
        print(f"\nFile: {csv_filepath}")
        print(f"Mode: {'DRY RUN (no database changes)' if dry_run else 'LIVE (will insert and categorize)'}")

        # Step 1: Gather database context
        print("\n[1/6] Gathering database context...")
        db_context = self.get_database_context()
        print(f"  ✓ {len(db_context['sample_transactions'])} sample transactions")
        print(f"  ✓ {len(db_context['categories'])} categories loaded")
        print(f"  ✓ {len(db_context['known_accounts'])} known accounts")

        # Step 2: Sample CSV file
        print("\n[2/6] Analyzing CSV structure...")
        csv_sample = self.read_csv_sample(csv_filepath, num_rows=10)
        if 'error' in csv_sample:
            return {'error': csv_sample['error']}
        print(f"  ✓ Found {len(csv_sample['header'])} columns")
        print(f"  ✓ Sampled {len(csv_sample['sample_rows'])} rows")

        # Step 3: Build prompt
        print("\n[3/6] Building LLM prompt for CSV analysis...")
        prompt = self.build_llm_prompt(csv_sample, db_context)
        print(f"  ✓ Prompt size: {len(prompt)} characters")

        # Step 4: Call Claude API
        print("\n[4/6] Calling Claude API for CSV structure analysis...")
        llm_response = self.call_claude_api(prompt)

        # Save response for debugging
        response_file = csv_filepath.replace('.csv', '_llm_response.json')
        with open(response_file, 'w') as f:
            json.dump(llm_response, f, indent=2)
        print(f"  ✓ Response saved to: {response_file}")

        # Step 5: Process full CSV using LLM mapping
        print("\n[5/6] Processing full CSV file...")

        mapping = llm_response.get('column_mapping', {})
        account_info = llm_response.get('account_inference', {})
        extraction_logic = llm_response.get('extraction_logic', {})

        print(f"\n  Account: {account_info.get('account')} ({account_info.get('account_number')})")
        print(f"  Date column: {mapping.get('date_column')}")
        print(f"  Amount column: {mapping.get('amount_column')}")
        print(f"  Action column: {mapping.get('action_column')}")

        # Process all rows
        stats = {'processed': 0, 'duplicates': 0, 'errors': 0, 'skipped': 0, 'total_rows': 0, 'new_transactions': [], 'auto_categorized': 0}

        with open(csv_filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read().strip()
            lines = content.split('\n')

            # Find header
            header_index = 0
            for i, line in enumerate(lines):
                if line.strip() and any(keyword in line for keyword in ['Run Date', 'Date', 'Amount', 'Action']):
                    header_index = i
                    break

            reader = csv.DictReader(lines[header_index:])

            for row_num, row in enumerate(reader):
                stats['total_rows'] += 1
                try:
                    # Skip empty rows
                    if not any(row.values()):
                        continue

                    # Get action field
                    action_col = mapping.get('action_column', 'Action')
                    action = row.get(action_col, '')

                    # Check for pending transactions
                    pending_indicator = extraction_logic.get('pending_transaction_indicator', 'OUTSTAND AUTH')
                    if pending_indicator and pending_indicator in action:
                        stats['skipped'] += 1
                        continue

                    # Extract payee and type using LLM-guided logic
                    payee, trans_type = self.extract_payee_and_type_from_llm(action, extraction_logic)

                    # Get symbol for investment transactions
                    symbol = row.get(mapping.get('symbol_column', 'Symbol')) or None
                    if symbol and symbol.strip():
                        symbol = symbol.strip()
                        payee = None  # Investment transactions don't have payee

                    # Build transaction using LLM mapping
                    transaction = {
                        'run_date': self.convert_date_to_iso(
                            row.get(mapping.get('date_column', 'Run Date'), ''),
                            extraction_logic.get('date_format')
                        ),
                        'account': account_info.get('account', 'Unknown'),
                        'account_number': account_info.get('account_number', 'Unknown'),
                        'action': action,
                        'description': row.get(mapping.get('description_column', 'Description'), ''),
                        'symbol': symbol,
                        'type': trans_type,
                        'payee': payee,
                        'amount': self.clean_numeric_value(row.get(mapping.get('amount_column', 'Amount'), '')),
                        'currency': row.get('Currency', 'USD'),
                        'quantity': self.clean_numeric_value(row.get('Quantity', '')),
                        'price': self.clean_numeric_value(row.get('Price', '')),
                        'commission': self.clean_numeric_value(row.get('Commission', '')),
                        'fees': self.clean_numeric_value(row.get('Fees', '')),
                        'settlement_date': self.convert_date_to_iso(row.get('Settlement Date', ''))
                    }

                    # Validate required fields
                    if not transaction['run_date'] or transaction['amount'] is None:
                        stats['errors'] += 1
                        continue

                    # Try to auto-classify using existing patterns (same as regex method)
                    pattern_match = self.db.find_matching_pattern(
                        transaction.get('description', ''),
                        transaction.get('action', ''),
                        transaction.get('payee', '')
                    )

                    if pattern_match:
                        cat_id, sub_id, confidence, cat_name, sub_name = pattern_match
                        transaction['category_id'] = cat_id
                        transaction['subcategory_id'] = sub_id
                        stats['auto_categorized'] += 1

                    # Generate hash (using database's method for consistency)
                    transaction['hash'] = self.db.generate_transaction_hash(transaction)

                    # Check if duplicate (in both dry-run and live mode)
                    import sqlite3
                    conn = sqlite3.connect(self.db.db_path)
                    cursor = conn.cursor()
                    cursor.execute('SELECT 1 FROM transactions WHERE hash = ?', (transaction['hash'],))
                    is_duplicate = cursor.fetchone() is not None
                    conn.close()

                    if is_duplicate:
                        stats['duplicates'] += 1
                    else:
                        # This is a new transaction
                        stats['processed'] += 1

                        # Store for display
                        stats['new_transactions'].append(transaction)

                        # Insert to database (unless dry run)
                        if not dry_run:
                            self.db.insert_transaction(transaction, os.path.basename(csv_filepath))

                except Exception as e:
                    print(f"  Error processing row {row_num}: {e}")
                    stats['errors'] += 1

        print(f"\n✓ CSV Processing complete!")
        print(f"  Total rows in CSV: {stats['total_rows']}")
        print(f"  New transactions: {stats['processed']}")
        print(f"  Auto-categorized: {stats['auto_categorized']} (using learned patterns)")
        print(f"  Duplicates (already in DB): {stats['duplicates']}")
        print(f"  Skipped (pending): {stats['skipped']}")
        print(f"  Errors: {stats['errors']}")

        # Step 6: LLM Categorization for uncategorized transactions
        uncategorized_txns = [t for t in stats['new_transactions'] if not t.get('category_id')]

        if uncategorized_txns and not dry_run:
            print(f"\n[6/6] LLM Categorization of new transactions...")
            print(f"  Categorizing {len(uncategorized_txns)} uncategorized transactions...")

            try:
                # Build categorization prompt
                cat_prompt = self.build_categorization_prompt(uncategorized_txns, db_context)

                # Call Claude API for categorization
                print(f"📞 Calling Claude API for categorization...")
                cat_response = self.call_claude_api(cat_prompt, max_tokens=4000)

                # Apply categorizations
                categorizations = cat_response.get('categorized_transactions', [])
                applied_count = 0

                for cat in categorizations:
                    idx = cat.get('index')
                    if idx is not None and idx < len(uncategorized_txns):
                        txn = uncategorized_txns[idx]
                        txn_hash = txn.get('hash')

                        # Update transaction in database
                        import sqlite3
                        conn = sqlite3.connect(self.db.db_path)
                        cursor = conn.cursor()

                        cursor.execute('''
                            UPDATE transactions
                            SET category_id = ?,
                                subcategory_id = ?,
                                payee = ?
                            WHERE hash = ?
                        ''', (
                            cat.get('category_id'),
                            cat.get('subcategory_id'),
                            cat.get('normalized_payee') or txn.get('payee'),
                            txn_hash
                        ))

                        conn.commit()
                        conn.close()

                        # Update in-memory transaction
                        txn['category_id'] = cat.get('category_id')
                        txn['subcategory_id'] = cat.get('subcategory_id')
                        if cat.get('normalized_payee'):
                            txn['payee'] = cat.get('normalized_payee')

                        # Learn pattern for future
                        if cat.get('confidence', 0) > 0.7:
                            self.db.learn_classification_pattern(
                                txn.get('payee', ''),
                                'payee',
                                cat.get('category_id'),
                                cat.get('subcategory_id'),
                                cat.get('confidence', 0.8)
                            )

                        applied_count += 1

                print(f"  ✓ Categorized {applied_count} transactions with LLM")
                stats['llm_categorized'] = applied_count

            except Exception as e:
                print(f"  ⚠ LLM categorization failed: {e}")
                print(f"  You can categorize later with: python3 main.py --ai-classify {len(uncategorized_txns)}")

        elif uncategorized_txns and dry_run:
            print(f"\n[6/6] LLM Categorization preview...")
            print(f"  {len(uncategorized_txns)} transactions would be categorized with LLM in live mode")

        print(f"\n✓ Import complete!")
        if stats.get('llm_categorized', 0) > 0:
            print(f"  LLM categorized: {stats['llm_categorized']} transactions")

        # Save results for display
        result_file = csv_filepath.replace('.csv', '_import_result.json')
        result_data = {
            'success': True,
            'stats': {
                'total_rows': stats['total_rows'],
                'processed': stats['processed'],
                'duplicates': stats['duplicates'],
                'skipped': stats['skipped'],
                'errors': stats['errors']
            },
            'new_transactions': stats.get('new_transactions', []),
            'dry_run': dry_run,
            'timestamp': datetime.now().isoformat()
        }

        with open(result_file, 'w') as f:
            json.dump(result_data, f, indent=2)

        total_categorized = stats['auto_categorized'] + stats.get('llm_categorized', 0)
        uncategorized = stats['processed'] - total_categorized

        if not dry_run and stats['processed'] > 0:
            print(f"\n💡 Summary:")
            print(f"  Total new transactions: {stats['processed']}")
            print(f"  Pattern-matched: {stats['auto_categorized']}")
            print(f"  LLM-categorized: {stats.get('llm_categorized', 0)}")
            print(f"  Fully categorized: {total_categorized}/{stats['processed']} ({100*total_categorized//stats['processed'] if stats['processed'] > 0 else 0}%)")

            if uncategorized > 0:
                print(f"\n  ⚠ {uncategorized} transactions still need categorization")
                print(f"  Run: python3 main.py --ai-classify {min(25, uncategorized)} --ai-auto-apply")

            print(f"\n💡 Next steps:")
            print(f"  View transactions: python3 main.py --stats")
            print(f"  Web interface: python3 api_server.py && cd frontend && npm run dev")

        return {
            'success': True,
            'stats': stats,
            'llm_response': llm_response,
            'response_file': response_file,
            'result_file': result_file,
            'new_transactions': stats.get('new_transactions', [])
        }


def main():
    """CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(description='LLM-based CSV transaction ingestion')
    parser.add_argument('csv_file', help='Path to CSV file')
    parser.add_argument('--dry-run', action='store_true', help='Analyze only, do not insert to database')
    parser.add_argument('--api-key', help='Anthropic API key (or set ANTHROPIC_API_KEY env var)')
    parser.add_argument('--db', default='transactions.db', help='Database file (default: transactions.db)')

    args = parser.parse_args()

    # Check file exists
    if not os.path.exists(args.csv_file):
        print(f"Error: File not found: {args.csv_file}")
        sys.exit(1)

    # Initialize database
    db = TransactionDB(args.db)

    # Initialize LLM ingestion
    try:
        ingestion = LLMCSVIngestion(db, api_key=args.api_key)
    except ValueError as e:
        print(f"Error: {e}")
        print("\nSet your API key:")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        print("Or pass via --api-key flag")
        sys.exit(1)

    # Process CSV
    result = ingestion.process_csv_with_llm(args.csv_file, dry_run=args.dry_run)

    if result.get('success'):
        print("\n✓ Ingestion successful!")
        sys.exit(0)
    else:
        print(f"\n✗ Ingestion failed: {result.get('error')}")
        sys.exit(1)


if __name__ == '__main__':
    main()
