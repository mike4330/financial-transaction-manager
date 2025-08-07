#!/usr/bin/env python3
"""
Financial Transaction Parser and Manager
A Quicken-like application for parsing bank/brokerage CSV files
"""

import os
import sys
import argparse
import logging
from typing import List
from database import TransactionDB
from csv_parser import CSVParser
from file_monitor import FileMonitor
from ai_classifier import AITransactionClassifier
from html_generator import HTMLGenerator

def launch_web_interface(simple=False):
    """Launch Streamlit web interface"""
    import subprocess
    
    app_file = "web_app_simple.py" if simple else "web_app.py"
    interface_type = "simple" if simple else "AG-Grid"
    
    print(f"🚀 Launching {interface_type} web interface...")
    print("📊 The transaction editor will open in your default browser")
    print("🛑 Press Ctrl+C to stop the web server")
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", app_file])
    except KeyboardInterrupt:
        print("\n👋 Web interface shutting down...")
    except Exception as e:
        print(f"❌ Error launching web interface: {e}")
        print("💡 Make sure you have installed the required dependencies:")
        if simple:
            print("   pip install streamlit pandas")
        else:
            print("   pip install streamlit streamlit-aggrid pandas")

def setup_logging(level=logging.INFO):
    """Setup logging configuration"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('transaction_parser.log')
        ]
    )

def main():
    parser = argparse.ArgumentParser(description='Financial Transaction Parser and Manager')
    parser.add_argument('--transactions-dir', '-d', 
                       default='./transactions',
                       help='Directory to monitor for CSV files (default: ./transactions)')
    parser.add_argument('--database', '-db',
                       default='transactions.db',
                       help='SQLite database file (default: transactions.db)')
    parser.add_argument('--process-existing', '-p',
                       action='store_true',
                       help='Process existing CSV files and exit')
    parser.add_argument('--monitor', '-m',
                       action='store_true',
                       help='Start file monitoring mode')
    parser.add_argument('--stats', '-s',
                       action='store_true',
                       help='Show database statistics')
    parser.add_argument('--verbose', '-v',
                       action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--categories', '-c',
                       action='store_true',
                       help='Show category summary')
    parser.add_argument('--uncategorized', '-u',
                       type=int, nargs='?', const=20, metavar='LIMIT',
                       help='Show uncategorized transactions (default: 20)')
    parser.add_argument('--categorize',
                       nargs=3, metavar=('PATTERN', 'CATEGORY', 'SUBCATEGORY'),
                       help='Bulk categorize transactions by action pattern')
    parser.add_argument('--categorizedesc',
                       nargs=3, metavar=('PATTERN', 'CATEGORY', 'SUBCATEGORY'),
                       help='Bulk categorize transactions by description pattern')
    parser.add_argument('--ai-classify',
                       type=int, nargs='?', const=10, metavar='SAMPLE_SIZE',
                       help='Use AI to classify random sample of transactions (default: 10)')
    parser.add_argument('--ai-classify-ids',
                       nargs='+', type=int, metavar='ID',
                       help='Use AI to classify specific transaction IDs')
    parser.add_argument('--ai-auto-apply',
                       action='store_true',
                       help='Automatically apply high-confidence AI classifications')
    parser.add_argument('--fix',
                       action='store_true',
                       help='Fix problematic payees and misclassifications using learned patterns')
    parser.add_argument('--generate-html',
                       action='store_true',
                       help='Generate HTML report after operations')
    parser.add_argument('--html-file',
                       default='transactions_report.html',
                       help='HTML output file name (default: transactions_report.html)')
    parser.add_argument('--web', '-w',
                       action='store_true',
                       help='Launch web interface for transaction editing')
    parser.add_argument('--web-simple',
                       action='store_true',
                       help='Launch simple web interface (native Streamlit)')
    parser.add_argument('--detect-recurring',
                       action='store_true',
                       help='Detect recurring transaction patterns')
    parser.add_argument('--save-patterns',
                       action='store_true',
                       help='Save detected patterns to database (use with --detect-recurring)')
    parser.add_argument('--show-patterns',
                       action='store_true',
                       help='Show existing recurring patterns')
    parser.add_argument('--lookback-days',
                       type=int, default=365, metavar='DAYS',
                       help='Days to look back for pattern detection (default: 365)')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Financial Transaction Parser")
    
    # Launch web interface if requested
    if args.web:
        launch_web_interface(simple=False)
        return 0
    
    if args.web_simple:
        launch_web_interface(simple=True)
        return 0
    
    # Initialize database
    try:
        db = TransactionDB(args.database)
        logger.info(f"Database initialized: {args.database}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return 1
    
    # Show stats if requested
    if args.stats:
        show_stats(db)
        if args.generate_html:
            generate_html_report(db, args.html_file)
        if not (args.process_existing or args.monitor or args.categories or args.uncategorized or args.categorize or args.categorizedesc or args.ai_classify or args.ai_classify_ids):
            return 0
    
    # Show category summary if requested
    if args.categories:
        show_category_summary(db)
        if args.generate_html:
            generate_html_report(db, args.html_file)
        if not (args.process_existing or args.monitor or args.uncategorized or args.categorize or args.categorizedesc or args.ai_classify or args.ai_classify_ids):
            return 0
    
    # Show uncategorized transactions if requested
    if args.uncategorized is not None:
        show_uncategorized(db, args.uncategorized)
        if not (args.process_existing or args.monitor or args.categorize or args.categorizedesc or args.ai_classify or args.ai_classify_ids):
            return 0
    
    # Bulk categorize by action if requested
    if args.categorize:
        pattern, category, subcategory = args.categorize
        count = db.bulk_categorize_by_action(pattern, category, subcategory)
        print(f"Categorized {count} transactions matching '{pattern}' in action field as {category}/{subcategory}")
        
        # Generate HTML if requested or if categorization occurred
        if args.generate_html or count > 0:
            generate_html_report(db, args.html_file)
        
        if not (args.process_existing or args.monitor or args.categorizedesc or args.ai_classify or args.ai_classify_ids):
            return 0
    
    # Bulk categorize by description if requested
    if args.categorizedesc:
        pattern, category, subcategory = args.categorizedesc
        count = db.bulk_categorize_by_description(pattern, category, subcategory)
        print(f"Categorized {count} transactions matching '{pattern}' in description field as {category}/{subcategory}")
        
        # Generate HTML if requested or if categorization occurred
        if args.generate_html or count > 0:
            generate_html_report(db, args.html_file)
        
        if not (args.process_existing or args.monitor or args.ai_classify or args.ai_classify_ids):
            return 0
    
    # AI classify if requested
    if args.ai_classify is not None:
        if args.fix:
            applied_count = run_ai_fix_issues(db, args.ai_classify, args.ai_auto_apply)
        else:
            applied_count = run_ai_classification(db, args.ai_classify, args.ai_auto_apply)
        
        # Generate HTML if requested or if classifications were applied
        if args.generate_html or applied_count > 0:
            generate_html_report(db, args.html_file)
        
        if not (args.process_existing or args.monitor):
            return 0
    
    # AI classify specific IDs if requested
    if args.ai_classify_ids:
        applied_count = run_ai_classification_by_ids(db, args.ai_classify_ids, args.ai_auto_apply)
        
        # Generate HTML if requested or if classifications were applied
        if args.generate_html or applied_count > 0:
            generate_html_report(db, args.html_file)
        
        if not (args.process_existing or args.monitor):
            return 0
    
    # Process existing files if requested
    if args.process_existing:
        try:
            monitor = FileMonitor(args.transactions_dir, db, auto_process=False)
            stats = monitor.process_existing_files()
            
            print(f"\nProcessing Results:")
            print(f"  Files processed: {stats['files']}")
            print(f"  New transactions: {stats['processed']}")
            print(f"  Duplicates skipped: {stats['duplicates']}")
            print(f"  Errors: {stats['errors']}")
            
            # Generate HTML if requested or if significant processing occurred
            if args.generate_html or stats['processed'] > 0:
                generate_html_report(db, args.html_file)
            
        except Exception as e:
            logger.error(f"Error processing existing files: {e}")
            return 1
    
    # Start monitoring if requested
    if args.monitor:
        try:
            logger.info(f"Starting file monitor for directory: {args.transactions_dir}")
            
            # Create HTML callback function - always regenerate HTML in monitor mode when data changes
            html_callback = lambda: generate_html_report(db, args.html_file)
            
            monitor = FileMonitor(args.transactions_dir, db, auto_process=True, html_callback=html_callback)
            
            # Process existing files first
            stats = monitor.process_existing_files()
            
            # Generate initial HTML report (always generate in monitor mode)
            generate_html_report(db, args.html_file)
            print(f"Initial HTML report generated: {args.html_file}")
            
            print(f"\nMonitoring {args.transactions_dir} for new CSV files...")
            print("Press Ctrl+C to stop")
            
            monitor.start_monitoring()
            
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Error in monitoring mode: {e}")
            return 1
    
    # Recurring pattern detection
    if args.detect_recurring:
        patterns = detect_recurring_patterns(db, args.lookback_days)
        if args.save_patterns:
            save_detected_patterns(db, patterns)
    
    # Show recurring patterns  
    if args.show_patterns:
        show_recurring_patterns(db)
    
    # If no action specified, show help
    if not (args.process_existing or args.monitor or args.stats or args.categories or args.uncategorized or args.categorize or args.categorizedesc or args.ai_classify or args.ai_classify_ids or args.web or args.web_simple or args.detect_recurring or args.show_patterns):
        parser.print_help()
        return 1
    
    logger.info("Financial Transaction Parser completed")
    return 0

def show_stats(db: TransactionDB):
    """Display database statistics"""
    try:
        total_transactions = db.get_transaction_count()
        account_summary = db.get_account_summary()
        
        print(f"\nDatabase Statistics:")
        print(f"  Total transactions: {total_transactions:,}")
        
        if account_summary:
            print(f"\nAccount Summary:")
            for account, account_num, count, total in account_summary:
                print(f"  {account} ({account_num}): {count:,} transactions, ${total:,.2f}")
        
    except Exception as e:
        logging.error(f"Error displaying stats: {e}")

def show_category_summary(db: TransactionDB):
    """Display category summary"""
    try:
        category_summary = db.get_category_summary()
        
        print(f"\nCategory Summary:")
        print(f"{'Category':<20} {'Subcategory':<15} {'Count':>8} {'Total':>12} {'Average':>10}")
        print("-" * 70)
        
        for category, subcategory, count, total, avg in category_summary:
            subcategory_display = subcategory if subcategory else ""
            print(f"{category:<20} {subcategory_display:<15} {count:>8} ${total:>10.2f} ${avg:>8.2f}")
        
    except Exception as e:
        logging.error(f"Error displaying category summary: {e}")

def show_uncategorized(db: TransactionDB, limit: int):
    """Display uncategorized transactions"""
    try:
        uncategorized = db.get_uncategorized_transactions(limit)
        
        print(f"\nUncategorized Transactions (showing {len(uncategorized)} of max {limit}):")
        print(f"{'ID':>5} {'Date':<12} {'Account':<20} {'Amount':>10} {'Payee':<15} {'Description'}")
        print("-" * 95)
        
        for tx_id, date, account, description, amount, action, payee in uncategorized:
            # Truncate long descriptions and payee
            desc_short = description[:30] + "..." if len(description) > 30 else description
            payee_short = (payee[:12] + "..." if payee and len(payee) > 12 else payee) or ""
            print(f"{tx_id:>5} {date:<12} {account[:20]:<20} ${amount:>8.2f} {payee_short:<15} {desc_short}")
        
        if len(uncategorized) == limit:
            print(f"\n(Use --uncategorized {limit + 50} to see more)")
        
    except Exception as e:
        logging.error(f"Error displaying uncategorized transactions: {e}")

def run_ai_classification(db: TransactionDB, sample_size: int, auto_apply: bool):
    """Run AI classification on a sample of transactions"""
    try:
        classifier = AITransactionClassifier(db)
        results = classifier.classify_sample_transactions(sample_size, auto_apply)
        
        if not results:
            print("No uncategorized transactions found to classify.")
            return
        
        applied_count = 0
        high_confidence_count = 0
        
        # Only print applied changes when auto_apply is enabled
        if auto_apply:
            applied_results = [r for r in results if r['applied']]
            if applied_results:
                print(f"Applied AI Classifications ({len(applied_results)} changes):")
                print("=" * 80)
                
                for result in applied_results:
                    payee = result.get('payee') or 'None'
                    print(f"✅ ID:{result['id']} | {result['date']} | ${result['amount']:.2f} | {payee[:20]:<20} | → {result['suggested_category']}/{result['suggested_subcategory']} ({result['confidence']:.2f})")
                    applied_count += 1
        else:
            # When not auto-applying, show all results as before
            print(f"\nAI Classification Results (Sample of {len(results)} transactions):")
            print("=" * 100)
            
            for result in results:
                confidence_marker = "🎯" if result['confidence'] > 0.7 else "❓"
                applied_marker = "✅" if result['applied'] else ""
                
                # Single line format with payee
                payee = result.get('payee') or 'None'
                print(f"{confidence_marker} ID:{result['id']} {applied_marker} | {result['date']} | ${result['amount']:.2f} | {payee[:20]:<20} | {result['suggested_category']}/{result['suggested_subcategory']} ({result['confidence']:.2f})")
                
                if result['applied']:
                    applied_count += 1
        
        # Count high confidence for summary
        for result in results:
            if result['confidence'] > 0.7:
                high_confidence_count += 1
        
        # Summary only when not auto-applying or when there are applied changes
        if not auto_apply or applied_count > 0:
            if not auto_apply:
                print(f"\n" + "=" * 100)
                print(f"Summary:")
                print(f"  High confidence suggestions (>70%): {high_confidence_count}")
                print(f"  Auto-applied classifications: {applied_count}")
                print(f"  Remaining uncategorized: {db.get_transaction_count() - len([r for r in results if r['applied']])}")
            else:
                print(f"\nSummary: {applied_count} transactions categorized")
        
        if not auto_apply and high_confidence_count > 0:
            print(f"\nTo auto-apply high confidence classifications, run:")
            print(f"python3 main.py --ai-classify {sample_size} --ai-auto-apply")
        
        # Return count of applied classifications for HTML generation
        return applied_count
        
    except Exception as e:
        logging.error(f"Error in AI classification: {e}")
        return 0

def run_ai_classification_by_ids(db: TransactionDB, transaction_ids: List[int], auto_apply: bool):
    """Run AI classification on specific transaction IDs"""
    try:
        classifier = AITransactionClassifier(db)
        results = classifier.classify_transactions_by_ids(transaction_ids, auto_apply)
        
        if not results:
            print("No transactions found for the provided IDs.")
            return 0
        
        applied_count = 0
        high_confidence_count = 0
        
        # Only print applied changes when auto_apply is enabled
        if auto_apply:
            applied_results = [r for r in results if r['applied']]
            if applied_results:
                print(f"Applied AI Classifications ({len(applied_results)} changes):")
                print("=" * 80)
                
                for result in applied_results:
                    payee = result.get('payee') or 'None'
                    print(f"✅ ID:{result['id']} | {result['date']} | ${result['amount']:.2f} | {payee[:20]:<20} | → {result['suggested_category']}/{result['suggested_subcategory']} ({result['confidence']:.2f})")
                    applied_count += 1
        else:
            # When not auto-applying, show all results as before
            print(f"\nAI Classification Results ({len(results)} specific transactions):")
            print("=" * 100)
            
            for result in results:
                confidence_marker = "🎯" if result['confidence'] > 0.7 else "❓"
                applied_marker = "✅" if result['applied'] else ""
                
                # Single line format with payee
                payee = result.get('payee') or 'None'
                print(f"{confidence_marker} ID:{result['id']} {applied_marker} | {result['date']} | ${result['amount']:.2f} | {payee[:20]:<20} | {result['suggested_category']}/{result['suggested_subcategory']} ({result['confidence']:.2f})")
                
                if result['applied']:
                    applied_count += 1
        
        # Count high confidence for summary
        for result in results:
            if result['confidence'] > 0.7:
                high_confidence_count += 1
        
        # Summary only when not auto-applying or when there are applied changes
        if not auto_apply or applied_count > 0:
            if not auto_apply:
                print(f"\n" + "=" * 100)
                print(f"Summary:")
                print(f"  High confidence suggestions (>70%): {high_confidence_count}")
                print(f"  Auto-applied classifications: {applied_count}")
                print(f"  Remaining uncategorized: {db.get_transaction_count() - len([r for r in results if r['applied']])}")
            else:
                print(f"\nSummary: {applied_count} transactions categorized")
        
        if not auto_apply and high_confidence_count > 0:
            ids_str = ' '.join(map(str, transaction_ids))
            print(f"\nTo auto-apply high confidence classifications, run:")
            print(f"python3 main.py --ai-classify-ids {ids_str} --ai-auto-apply")
        
        # Return count of applied classifications for HTML generation
        return applied_count
        
    except Exception as e:
        logging.error(f"Error in AI classification by IDs: {e}")
        return 0

def run_ai_fix_issues(db: TransactionDB, sample_size: int, auto_apply: bool):
    """Run AI fix on problematic transactions"""
    try:
        classifier = AITransactionClassifier(db)
        results = classifier.fix_transaction_issues(sample_size, auto_apply)
        
        if not results:
            print("No problematic transactions found to fix.")
            return 0
        
        print(f"\nAI Fix Results ({len(results)} problematic transactions):")
        print("=" * 120)
        
        applied_count = 0
        payee_fixes = 0
        category_fixes = 0
        
        for result in results:
            # Only show high confidence if we actually have improvements to suggest
            has_improvements = result['payee_improved'] or result['category_improved']
            confidence_marker = "🎯" if (result['confidence'] > 0.7 and has_improvements) else "❓"
            applied_marker = "✅" if result['applied'] else ""
            
            # Show what's being fixed or current state if no fixes
            fixes = []
            if result['payee_improved']:
                fixes.append(f"Payee: '{result['current_payee']}' → '{result['suggested_payee']}'")
                payee_fixes += 1
            if result['category_improved']:
                fixes.append(f"Category: {result['current_category']} → {result['suggested_category']}/{result['suggested_subcategory']}")
                category_fixes += 1
            
            if fixes:
                fix_description = " | ".join(fixes)
            else:
                # Show current state if no improvements suggested
                current_state = []
                if not result['current_payee'] or result['current_payee'] in ['No Description', 'Chase Bank']:
                    current_state.append(f"Payee: '{result['current_payee'] or 'None'}' (no improvement found)")
                if not result['current_category']:
                    current_state.append("Category: None (no improvement found)")
                fix_description = " | ".join(current_state) if current_state else "Already properly classified"
            
            print(f"{confidence_marker} ID:{result['id']} {applied_marker} | {result['date']} | ${result['amount']:.2f} | {fix_description}")
            
            if result['applied']:
                applied_count += 1
        
        print(f"\n" + "=" * 120)
        print(f"Summary:")
        print(f"  Payee improvements found: {payee_fixes}")
        print(f"  Category improvements found: {category_fixes}")
        print(f"  Auto-applied fixes: {applied_count}")
        
        if not auto_apply and len(results) > 0:
            print(f"\nTo auto-apply high confidence fixes, run:")
            print(f"python3 main.py --ai-classify {sample_size} --fix --ai-auto-apply")
        
        # Return count of applied fixes for HTML generation
        return applied_count
        
    except Exception as e:
        logging.error(f"Error in AI fix: {e}")
        return 0

def detect_recurring_patterns(db: TransactionDB, lookback_days: int):
    """Detect recurring transaction patterns and display results"""
    print(f"\n🔍 Detecting recurring patterns (looking back {lookback_days} days)...")
    
    patterns = db.detect_recurring_patterns(lookback_days=lookback_days)
    
    if not patterns:
        print("❌ No recurring patterns detected")
        return []
    
    print(f"\n✅ Found {len(patterns)} recurring patterns:")
    print("=" * 120)
    
    for i, pattern in enumerate(patterns, 1):
        confidence_pct = pattern['confidence'] * 100
        confidence_icon = "🟢" if confidence_pct >= 70 else "🟡" if confidence_pct >= 50 else "🔴"
        
        print(f"{i:2d}. {confidence_icon} {pattern['pattern_name']}")
        print(f"     Account: {pattern['account_number']}")
        print(f"     Frequency: {pattern['frequency_type']} (every {pattern.get('frequency_interval', 1)})")
        print(f"     Amount: ${pattern['typical_amount']:.2f}")
        if pattern['amount_variance'] > 0:
            print(f"     Amount variance: ±${pattern['amount_variance']:.2f}")
        print(f"     Confidence: {confidence_pct:.1f}%")
        print(f"     Occurrences: {pattern['occurrence_count']}")
        print(f"     Last seen: {pattern['last_occurrence_date']}")
        print(f"     Next expected: {pattern['next_expected_date']}")
        print(f"     Pattern type: {pattern.get('pattern_type', 'unknown')}")
        print()
    
    return patterns

def save_detected_patterns(db: TransactionDB, patterns: List):
    """Save detected patterns to the database"""
    if not patterns:
        print("❌ No patterns to save")
        return
    
    print(f"\n💾 Saving {len(patterns)} patterns to database...")
    
    saved_count = 0
    for pattern in patterns:
        pattern_id = db.save_recurring_pattern(pattern)
        if pattern_id:
            saved_count += 1
            print(f"✅ Saved: {pattern['pattern_name']}")
        else:
            print(f"❌ Failed to save: {pattern['pattern_name']}")
    
    print(f"\n✅ Successfully saved {saved_count}/{len(patterns)} patterns")

def show_recurring_patterns(db: TransactionDB):
    """Display stored recurring patterns"""
    print("\n📊 Stored Recurring Patterns:")
    
    patterns = db.get_recurring_patterns()
    
    if not patterns:
        print("❌ No stored patterns found")
        return
    
    print("=" * 120)
    print(f"{'ID':<3} {'Pattern Name':<40} {'Account':<12} {'Amount':<12} {'Frequency':<10} {'Confidence':<10} {'Next Due':<12}")
    print("=" * 120)
    
    for pattern in patterns:
        pattern_id, pattern_name, account_number, payee, typical_amount, amount_variance, frequency_type, frequency_interval, next_expected_date, last_occurrence_date, confidence, occurrence_count, is_active, created_at, category, subcategory = pattern
        
        status_icon = "🟢" if is_active else "🔴"
        confidence_pct = confidence * 100 if confidence else 0
        amount_str = f"${typical_amount:.2f}"
        if amount_variance and amount_variance > 0:
            amount_str += f"±{amount_variance:.0f}"
        
        print(f"{status_icon}{pattern_id:<2} {pattern_name[:38]:<40} {account_number[:10]:<12} {amount_str:<12} {frequency_type:<10} {confidence_pct:>6.1f}%   {next_expected_date:<12}")
    
    print("=" * 120)
    print(f"Total patterns: {len(patterns)}")
    active_count = sum(1 for p in patterns if p[12])  # is_active column
    print(f"Active patterns: {active_count}")

def generate_html_report(db: TransactionDB, html_file: str):
    """Generate HTML report"""
    try:
        generator = HTMLGenerator(db, html_file)
        generator.generate_report()
        print(f"HTML report generated: {html_file}")
        return True
    except Exception as e:
        logging.error(f"Error generating HTML report: {e}")
        return False

if __name__ == "__main__":
    sys.exit(main())