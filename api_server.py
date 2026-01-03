#!/usr/bin/env python3
"""
Flask API Server for Financial Transaction Management
Separate from main.py - provides REST API for React frontend
"""

from flask import Flask, jsonify, request, flash, redirect
from flask_cors import CORS
import sqlite3
import logging
import threading
import signal
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional
from werkzeug.utils import secure_filename

# Configure logging
import os
from logging.handlers import RotatingFileHandler

# Configure logging with rotation
log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, 'flask_app.log')

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# File handler with rotation (10MB max, keep 3 files)
file_handler = RotatingFileHandler(
    log_file, maxBytes=10*1024*1024, backupCount=3
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Suppress Flask's default logging to avoid duplicates
logging.getLogger('werkzeug').setLevel(logging.WARNING)

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Request logging middleware
@app.before_request
def log_request_info():
    if request.endpoint != 'health_check':  # Skip health check spam
        logger.info(f"{request.method} {request.path} - {request.remote_addr}")

@app.after_request
def log_response_info(response):
    if request.endpoint != 'health_check' and response.status_code >= 400:
        logger.warning(f"{request.method} {request.path} - {response.status_code}")
    return response

DATABASE_PATH = "transactions.db"
TRANSACTIONS_DIR = "./transactions"

# Global database instance to avoid re-initialization
_db_instance = None

# Global file monitor instance
_file_monitor = None
_monitor_thread = None
_shutdown_event = threading.Event()

def get_transaction_db():
    """Get a shared TransactionDB instance to avoid re-initialization"""
    global _db_instance
    if _db_instance is None:
        logger.info("Initializing shared TransactionDB instance")
        from database import TransactionDB
        _db_instance = TransactionDB(DATABASE_PATH)
        logger.info("TransactionDB instance created successfully")
    return _db_instance

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn

def start_file_monitoring():
    """Start file monitoring in a separate thread"""
    global _file_monitor, _monitor_thread
    
    if _monitor_thread and _monitor_thread.is_alive():
        logger.info("File monitoring is already running")
        return
    
    try:
        from file_monitor import FileMonitor
        from database import TransactionDB
        
        # Ensure transactions directory exists
        if not os.path.exists(TRANSACTIONS_DIR):
            os.makedirs(TRANSACTIONS_DIR)
            logger.info(f"Created transactions directory: {TRANSACTIONS_DIR}")
        
        # Initialize database and file monitor with post-processing enabled
        db = get_transaction_db()
        _file_monitor = FileMonitor(TRANSACTIONS_DIR, db, auto_process=True, enable_post_processing=True)
        
        def monitor_worker():
            """Worker function to run file monitoring"""
            try:
                logger.info(f"Starting file monitoring thread for {TRANSACTIONS_DIR}")
                
                # Process existing files first
                stats = _file_monitor.process_existing_files()
                if stats['processed'] > 0:
                    logger.info(f"Processed {stats['processed']} existing transactions on startup")
                
                # Start monitoring
                _file_monitor.start_monitoring()
                
            except Exception as e:
                logger.error(f"File monitoring thread error: {e}")
            finally:
                logger.info("File monitoring thread stopped")
        
        _monitor_thread = threading.Thread(target=monitor_worker, daemon=True, name="FileMonitor")
        _monitor_thread.start()
        
        logger.info("File monitoring thread started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start file monitoring: {e}")

def stop_file_monitoring():
    """Stop file monitoring"""
    global _file_monitor, _monitor_thread
    
    if _file_monitor:
        logger.info("Stopping file monitoring...")
        _file_monitor.stop_monitoring()
        _file_monitor = None
    
    if _monitor_thread and _monitor_thread.is_alive():
        logger.info("Waiting for monitor thread to finish...")
        _monitor_thread.join(timeout=5)
        if _monitor_thread.is_alive():
            logger.warning("Monitor thread did not stop gracefully")
        else:
            logger.info("Monitor thread stopped")
    
    _monitor_thread = None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    _shutdown_event.set()
    stop_file_monitoring()
    sys.exit(0)


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "file_monitoring": _monitor_thread.is_alive() if _monitor_thread else False
    })

@app.route('/api/file-monitoring', methods=['GET'])
def get_file_monitoring_status():
    """Get file monitoring status"""
    try:
        status = {
            "enabled": _monitor_thread.is_alive() if _monitor_thread else False,
            "watch_directory": TRANSACTIONS_DIR,
            "thread_name": _monitor_thread.name if _monitor_thread else None
        }
        
        # Check if transactions directory exists
        status["directory_exists"] = os.path.exists(TRANSACTIONS_DIR)
        
        # Count CSV files in directory
        if status["directory_exists"]:
            csv_files = [f for f in os.listdir(TRANSACTIONS_DIR) if f.lower().endswith('.csv')]
            status["csv_files_in_directory"] = len(csv_files)
        else:
            status["csv_files_in_directory"] = 0
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting file monitoring status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/file-monitoring/start', methods=['POST'])
def start_monitoring_endpoint():
    """Start file monitoring"""
    try:
        if _monitor_thread and _monitor_thread.is_alive():
            return jsonify({
                "message": "File monitoring is already running",
                "status": "already_running"
            })
        
        start_file_monitoring()
        
        return jsonify({
            "message": "File monitoring started successfully",
            "watch_directory": TRANSACTIONS_DIR,
            "status": "started"
        })
        
    except Exception as e:
        logger.error(f"Error starting file monitoring: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/file-monitoring/stop', methods=['POST'])
def stop_monitoring_endpoint():
    """Stop file monitoring"""
    try:
        if not _monitor_thread or not _monitor_thread.is_alive():
            return jsonify({
                "message": "File monitoring is not running",
                "status": "not_running"
            })
        
        stop_file_monitoring()
        
        return jsonify({
            "message": "File monitoring stopped successfully",
            "status": "stopped"
        })
        
    except Exception as e:
        logger.error(f"Error stopping file monitoring: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/file-monitoring/process-existing', methods=['POST'])
def process_existing_files():
    """Process existing CSV files in the transactions directory"""
    try:
        from file_monitor import FileMonitor
        
        if not os.path.exists(TRANSACTIONS_DIR):
            return jsonify({
                "error": f"Transactions directory does not exist: {TRANSACTIONS_DIR}"
            }), 404
        
        db = get_transaction_db()
        monitor = FileMonitor(TRANSACTIONS_DIR, db, auto_process=False, enable_post_processing=True)
        stats = monitor.process_existing_files()
        
        return jsonify({
            "message": "Processing completed",
            "stats": {
                "files_processed": stats['files'],
                "new_transactions": stats['processed'],
                "duplicates_skipped": stats['duplicates'],
                "errors": stats['errors']
            }
        })
        
    except Exception as e:
        logger.error(f"Error processing existing files: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    """Get transactions with optional filtering"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        account = request.args.get('account')
        category = request.args.get('category')
        subcategory = request.args.get('subcategory')
        transaction_type = request.args.get('type')
        symbol = request.args.get('symbol')
        payee = request.args.get('payee')
        exclude_investments = request.args.get('exclude_investments') == 'true'
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        uncategorized_only = request.args.get('uncategorized') == 'true'
        search = request.args.get('search')
        sort_column = request.args.get('sort_column', 'date')
        sort_direction = request.args.get('sort_direction', 'desc')
        
        conn = get_db_connection()
        
        # Build query with filters
        query = """
        SELECT
            t.id,
            t.run_date as date,
            t.account,
            t.account_number,
            t.amount,
            t.payee,
            t.description,
            t.action,
            t.type as transaction_type,
            t.note,
            c.name as category,
            s.name as subcategory,
            t.category_id,
            t.subcategory_id,
            t.is_split,
            (SELECT COUNT(*) FROM transaction_splits WHERE transaction_id = t.id) as split_count
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        LEFT JOIN subcategories s ON t.subcategory_id = s.id
        WHERE 1=1
        """
        
        params = []
        
        # Apply filters
        if account:
            query += " AND t.account = ?"
            params.append(account)
        
        if category:
            if category == 'Uncategorized':
                query += " AND c.name IS NULL"
            else:
                query += " AND c.name = ?"
                params.append(category)
        
        if subcategory:
            query += " AND s.name = ?"
            params.append(subcategory)
        
        if transaction_type:
            query += " AND t.type = ?"
            params.append(transaction_type)
        
        if symbol:
            query += " AND t.symbol = ?"
            params.append(symbol)

        if payee:
            query += " AND t.payee = ?"
            params.append(payee)

        if exclude_investments:
            query += " AND t.type NOT IN ('Investment Trade', 'Dividend', 'Reinvestment', 'Dividend Taxes', 'Brokerage Fee')"
        
        if start_date:
            # Date is already in YYYY-MM-DD format
            query += """ AND date(t.run_date) >= date(?)"""
            params.append(start_date)
        
        if end_date:
            # Date is already in YYYY-MM-DD format
            query += """ AND date(t.run_date) <= date(?)"""
            params.append(end_date)
        
        if uncategorized_only:
            query += " AND t.category_id IS NULL"
        
        # Add search filter
        if search:
            search_term = f"%{search.lower()}%"
            query += """
                AND (
                    LOWER(t.description) LIKE ? 
                    OR LOWER(t.payee) LIKE ? 
                    OR LOWER(t.action) LIKE ? 
                    OR LOWER(c.name) LIKE ? 
                    OR LOWER(s.name) LIKE ?
                    OR CAST(ABS(t.amount) AS TEXT) LIKE ?
                )
            """
            params.extend([search_term, search_term, search_term, search_term, search_term, search_term])
        
        # Add dynamic ordering
        # Map frontend column names to database column names
        column_mapping = {
            'date': 't.run_date',
            'account': 't.account',
            'amount': 't.amount',
            'payee': 't.payee',
            'category': 'c.name',
            'subcategory': 's.name',
            'transaction_type': 't.type',
            'note': 't.note'
        }
        
        # Validate sort column and direction
        db_column = column_mapping.get(sort_column, 't.run_date')
        direction = 'ASC' if sort_direction.lower() == 'asc' else 'DESC'
        
        query += f" ORDER BY {db_column} {direction}"
        
        # Count total records for pagination
        count_query = f"SELECT COUNT(*) as total FROM ({query}) as filtered"
        total_count = conn.execute(count_query, params).fetchone()['total']
        
        # Apply pagination
        offset = (page - 1) * limit
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        # Execute main query
        transactions = conn.execute(query, params).fetchall()
        
        # Convert to list of dictionaries with proper None handling
        transactions_list = []
        for row in transactions:
            transaction = dict(row)
            # Ensure all fields are JSON serializable
            for key, value in transaction.items():
                if value is None:
                    transaction[key] = None
                elif isinstance(value, bytes):
                    transaction[key] = value.decode('utf-8', errors='ignore')
                else:
                    transaction[key] = value
            transactions_list.append(transaction)
        
        conn.close()
        
        return jsonify({
            "transactions": transactions_list,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": (total_count + limit - 1) // limit
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/transactions/<int:transaction_id>', methods=['PUT'])
def update_transaction(transaction_id):
    """Update a transaction"""
    try:
        data = request.get_json()
        category_id = data.get('category_id')
        subcategory_id = data.get('subcategory_id')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE transactions 
            SET category_id = ?, subcategory_id = ?
            WHERE id = ?
        """, (category_id, subcategory_id, transaction_id))
        
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "Transaction not found"}), 404
        
        conn.close()
        return jsonify({"message": "Transaction updated successfully"})
        
    except Exception as e:
        logger.error(f"Error updating transaction {transaction_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/transactions/bulk-categorize', methods=['POST'])
def bulk_categorize():
    """Bulk categorize multiple transactions"""
    try:
        data = request.get_json()
        transaction_ids = data.get('transaction_ids', [])
        category_id = data.get('category_id')
        subcategory_id = data.get('subcategory_id')
        
        if not transaction_ids:
            return jsonify({"error": "No transaction IDs provided"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update all specified transactions
        placeholders = ','.join(['?' for _ in transaction_ids])
        query = f"""
            UPDATE transactions 
            SET category_id = ?, subcategory_id = ?
            WHERE id IN ({placeholders})
        """
        
        params = [category_id, subcategory_id] + transaction_ids
        cursor.execute(query, params)
        
        updated_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": f"Updated {updated_count} transactions",
            "updated_count": updated_count
        })
        
    except Exception as e:
        logger.error(f"Error bulk categorizing: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/transactions/bulk-delete', methods=['DELETE'])
def bulk_delete():
    """Delete multiple transactions"""
    try:
        data = request.get_json()
        transaction_ids = data.get('transaction_ids', [])
        
        if not transaction_ids:
            return jsonify({"error": "No transaction IDs provided"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete all specified transactions
        placeholders = ','.join(['?' for _ in transaction_ids])
        query = f"""
            DELETE FROM transactions 
            WHERE id IN ({placeholders})
        """
        
        cursor.execute(query, transaction_ids)
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": f"Deleted {deleted_count} transactions",
            "deleted_count": deleted_count
        })
        
    except Exception as e:
        logger.error(f"Error bulk deleting: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================================================
# SPLIT TRANSACTION ENDPOINTS
# ============================================================================

@app.route('/api/transactions/<int:transaction_id>/splits', methods=['POST'])
def create_splits(transaction_id):
    """Create splits for a transaction"""
    try:
        data = request.get_json()
        splits = data.get('splits', [])

        if not splits:
            return jsonify({"error": "No splits provided"}), 400

        if len(splits) < 2:
            return jsonify({"error": "At least 2 splits required"}), 400

        # Use TransactionDB methods for validation and creation
        db = get_transaction_db()

        # Validate splits
        is_valid, error_msg = db.validate_split_amounts(transaction_id, splits)
        if not is_valid:
            return jsonify({"error": error_msg}), 400

        # Create splits
        success = db.create_splits(transaction_id, splits)

        if not success:
            return jsonify({"error": "Failed to create splits"}), 500

        # Retrieve created splits to return
        created_splits = db.get_splits(transaction_id)

        return jsonify({
            "message": "Splits created successfully",
            "transaction_id": transaction_id,
            "split_count": len(created_splits),
            "splits": created_splits
        }), 201

    except Exception as e:
        logger.error(f"Error creating splits for transaction {transaction_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/transactions/<int:transaction_id>/splits', methods=['PUT'])
def update_splits(transaction_id):
    """Update splits for a transaction"""
    try:
        data = request.get_json()
        splits = data.get('splits', [])

        if not splits:
            return jsonify({"error": "No splits provided"}), 400

        if len(splits) < 2:
            return jsonify({"error": "At least 2 splits required"}), 400

        db = get_transaction_db()

        # Validate splits
        is_valid, error_msg = db.validate_split_amounts(transaction_id, splits)
        if not is_valid:
            return jsonify({"error": error_msg}), 400

        # Update splits
        success = db.update_splits(transaction_id, splits)

        if not success:
            return jsonify({"error": "Failed to update splits"}), 500

        # Retrieve updated splits to return
        updated_splits = db.get_splits(transaction_id)

        return jsonify({
            "message": "Splits updated successfully",
            "transaction_id": transaction_id,
            "split_count": len(updated_splits),
            "splits": updated_splits
        })

    except Exception as e:
        logger.error(f"Error updating splits for transaction {transaction_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/transactions/<int:transaction_id>/splits', methods=['DELETE'])
def delete_splits(transaction_id):
    """Delete all splits for a transaction"""
    try:
        # Optional: restore category after removing splits
        category_id = request.args.get('category_id', type=int)
        subcategory_id = request.args.get('subcategory_id', type=int)

        db = get_transaction_db()

        # Delete splits
        success = db.delete_splits(transaction_id, category_id, subcategory_id)

        if not success:
            return jsonify({"error": "Failed to delete splits"}), 500

        return jsonify({
            "message": "Splits deleted successfully",
            "transaction_id": transaction_id
        })

    except Exception as e:
        logger.error(f"Error deleting splits for transaction {transaction_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/transactions/<int:transaction_id>/splits', methods=['GET'])
def get_transaction_splits(transaction_id):
    """Get all splits for a transaction"""
    try:
        db = get_transaction_db()
        splits = db.get_splits(transaction_id)

        # Check if transaction exists and is split
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT is_split FROM transactions WHERE id = ?', (transaction_id,))
        result = cursor.fetchone()
        conn.close()

        if not result:
            return jsonify({"error": "Transaction not found"}), 404

        is_split = result['is_split']

        return jsonify({
            "transaction_id": transaction_id,
            "is_split": bool(is_split),
            "splits": splits
        })

    except Exception as e:
        logger.error(f"Error getting splits for transaction {transaction_id}: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================================================
# END SPLIT TRANSACTION ENDPOINTS
# ============================================================================

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Get all categories and subcategories"""
    try:
        conn = get_db_connection()
        
        # Get categories
        categories = conn.execute("""
            SELECT id, name FROM categories ORDER BY name
        """).fetchall()
        
        # Get subcategories with category info
        subcategories = conn.execute("""
            SELECT s.id, s.name, s.category_id, c.name as category_name
            FROM subcategories s
            JOIN categories c ON s.category_id = c.id
            ORDER BY c.name, s.name
        """).fetchall()
        
        conn.close()
        
        return jsonify({
            "categories": [dict(row) for row in categories],
            "subcategories": [dict(row) for row in subcategories]
        })
        
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/categories', methods=['POST'])
def create_category():
    """Create a new category"""
    try:
        data = request.get_json()
        name = data.get('name')

        if not name:
            return jsonify({"error": "Category name is required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if category already exists
        existing = cursor.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()
        if existing:
            conn.close()
            return jsonify({"error": "Category already exists"}), 400

        # Insert new category
        cursor.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        category_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Created new category: {name} (ID: {category_id})")

        return jsonify({
            "success": True,
            "message": "Category created successfully",
            "category": {"id": category_id, "name": name}
        }), 201

    except Exception as e:
        logger.error(f"Error creating category: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/categories/<int:category_id>', methods=['PUT'])
def update_category(category_id):
    """Update a category"""
    try:
        data = request.get_json()
        name = data.get('name')

        if not name:
            return jsonify({"error": "Category name is required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if category exists
        existing = cursor.execute("SELECT name FROM categories WHERE id = ?", (category_id,)).fetchone()
        if not existing:
            conn.close()
            return jsonify({"error": "Category not found"}), 404

        # Check if new name conflicts with another category
        conflict = cursor.execute("SELECT id FROM categories WHERE name = ? AND id != ?", (name, category_id)).fetchone()
        if conflict:
            conn.close()
            return jsonify({"error": "Category name already exists"}), 400

        # Update category
        cursor.execute("UPDATE categories SET name = ? WHERE id = ?", (name, category_id))
        conn.commit()
        conn.close()

        logger.info(f"Updated category ID {category_id}: {existing['name']} → {name}")

        return jsonify({
            "success": True,
            "message": "Category updated successfully"
        })

    except Exception as e:
        logger.error(f"Error updating category {category_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/categories/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):
    """Delete a category"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if category exists
        category = cursor.execute("SELECT name FROM categories WHERE id = ?", (category_id,)).fetchone()
        if not category:
            conn.close()
            return jsonify({"error": "Category not found"}), 404

        # Check if category has transactions
        transaction_count = cursor.execute("SELECT COUNT(*) as count FROM transactions WHERE category_id = ?", (category_id,)).fetchone()['count']

        if transaction_count > 0:
            conn.close()
            return jsonify({"error": f"Cannot delete category: {transaction_count} transactions are using it"}), 400

        # Delete subcategories first
        cursor.execute("DELETE FROM subcategories WHERE category_id = ?", (category_id,))

        # Delete category
        cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()
        conn.close()

        logger.info(f"Deleted category: {category['name']} (ID: {category_id})")

        return jsonify({
            "success": True,
            "message": "Category deleted successfully"
        })

    except Exception as e:
        logger.error(f"Error deleting category {category_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/categories/<int:category_id>/subcategories', methods=['POST'])
def create_subcategory(category_id):
    """Create a new subcategory"""
    try:
        data = request.get_json()
        name = data.get('name')

        if not name:
            return jsonify({"error": "Subcategory name is required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if category exists
        category = cursor.execute("SELECT name FROM categories WHERE id = ?", (category_id,)).fetchone()
        if not category:
            conn.close()
            return jsonify({"error": "Category not found"}), 404

        # Check if subcategory already exists in this category
        existing = cursor.execute(
            "SELECT id FROM subcategories WHERE name = ? AND category_id = ?",
            (name, category_id)
        ).fetchone()
        if existing:
            conn.close()
            return jsonify({"error": "Subcategory already exists in this category"}), 400

        # Insert new subcategory
        cursor.execute("INSERT INTO subcategories (name, category_id) VALUES (?, ?)", (name, category_id))
        subcategory_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Created new subcategory: {name} (ID: {subcategory_id}) under {category['name']}")

        return jsonify({
            "success": True,
            "message": "Subcategory created successfully",
            "subcategory": {
                "id": subcategory_id,
                "name": name,
                "category_id": category_id,
                "category_name": category['name']
            }
        }), 201

    except Exception as e:
        logger.error(f"Error creating subcategory for category {category_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/subcategories/<int:subcategory_id>', methods=['PUT'])
def update_subcategory(subcategory_id):
    """Update a subcategory"""
    try:
        data = request.get_json()
        name = data.get('name')

        if not name:
            return jsonify({"error": "Subcategory name is required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if subcategory exists
        existing = cursor.execute(
            "SELECT s.name, s.category_id FROM subcategories s WHERE s.id = ?",
            (subcategory_id,)
        ).fetchone()
        if not existing:
            conn.close()
            return jsonify({"error": "Subcategory not found"}), 404

        # Check if new name conflicts with another subcategory in the same category
        conflict = cursor.execute(
            "SELECT id FROM subcategories WHERE name = ? AND category_id = ? AND id != ?",
            (name, existing['category_id'], subcategory_id)
        ).fetchone()
        if conflict:
            conn.close()
            return jsonify({"error": "Subcategory name already exists in this category"}), 400

        # Update subcategory
        cursor.execute("UPDATE subcategories SET name = ? WHERE id = ?", (name, subcategory_id))
        conn.commit()
        conn.close()

        logger.info(f"Updated subcategory ID {subcategory_id}: {existing['name']} → {name}")

        return jsonify({
            "success": True,
            "message": "Subcategory updated successfully"
        })

    except Exception as e:
        logger.error(f"Error updating subcategory {subcategory_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/subcategories/<int:subcategory_id>', methods=['DELETE'])
def delete_subcategory(subcategory_id):
    """Delete a subcategory"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if subcategory exists
        subcategory = cursor.execute(
            "SELECT s.name FROM subcategories s WHERE s.id = ?",
            (subcategory_id,)
        ).fetchone()
        if not subcategory:
            conn.close()
            return jsonify({"error": "Subcategory not found"}), 404

        # Check if subcategory has transactions
        transaction_count = cursor.execute(
            "SELECT COUNT(*) as count FROM transactions WHERE subcategory_id = ?",
            (subcategory_id,)
        ).fetchone()['count']

        if transaction_count > 0:
            conn.close()
            return jsonify({"error": f"Cannot delete subcategory: {transaction_count} transactions are using it"}), 400

        # Delete subcategory
        cursor.execute("DELETE FROM subcategories WHERE id = ?", (subcategory_id,))
        conn.commit()
        conn.close()

        logger.info(f"Deleted subcategory: {subcategory['name']} (ID: {subcategory_id})")

        return jsonify({
            "success": True,
            "message": "Subcategory deleted successfully"
        })

    except Exception as e:
        logger.error(f"Error deleting subcategory {subcategory_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get dashboard statistics"""
    try:
        conn = get_db_connection()
        
        # Total transactions
        total = conn.execute("SELECT COUNT(*) as count FROM transactions").fetchone()['count']
        
        # Categorized transactions
        categorized = conn.execute("""
            SELECT COUNT(*) as count FROM transactions 
            WHERE category_id IS NOT NULL
        """).fetchone()['count']
        
        # Uncategorized transactions
        uncategorized = total - categorized
        
        # Total amount
        total_amount = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) as total FROM transactions
        """).fetchone()['total']
        
        # Accounts
        accounts = conn.execute("""
            SELECT account, COUNT(*) as count, SUM(amount) as total_amount
            FROM transactions 
            GROUP BY account 
            ORDER BY account
        """).fetchall()
        
        # Categories summary
        categories = conn.execute("""
            SELECT 
                c.name as category,
                s.name as subcategory,
                COUNT(*) as count,
                SUM(t.amount) as total_amount
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            LEFT JOIN subcategories s ON t.subcategory_id = s.id
            GROUP BY c.name, s.name
            ORDER BY total_amount DESC
        """).fetchall()
        
        conn.close()
        
        return jsonify({
            "summary": {
                "total_transactions": total,
                "categorized": categorized,
                "uncategorized": uncategorized,
                "total_amount": total_amount
            },
            "accounts": [dict(row) for row in accounts],
            "categories": [dict(row) for row in categories]
        })
        
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/treemap', methods=['GET'])
def get_treemap_data():
    """Get hierarchical data for tree map visualization"""
    try:
        conn = get_db_connection()
        
        # Get category and subcategory data with transaction counts
        query = """
        SELECT 
            c.name as category,
            s.name as subcategory,
            COUNT(t.id) as transaction_count,
            SUM(ABS(t.amount)) as total_amount
        FROM categories c
        LEFT JOIN subcategories s ON c.id = s.category_id
        LEFT JOIN transactions t ON (
            t.category_id = c.id AND 
            (t.subcategory_id = s.id OR (s.id IS NULL AND t.subcategory_id IS NULL))
        )
        GROUP BY c.name, s.name
        HAVING COUNT(t.id) > 0
        ORDER BY c.name, s.name
        """
        
        result = conn.execute(query).fetchall()
        
        # Organize data into hierarchical structure
        tree_data = {}
        for row in result:
            category = row['category']
            subcategory = row['subcategory']
            count = row['transaction_count']
            amount = row['total_amount'] or 0
            
            if category not in tree_data:
                tree_data[category] = {
                    'name': category,
                    'children': [],
                    'value': 0,
                    'amount': 0
                }
            
            if subcategory:
                tree_data[category]['children'].append({
                    'name': subcategory,
                    'value': count,
                    'amount': amount,
                    'category': category
                })
            
            tree_data[category]['value'] += count
            tree_data[category]['amount'] += amount
        
        # Convert to array format expected by tree map
        tree_array = list(tree_data.values())
        
        conn.close()
        
        return jsonify({
            'data': tree_array,
            'total_categories': len(tree_array),
            'total_transactions': sum(cat['value'] for cat in tree_array)
        })
        
    except Exception as e:
        logger.error(f"Error fetching tree map data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/filters', methods=['GET'])
def get_filter_options():
    """Get available filter options"""
    try:
        conn = get_db_connection()
        
        # Get unique accounts
        accounts = conn.execute("""
            SELECT DISTINCT account FROM transactions 
            WHERE account IS NOT NULL 
            ORDER BY account
        """).fetchall()
        
        # Get unique transaction types
        transaction_types = conn.execute("""
            SELECT DISTINCT type FROM transactions 
            WHERE type IS NOT NULL 
            ORDER BY type
        """).fetchall()
        
        # Get categories
        categories = conn.execute("""
            SELECT DISTINCT name FROM categories 
            ORDER BY name
        """).fetchall()
        
        conn.close()
        
        return jsonify({
            "accounts": [row['account'] for row in accounts],
            "transaction_types": [row['type'] for row in transaction_types],
            "categories": [row['name'] for row in categories] + ['Uncategorized']
        })
        
    except Exception as e:
        logger.error(f"Error fetching filter options: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/budget/<int:year>/<int:month>', methods=['GET'])
def get_monthly_budget(year: int, month: int):
    """Get monthly budget data for a specific year/month"""
    try:
        conn = get_db_connection()
        
        # Get monthly budget
        monthly_budget = conn.execute('''
            SELECT id, template_id, budget_year, budget_month, status, created_at
            FROM monthly_budgets
            WHERE budget_year = ? AND budget_month = ?
            ORDER BY created_at DESC
            LIMIT 1
        ''', (year, month)).fetchone()
        
        if not monthly_budget:
            return jsonify({"error": f"No budget found for {year}-{month:02d}"}), 404
        
        monthly_budget_id = monthly_budget['id']
        
        # Update actual amounts to ensure they're current
        db = get_transaction_db()
        db.update_actual_amounts(year, month)
        
        # Get budget items with category/subcategory names
        budget_items = conn.execute('''
            SELECT mbi.id, mbi.budgeted_amount, mbi.actual_amount, mbi.budget_type,
                   c.name as category, s.name as subcategory
            FROM monthly_budget_items mbi
            JOIN categories c ON mbi.category_id = c.id
            LEFT JOIN subcategories s ON mbi.subcategory_id = s.id
            WHERE mbi.monthly_budget_id = ?
            ORDER BY mbi.budget_type DESC, c.name, s.name
        ''', (monthly_budget_id,)).fetchall()
        
        # Convert to the format expected by the frontend
        items = []
        for item in budget_items:
            items.append({
                "id": str(item['id']),
                "category": item['category'],
                "subcategory": item['subcategory'],
                "budgeted": float(item['budgeted_amount']),
                "actual": float(item['actual_amount']),
                "type": item['budget_type']
            })
        
        # Calculate totals
        total_budgeted_income = sum(item['budgeted'] for item in items if item['type'] == 'income')
        total_actual_income = sum(item['actual'] for item in items if item['type'] == 'income')
        total_budgeted_expenses = sum(item['budgeted'] for item in items if item['type'] == 'expense')
        total_actual_expenses = sum(item['actual'] for item in items if item['type'] == 'expense')
        
        conn.close()
        
        return jsonify({
            "budget": {
                "id": monthly_budget_id,
                "year": year,
                "month": month,
                "status": monthly_budget['status'],
                "created_at": monthly_budget['created_at']
            },
            "items": items,
            "totals": {
                "income": {
                    "budgeted": total_budgeted_income,
                    "actual": total_actual_income
                },
                "expenses": {
                    "budgeted": total_budgeted_expenses,
                    "actual": total_actual_expenses
                },
                "net": {
                    "budgeted": total_budgeted_income - total_budgeted_expenses,
                    "actual": total_actual_income - total_actual_expenses
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching monthly budget: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/budget/<int:year>/<int:month>/update-actuals', methods=['POST'])
def update_budget_actuals(year: int, month: int):
    """Update actual amounts for a monthly budget from transaction data"""
    try:
        db = get_transaction_db()
        
        updated_count = db.update_actual_amounts(year, month)
        
        return jsonify({
            "message": f"Updated actual amounts for {updated_count} budget items",
            "updated_count": updated_count
        })
        
    except Exception as e:
        logger.error(f"Error updating actual amounts: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/budget/items/<int:item_id>/auto-calculate', methods=['GET'])
def auto_calculate_budget_amount(item_id: int):
    """Calculate historical average for a budget item"""
    try:
        db = get_transaction_db()
        
        conn = get_db_connection()
        
        # Get budget item details
        budget_item = conn.execute('''
            SELECT mbi.category_id, mbi.subcategory_id, mb.budget_year, mb.budget_month
            FROM monthly_budget_items mbi
            JOIN monthly_budgets mb ON mbi.monthly_budget_id = mb.id
            WHERE mbi.id = ?
        ''', (item_id,)).fetchone()
        
        if not budget_item:
            return jsonify({"error": "Budget item not found"}), 404
        
        category_id = budget_item['category_id']
        subcategory_id = budget_item['subcategory_id']
        target_year = budget_item['budget_year'] 
        target_month = budget_item['budget_month']
        
        conn.close()
        
        # Calculate historical average
        result = db.calculate_historical_average(
            category_id=category_id,
            subcategory_id=subcategory_id,
            target_year=target_year,
            target_month=target_month
        )
        
        if result is None:
            return jsonify({
                "error": "Insufficient historical data",
                "message": "Need at least 3 months of transaction data for auto-calculation"
            }), 400
        
        return jsonify({
            "suggested_amount": result['amount'],
            "confidence": result['confidence'],
            "analysis": {
                "months_used": result['months_used'],
                "outliers_removed": result['outliers_removed'],
                "median": result['median'],
                "confidence_description": _get_confidence_description(result['confidence'])
            }
        })
        
    except Exception as e:
        logger.error(f"Error auto-calculating budget amount: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/budget/items/<int:item_id>', methods=['PUT'])
def update_budget_item(item_id: int):
    """Update a budget item's budgeted amount"""
    try:
        data = request.get_json()
        budgeted_amount = data.get('budgeted_amount')
        
        if budgeted_amount is None:
            return jsonify({"error": "budgeted_amount is required"}), 400
        
        try:
            budgeted_amount = float(budgeted_amount)
            if budgeted_amount < 0:
                return jsonify({"error": "budgeted_amount must be positive"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "budgeted_amount must be a valid number"}), 400
        
        db = get_transaction_db()
        
        success = db.update_budget_item_amount(item_id, budgeted_amount)
        
        if not success:
            return jsonify({"error": "Budget item not found or update failed"}), 404
        
        return jsonify({
            "message": "Budget item updated successfully",
            "budgeted_amount": budgeted_amount
        })
        
    except Exception as e:
        logger.error(f"Error updating budget item: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/budget/create-next-month', methods=['POST'])
def create_next_month_budget():
    """Create next month's budget from the default template"""
    try:
        db = get_transaction_db()
        
        # Get the latest budget month to determine next month
        conn = get_db_connection()
        latest_budget = conn.execute('''
            SELECT budget_year, budget_month
            FROM monthly_budgets
            ORDER BY budget_year DESC, budget_month DESC
            LIMIT 1
        ''').fetchone()
        conn.close()
        
        if latest_budget:
            next_month = latest_budget['budget_month'] + 1
            next_year = latest_budget['budget_year']
            
            if next_month > 12:
                next_month = 1
                next_year += 1
        else:
            # Fallback to current date if no budgets exist
            from datetime import datetime
            now = datetime.now()
            next_month = now.month
            next_year = now.year
        
        # Check if budget already exists for next month
        existing_budget = db.get_monthly_budget(next_year, next_month)
        if existing_budget:
            return jsonify({
                "error": "Budget already exists",
                "message": f"Budget for {next_year}-{next_month:02d} already exists"
            }), 400
        
        # Get default template ID dynamically
        template_id = db.get_default_template_id()
        if not template_id:
            return jsonify({"error": "No default budget template found"}), 500
            
        monthly_budget_id = db.create_monthly_budget(template_id=template_id, year=next_year, month=next_month)
        
        if monthly_budget_id:
            # Update actual amounts for the new budget
            db.update_actual_amounts(next_year, next_month)
            
            return jsonify({
                "message": f"Created budget for {next_year}-{next_month:02d}",
                "budget_id": monthly_budget_id,
                "year": next_year,
                "month": next_month
            })
        else:
            return jsonify({"error": "Failed to create monthly budget"}), 500
            
    except Exception as e:
        logger.error(f"Error creating next month budget: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/budget/<int:year>/<int:month>/spending-by-category', methods=['GET'])
def get_monthly_spending_by_category(year: int, month: int):
    """Get spending by category for pie chart visualization"""
    try:
        conn = get_db_connection()
        
        # Calculate month start/end dates
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"
        
        # Get spending by category (expenses only, exclude transfers and investments)
        spending = conn.execute('''
            SELECT c.name as category, 
                   SUM(ABS(t.amount)) as total_spent,
                   COUNT(t.id) as transaction_count
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.run_date >= ? AND t.run_date < ?
            AND t.amount < 0  -- Only expenses (negative amounts)
            AND c.name NOT IN ('Banking', 'Investment', 'Transfer')  -- Exclude transfers/investments
            GROUP BY c.id, c.name
            HAVING total_spent > 0
            ORDER BY total_spent DESC
        ''', (start_date, end_date)).fetchall()
        
        conn.close()
        
        categories = []
        total_spending = 0
        
        for row in spending:
            amount = float(row['total_spent'])
            total_spending += amount
            categories.append({
                "category": row['category'],
                "amount": amount,
                "transaction_count": row['transaction_count']
            })
        
        # Calculate percentages
        for category in categories:
            category["percentage"] = (category["amount"] / total_spending * 100) if total_spending > 0 else 0
        
        return jsonify({
            "year": year,
            "month": month,
            "categories": categories,
            "total_spending": total_spending
        })
        
    except Exception as e:
        logger.error(f"Error fetching category spending: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/budget/<int:year>/<int:month>/unbudgeted-categories', methods=['GET'])
def get_unbudgeted_categories(year: int, month: int):
    """Get categories and subcategories that have spending but no budget line item for the given month"""
    try:
        conn = get_db_connection()

        # Calculate date range for the month
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"

        # Get all spending by category/subcategory combinations
        spending_query = conn.execute('''
            SELECT c.name as category,
                   s.name as subcategory,
                   SUM(ABS(t.amount)) as total_spent,
                   COUNT(t.id) as transaction_count
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            LEFT JOIN subcategories s ON t.subcategory_id = s.id
            WHERE t.run_date >= ? AND t.run_date < ?
            AND t.amount < 0  -- Only expenses (negative amounts)
            AND c.name NOT IN ('Banking', 'Investment', 'Transfer')  -- Exclude transfers/investments
            GROUP BY c.id, c.name, s.id, s.name
            HAVING total_spent > 0
            ORDER BY c.name, s.name
        ''', (start_date, end_date)).fetchall()

        # Get all budgeted category/subcategory combinations for this month
        budgeted_query = conn.execute('''
            SELECT c.name as category, s.name as subcategory
            FROM monthly_budget_items mbi
            JOIN monthly_budgets mb ON mbi.monthly_budget_id = mb.id
            JOIN categories c ON mbi.category_id = c.id
            LEFT JOIN subcategories s ON mbi.subcategory_id = s.id
            WHERE mb.budget_year = ? AND mb.budget_month = ?
        ''', (year, month)).fetchall()

        # Build budgeted set using category|subcategory keys
        budgeted_combinations = set()
        for row in budgeted_query:
            key = f"{row['category']}|{row['subcategory'] or ''}"
            budgeted_combinations.add(key)

        # Simple grouping: treat each category/subcategory combination as literal
        unbudgeted_items = []
        total_spending = 0
        total_unbudgeted = 0

        # Calculate total spending
        for row in spending_query:
            total_spending += row['total_spent']

        # Check each spending combination against budget combinations
        for row in spending_query:
            category = row['category']
            subcategory = row['subcategory']

            # Create key for exact matching - treat subcategory as literal string
            spending_key = f"{category}|{subcategory or ''}"

            # Check if this exact combination is budgeted
            is_budgeted = spending_key in budgeted_combinations

            if not is_budgeted:
                percentage = (row['total_spent'] / total_spending * 100) if total_spending > 0 else 0

                # Format display name
                if subcategory:
                    display_name = f"{category} - {subcategory}"
                else:
                    display_name = category

                unbudgeted_item = {
                    "category": category,
                    "subcategory": subcategory,
                    "display_name": display_name,
                    "amount": float(row['total_spent']),
                    "percentage": percentage,
                    "transaction_count": row['transaction_count']
                }
                unbudgeted_items.append(unbudgeted_item)
                total_unbudgeted += row['total_spent']

        conn.close()

        # Sort by amount descending
        unbudgeted_items.sort(key=lambda x: x['amount'], reverse=True)

        # Debug output
        logger.info(f"Found {len(unbudgeted_items)} unbudgeted category/subcategory combinations for {year}-{month:02d}")
        for item in unbudgeted_items[:5]:  # Log first 5
            logger.info(f"  Unbudgeted: {item['display_name']} - ${item['amount']:.2f}")

        return jsonify({
            "year": year,
            "month": month,
            "categories": unbudgeted_items,
            "total_unbudgeted": float(total_unbudgeted),
            "count": len(unbudgeted_items)
        })

    except Exception as e:
        logger.error(f"Error fetching unbudgeted categories: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/budget/<int:year>/<int:month>/add-category', methods=['POST'])
def add_budget_category(year: int, month: int):
    """Add a category to the monthly budget"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        category_name = data.get('category')
        subcategory_name = data.get('subcategory')
        budgeted_amount = data.get('budgeted_amount', 0.0)
        budget_type = data.get('budget_type', 'expense')
        
        if not category_name:
            return jsonify({"error": "Category name is required"}), 400
        
        conn = get_db_connection()
        
        # Get the monthly budget ID
        monthly_budget = conn.execute('''
            SELECT id FROM monthly_budgets 
            WHERE budget_year = ? AND budget_month = ?
        ''', (year, month)).fetchone()
        
        if not monthly_budget:
            return jsonify({"error": f"No budget found for {year}-{month:02d}"}), 404
        
        monthly_budget_id = monthly_budget['id']
        
        # Get or create category
        category = conn.execute('SELECT id FROM categories WHERE name = ?', (category_name,)).fetchone()
        if not category:
            cursor = conn.execute('INSERT INTO categories (name) VALUES (?)', (category_name,))
            category_id = cursor.lastrowid
        else:
            category_id = category['id']
        
        # Get or create subcategory if provided
        subcategory_id = None
        if subcategory_name:
            subcategory = conn.execute('''
                SELECT id FROM subcategories 
                WHERE name = ? AND category_id = ?
            ''', (subcategory_name, category_id)).fetchone()
            
            if not subcategory:
                cursor = conn.execute('''
                    INSERT INTO subcategories (name, category_id) 
                    VALUES (?, ?)
                ''', (subcategory_name, category_id))
                subcategory_id = cursor.lastrowid
            else:
                subcategory_id = subcategory['id']
        
        # Check if budget item already exists
        existing = conn.execute('''
            SELECT id FROM monthly_budget_items 
            WHERE monthly_budget_id = ? AND category_id = ? 
            AND (subcategory_id = ? OR (subcategory_id IS NULL AND ? IS NULL))
        ''', (monthly_budget_id, category_id, subcategory_id, subcategory_id)).fetchone()
        
        if existing:
            return jsonify({"error": "Budget item already exists for this category/subcategory"}), 409
        
        # Add the budget item
        cursor = conn.execute('''
            INSERT INTO monthly_budget_items 
            (monthly_budget_id, category_id, subcategory_id, budgeted_amount, budget_type)
            VALUES (?, ?, ?, ?, ?)
        ''', (monthly_budget_id, category_id, subcategory_id, budgeted_amount, budget_type))
        
        new_item_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": f"Added {category_name}" + (f" - {subcategory_name}" if subcategory_name else "") + f" to {year}-{month:02d} budget",
            "item_id": new_item_id,
            "category": category_name,
            "subcategory": subcategory_name,
            "budgeted_amount": budgeted_amount,
            "budget_type": budget_type
        })
        
    except Exception as e:
        logger.error(f"Error adding budget category: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/budget/<int:year>/<int:month>/remove-category', methods=['DELETE'])
def remove_budget_category(year: int, month: int):
    """Remove a category from the monthly budget"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        category_name = data.get('category')
        subcategory_name = data.get('subcategory')
        
        if not category_name:
            return jsonify({"error": "Category name is required"}), 400
        
        conn = get_db_connection()
        
        # Get the monthly budget ID
        monthly_budget = conn.execute('''
            SELECT id FROM monthly_budgets 
            WHERE budget_year = ? AND budget_month = ?
        ''', (year, month)).fetchone()
        
        if not monthly_budget:
            return jsonify({"error": f"No budget found for {year}-{month:02d}"}), 404
        
        monthly_budget_id = monthly_budget['id']
        
        # Get category ID
        category = conn.execute('SELECT id FROM categories WHERE name = ?', (category_name,)).fetchone()
        if not category:
            return jsonify({"error": f"Category '{category_name}' not found"}), 404
        
        category_id = category['id']
        
        # Get subcategory ID if provided
        subcategory_id = None
        if subcategory_name:
            subcategory = conn.execute('''
                SELECT id FROM subcategories 
                WHERE name = ? AND category_id = ?
            ''', (subcategory_name, category_id)).fetchone()
            
            if not subcategory:
                return jsonify({"error": f"Subcategory '{subcategory_name}' not found"}), 404
            
            subcategory_id = subcategory['id']
        
        # Find and delete the budget item
        budget_item = conn.execute('''
            SELECT id, budgeted_amount FROM monthly_budget_items 
            WHERE monthly_budget_id = ? AND category_id = ? 
            AND (subcategory_id = ? OR (subcategory_id IS NULL AND ? IS NULL))
        ''', (monthly_budget_id, category_id, subcategory_id, subcategory_id)).fetchone()
        
        if not budget_item:
            return jsonify({"error": "Budget item not found for this category/subcategory"}), 404
        
        # Delete the budget item
        conn.execute('''
            DELETE FROM monthly_budget_items WHERE id = ?
        ''', (budget_item['id'],))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": f"Removed {category_name}" + (f" - {subcategory_name}" if subcategory_name else "") + f" from {year}-{month:02d} budget",
            "removed_amount": float(budget_item['budgeted_amount'])
        })
        
    except Exception as e:
        logger.error(f"Error removing budget category: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/budget/available-months', methods=['GET'])
def get_available_budget_months():
    """Get list of all available budget months for pagination"""
    try:
        conn = get_db_connection()
        
        # Get all monthly budgets ordered by year, month
        budgets = conn.execute('''
            SELECT budget_year, budget_month, status, created_at
            FROM monthly_budgets
            ORDER BY budget_year DESC, budget_month DESC
        ''').fetchall()
        
        conn.close()
        
        available_months = []
        for budget in budgets:
            available_months.append({
                "year": budget['budget_year'],
                "month": budget['budget_month'],
                "status": budget['status'],
                "created_at": budget['created_at']
            })
        
        return jsonify({
            "available_months": available_months,
            "total_count": len(available_months)
        })
        
    except Exception as e:
        logger.error(f"Error fetching available budget months: {e}")
        return jsonify({"error": str(e)}), 500

# Recurring Patterns Endpoints

@app.route('/api/recurring-patterns/detect', methods=['POST'])
def detect_recurring_patterns():
    """Detect recurring patterns in transactions"""
    try:
        data = request.get_json() or {}
        lookback_days = data.get('lookback_days', 365)
        account_number = data.get('account_number')  # Optional account filter
        
        db = get_transaction_db()
        
        patterns = db.detect_recurring_patterns(
            account_number=account_number,
            lookback_days=lookback_days
        )
        
        # Convert patterns to API-friendly format
        api_patterns = []
        conn = get_db_connection()
        
        try:
            for pattern in patterns:
                confidence_pct = pattern['confidence'] * 100
                
                # Fetch category and subcategory names if IDs exist
                category_name = None
                subcategory_name = None
                if pattern.get('category_id'):
                    category_result = conn.execute('SELECT name FROM categories WHERE id = ?', 
                                                    (pattern['category_id'],)).fetchone()
                    if category_result:
                        category_name = category_result['name']
                if pattern.get('subcategory_id'):
                    subcat_result = conn.execute('SELECT name FROM subcategories WHERE id = ?', 
                                                (pattern['subcategory_id'],)).fetchone()
                    if subcat_result:
                        subcategory_name = subcat_result['name']
                
                api_pattern = {
                    'pattern_name': pattern['pattern_name'],
                    'account_number': pattern['account_number'],
                    'payee': pattern['payee'],
                    'typical_amount': float(pattern['typical_amount']),
                    'amount_variance': float(pattern.get('amount_variance', 0)),
                    'frequency_type': pattern['frequency_type'],
                    'frequency_interval': pattern.get('frequency_interval', 1),
                    'next_expected_date': pattern['next_expected_date'],
                    'last_occurrence_date': pattern['last_occurrence_date'],
                    'confidence': round(confidence_pct, 1),
                    'confidence_level': _get_confidence_level(pattern['confidence']),
                    'occurrence_count': pattern['occurrence_count'],
                    'pattern_type': pattern.get('pattern_type', 'unknown'),
                    'category_id': pattern.get('category_id'),
                    'subcategory_id': pattern.get('subcategory_id'),
                    'category': category_name,
                    'subcategory': subcategory_name
                }
                api_patterns.append(api_pattern)
        finally:
            conn.close()
        
        return jsonify({
            'patterns': api_patterns,
            'total_detected': len(patterns),
            'lookback_days': lookback_days
        })
        
    except Exception as e:
        logger.error(f"Error detecting recurring patterns: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/recurring-patterns', methods=['GET'])
def get_recurring_patterns():
    """Get saved recurring patterns"""
    try:
        account_number = request.args.get('account_number')
        active_only = request.args.get('active_only', 'true') == 'true'
        
        db = get_transaction_db()
        
        patterns = db.get_recurring_patterns(
            account_number=account_number, 
            active_only=active_only
        )
        
        # Convert to API format
        api_patterns = []
        for pattern in patterns:
            pattern_id, pattern_name, account_number, payee, typical_amount, amount_variance, frequency_type, frequency_interval, next_expected_date, last_occurrence_date, confidence, occurrence_count, is_active, created_at, category, subcategory = pattern
            
            confidence_pct = (confidence * 100) if confidence else 0
            api_pattern = {
                'id': pattern_id,
                'pattern_name': pattern_name,
                'account_number': account_number,
                'payee': payee,
                'typical_amount': float(typical_amount) if typical_amount else 0,
                'amount_variance': float(amount_variance) if amount_variance else 0,
                'frequency_type': frequency_type,
                'frequency_interval': frequency_interval,
                'next_expected_date': next_expected_date,
                'last_occurrence_date': last_occurrence_date,
                'confidence': round(confidence_pct, 1),
                'confidence_level': _get_confidence_level(confidence or 0),
                'occurrence_count': occurrence_count,
                'is_active': bool(is_active),
                'created_at': created_at,
                'category': category,
                'subcategory': subcategory
            }
            api_patterns.append(api_pattern)
        
        return jsonify({
            'patterns': api_patterns,
            'total_count': len(api_patterns)
        })
        
    except Exception as e:
        logger.error(f"Error getting recurring patterns: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/recurring-patterns/save', methods=['POST'])
def save_recurring_pattern():
    """Save a detected pattern to the database"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        db = get_transaction_db()
        
        # Convert API format back to internal format
        pattern = {
            'pattern_name': data['pattern_name'],
            'account_number': data['account_number'],
            'payee': data['payee'],
            'typical_amount': data['typical_amount'],
            'amount_variance': data.get('amount_variance', 0),
            'frequency_type': data['frequency_type'],
            'frequency_interval': data.get('frequency_interval', 1),
            'next_expected_date': data['next_expected_date'],
            'last_occurrence_date': data['last_occurrence_date'],
            'confidence': data['confidence'] / 100,  # Convert percentage back to decimal
            'occurrence_count': data['occurrence_count'],
            'category_id': data.get('category_id'),
            'subcategory_id': data.get('subcategory_id')
        }
        
        pattern_id = db.save_recurring_pattern(pattern)
        
        if pattern_id:
            return jsonify({
                'success': True,
                'pattern_id': pattern_id,
                'message': 'Pattern saved successfully'
            })
        else:
            return jsonify({"error": "Failed to save pattern"}), 500
        
    except Exception as e:
        logger.error(f"Error saving recurring pattern: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/recurring-patterns/<int:pattern_id>', methods=['PUT'])
def update_recurring_pattern(pattern_id):
    """Update a recurring pattern with comprehensive field support"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        db = get_transaction_db()
        
        # Use the new comprehensive update method
        success = db.update_pattern(pattern_id, data)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Pattern updated successfully'
            })
        else:
            return jsonify({"error": "Failed to update pattern or no changes made"}), 500
        
    except Exception as e:
        logger.error(f"Error updating recurring pattern: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/recurring-patterns/<int:pattern_id>', methods=['DELETE'])
def delete_recurring_pattern(pattern_id):
    """Delete (deactivate) a recurring pattern"""
    try:
        db = get_transaction_db()
        
        success = db.deactivate_pattern(pattern_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Pattern deactivated successfully'
            })
        else:
            return jsonify({"error": "Failed to deactivate pattern"}), 500
        
    except Exception as e:
        logger.error(f"Error deactivating recurring pattern: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/category-spending-analysis', methods=['GET'])
def analyze_category_spending():
    """Analyze spending patterns for a category to create estimated patterns"""
    try:
        # Get query parameters
        category = request.args.get('category', '')
        subcategory = request.args.get('subcategory', '')
        frequency = request.args.get('frequency', 'biweekly')
        lookback_days = int(request.args.get('lookback_days', 120))
        account = request.args.get('account', '')
        
        if not category:
            return jsonify({"error": "Category parameter is required"}), 400
        
        # Calculate date range
        from datetime import datetime, timedelta
        import statistics
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        conn = get_db_connection()
        
        # Build query based on parameters
        where_conditions = [
            "t.run_date >= ?",
            "t.run_date <= ?", 
            "c.name = ?",
            "t.amount < 0"  # Only expenses
        ]
        params = [start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), category]
        
        if subcategory:
            where_conditions.append("sc.name = ?")
            params.append(subcategory)
            
        # Include both target accounts for placeholder analysis
        where_conditions.append("t.account_number IN (?, ?)")
        params.extend(['Z06431462', 'Z23693697'])
        
        # Get transactions
        query = f'''
            SELECT t.run_date, ABS(t.amount) as amount
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            LEFT JOIN subcategories sc ON t.subcategory_id = sc.id
            WHERE {' AND '.join(where_conditions)}
            ORDER BY t.run_date
        '''
        
        transactions = conn.execute(query, params).fetchall()
        conn.close()
        
        if len(transactions) < 2:
            return jsonify({"error": "Not enough transaction data for analysis"}), 400
        
        # Group transactions by frequency period
        frequency_days = {
            'weekly': 7,
            'biweekly': 14, 
            'monthly': 30
        }
        
        period_length = frequency_days.get(frequency, 14)
        
        # Create period bins
        periods = []
        current_start = start_date
        period_num = 1
        
        # Convert transactions to dict for lookup
        tx_by_date = {}
        for tx in transactions:
            date = datetime.strptime(tx['run_date'], '%Y-%m-%d')
            amount = float(tx['amount'])
            
            if date not in tx_by_date:
                tx_by_date[date] = 0
            tx_by_date[date] += amount
        
        while current_start < end_date:
            period_end = current_start + timedelta(days=period_length)
            if period_end > end_date:
                period_end = end_date
            
            # Sum all transactions in this period
            period_total = 0
            for date, amount in tx_by_date.items():
                if current_start <= date < period_end:
                    period_total += amount
            
            periods.append({
                'period': period_num,
                'start': current_start.strftime('%m/%d'),
                'end': period_end.strftime('%m/%d'),
                'total': period_total
            })
            
            current_start = period_end
            period_num += 1
        
        # Calculate statistics
        amounts = [p['total'] for p in periods if p['total'] > 0]  # Only non-zero periods
        
        if len(amounts) < 2:
            return jsonify({"error": "Insufficient spending data for reliable analysis"}), 400
        
        mean_spending = statistics.mean(amounts)
        std_dev = statistics.stdev(amounts)
        cv = std_dev / mean_spending if mean_spending > 0 else 0
        min_spending = min(amounts)
        max_spending = max(amounts)
        
        # Add deviation percentages to periods
        for period in periods:
            if period['total'] > 0:
                period['deviation'] = (period['total'] - mean_spending) / mean_spending * 100
            else:
                period['deviation'] = -100  # Empty period
        
        # Determine predictability rating
        if cv < 0.2:
            predictability_rating = 'Very High (Excellent for forecasting)'
        elif cv < 0.3:
            predictability_rating = 'High (Good for forecasting)'
        elif cv < 0.5:
            predictability_rating = 'Medium (Acceptable for forecasting)'
        else:
            predictability_rating = 'Low (Poor for forecasting)'
        
        return jsonify({
            'category': category,
            'subcategory': subcategory,
            'frequency': frequency,
            'lookback_days': lookback_days,
            'mean': mean_spending,
            'std_dev': std_dev,
            'cv': cv,
            'min': min_spending,
            'max': max_spending,
            'range': max_spending - min_spending,
            'periods': periods,
            'predictability_rating': predictability_rating,
            'transaction_count': len(transactions),
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        logger.error(f"Error analyzing category spending: {e}")
        return jsonify({"error": str(e)}), 500

def _get_confidence_level(confidence: float) -> str:
    """Get confidence level category"""
    if confidence >= 0.7:
        return "high"
    elif confidence >= 0.5:
        return "medium"
    else:
        return "low"

def _get_confidence_description(confidence: float) -> str:
    """Get human-readable confidence description"""
    if confidence >= 0.8:
        return "High confidence - consistent historical data"
    elif confidence >= 0.6:
        return "Medium confidence - some variation in data"
    elif confidence >= 0.4:
        return "Low confidence - limited or inconsistent data"
    else:
        return "Very low confidence - insufficient historical data"

@app.route('/api/balance-projection', methods=['POST'])
def calculate_balance_projection():
    """Calculate future balance projection using recurring patterns"""
    try:
        data = request.get_json() or {}
        starting_balance = data.get('starting_balance', 10000.0)  # Default starting balance
        projection_days = data.get('projection_days', 90)
        account_number = 'Z06431462'  # Individual - TOD account only
        
        from datetime import datetime, timedelta
        
        db = get_transaction_db()
        
        # Get active recurring patterns for the Individual - TOD account
        patterns = db.get_recurring_patterns(account_number=account_number, active_only=True)
        
        # Generate daily projection
        current_date = datetime.now()
        projection_data = []
        running_balance = starting_balance
        
        for day_offset in range(projection_days + 1):
            projection_date = current_date + timedelta(days=day_offset)
            daily_change = 0
            projected_transactions = []
            
            # Check each pattern for occurrences on this date
            for pattern in patterns:
                pattern_id, pattern_name, acc_num, payee, typical_amount, amount_variance, frequency_type, frequency_interval, next_expected_date, last_occurrence_date, confidence, occurrence_count, is_active, created_at, category, subcategory = pattern
                
                # Parse next expected date
                try:
                    expected_date = datetime.strptime(next_expected_date, '%Y-%m-%d')
                except:
                    continue
                
                # Check if this pattern occurs on the current projection date
                should_occur = False
                
                if frequency_type == 'weekly':
                    # Weekly patterns: check if same day of week and appropriate interval
                    days_diff = (projection_date - expected_date).days
                    if days_diff >= 0 and days_diff % (7 * frequency_interval) == 0:
                        should_occur = True
                        
                elif frequency_type == 'biweekly':
                    # Biweekly patterns: check if same day and 14-day intervals
                    days_diff = (projection_date - expected_date).days
                    if days_diff >= 0 and days_diff % 14 == 0:
                        should_occur = True
                        
                elif frequency_type == 'monthly':
                    # Monthly patterns: check if same day of month
                    if (projection_date.day == expected_date.day and 
                        projection_date >= expected_date and
                        (projection_date.year > expected_date.year or 
                         projection_date.month > expected_date.month)):
                        should_occur = True
                    elif projection_date.date() == expected_date.date():
                        should_occur = True
                        
                elif frequency_type == 'quarterly':
                    # Quarterly patterns: check if same day and 3-month intervals
                    if (projection_date.day == expected_date.day and
                        projection_date >= expected_date):
                        months_diff = (projection_date.year - expected_date.year) * 12 + projection_date.month - expected_date.month
                        if months_diff > 0 and months_diff % 3 == 0:
                            should_occur = True
                    elif projection_date.date() == expected_date.date():
                        should_occur = True
                
                if should_occur:
                    # Use full typical amount for cashflow estimates
                    # Determine if this is income (positive) or expense (negative)
                    # Income patterns: direct deposit, dividends, transfers in
                    is_income = ('direct deposit' in pattern_name.lower() or 
                               'dividend' in pattern_name.lower() or
                               'interest' in pattern_name.lower())
                    
                    transaction_amount = typical_amount if is_income else -typical_amount
                    daily_change += transaction_amount
                    
                    projected_transactions.append({
                        'pattern_name': pattern_name,
                        'payee': payee,
                        'amount': transaction_amount,
                        'confidence': round(confidence * 100, 1) if confidence else 50,
                        'category': category,
                        'subcategory': subcategory
                    })
            
            running_balance += daily_change
            
            projection_data.append({
                'date': projection_date.strftime('%Y-%m-%d'),
                'balance': round(running_balance, 2),
                'daily_change': round(daily_change, 2),
                'projected_transactions': projected_transactions
            })
        
        # Calculate summary statistics
        final_balance = projection_data[-1]['balance'] if projection_data else starting_balance
        total_change = final_balance - starting_balance
        
        # Calculate projected income and expenses
        total_income = sum(day['daily_change'] for day in projection_data if day['daily_change'] > 0)
        total_expenses = abs(sum(day['daily_change'] for day in projection_data if day['daily_change'] < 0))
        
        return jsonify({
            'account_number': account_number,
            'account_name': 'Individual - TOD',
            'starting_balance': starting_balance,
            'final_balance': round(final_balance, 2),
            'total_change': round(total_change, 2),
            'projection_days': projection_days,
            'projected_income': round(total_income, 2),
            'projected_expenses': round(total_expenses, 2),
            'patterns_used': len([p for p in patterns if p[4] is not None]),  # Count valid patterns
            'daily_projections': projection_data,
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error calculating balance projection: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/monthly-pattern-projections', methods=['GET'])
def get_monthly_pattern_projections():
    """Get projected amounts from recurring patterns for a specific month"""
    try:
        from datetime import datetime, timedelta
        import calendar
        
        # Get query parameters
        year = int(request.args.get('year', datetime.now().year))
        month = int(request.args.get('month', datetime.now().month))
        
        # Calculate month boundaries
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        
        days_in_month = (end_date - start_date).days + 1
        
        conn = get_db_connection()
        
        # Get active recurring patterns
        patterns = conn.execute('''
            SELECT id, pattern_name, account_number, payee, typical_amount, 
                   frequency_type, frequency_interval, next_expected_date,
                   last_occurrence_date, category_id, subcategory_id
            FROM recurring_patterns 
            WHERE is_active = 1
        ''').fetchall()
        
        # Group projections by category/subcategory
        category_projections = {}
        
        for pattern in patterns:
            pattern_id, pattern_name, account_number, payee, typical_amount, frequency_type, frequency_interval, next_expected_date, last_occurrence_date, category_id, subcategory_id = pattern
            
            # Calculate expected occurrences in the month
            frequency_days = {
                'daily': 1,
                'weekly': 7, 
                'biweekly': 14,
                'monthly': 30,
                'quarterly': 90,
                'annual': 365
            }
            
            period_days = frequency_days.get(frequency_type, 30)
            expected_occurrences = max(1, round(days_in_month / period_days))
            
            # Calculate monthly projection
            monthly_amount = typical_amount * expected_occurrences
            
            # Determine if income or expense
            is_income = ('direct deposit' in pattern_name.lower() or 
                        'dividend' in pattern_name.lower() or
                        'salary' in pattern_name.lower() or
                        'income' in pattern_name.lower())
            
            transaction_type = 'income' if is_income else 'expense'
            monthly_amount = abs(monthly_amount)  # Always positive for aggregation
            
            # Get category/subcategory names
            category_name = 'Uncategorized'
            subcategory_name = None
            
            if category_id:
                cat_result = conn.execute('SELECT name FROM categories WHERE id = ?', (category_id,)).fetchone()
                if cat_result:
                    category_name = cat_result[0]
                    
            if subcategory_id:
                sub_result = conn.execute('SELECT name FROM subcategories WHERE id = ?', (subcategory_id,)).fetchone()
                if sub_result:
                    subcategory_name = sub_result[0]
            
            # Create category key
            category_key = f"{category_name}|{subcategory_name or ''}"
            
            if category_key not in category_projections:
                category_projections[category_key] = {
                    'category': category_name,
                    'subcategory': subcategory_name,
                    'income_projected': 0,
                    'expense_projected': 0,
                    'patterns': []
                }
            
            # Add to appropriate total
            if transaction_type == 'income':
                category_projections[category_key]['income_projected'] += monthly_amount
            else:
                category_projections[category_key]['expense_projected'] += monthly_amount
                
            # Add pattern details
            category_projections[category_key]['patterns'].append({
                'pattern_name': pattern_name,
                'payee': payee,
                'amount': monthly_amount,
                'type': transaction_type,
                'frequency': frequency_type,
                'occurrences': expected_occurrences
            })
        
        conn.close()
        
        return jsonify({
            'year': year,
            'month': month,
            'days_in_month': days_in_month,
            'category_projections': list(category_projections.values())
        })
        
    except Exception as e:
        logger.error(f"Error calculating monthly pattern projections: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/transactions/<int:transaction_id>/note', methods=['PUT'])
def update_transaction_note(transaction_id):
    """Update the note field for a specific transaction"""
    try:
        data = request.get_json()
        note = data.get('note')
        
        # Note can be None/null to clear it
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE transactions 
            SET note = ? 
            WHERE id = ?
        ''', (note, transaction_id))
        conn.commit()
        
        # Check if the update was successful
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "Transaction not found"}), 404
            
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Note updated successfully",
            "transaction_id": transaction_id,
            "note": note
        })
        
    except Exception as e:
        logger.error(f"Error updating transaction note: {e}")
        return jsonify({"error": str(e)}), 500

# Payee Pattern Management API Endpoints

@app.route('/api/payee-patterns', methods=['GET'])
def get_payee_patterns():
    """Get all payee extraction patterns"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, pattern, replacement, is_regex, is_active, 
                   created_by, usage_count, created_at, updated_at
            FROM payee_extraction_patterns 
            ORDER BY usage_count DESC, created_at DESC
        ''')
        
        patterns = []
        for row in cursor.fetchall():
            patterns.append({
                "id": row['id'],
                "name": row['name'],
                "pattern": row['pattern'],
                "replacement": row['replacement'],
                "is_regex": bool(row['is_regex']),
                "is_active": bool(row['is_active']),
                "created_by": row['created_by'],
                "usage_count": row['usage_count'],
                "created_at": row['created_at'],
                "updated_at": row['updated_at']
            })
        
        conn.close()
        return jsonify({"patterns": patterns})
        
    except Exception as e:
        logger.error(f"Error fetching payee patterns: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/payee-patterns', methods=['POST'])
def create_payee_pattern():
    """Create a new payee extraction pattern"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or not all(key in data for key in ['name', 'pattern', 'replacement']):
            return jsonify({"error": "Missing required fields: name, pattern, replacement"}), 400
        
        name = data['name'].strip()
        pattern = data['pattern'].strip()
        replacement = data['replacement'].strip()
        is_regex = data.get('is_regex', False)
        is_active = data.get('is_active', True)
        
        if not name or not pattern or not replacement:
            return jsonify({"error": "Name, pattern, and replacement cannot be empty"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check for duplicate pattern/replacement combination
        cursor.execute('''
            SELECT id FROM payee_extraction_patterns 
            WHERE pattern = ? AND replacement = ?
        ''', (pattern, replacement))
        
        if cursor.fetchone():
            conn.close()
            return jsonify({"error": "Pattern with this replacement already exists"}), 409
        
        # Insert new pattern
        cursor.execute('''
            INSERT INTO payee_extraction_patterns (name, pattern, replacement, is_regex, is_active)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, pattern, replacement, is_regex, is_active))
        
        pattern_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Created new payee pattern: {name} ({pattern} → {replacement})")
        
        return jsonify({
            "success": True,
            "message": "Pattern created successfully",
            "id": pattern_id
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating payee pattern: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/payee-patterns/<int:pattern_id>', methods=['PUT'])
def update_payee_pattern(pattern_id: int):
    """Update an existing payee extraction pattern"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if pattern exists
        cursor.execute('SELECT id FROM payee_extraction_patterns WHERE id = ?', (pattern_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"error": "Pattern not found"}), 404
        
        # Build update query dynamically based on provided fields
        update_fields = []
        update_values = []
        
        if 'name' in data:
            update_fields.append('name = ?')
            update_values.append(data['name'].strip())
        
        if 'pattern' in data:
            update_fields.append('pattern = ?')
            update_values.append(data['pattern'].strip())
        
        if 'replacement' in data:
            update_fields.append('replacement = ?')
            update_values.append(data['replacement'].strip())
        
        if 'is_regex' in data:
            update_fields.append('is_regex = ?')
            update_values.append(data['is_regex'])
        
        if 'is_active' in data:
            update_fields.append('is_active = ?')
            update_values.append(data['is_active'])
        
        if not update_fields:
            conn.close()
            return jsonify({"error": "No valid fields to update"}), 400
        
        # Add updated_at timestamp
        update_fields.append('updated_at = CURRENT_TIMESTAMP')
        update_values.append(pattern_id)
        
        query = f"UPDATE payee_extraction_patterns SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(query, update_values)
        
        conn.commit()
        conn.close()
        
        logger.info(f"Updated payee pattern ID {pattern_id}")
        
        return jsonify({
            "success": True,
            "message": "Pattern updated successfully"
        })
        
    except Exception as e:
        logger.error(f"Error updating payee pattern: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/payee-patterns/<int:pattern_id>', methods=['DELETE'])
def delete_payee_pattern(pattern_id: int):
    """Delete a payee extraction pattern"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if pattern exists
        cursor.execute('SELECT name FROM payee_extraction_patterns WHERE id = ?', (pattern_id,))
        pattern = cursor.fetchone()
        
        if not pattern:
            conn.close()
            return jsonify({"error": "Pattern not found"}), 404
        
        # Delete the pattern
        cursor.execute('DELETE FROM payee_extraction_patterns WHERE id = ?', (pattern_id,))
        conn.commit()
        conn.close()
        
        logger.info(f"Deleted payee pattern: {pattern['name']} (ID: {pattern_id})")
        
        return jsonify({
            "success": True,
            "message": "Pattern deleted successfully"
        })
        
    except Exception as e:
        logger.error(f"Error deleting payee pattern: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/payee-patterns/test', methods=['POST'])
def test_payee_pattern():
    """Test a payee extraction pattern against sample text"""
    try:
        data = request.get_json()
        
        if not data or not all(key in data for key in ['pattern', 'replacement', 'test_text']):
            return jsonify({"error": "Missing required fields: pattern, replacement, test_text"}), 400
        
        pattern = data['pattern']
        replacement = data['replacement']
        test_text = data['test_text']
        is_regex = data.get('is_regex', False)
        
        # Import the payee extractor logic
        import re
        
        result = None
        error = None
        
        try:
            if is_regex:
                # Use regex replacement
                if '(' in pattern and '$' in replacement:
                    # Capture group replacement
                    match = re.search(pattern, test_text, re.IGNORECASE)
                    if match:
                        # Handle $1, $2, etc. replacements
                        result = replacement
                        for i in range(1, min(10, len(match.groups()) + 1)):
                            result = result.replace(f'${i}', match.group(i))
                else:
                    # Simple regex match
                    if re.search(pattern, test_text, re.IGNORECASE):
                        result = replacement
            else:
                # Simple string matching
                if pattern.upper() in test_text.upper():
                    result = replacement
        
        except Exception as regex_error:
            error = f"Pattern error: {str(regex_error)}"
        
        return jsonify({
            "success": True,
            "test_text": test_text,
            "pattern": pattern,
            "replacement": replacement,
            "is_regex": is_regex,
            "result": result,
            "error": error
        })
        
    except Exception as e:
        logger.error(f"Error testing payee pattern: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/payee-patterns/<int:pattern_id>/apply', methods=['POST'])
def apply_payee_pattern(pattern_id: int):
    """Apply a specific payee pattern to matching transactions"""
    try:
        data = request.get_json() or {}
        preview_only = data.get('preview', False)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get the pattern details
        cursor.execute('''
            SELECT pattern, replacement, is_regex, name 
            FROM payee_extraction_patterns 
            WHERE id = ? AND is_active = 1
        ''', (pattern_id,))
        
        pattern_row = cursor.fetchone()
        if not pattern_row:
            conn.close()
            return jsonify({"error": "Pattern not found or inactive"}), 404
        
        pattern = pattern_row['pattern']
        replacement = pattern_row['replacement']
        is_regex = bool(pattern_row['is_regex'])
        pattern_name = pattern_row['name']
        
        # Find matching transactions from all transactions (not just missing payees)
        cursor.execute('''
            SELECT id, action, payee, run_date, account, amount
            FROM transactions
            ORDER BY id DESC
            LIMIT 1000
        ''')
        
        transactions = cursor.fetchall()
        matches = []
        
        import re
        
        for transaction in transactions:
            action = transaction['action'] or ''
            extracted_payee = None
            
            try:
                if is_regex:
                    # Use regex replacement
                    if '(' in pattern and '$' in replacement:
                        # Capture group replacement
                        match = re.search(pattern, action, re.IGNORECASE)
                        if match:
                            # Handle $1, $2, etc. replacements
                            extracted_payee = replacement
                            for i in range(1, min(10, len(match.groups()) + 1)):
                                extracted_payee = extracted_payee.replace(f'${i}', match.group(i))
                    else:
                        # Simple regex match
                        if re.search(pattern, action, re.IGNORECASE):
                            extracted_payee = replacement
                else:
                    # Simple string matching
                    if pattern.upper() in action.upper():
                        extracted_payee = replacement
                
                if extracted_payee:
                    matches.append({
                        "id": transaction['id'],
                        "action": action,
                        "current_payee": transaction['payee'],
                        "new_payee": extracted_payee,
                        "date": transaction['run_date'],
                        "account": transaction['account'],
                        "amount": float(transaction['amount'])
                    })
            
            except Exception as regex_error:
                logger.warning(f"Pattern error for transaction {transaction['id']}: {regex_error}")
                continue
        
        if preview_only:
            conn.close()
            return jsonify({
                "success": True,
                "preview": True,
                "pattern_name": pattern_name,
                "matches_found": len(matches),
                "matches": matches[:50],  # Limit preview to 50 transactions
                "total_matches": len(matches)
            })
        
        # Apply the updates
        updated_count = 0
        for match in matches:
            cursor.execute('''
                UPDATE transactions 
                SET payee = ?
                WHERE id = ?
            ''', (match['new_payee'], match['id']))
            updated_count += cursor.rowcount
        
        # Update pattern usage count
        cursor.execute('''
            UPDATE payee_extraction_patterns 
            SET usage_count = usage_count + ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (updated_count, pattern_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Applied pattern '{pattern_name}' to {updated_count} transactions")
        
        return jsonify({
            "success": True,
            "applied": True,
            "pattern_name": pattern_name,
            "updated_count": updated_count,
            "matches": matches[:20] if len(matches) <= 20 else matches[:10] + [{"summary": f"... and {len(matches) - 10} more"}]
        })
        
    except Exception as e:
        logger.error(f"Error applying payee pattern: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/categories/<category>/auto-calculate', methods=['GET'])
def auto_calculate_category_amount(category: str):
    """Calculate historical average for a category/subcategory combination (same logic as budget item auto-calculate)"""
    try:
        from urllib.parse import unquote
        from datetime import datetime

        # URL decode the category name
        category = unquote(category)
        subcategory = request.args.get('subcategory')
        if subcategory:
            subcategory = unquote(subcategory)

        # Get target year/month from query params or use current
        target_year = int(request.args.get('year', datetime.now().year))
        target_month = int(request.args.get('month', datetime.now().month))

        db = get_transaction_db()
        conn = get_db_connection()

        # Get category and subcategory IDs (same logic as existing endpoint)
        category_query = conn.execute('SELECT id FROM categories WHERE name = ?', (category,)).fetchone()
        if not category_query:
            return jsonify({"error": f"Category '{category}' not found"}), 404
        category_id = category_query['id']

        subcategory_id = None
        if subcategory:
            subcategory_query = conn.execute('SELECT id FROM subcategories WHERE name = ?', (subcategory,)).fetchone()
            if subcategory_query:
                subcategory_id = subcategory_query['id']

        conn.close()

        # Calculate historical average (exact same logic as existing endpoint)
        result = db.calculate_historical_average(
            category_id=category_id,
            subcategory_id=subcategory_id,
            target_year=target_year,
            target_month=target_month
        )

        if result is None:
            return jsonify({
                "error": "Insufficient historical data",
                "message": "Need at least 3 months of transaction data for auto-calculation"
            }), 400

        # Return exact same format as existing endpoint
        return jsonify({
            "suggested_amount": result['amount'],
            "confidence": result['confidence'],
            "analysis": {
                "months_used": result['months_used'],
                "outliers_removed": result['outliers_removed'],
                "median": result['median'],
                "confidence_description": _get_confidence_description(result['confidence'])
            }
        })

    except Exception as e:
        logger.error(f"Error auto-calculating category amount: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/categories-with-spending', methods=['GET'])
def get_categories_with_spending():
    """Get all categories and subcategories that have transaction activity"""
    try:
        conn = get_db_connection()

        # Get all category/subcategory combinations that have transactions
        query = conn.execute('''
            SELECT c.name as category,
                   s.name as subcategory,
                   COUNT(t.id) as transaction_count,
                   SUM(ABS(t.amount)) as total_amount
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            LEFT JOIN subcategories s ON t.subcategory_id = s.id
            WHERE c.name NOT IN ('Banking', 'Investment', 'Transfer')  -- Exclude system categories
            GROUP BY c.id, c.name, s.id, s.name
            HAVING transaction_count > 0
            ORDER BY c.name, s.name
        ''').fetchall()

        categories = []
        for row in query:
            categories.append({
                "category": row['category'],
                "subcategory": row['subcategory'],
                "transaction_count": row['transaction_count'],
                "total_amount": float(row['total_amount'])
            })

        conn.close()

        return jsonify({
            "categories": categories,
            "count": len(categories)
        })

    except Exception as e:
        logger.error(f"Error fetching categories with spending: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/upload-csv', methods=['POST'])
def upload_csv_file():
    """Handle CSV file upload to transactions directory"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Validate file extension
        if not file.filename.lower().endswith('.csv'):
            return jsonify({"error": "Only CSV files are allowed"}), 400

        # Secure the filename
        filename = secure_filename(file.filename)
        if not filename:
            return jsonify({"error": "Invalid filename"}), 400

        # Ensure transactions directory exists
        if not os.path.exists(TRANSACTIONS_DIR):
            os.makedirs(TRANSACTIONS_DIR)
            logger.info(f"Created transactions directory: {TRANSACTIONS_DIR}")

        # Save the file
        filepath = os.path.join(TRANSACTIONS_DIR, filename)
        file.save(filepath)

        # Log the upload
        logger.info(f"CSV file uploaded: {filename} ({os.path.getsize(filepath)} bytes)")

        # If file monitoring is active, it should automatically process this file
        monitoring_active = _monitor_thread and _monitor_thread.is_alive()

        return jsonify({
            "message": f"File '{filename}' uploaded successfully",
            "filename": filename,
            "size": os.path.getsize(filepath),
            "monitoring_active": monitoring_active,
            "auto_processing": monitoring_active
        })

    except Exception as e:
        logger.error(f"Error uploading CSV file: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================================================
# REPORTS ENDPOINTS
# ============================================================================

@app.route('/api/reports/yearly-category-totals', methods=['GET'])
def get_yearly_category_totals():
    """Get category totals for a given year (defaults to most recent completed year)"""
    try:
        conn = get_db_connection()

        # Get year parameter or determine most recent completed year
        year = request.args.get('year', type=int)

        if not year:
            # Find the most recent completed year (not current year unless we're past December)
            current_date = datetime.now()
            current_year = current_date.year
            current_month = current_date.month

            # If we're in January-November, use previous year as "completed"
            # If we're in December, still use previous year to be safe
            year = current_year - 1

            # Verify we have data for this year, otherwise find the latest year with data
            year_check = conn.execute('''
                SELECT DISTINCT CAST(strftime('%Y', run_date) as INTEGER) as year
                FROM transactions
                WHERE run_date IS NOT NULL
                ORDER BY year DESC
                LIMIT 5
            ''').fetchall()

            if year_check:
                available_years = [row['year'] for row in year_check]
                # Use the most recent year that's not the current year, or current if it's all we have
                for available_year in available_years:
                    if available_year < current_year:
                        year = available_year
                        break
                else:
                    # If no year before current, use the most recent available
                    year = available_years[0]

        # Get category totals for the year
        start_date = f"{year}-01-01"
        end_date = f"{year + 1}-01-01"

        category_totals = conn.execute('''
            SELECT
                c.name as category,
                s.name as subcategory,
                SUM(ABS(t.amount)) as total_amount,
                COUNT(t.id) as transaction_count
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            LEFT JOIN subcategories s ON t.subcategory_id = s.id
            WHERE t.run_date >= ? AND t.run_date < ?
            AND t.amount < 0  -- Only expenses (negative amounts)
            AND c.name NOT IN ('Banking', 'Investment', 'Transfer')  -- Exclude transfers/investments
            GROUP BY c.id, c.name, s.id, s.name
            HAVING total_amount > 0
            ORDER BY total_amount DESC
        ''', (start_date, end_date)).fetchall()

        # Get total spending for the year
        total_spending = conn.execute('''
            SELECT SUM(ABS(amount)) as total
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.run_date >= ? AND t.run_date < ?
            AND t.amount < 0
            AND c.name NOT IN ('Banking', 'Investment', 'Transfer')
        ''', (start_date, end_date)).fetchone()['total']

        # Get available years for dropdown
        available_years = conn.execute('''
            SELECT DISTINCT CAST(strftime('%Y', run_date) as INTEGER) as year
            FROM transactions
            WHERE run_date IS NOT NULL
            ORDER BY year DESC
        ''').fetchall()

        conn.close()

        # Format response - group by category with subcategories nested
        categories_dict = {}
        for row in category_totals:
            category_name = row['category']
            subcategory_name = row['subcategory']
            amount = float(row['total_amount'])
            transaction_count = row['transaction_count']

            # Initialize category if not exists
            if category_name not in categories_dict:
                categories_dict[category_name] = {
                    "category": category_name,
                    "amount": 0,
                    "transaction_count": 0,
                    "subcategories": []
                }

            # Add to category total
            categories_dict[category_name]["amount"] += amount
            categories_dict[category_name]["transaction_count"] += transaction_count

            # Add subcategory if it exists
            if subcategory_name:
                categories_dict[category_name]["subcategories"].append({
                    "subcategory": subcategory_name,
                    "amount": amount,
                    "transaction_count": transaction_count
                })

        # Convert to list and calculate percentages
        categories = []
        for category_data in categories_dict.values():
            category_data["percentage"] = (category_data["amount"] / total_spending * 100) if total_spending and total_spending > 0 else 0

            # Calculate percentages for subcategories
            for subcat in category_data["subcategories"]:
                subcat["percentage"] = (subcat["amount"] / total_spending * 100) if total_spending and total_spending > 0 else 0

            # Sort subcategories by amount descending
            category_data["subcategories"].sort(key=lambda x: x["amount"], reverse=True)

            categories.append(category_data)

        # Sort categories by amount descending
        categories.sort(key=lambda x: x["amount"], reverse=True)

        return jsonify({
            "year": year,
            "categories": categories,
            "total_spending": float(total_spending) if total_spending else 0,
            "available_years": [row['year'] for row in available_years]
        })

    except Exception as e:
        logger.error(f"Error fetching yearly category totals: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("🚀 Starting Flask API Server with File Monitoring...")
    logger.info("📊 API will be available at http://localhost:5000")
    logger.info("🔗 Health check: http://localhost:5000/api/health")
    logger.info("📋 Transactions: http://localhost:5000/api/transactions")
    logger.info("💰 Budget: http://localhost:5000/api/budget/2025/8")
    logger.info("📁 File monitoring: http://localhost:5000/api/file-monitoring")
    logger.info("🛑 Press Ctrl+C to stop")
    
    print("🚀 Starting Flask API Server with File Monitoring...")
    print("📊 API will be available at http://localhost:5000")
    print("🔗 Health check: http://localhost:5000/api/health")
    print("📋 Transactions: http://localhost:5000/api/transactions")
    print("💰 Budget: http://localhost:5000/api/budget/2025/8")
    print("📁 File monitoring: http://localhost:5000/api/file-monitoring")
    print("🛑 Press Ctrl+C to stop")
    
    # Start file monitoring automatically
    try:
        start_file_monitoring()
        logger.info("✅ File monitoring started automatically")
    except Exception as e:
        logger.error(f"⚠️  Failed to start file monitoring: {e}")
        print(f"⚠️  File monitoring disabled due to error: {e}")
    
    try:
        # Note: use_reloader=False to prevent conflicts with background threads
        app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("Flask server stopped by user")
        stop_file_monitoring()
    except Exception as e:
        logger.error(f"Flask server error: {e}")
        stop_file_monitoring()
        raise
