#!/usr/bin/env python3
"""
LLM-Based CSV Ingestion Experiment

This is a proof-of-concept to test if LLM API calls can replace hardcoded regex rules
during CSV transaction ingestion. Instead of predefined column mappings and extraction
patterns, we let the LLM analyze the CSV structure and existing database context to
determine how to properly map and classify transactions.

In production, this would call an actual LLM API. For this experiment, Claude Code
acts as a proxy for the API call.
"""

import csv
import sqlite3
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from database import TransactionDB


class LLMIngestionExperiment:
    """
    Experimental CSV ingestion using LLM-based dynamic mapping instead of hardcoded rules.
    """

    def __init__(self, db: TransactionDB):
        self.db = db
        self.db_path = db.db_path

    def get_database_context(self) -> Dict[str, Any]:
        """
        Gather context about the database schema and existing data to pass to the LLM.
        This simulates what we'd send as context in a real API call.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get schema info
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='transactions'")
        schema = cursor.fetchone()

        # Get sample transactions for pattern learning
        cursor.execute("""
            SELECT run_date, account, account_number, action, description, type,
                   amount, payee, symbol, category_id, subcategory_id
            FROM transactions
            WHERE payee IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 10
        """)
        sample_transactions = [dict(row) for row in cursor.fetchall()]

        # Get all categories/subcategories
        cursor.execute("""
            SELECT c.id as category_id, c.name as category_name,
                   s.id as subcategory_id, s.name as subcategory_name
            FROM categories c
            LEFT JOIN subcategories s ON c.id = s.category_id
            ORDER BY c.name, s.name
        """)
        categories = [dict(row) for row in cursor.fetchall()]

        # Get account mappings from existing data
        cursor.execute("""
            SELECT DISTINCT account, account_number
            FROM transactions
            ORDER BY account
        """)
        known_accounts = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return {
            'schema': schema['sql'] if schema else None,
            'sample_transactions': sample_transactions,
            'categories': categories,
            'known_accounts': known_accounts,
            'required_fields': ['run_date', 'account', 'account_number', 'action', 'amount', 'hash'],
            'optional_fields': ['symbol', 'description', 'type', 'payee', 'category_id', 'subcategory_id',
                              'quantity', 'price', 'commission', 'fees', 'settlement_date'],
            'date_format': 'YYYY-MM-DD (ISO format)',
            'notes': [
                'Investment transactions (stocks, ETFs, dividends) should have symbol populated and payee as None',
                'Cash transactions should extract merchant/payee from the action field',
                'Hash must be unique per transaction for duplicate detection',
                'Amounts are stored as signed floats (negative for debits)',
                'Dates in database are ISO format (YYYY-MM-DD)'
            ]
        }

    def read_csv_sample(self, filepath: str, num_rows: int = 5) -> Dict[str, Any]:
        """
        Read a small sample of the CSV to understand its structure.
        This would be sent to the LLM for analysis.
        """
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read().strip()
            lines = content.split('\n')

            # Find header
            header_line = None
            header_index = 0
            for i, line in enumerate(lines):
                if line.strip() and 'Run Date' in line and 'Amount' in line:
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
                'sample_rows': sample_rows,
                'total_sample_lines': len(sample_rows)
            }

    def generate_transaction_hash(self, transaction: Dict[str, Any]) -> str:
        """Generate unique hash for duplicate detection"""
        hash_string = f"{transaction.get('run_date', '')}-{transaction.get('account_number', '')}-{transaction.get('action', '')}-{transaction.get('amount', '')}"
        return hashlib.md5(hash_string.encode()).hexdigest()

    def convert_date_to_iso(self, date_str: str) -> Optional[str]:
        """Convert various date formats to ISO (YYYY-MM-DD)"""
        if not date_str or not date_str.strip():
            return None

        date_formats = ['%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d']

        for fmt in date_formats:
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
                cleaned = value.replace(',', '').strip()
                return float(cleaned) if cleaned else None
            return float(value)
        except (ValueError, AttributeError):
            return None

    def prepare_llm_prompt(self, csv_sample: Dict[str, Any], db_context: Dict[str, Any]) -> str:
        """
        Prepare the prompt that would be sent to an LLM API.
        In this experiment, this will be presented to Claude Code for processing.
        """
        prompt = f"""You are a financial transaction data mapping expert. Your task is to analyze a CSV file
and map its rows to a database schema, without using any hardcoded rules or regex patterns.

## DATABASE CONTEXT

### Target Schema:
```sql
{db_context['schema']}
```

### Known Accounts:
{json.dumps(db_context['known_accounts'], indent=2)}

### Available Categories (sample):
{json.dumps(db_context['categories'][:20], indent=2)}

### Sample Existing Transactions (for pattern learning):
{json.dumps(db_context['sample_transactions'], indent=2)}

### Important Rules:
{json.dumps(db_context['notes'], indent=2)}

## INPUT CSV FILE

### File: {csv_sample['filepath']}

### Headers:
{json.dumps(csv_sample['header'], indent=2)}

### Sample Rows:
{json.dumps(csv_sample['sample_rows'], indent=2)}

## YOUR TASK

For each row in the sample, produce a JSON mapping that shows:

1. **Column Mapping**: How CSV columns map to database fields
2. **Payee Extraction**: Extract merchant/payee name from the 'Action' field (for non-investment transactions)
3. **Transaction Type**: Classify the transaction type based on the action text
4. **Account Resolution**: Match or infer the account name and number
5. **Date Conversion**: Convert dates to ISO format (YYYY-MM-DD)
6. **Categorization**: Suggest category/subcategory based on existing patterns

Return your response as a JSON object with this structure:

{{
  "mapping_rules": {{
    "run_date": "name of CSV column for date",
    "action": "name of CSV column for transaction description",
    "amount": "name of CSV column for amount",
    ... (map all relevant fields)
  }},
  "account_inference": {{
    "account": "inferred account name",
    "account_number": "inferred account number",
    "source": "filename|csv_column|default"
  }},
  "transactions": [
    {{
      "csv_row_index": 0,
      "mapped_fields": {{
        "run_date": "2025-07-30",
        "account": "Individual - TOD",
        "account_number": "Z06431462",
        "action": "original action text",
        "amount": -2.80,
        "payee": "Market@Work",
        "type": "Debit Card",
        "symbol": null,
        ... (all database fields)
      }},
      "reasoning": "Brief explanation of extraction logic for payee, type, etc."
    }}
  ]
}}

IMPORTANT:
- Do NOT write code or rules, just analyze the data and produce the mapping
- Extract payee names intelligently from the action field
- Skip rows with "OUTSTAND AUTH" (pending transactions)
- Investment transactions should have symbol populated and payee=null
- Use patterns from existing transactions to inform your categorization
"""
        return prompt

    def save_prompt_for_review(self, prompt: str, output_file: str = "llm_prompt.txt"):
        """Save the generated prompt for review"""
        with open(output_file, 'w') as f:
            f.write(prompt)
        print(f"✓ LLM prompt saved to: {output_file}")
        print(f"✓ Prompt length: {len(prompt)} characters")

    def process_csv_with_llm_response(self, csv_filepath: str, llm_response: Dict[str, Any]) -> Dict[str, int]:
        """
        Process the full CSV file using the mapping rules determined by the LLM.
        This simulates applying the LLM's analysis to the complete dataset.
        """
        stats = {'processed': 0, 'duplicates': 0, 'errors': 0}

        # Extract mapping rules from LLM response
        mapping_rules = llm_response.get('mapping_rules', {})
        account_info = llm_response.get('account_inference', {})

        with open(csv_filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read().strip()
            lines = content.split('\n')

            # Find header
            header_index = 0
            for i, line in enumerate(lines):
                if line.strip() and 'Run Date' in line and 'Amount' in line:
                    header_index = i
                    break

            reader = csv.DictReader(lines[header_index:])

            for row_num, row in enumerate(reader):
                try:
                    # Skip empty rows
                    if not any(row.values()):
                        continue

                    # Skip pending transactions
                    action = row.get('Action', '')
                    if 'OUTSTAND AUTH' in action:
                        continue

                    # Apply LLM mapping rules (simplified for POC)
                    # In real implementation, this would use the full LLM response logic
                    transaction = self.apply_llm_mapping(row, mapping_rules, account_info)

                    if transaction:
                        # Try to insert
                        if self.db.insert_transaction(transaction, csv_filepath):
                            stats['processed'] += 1
                        else:
                            stats['duplicates'] += 1

                except Exception as e:
                    print(f"Error processing row {row_num}: {e}")
                    stats['errors'] += 1

        return stats

    def apply_llm_mapping(self, csv_row: Dict[str, Any], mapping_rules: Dict[str, str],
                         account_info: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Apply the LLM-determined mapping rules to a CSV row.
        This is a simplified version - real implementation would be more sophisticated.
        """
        # This is intentionally simplified for the POC
        # In production, the LLM would provide complete mapping logic

        transaction = {}

        # Required fields
        run_date_raw = csv_row.get(mapping_rules.get('run_date', 'Run Date'))
        transaction['run_date'] = self.convert_date_to_iso(run_date_raw)

        transaction['action'] = csv_row.get(mapping_rules.get('action', 'Action'), '')

        amount_raw = csv_row.get(mapping_rules.get('amount', 'Amount'))
        transaction['amount'] = self.clean_numeric_value(amount_raw)

        transaction['account'] = account_info.get('account', 'Unknown')
        transaction['account_number'] = account_info.get('account_number', 'Unknown')

        # Optional fields
        transaction['description'] = csv_row.get(mapping_rules.get('description', 'Description'), '')
        transaction['symbol'] = csv_row.get(mapping_rules.get('symbol', 'Symbol')) or None

        # Generate hash
        transaction['hash'] = self.generate_transaction_hash(transaction)

        # Validate required fields
        if not transaction['run_date'] or transaction['amount'] is None:
            return None

        return transaction

    def run_experiment(self, csv_filepath: str, sample_size: int = 5):
        """
        Main experiment runner:
        1. Gather database context
        2. Sample the CSV file
        3. Generate LLM prompt
        4. Save prompt for manual review
        """
        print("=" * 80)
        print("LLM-Based CSV Ingestion Experiment")
        print("=" * 80)

        print("\n[1/3] Gathering database context...")
        db_context = self.get_database_context()
        print(f"  ✓ Schema loaded")
        print(f"  ✓ {len(db_context['sample_transactions'])} sample transactions")
        print(f"  ✓ {len(db_context['categories'])} category/subcategory pairs")
        print(f"  ✓ {len(db_context['known_accounts'])} known accounts")

        print("\n[2/3] Analyzing CSV structure...")
        csv_sample = self.read_csv_sample(csv_filepath, sample_size)
        if 'error' in csv_sample:
            print(f"  ✗ Error: {csv_sample['error']}")
            return
        print(f"  ✓ Found {len(csv_sample['header'])} columns")
        print(f"  ✓ Sampled {len(csv_sample['sample_rows'])} rows")
        print(f"  ✓ Columns: {', '.join(csv_sample['header'][:5])}...")

        print("\n[3/3] Generating LLM prompt...")
        prompt = self.prepare_llm_prompt(csv_sample, db_context)
        self.save_prompt_for_review(prompt)

        print("\n" + "=" * 80)
        print("EXPERIMENT READY")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Review the generated prompt in 'llm_prompt.txt'")
        print("2. In production, this would be sent to an LLM API (Claude, GPT-4, etc.)")
        print("3. For this POC, you (Claude Code) will analyze the prompt and provide a JSON response")
        print("4. The response will be used to process the full CSV file")
        print("\nThis tests whether LLM-based mapping can replace hardcoded regex rules.")


def main():
    """Run the experiment"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 llm_ingestion_experiment.py <csv_file>")
        print("\nExample:")
        print("  python3 llm_ingestion_experiment.py transactions/processed/History_for_Account_Z06431462.csv")
        sys.exit(1)

    csv_file = sys.argv[1]

    # Initialize database
    db = TransactionDB('transactions.db')

    # Run experiment
    experiment = LLMIngestionExperiment(db)
    experiment.run_experiment(csv_file, sample_size=5)


if __name__ == '__main__':
    main()
