import os
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from csv_parser import CSVParser
from database import TransactionDB

class CSVFileHandler(FileSystemEventHandler):
    def __init__(self, parser: CSVParser, auto_process: bool = True, html_callback=None):
        self.parser = parser
        self.auto_process = auto_process
        self.html_callback = html_callback
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

class FileMonitor:
    def __init__(self, watch_directory: str, db: TransactionDB, auto_process: bool = True, html_callback=None):
        self.watch_directory = watch_directory
        self.db = db
        self.auto_process = auto_process
        self.html_callback = html_callback
        self.observer = None
        self.parser = CSVParser(db)
        self.logger = logging.getLogger(__name__)
        
    def start_monitoring(self):
        """Start monitoring the directory for new CSV files"""
        if not os.path.exists(self.watch_directory):
            raise FileNotFoundError(f"Watch directory does not exist: {self.watch_directory}")
        
        event_handler = CSVFileHandler(self.parser, self.auto_process, self.html_callback)
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