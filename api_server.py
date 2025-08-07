#!/usr/bin/env python3
"""
Flask API Server for Financial Transaction Management
Separate from main.py - provides REST API for React frontend
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

DATABASE_PATH = "transactions.db"

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

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
            c.name as category,
            s.name as subcategory,
            t.category_id,
            t.subcategory_id
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
            'transaction_type': 't.type'
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
        from database import TransactionDB
        db = TransactionDB()
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
        from database import TransactionDB
        db = TransactionDB()
        
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
        from database import TransactionDB
        db = TransactionDB()
        
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
        
        from database import TransactionDB
        db = TransactionDB()
        
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
        from database import TransactionDB
        db = TransactionDB()
        
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
        
        from database import TransactionDB
        db = TransactionDB()
        
        patterns = db.detect_recurring_patterns(
            account_number=account_number,
            lookback_days=lookback_days
        )
        
        # Convert patterns to API-friendly format
        api_patterns = []
        for pattern in patterns:
            confidence_pct = pattern['confidence'] * 100
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
                'subcategory_id': pattern.get('subcategory_id')
            }
            api_patterns.append(api_pattern)
        
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
        
        from database import TransactionDB
        db = TransactionDB()
        
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
        
        from database import TransactionDB
        db = TransactionDB()
        
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
def update_recurring_pattern():
    """Update a recurring pattern (mainly for activating/deactivating)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        from database import TransactionDB
        db = TransactionDB()
        
        # For now, only support activate/deactivate
        if 'is_active' in data and not data['is_active']:
            success = db.deactivate_pattern(pattern_id)
        elif 'next_expected_date' in data:
            success = db.update_pattern_next_date(pattern_id, data['next_expected_date'])
        else:
            return jsonify({"error": "Invalid update operation"}), 400
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Pattern updated successfully'
            })
        else:
            return jsonify({"error": "Failed to update pattern"}), 500
        
    except Exception as e:
        logger.error(f"Error updating recurring pattern: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/recurring-patterns/<int:pattern_id>', methods=['DELETE'])
def delete_recurring_pattern(pattern_id):
    """Delete (deactivate) a recurring pattern"""
    try:
        from database import TransactionDB
        db = TransactionDB()
        
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
        
        from database import TransactionDB
        from datetime import datetime, timedelta
        
        db = TransactionDB()
        
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
                    # Apply confidence weighting to the transaction
                    confidence_factor = confidence if confidence else 0.5
                    weighted_amount = typical_amount * confidence_factor
                    
                    # Determine if this is income (positive) or expense (negative)
                    # Income patterns: direct deposit, dividends, transfers in
                    is_income = ('direct deposit' in pattern_name.lower() or 
                               'dividend' in pattern_name.lower() or
                               'interest' in pattern_name.lower())
                    
                    transaction_amount = weighted_amount if is_income else -weighted_amount
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

if __name__ == '__main__':
    print("🚀 Starting Flask API Server...")
    print("📊 API will be available at http://localhost:5000")
    print("🔗 Health check: http://localhost:5000/api/health")
    print("📋 Transactions: http://localhost:5000/api/transactions")
    print("💰 Budget: http://localhost:5000/api/budget/2025/8")
    print("🛑 Press Ctrl+C to stop")
    
    app.run(debug=True, host='0.0.0.0', port=5000)