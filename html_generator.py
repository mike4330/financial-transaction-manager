import os
from datetime import datetime
from typing import List, Tuple
from database import TransactionDB

class HTMLGenerator:
    def __init__(self, db: TransactionDB, output_file: str = "transactions_report.html"):
        self.db = db
        self.output_file = output_file
    
    def generate_report(self):
        """Generate complete HTML report"""
        # Get data
        total_transactions = self.db.get_transaction_count()
        account_summary = self.db.get_account_summary()
        category_summary = self.db.get_category_summary()
        uncategorized = self.db.get_uncategorized_transactions(limit=20)
        payee_summary = self._get_payee_summary()
        transaction_type_summary = self._get_transaction_type_summary()
        grocery_data = self._get_grocery_spending_by_month()
        
        # Generate HTML
        html_content = self._generate_html(
            total_transactions, account_summary, category_summary, uncategorized, payee_summary, transaction_type_summary, grocery_data
        )
        
        # Write to file
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _get_payee_summary(self) -> List[Tuple]:
        """Get summary of top payees by transaction count and amount"""
        import sqlite3
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT 
                    COALESCE(payee, 'Unknown') as payee_name,
                    COUNT(*) as transaction_count,
                    SUM(amount) as total_amount,
                    AVG(amount) as avg_amount
                FROM transactions 
                WHERE payee IS NOT NULL AND payee != ''
                GROUP BY payee
                ORDER BY transaction_count DESC, total_amount DESC
                LIMIT 20
            ''')
            
            results = cursor.fetchall()
            return results
            
        except Exception as e:
            print(f"Error getting payee summary: {e}")
            return []
        finally:
            conn.close()
    
    def _get_transaction_type_summary(self) -> List[Tuple]:
        """Get summary of transactions by type"""
        import sqlite3
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT 
                    COALESCE(type, 'Unknown') as transaction_type,
                    COUNT(*) as transaction_count,
                    SUM(amount) as total_amount,
                    AVG(amount) as avg_amount
                FROM transactions 
                GROUP BY type
                ORDER BY transaction_count DESC
                LIMIT 20
            ''')
            
            results = cursor.fetchall()
            return results
            
        except Exception as e:
            print(f"Error getting transaction type summary: {e}")
            return []
        finally:
            conn.close()
    
    def _get_grocery_spending_by_month(self) -> List[Tuple]:
        """Get grocery spending by month for chart"""
        import sqlite3
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT 
                    strftime('%Y-%m', substr(run_date, 7, 4) || '-' || substr(run_date, 1, 2) || '-' || substr(run_date, 4, 2)) as month,
                    SUM(ABS(amount)) as total_spent,
                    COUNT(*) as transaction_count
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                JOIN subcategories s ON t.subcategory_id = s.id
                WHERE c.name = 'Food & Dining' AND s.name = 'Groceries'
                AND month IS NOT NULL
                GROUP BY month
                ORDER BY month DESC
                LIMIT 12
            ''')
            
            results = cursor.fetchall()
            return list(reversed(results))  # Oldest to newest for chart
            
        except Exception as e:
            print(f"Error getting grocery spending data: {e}")
            return []
        finally:
            conn.close()
    
    def _generate_html(self, total_transactions: int, account_summary: List[Tuple], 
                      category_summary: List[Tuple], uncategorized: List[Tuple], payee_summary: List[Tuple], transaction_type_summary: List[Tuple], grocery_data: List[Tuple]) -> str:
        """Generate the HTML content"""
        
        # Calculate totals
        categorized_count = total_transactions - len(uncategorized) if uncategorized else total_transactions
        uncategorized_count = len(uncategorized) if uncategorized else 0
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Financial Transaction Report</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }}
        h1 {{ color: #333; border-bottom: 3px solid #007acc; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .summary-card {{ flex: 1; padding: 20px; background: #f8f9fa; border-left: 4px solid #007acc; }}
        .summary-card h3 {{ margin: 0 0 10px 0; color: #333; }}
        .summary-card .number {{ font-size: 24px; font-weight: bold; color: #007acc; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; font-weight: bold; color: #333; }}
        tr:hover {{ background: #f8f9fa; }}
        .amount {{ text-align: right; font-family: monospace; }}
        .positive {{ color: #28a745; }}
        .negative {{ color: #dc3545; }}
        .footer {{ text-align: center; color: #666; margin-top: 40px; font-size: 14px; }}
        .uncategorized {{ background: #fff3cd; }}
        
        /* Simple bar chart styles */
        .chart-container {{ margin: 30px 0; padding: 20px; background: #f8f9fa; border-radius: 8px; }}
        .chart {{ display: flex; align-items: end; height: 200px; gap: 5px; margin: 20px 0; }}
        .bar {{ 
            background: linear-gradient(to top, #007acc 0%, #4da6d9 100%); 
            border-radius: 4px 4px 0 0; 
            min-width: 30px; 
            display: flex; 
            flex-direction: column; 
            justify-content: end; 
            position: relative;
            transition: all 0.3s ease;
        }}
        .bar:hover {{ 
            background: linear-gradient(to top, #005c99 0%, #3d8bb3 100%); 
            transform: scale(1.05);
        }}
        .bar-value {{ 
            color: white; 
            font-size: 10px; 
            text-align: center; 
            padding: 5px 2px; 
            font-weight: bold;
        }}
        .bar-label {{ 
            position: absolute; 
            bottom: -25px; 
            left: 50%; 
            transform: translateX(-50%); 
            font-size: 10px; 
            color: #666; 
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Financial Transaction Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="summary">
            <div class="summary-card">
                <h3>Total Transactions</h3>
                <div class="number">{total_transactions:,}</div>
            </div>
            <div class="summary-card">
                <h3>Categorized</h3>
                <div class="number">{categorized_count:,}</div>
            </div>
            <div class="summary-card">
                <h3>Uncategorized</h3>
                <div class="number">{uncategorized_count:,}</div>
            </div>
        </div>
        
        <h2>Account Summary</h2>
        <table>
            <thead>
                <tr>
                    <th>Account</th>
                    <th>Account Number</th>
                    <th>Transactions</th>
                    <th class="amount">Total Amount</th>
                </tr>
            </thead>
            <tbody>
"""
        
        # Account summary rows
        for account, account_num, count, total in account_summary:
            amount_class = "positive" if total > 0 else "negative"
            html += f"""                <tr>
                    <td>{account}</td>
                    <td>{account_num}</td>
                    <td>{count:,}</td>
                    <td class="amount {amount_class}">${total:,.2f}</td>
                </tr>
"""
        
        html += """            </tbody>
        </table>
        
        <h2>Category Summary</h2>
        <table>
            <thead>
                <tr>
                    <th>Category</th>
                    <th>Subcategory</th>
                    <th>Transactions</th>
                    <th class="amount">Total Amount</th>
                    <th class="amount">Average</th>
                </tr>
            </thead>
            <tbody>
"""
        
        # Category summary rows
        for category, subcategory, count, total, avg in category_summary:
            amount_class = "positive" if total > 0 else "negative"
            row_class = "uncategorized" if category == "Uncategorized" else ""
            html += f"""                <tr class="{row_class}">
                    <td>{category}</td>
                    <td>{subcategory}</td>
                    <td>{count:,}</td>
                    <td class="amount {amount_class}">${total:,.2f}</td>
                    <td class="amount {amount_class}">${avg:,.2f}</td>
                </tr>
"""
        
        html += """            </tbody>
        </table>
"""
        
        # Recent uncategorized transactions
        if uncategorized:
            html += f"""        
        <h2>Recent Uncategorized Transactions (Last {len(uncategorized)})</h2>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Date</th>
                    <th>Account</th>
                    <th class="amount">Amount</th>
                    <th>Payee</th>
                    <th>Description</th>
                </tr>
            </thead>
            <tbody>
"""
            
            for tx_id, date, account, description, amount, action, payee in uncategorized:
                amount_class = "positive" if amount > 0 else "negative"
                desc_short = description[:60] + "..." if len(description) > 60 else description
                payee_display = payee[:20] + "..." if payee and len(payee) > 20 else (payee or "")
                html += f"""                <tr>
                    <td>{tx_id}</td>
                    <td>{date}</td>
                    <td>{account[:20]}</td>
                    <td class="amount {amount_class}">${amount:,.2f}</td>
                    <td>{payee_display}</td>
                    <td>{desc_short}</td>
                </tr>
"""
            
            html += """            </tbody>
        </table>
        
        <h2>Top Payees</h2>
        <table>
            <thead>
                <tr>
                    <th>Payee</th>
                    <th>Transactions</th>
                    <th class="amount">Total Amount</th>
                    <th class="amount">Average</th>
                </tr>
            </thead>
            <tbody>
"""
        
        # Payee summary rows
        for payee, count, total, avg in payee_summary:
            amount_class = "positive" if total > 0 else "negative"
            payee_display = payee or "Unknown"
            html += f"""                <tr>
                    <td>{payee_display}</td>
                    <td>{count:,}</td>
                    <td class="amount {amount_class}">${total:,.2f}</td>
                    <td class="amount {amount_class}">${avg:,.2f}</td>
                </tr>
"""
        
        html += """            </tbody>
        </table>
        
        <h2>Transaction Types</h2>
        <table>
            <thead>
                <tr>
                    <th>Transaction Type</th>
                    <th>Count</th>
                    <th class="amount">Total Amount</th>
                    <th class="amount">Average</th>
                    <th>Percentage</th>
                </tr>
            </thead>
            <tbody>
"""
        
        # Transaction type summary rows  
        for tx_type, count, total, avg in transaction_type_summary:
            amount_class = "positive" if total > 0 else "negative"
            percentage = (count / total_transactions * 100) if total_transactions > 0 else 0
            html += f"""                <tr>
                    <td>{tx_type}</td>
                    <td>{count:,}</td>
                    <td class="amount {amount_class}">${total:,.2f}</td>
                    <td class="amount {amount_class}">${avg:,.2f}</td>
                    <td>{percentage:.1f}%</td>
                </tr>
"""
        
        html += """            </tbody>
        </table>
"""
        
        # Add grocery spending chart if we have data
        if grocery_data:
            max_amount = max(amount for _, amount, _ in grocery_data) if grocery_data else 1
            
            html += """        
        <div class="chart-container">
            <h2>Grocery Spending by Month</h2>
            <div class="chart">
"""
            
            for month, amount, count in grocery_data:
                # Calculate bar height as percentage of max
                height_pct = (amount / max_amount * 100) if max_amount > 0 else 0
                # Format month as MM/YY (e.g., "07/25" from "2025-07")
                if month and len(month) >= 7:
                    month_short = f"{month[5:7]}/{month[2:4]}"  # MM/YY from YYYY-MM
                else:
                    month_short = "??"
                
                html += f"""                <div class="bar" style="height: {height_pct}%; flex: 1;">
                    <div class="bar-value">${amount:.0f}</div>
                    <div class="bar-label">{month_short}</div>
                </div>
"""
            
            html += """            </div>
            <p style="text-align: center; color: #666; font-size: 14px; margin-top: 30px;">
                Monthly grocery spending over the last 12 months (amounts in USD)
            </p>
        </div>
"""
        
        html += f"""        
        <div class="footer">
            <p>Financial Transaction Parser | Database: {os.path.basename(self.db.db_path)}</p>
        </div>
    </div>
</body>
</html>"""
        
        return html