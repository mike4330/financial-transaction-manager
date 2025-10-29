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
    def __init__(self, parser: CSVParser, auto_process: bool = True, html_callback=None, enable_post_processing: bool = True):
        self.parser = parser
        self.auto_process = auto_process
        self.html_callback = html_callback
        self.enable_post_processing = enable_post_processing
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
            # Step 1: Run payee extraction
            self.logger.info("Running payee extraction on new transactions...")
            payee_result = self._run_payee_extraction()
            
            if payee_result:
                self.logger.info(f"Payee extraction completed: {payee_result}")
            else:
                self.logger.warning("Payee extraction failed or returned no results")
            
            # Step 2: Run AI classification
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
                        # Get classification suggestion
                        suggestion = classifier.classify_transaction(transaction)
                        
                        if suggestion and suggestion.get('confidence', 0) >= 0.7:  # High confidence threshold
                            # Auto-apply high confidence classifications
                            category_id = self.parser.db.get_or_create_category(suggestion['category'])
                            subcategory_id = None
                            
                            if suggestion.get('subcategory'):
                                subcategory_id = self.parser.db.get_or_create_subcategory(
                                    suggestion['subcategory'], category_id
                                )
                            
                            # Apply classification without note
                            success = self.parser.db.update_transaction_category(
                                transaction['id'], category_id, subcategory_id, None
                            )
                            
                            if success:
                                processed_count += 1
                                
                    except Exception as e:
                        self.logger.warning(f"Error classifying transaction {transaction.get('id', 'unknown')}: {e}")
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
    def __init__(self, watch_directory: str, db: TransactionDB, auto_process: bool = True, html_callback=None, enable_post_processing: bool = True):
        self.watch_directory = watch_directory
        self.db = db
        self.auto_process = auto_process
        self.html_callback = html_callback
        self.enable_post_processing = enable_post_processing
        self.observer = None
        self.parser = CSVParser(db)
        self.logger = logging.getLogger(__name__)
        
    def start_monitoring(self):
        """Start monitoring the directory for new CSV files"""
        if not os.path.exists(self.watch_directory):
            raise FileNotFoundError(f"Watch directory does not exist: {self.watch_directory}")
        
        event_handler = CSVFileHandler(self.parser, self.auto_process, self.html_callback, self.enable_post_processing)
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