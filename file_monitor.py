import os
import time
import logging
import subprocess
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from csv_parser import CSVParser
from database import TransactionDB

class CSVFileHandler(FileSystemEventHandler):
    def __init__(self, parser: CSVParser, auto_process: bool = True, html_callback=None, enable_post_processing: bool = True, enable_llm_payee: bool = False):
        self.parser = parser
        self.auto_process = auto_process
        self.html_callback = html_callback
        self.enable_post_processing = enable_post_processing
        self.enable_llm_payee = enable_llm_payee
        self.logger = logging.getLogger(__name__)
        
    def on_created(self, event):
        if event.is_directory:
            return
            
        if event.src_path.lower().endswith('.csv'):
            self.logger.info(f"New CSV file detected: {event.src_path}")
            if self.auto_process:
                # Wait a moment for file to be fully written
                time.sleep(2)
                self._process_file(event.src_path)
    
    def on_modified(self, event):
        if event.is_directory:
            return
            
        if event.src_path.lower().endswith('.csv'):
            self.logger.info(f"CSV file modified: {event.src_path}")
            if self.auto_process:
                # Wait a moment for file to be fully written
                time.sleep(2)
                self._process_file(event.src_path)
    
    def _process_file(self, filepath):
        """Process a single file with error handling"""
        try:
            if os.path.exists(filepath):
                stats = self.parser.process_file(filepath)
                self.logger.info(f"Auto-processed {os.path.basename(filepath)}: {stats}")
                
                # Run post-processing if new transactions were imported
                if self.enable_post_processing and stats['processed'] > 0:
                    self.logger.info(f"Running post-processing for {stats['processed']} new transactions...")
                    self._run_post_processing()
                
                # Move processed file
                if stats['errors'] == 0:
                    self.parser.move_processed_file(filepath)
                
                # Generate HTML if callback provided and new transactions were processed
                if self.html_callback and stats['processed'] > 0:
                    self.html_callback()
                    
            else:
                self.logger.warning(f"File no longer exists: {filepath}")
        except Exception as e:
            self.logger.error(f"Error auto-processing {filepath}: {e}")
    
    def _run_post_processing(self):
        """Run payee extraction and AI classification on newly imported transactions"""
        try:
            # Step 1: Run regex-based payee extraction
            self.logger.info("Running regex-based payee extraction on new transactions...")
            payee_result = self._run_payee_extraction()

            if payee_result:
                self.logger.info(f"Regex payee extraction completed: {payee_result}")
            else:
                self.logger.warning("Regex payee extraction failed or returned no results")

            # Step 2: Run LLM-based payee extraction for failures (NEW!)
            if self.enable_llm_payee:
                self.logger.info("Running LLM fallback for missing payees...")
                llm_result = self._run_llm_payee_extraction()

                if llm_result:
                    self.logger.info(f"LLM payee extraction completed: {llm_result}")
                else:
                    self.logger.warning("LLM payee extraction failed or returned no results")

            # Step 3: Run pattern-based AI classification
            self.logger.info("Running AI classification on uncategorized transactions...")
            ai_result = self._run_ai_classification()

            if ai_result:
                self.logger.info(f"AI classification completed: {ai_result}")
            else:
                self.logger.warning("AI classification failed or returned no results")

        except Exception as e:
            self.logger.error(f"Error during post-processing: {e}")
    
    def _run_payee_extraction(self):
        """Run payee extraction using the PayeeExtractor module"""
        try:
            # Import and run payee extractor directly
            from payee_extractor import PayeeExtractor
            
            extractor = PayeeExtractor(self.parser.db.db_path)
            results = extractor.extract_all_payees(dry_run=False)
            
            return f"extracted {results.get('updated_count', 0)} payees"
            
        except ImportError as e:
            self.logger.error(f"Could not import PayeeExtractor: {e}")
            # Fallback to subprocess call
            return self._run_payee_extraction_subprocess()
        except Exception as e:
            self.logger.error(f"Error running payee extraction: {e}")
            return None
    
    def _run_payee_extraction_subprocess(self):
        """Fallback method to run payee extraction via subprocess"""
        try:
            result = subprocess.run(
                [sys.executable, 'payee_extractor.py', '--apply'],
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
                cwd=os.path.dirname(os.path.abspath(__file__))
            )

            if result.returncode == 0:
                # Parse output for success info
                output_lines = result.stdout.strip().split('\n')
                return f"subprocess completed: {output_lines[-1] if output_lines else 'success'}"
            else:
                self.logger.error(f"Payee extraction subprocess failed: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            self.logger.error("Payee extraction subprocess timed out")
            return None
        except Exception as e:
            self.logger.error(f"Error running payee extraction subprocess: {e}")
            return None

    def _run_llm_payee_extraction(self):
        """
        Run LLM-based payee extraction for transactions where regex failed

        This is the NEW fallback layer that uses Claude API to extract payees
        when regex patterns don't match.
        """
        try:
            self.logger.info("=" * 80)
            self.logger.info("STARTING LLM PAYEE EXTRACTION FALLBACK")
            self.logger.info("=" * 80)

            # Import LLM payee extractor
            from llm_payee_extractor import LLMPayeeExtractor

            # Get transactions with missing payees
            import sqlite3
            conn = sqlite3.connect(self.parser.db.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Find transactions with NULL or "No Description" payees
            self.logger.debug("Querying for transactions with missing payees...")
            cursor.execute('''
                SELECT id, action, description, amount
                FROM transactions
                WHERE (payee IS NULL OR payee = '' OR payee = 'No Description')
                AND type NOT IN ('Investment Trade', 'Dividend', 'Reinvestment', 'Dividend Taxes', 'Brokerage Fee')
                AND symbol IS NULL
                ORDER BY id DESC
                LIMIT 100
            ''')

            failed_transactions = [dict(row) for row in cursor.fetchall()]
            conn.close()

            if not failed_transactions:
                self.logger.info("No transactions with missing payees found")
                self.logger.info("=" * 80)
                return "no transactions with missing payees"

            self.logger.info(f"Found {len(failed_transactions)} transactions with missing payees")
            self.logger.debug(f"Transaction IDs: {[tx['id'] for tx in failed_transactions[:20]]}"
                            f"{'...' if len(failed_transactions) > 20 else ''}")

            # Initialize LLM extractor
            self.logger.info("Initializing LLM payee extractor...")
            extractor = LLMPayeeExtractor(self.parser.db, enable_caching=True, max_batch_size=20)
            self.logger.info(f"LLM extractor initialized (caching: enabled, max_batch: 20)")

            # Extract payees in batches
            self.logger.info(f"Starting batch extraction for {len(failed_transactions)} transactions...")
            results = extractor.extract_batch(failed_transactions)
            self.logger.info(f"Batch extraction complete, processing {len(results)} results...")

            # Update database with successful extractions
            updated_count = 0
            low_confidence_count = 0
            failed_count = 0

            for result in results:
                if result.get('payee') and result.get('confidence', 0.0) >= 0.7:
                    try:
                        conn = sqlite3.connect(self.parser.db.db_path)
                        cursor = conn.cursor()
                        cursor.execute('''
                            UPDATE transactions
                            SET payee = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (result['payee'], result['id']))
                        conn.commit()
                        conn.close()
                        updated_count += 1
                        self.logger.debug(f"✓ TX#{result['id']}: '{result['payee']}' (confidence: {result['confidence']:.2f})")
                    except Exception as e:
                        self.logger.warning(f"✗ Failed to update TX#{result['id']}: {e}")
                        failed_count += 1
                elif result.get('payee'):
                    low_confidence_count += 1
                    self.logger.debug(f"? TX#{result['id']}: '{result['payee']}' skipped (confidence: {result['confidence']:.2f} < 0.7)")
                else:
                    failed_count += 1
                    self.logger.debug(f"✗ TX#{result['id']}: No payee extracted - {result.get('explanation', 'unknown')}")

            # Get caching stats
            stats = extractor.get_stats()

            # Summary logging
            self.logger.info("=" * 80)
            self.logger.info("LLM PAYEE EXTRACTION SUMMARY:")
            self.logger.info(f"  Total processed: {len(failed_transactions)}")
            self.logger.info(f"  Successfully updated: {updated_count}")
            self.logger.info(f"  Low confidence (skipped): {low_confidence_count}")
            self.logger.info(f"  Failed: {failed_count}")
            self.logger.info(f"  Patterns cached: {stats.get('cached_patterns', 0)} total")
            self.logger.info("=" * 80)

            return f"extracted {updated_count}/{len(failed_transactions)} payees via LLM (cached {stats.get('cached_patterns', 0)} patterns)"

        except ImportError as e:
            self.logger.warning(f"LLM payee extraction not available: {e}")
            self.logger.info("=" * 80)
            return None
        except ValueError as e:
            # API key not configured
            self.logger.warning(f"LLM payee extraction disabled: {e}")
            self.logger.warning("Set ANTHROPIC_API_KEY environment variable to enable LLM payee extraction")
            self.logger.info("=" * 80)
            return None
        except Exception as e:
            self.logger.error(f"Error running LLM payee extraction: {e}", exc_info=True)
            self.logger.info("=" * 80)
            return None
    
    def _run_ai_classification(self):
        """Run AI classification using the main.py module functionality"""
        try:
            # Import and run AI classifier directly
            from ai_classifier import AITransactionClassifier
            
            classifier = AITransactionClassifier(self.parser.db)
            
            # Get uncategorized transactions (limit to recent ones for performance)
            uncategorized = self.parser.db.get_uncategorized_transactions(limit=2000)
            
            if not uncategorized:
                return "no uncategorized transactions to process"
            
            # Process transactions in batches
            processed_count = 0
            batch_size = 50
            
            for i in range(0, min(len(uncategorized), 2000), batch_size):
                batch = uncategorized[i:i+batch_size]
                
                for transaction in batch:
                    try:
                        # Get classification suggestion (returns tuple: category, subcategory, confidence)
                        # Transaction format from get_uncategorized_transactions:
                        # (id, run_date, account, description, amount, action, payee)
                        tx_id = transaction[0]
                        description = transaction[3]
                        amount = transaction[4]
                        action = transaction[5]
                        payee = transaction[6]
                        transaction_type = None  # Not included in uncategorized query

                        category, subcategory, confidence = classifier.classify_transaction_text(
                            description, action, amount, payee, transaction_type
                        )

                        if confidence >= 0.7:  # High confidence threshold
                            # Auto-apply high confidence classifications
                            # update_transaction_category expects category/subcategory as string names
                            # and will handle ID creation internally
                            success = self.parser.db.update_transaction_category(
                                tx_id, category, subcategory, None
                            )

                            if success:
                                processed_count += 1
                                
                    except Exception as e:
                        tx_id_for_log = transaction[0] if transaction and len(transaction) > 0 else 'unknown'
                        self.logger.warning(f"Error classifying transaction {tx_id_for_log}: {e}")
                        continue
            
            return f"classified {processed_count} transactions"
            
        except ImportError as e:
            self.logger.error(f"Could not import AITransactionClassifier: {e}")
            # Fallback to subprocess call
            return self._run_ai_classification_subprocess()
        except Exception as e:
            self.logger.error(f"Error running AI classification: {e}")
            return None
    
    def _run_ai_classification_subprocess(self):
        """Fallback method to run AI classification via subprocess"""
        try:
            result = subprocess.run(
                [sys.executable, 'main.py', '--ai-classify', '2000', '--ai-auto-apply'],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            if result.returncode == 0:
                # Parse output for success info
                output_lines = result.stdout.strip().split('\n')
                return f"subprocess completed: {output_lines[-1] if output_lines else 'success'}"
            else:
                self.logger.error(f"AI classification subprocess failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            self.logger.error("AI classification subprocess timed out")
            return None
        except Exception as e:
            self.logger.error(f"Error running AI classification subprocess: {e}")
            return None

class FileMonitor:
    def __init__(self, watch_directory: str, db: TransactionDB, auto_process: bool = True, html_callback=None, enable_post_processing: bool = True, enable_llm_payee: bool = False):
        self.watch_directory = watch_directory
        self.db = db
        self.auto_process = auto_process
        self.html_callback = html_callback
        self.enable_post_processing = enable_post_processing
        self.enable_llm_payee = enable_llm_payee
        self.observer = None
        self.parser = CSVParser(db)
        self.logger = logging.getLogger(__name__)
        
    def start_monitoring(self):
        """Start monitoring the directory for new CSV files"""
        if not os.path.exists(self.watch_directory):
            raise FileNotFoundError(f"Watch directory does not exist: {self.watch_directory}")

        event_handler = CSVFileHandler(self.parser, self.auto_process, self.html_callback, self.enable_post_processing, self.enable_llm_payee)
        self.observer = Observer()
        self.observer.schedule(event_handler, self.watch_directory, recursive=False)
        
        self.observer.start()
        self.logger.info(f"Started monitoring {self.watch_directory} for CSV files")
        
        try:
            while True:
                time.sleep(10)  # Check every 10 seconds
        except KeyboardInterrupt:
            self.stop_monitoring()
    
    def stop_monitoring(self):
        """Stop monitoring"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.logger.info("Stopped file monitoring")
    
    def process_existing_files(self):
        """Process any existing CSV files in the directory"""
        self.logger.info("Processing existing CSV files...")
        stats = self.parser.scan_and_process_directory(self.watch_directory, move_processed=True)
        
        self.logger.info(f"Processed {stats['files']} files: "
                        f"{stats['processed']} new transactions, "
                        f"{stats['duplicates']} duplicates, "
                        f"{stats['errors']} errors")
        
        # Generate HTML if callback provided and new transactions were processed
        if self.html_callback and stats['processed'] > 0:
            self.logger.info("Regenerating HTML report due to new transactions")
            self.html_callback()
        
        return stats