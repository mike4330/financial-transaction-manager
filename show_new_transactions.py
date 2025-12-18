#!/usr/bin/env python3
"""
Display new transactions in a pretty table format
"""

import sys
import json
from datetime import datetime


def format_currency(amount):
    """Format amount as currency"""
    if amount is None:
        return "$0.00"
    return f"${amount:,.2f}" if amount >= 0 else f"-${abs(amount):,.2f}"


def truncate(text, length):
    """Truncate text to length"""
    if not text:
        return ""
    text = str(text)
    return text if len(text) <= length else text[:length-3] + "..."


def print_transaction_table(transactions, title="New Transactions"):
    """Print transactions in a nice table format"""

    if not transactions:
        print(f"\n{title}: None")
        return

    print(f"\n{'=' * 140}")
    print(f"{title} ({len(transactions)} transactions)")
    print(f"{'=' * 140}")

    # Header
    print(f"{'Date':<12} {'Amount':>12} {'Type':<18} {'Payee':<25} {'Action':<60}")
    print(f"{'-' * 140}")

    # Sort by date
    sorted_txns = sorted(transactions, key=lambda x: x.get('run_date', ''))

    total = 0
    for txn in sorted_txns:
        date = txn.get('run_date', 'N/A')
        amount = txn.get('amount', 0)
        trans_type = truncate(txn.get('type', 'Unknown'), 18)
        payee = truncate(txn.get('payee', 'None'), 25)
        action = truncate(txn.get('action', ''), 60)

        # Color coding for terminal (optional)
        amount_str = format_currency(amount)

        print(f"{date:<12} {amount_str:>12} {trans_type:<18} {payee:<25} {action:<60}")

        total += (amount or 0)

    print(f"{'-' * 140}")
    print(f"{'Total:':<30} {format_currency(total):>12}")
    print(f"{'=' * 140}")


def print_summary_stats(transactions):
    """Print summary statistics"""
    if not transactions:
        return

    # Group by type
    by_type = {}
    by_date = {}

    for txn in transactions:
        trans_type = txn.get('type', 'Unknown')
        date = txn.get('run_date', 'N/A')[:7]  # YYYY-MM
        amount = txn.get('amount', 0)

        by_type[trans_type] = by_type.get(trans_type, {'count': 0, 'total': 0})
        by_type[trans_type]['count'] += 1
        by_type[trans_type]['total'] += amount

        by_date[date] = by_date.get(date, {'count': 0, 'total': 0})
        by_date[date]['count'] += 1
        by_date[date]['total'] += amount

    print(f"\n{'=' * 80}")
    print("Summary by Transaction Type")
    print(f"{'=' * 80}")
    print(f"{'Type':<25} {'Count':>10} {'Total':>15}")
    print(f"{'-' * 80}")

    for trans_type, stats in sorted(by_type.items()):
        print(f"{trans_type:<25} {stats['count']:>10} {format_currency(stats['total']):>15}")

    print(f"\n{'=' * 80}")
    print("Summary by Month")
    print(f"{'=' * 80}")
    print(f"{'Month':<15} {'Count':>10} {'Total':>15}")
    print(f"{'-' * 80}")

    for month, stats in sorted(by_date.items()):
        print(f"{month:<15} {stats['count']:>10} {format_currency(stats['total']):>15}")

    print(f"{'=' * 80}")


def main():
    """Main entry point"""

    if len(sys.argv) < 2:
        print("Usage: python3 show_new_transactions.py <result_json_file>")
        print("\nThis script is typically called from test_llm_ingest.sh")
        sys.exit(1)

    result_file = sys.argv[1]

    try:
        with open(result_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {result_file}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {result_file}")
        sys.exit(1)

    # Get new transactions from the result
    new_transactions = data.get('new_transactions', [])

    if not new_transactions:
        print("\n" + "=" * 80)
        print("No new transactions to display")
        print("=" * 80)
        print("\nAll transactions in the CSV are either:")
        print("  • Already in the database (duplicates)")
        print("  • Pending/uncleared (skipped)")
        print("  • Invalid (errors)")
        return

    # Print the table
    print_transaction_table(new_transactions)

    # Print summary
    print_summary_stats(new_transactions)

    # Print categorization info
    uncategorized = [t for t in new_transactions if not t.get('category_id')]
    categorized = len(new_transactions) - len(uncategorized)

    print(f"\n📊 Categorization Status:")
    print(f"  Auto-categorized: {categorized} (using learned patterns)")
    print(f"  Needs categorization: {len(uncategorized)}")

    if uncategorized:
        print(f"\n💡 Categorize remaining with AI:")
        print(f"   python3 main.py --ai-classify {min(25, len(uncategorized))} --ai-auto-apply")


if __name__ == '__main__':
    main()
