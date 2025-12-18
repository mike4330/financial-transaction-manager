#!/usr/bin/env python3
"""
LLM Payee Fix Tool

Fixes missing payees in existing transactions using LLM extraction.
This tool finds transactions with NULL or "No Description" payees and
uses Claude API to extract proper merchant/payee names.

Usage:
    # Preview what would be extracted (dry run)
    python3 llm_payee_fix.py --dry-run

    # Fix missing payees (limited batch)
    python3 llm_payee_fix.py --apply --limit 50

    # Fix all missing payees
    python3 llm_payee_fix.py --apply --limit 1000

    # Show statistics
    python3 llm_payee_fix.py --stats
"""

import argparse
import logging
import sys
import sqlite3
from typing import List, Dict
from database import TransactionDB
from llm_payee_extractor import LLMPayeeExtractor


def get_transactions_with_missing_payees(db_path: str, limit: int = 100) -> List[Dict]:
    """Get transactions that need payee extraction"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, run_date, account, action, description, amount, type
        FROM transactions
        WHERE (payee IS NULL OR payee = '' OR payee = 'No Description')
        AND type NOT IN ('Investment Trade', 'Dividend', 'Reinvestment', 'Dividend Taxes', 'Brokerage Fee')
        AND symbol IS NULL
        ORDER BY run_date DESC
        LIMIT ?
    ''', (limit,))

    transactions = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return transactions


def apply_llm_payee_fixes(db_path: str, results: List[Dict], dry_run: bool = True) -> int:
    """Apply LLM-extracted payees to database"""
    if dry_run:
        return 0

    updated_count = 0
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for result in results:
        if result.get('payee') and result.get('confidence', 0.0) >= 0.7:
            try:
                cursor.execute('''
                    UPDATE transactions
                    SET payee = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (result['payee'], result['id']))
                updated_count += 1
            except Exception as e:
                logging.warning(f"Failed to update TX#{result['id']}: {e}")

    conn.commit()
    conn.close()

    return updated_count


def main():
    parser = argparse.ArgumentParser(description='LLM-based Payee Extraction Fix Tool')
    parser.add_argument('--db', default='transactions.db', help='Database file')
    parser.add_argument('--dry-run', action='store_true', help='Preview extractions without applying')
    parser.add_argument('--apply', action='store_true', help='Apply LLM-extracted payees to database')
    parser.add_argument('--limit', type=int, default=100, help='Max transactions to process (default: 100)')
    parser.add_argument('--stats', action='store_true', help='Show LLM extraction statistics')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger(__name__)

    # Initialize database
    db = TransactionDB(args.db)

    # Show stats if requested
    if args.stats:
        try:
            extractor = LLMPayeeExtractor(db)
            stats = extractor.get_stats()

            print("\n" + "=" * 80)
            print("LLM PAYEE EXTRACTION STATISTICS")
            print("=" * 80)
            print(f"Cached patterns: {stats.get('cached_patterns', 0)}")
            print(f"Total pattern usage: {stats.get('total_pattern_usage', 0)}")
            print(f"Cache enabled: {stats.get('cache_enabled', False)}")
            print("=" * 80)

            # Show sample cached patterns
            conn = sqlite3.connect(args.db)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT pattern, replacement, usage_count
                FROM payee_extraction_patterns
                WHERE is_active = 1
                ORDER BY usage_count DESC
                LIMIT 10
            ''')

            patterns = cursor.fetchall()
            if patterns:
                print("\nTop 10 Cached Patterns:")
                print(f"{'Pattern':<40} {'Replacement':<25} {'Usage':>8}")
                print("-" * 75)
                for pattern, replacement, usage in patterns:
                    print(f"{pattern[:38]:<40} {replacement[:23]:<25} {usage:>8}")

            conn.close()

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return 1

        return 0

    # Get transactions with missing payees
    logger.info(f"Finding transactions with missing payees (limit: {args.limit})...")
    transactions = get_transactions_with_missing_payees(args.db, args.limit)

    if not transactions:
        print("\nNo transactions with missing payees found.")
        return 0

    print(f"\nFound {len(transactions)} transactions with missing payees")

    # Initialize LLM extractor
    try:
        extractor = LLMPayeeExtractor(db, enable_caching=True, max_batch_size=20)
    except ValueError as e:
        logger.error(f"Failed to initialize LLM extractor: {e}")
        print("\nERROR: ANTHROPIC_API_KEY environment variable not set.")
        print("Get your key from: https://console.anthropic.com/settings/keys")
        print("Then: export ANTHROPIC_API_KEY='your-key-here'")
        return 1

    # Extract payees
    logger.info("Extracting payees using LLM...")
    results = extractor.extract_batch(transactions)

    # Display results
    print("\n" + "=" * 120)
    print("LLM PAYEE EXTRACTION RESULTS")
    print("=" * 120)
    print(f"{'ID':<6} {'Date':<12} {'Account':<25} {'Amount':>10} {'Extracted Payee':<25} {'Conf':>6} {'Action Sample'}")
    print("=" * 120)

    high_confidence_count = 0
    for i, result in enumerate(results):
        tx = transactions[i]
        payee = result.get('payee', 'FAILED')
        confidence = result.get('confidence', 0.0)
        confidence_marker = "✓" if confidence >= 0.7 else "?"

        if confidence >= 0.7:
            high_confidence_count += 1

        # Truncate long fields
        account = tx['account'][:23] if tx['account'] else 'N/A'
        action_sample = tx['action'][:50] if tx['action'] else ''

        print(f"{tx['id']:<6} {tx['run_date']:<12} {account:<25} ${tx['amount']:>8.2f} "
              f"{confidence_marker} {payee[:23]:<25} {confidence:>5.2f} {action_sample}")

    print("=" * 120)
    print(f"High confidence extractions (≥0.7): {high_confidence_count}/{len(results)}")

    # Apply if requested
    if args.apply:
        updated_count = apply_llm_payee_fixes(args.db, results, dry_run=False)
        print(f"\n✓ Updated {updated_count} transactions with LLM-extracted payees")

        # Show caching stats
        stats = extractor.get_stats()
        print(f"✓ Cached {stats.get('cached_patterns', 0)} new extraction patterns for future use")

    elif args.dry_run or not args.apply:
        print("\nDRY RUN - No changes made to database")
        print(f"Run with --apply to update {high_confidence_count} high-confidence payees")

    return 0


if __name__ == '__main__':
    sys.exit(main())
