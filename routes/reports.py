"""
Reports API Blueprint
Handles all reporting endpoints including yearly reports, variance analysis, etc.
"""

from flask import Blueprint, jsonify, request
from datetime import datetime
import sqlite3
import logging

# Create blueprint
reports_bp = Blueprint('reports', __name__)

# Get logger
logger = logging.getLogger(__name__)

DATABASE_PATH = "transactions.db"

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn


@reports_bp.route('/reports/yearly-category-totals', methods=['GET'])
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
