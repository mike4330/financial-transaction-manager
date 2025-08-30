import sqlite3
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Tuple

class TransactionDB:
    def __init__(self, db_path: str = "transactions.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Categories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Subcategories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subcategories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories (id),
                UNIQUE (category_id, name)
            )
        ''')
        
        # Classification patterns table for caching learned patterns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS classification_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT NOT NULL,
                pattern_type TEXT NOT NULL DEFAULT 'description',
                category_id INTEGER NOT NULL,
                subcategory_id INTEGER,
                confidence REAL NOT NULL,
                usage_count INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories (id),
                FOREIGN KEY (subcategory_id) REFERENCES subcategories (id),
                UNIQUE (pattern, pattern_type)
            )
        ''')
        
        # Transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TEXT NOT NULL,
                account TEXT NOT NULL,
                account_number TEXT NOT NULL,
                action TEXT NOT NULL,
                symbol TEXT,
                description TEXT,
                type TEXT,
                exchange_quantity REAL,
                exchange_currency TEXT,
                quantity REAL,
                currency TEXT,
                price REAL,
                exchange_rate REAL,
                commission REAL,
                fees REAL,
                accrued_interest REAL,
                amount REAL NOT NULL,
                settlement_date TEXT,
                payee TEXT,
                category_id INTEGER,
                subcategory_id INTEGER,
                note TEXT,
                hash TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_file TEXT,
                FOREIGN KEY (category_id) REFERENCES categories (id),
                FOREIGN KEY (subcategory_id) REFERENCES subcategories (id)
            )
        ''')
        
        # Processed files table to track what's been imported
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE NOT NULL,
                file_hash TEXT NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                record_count INTEGER
            )
        ''')
        
        # Budget Templates (reusable budget definitions)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS budget_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Budget Template Items (category/subcategory allocations within a template)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS budget_template_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                subcategory_id INTEGER,
                budget_amount DECIMAL(10,2) NOT NULL,
                budget_type TEXT CHECK (budget_type IN ('expense', 'income')) DEFAULT 'expense',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (template_id) REFERENCES budget_templates (id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories (id),
                FOREIGN KEY (subcategory_id) REFERENCES subcategories (id),
                UNIQUE (template_id, category_id, subcategory_id)
            )
        ''')
        
        # Monthly Budget Journals (actual monthly instances)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monthly_budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                budget_year INTEGER NOT NULL,
                budget_month INTEGER NOT NULL CHECK (budget_month BETWEEN 1 AND 12),
                status TEXT CHECK (status IN ('draft', 'active', 'closed')) DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                FOREIGN KEY (template_id) REFERENCES budget_templates (id),
                UNIQUE (template_id, budget_year, budget_month)
            )
        ''')
        
        # Monthly Budget Line Items (journalized entries)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monthly_budget_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                monthly_budget_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                subcategory_id INTEGER,
                budgeted_amount DECIMAL(10,2) NOT NULL,
                actual_amount DECIMAL(10,2) DEFAULT 0.00,
                budget_type TEXT CHECK (budget_type IN ('expense', 'income')) DEFAULT 'expense',
                notes TEXT,
                last_calculated_at TIMESTAMP,
                FOREIGN KEY (monthly_budget_id) REFERENCES monthly_budgets (id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories (id),
                FOREIGN KEY (subcategory_id) REFERENCES subcategories (id),
                UNIQUE (monthly_budget_id, category_id, subcategory_id)
            )
        ''')
        
        # Budget Adjustments (mid-month changes)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS budget_adjustments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                monthly_budget_item_id INTEGER NOT NULL,
                adjustment_amount DECIMAL(10,2) NOT NULL,
                adjustment_reason TEXT NOT NULL,
                adjustment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                FOREIGN KEY (monthly_budget_item_id) REFERENCES monthly_budget_items (id) ON DELETE CASCADE
            )
        ''')
        
        # Recurring Transaction Patterns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recurring_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_name TEXT NOT NULL,
                account_number TEXT NOT NULL,
                payee TEXT,
                category_id INTEGER,
                subcategory_id INTEGER,
                typical_amount DECIMAL(12,2),
                amount_variance DECIMAL(12,2) DEFAULT 0.00,
                frequency_type TEXT CHECK (frequency_type IN ('weekly', 'biweekly', 'monthly', 'quarterly', 'annual')) NOT NULL,
                frequency_interval INTEGER DEFAULT 1,
                next_expected_date DATE,
                last_occurrence_date DATE,
                confidence REAL DEFAULT 0.0,
                occurrence_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories (id),
                FOREIGN KEY (subcategory_id) REFERENCES subcategories (id)
            )
        ''')
        
        # Payee Extraction Patterns (user-defined patterns for payee extraction)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payee_extraction_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                pattern TEXT NOT NULL,
                replacement TEXT NOT NULL,
                is_regex BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_by TEXT DEFAULT 'user',
                usage_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (pattern, replacement)
            )
        ''')
        
        # Quicken Reconciliation Tracking - tracks which QIF transactions have been processed
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS qif_reconciliation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                qif_file_path TEXT NOT NULL,
                batch_number INTEGER NOT NULL,
                qif_transaction_hash TEXT NOT NULL,
                qif_date DATE NOT NULL,
                qif_amount DECIMAL(12,2) NOT NULL,
                qif_payee TEXT,
                qif_category TEXT,
                qif_memo TEXT,
                reconciliation_status TEXT CHECK (reconciliation_status IN ('pending', 'matched', 'imported', 'skipped', 'duplicate')) DEFAULT 'pending',
                matched_transaction_id INTEGER,
                import_decision TEXT,  -- JSON of LLM decisions
                reconciled_at TIMESTAMP,
                reconciled_by TEXT DEFAULT 'claude_code',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (matched_transaction_id) REFERENCES transactions (id),
                UNIQUE (qif_file_path, qif_transaction_hash)
            )
        ''')
        
        # Quicken Category Mappings - learned rules for category mapping
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS qif_category_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quicken_category TEXT NOT NULL,
                quicken_subcategory TEXT,
                app_category_id INTEGER NOT NULL,
                app_subcategory_id INTEGER,
                confidence REAL DEFAULT 1.0,
                mapping_type TEXT CHECK (mapping_type IN ('exact', 'fuzzy', 'llm_learned')) DEFAULT 'exact',
                usage_count INTEGER DEFAULT 0,
                last_used TIMESTAMP,
                created_by TEXT DEFAULT 'claude_code',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (app_category_id) REFERENCES categories (id),
                FOREIGN KEY (app_subcategory_id) REFERENCES subcategories (id),
                UNIQUE (quicken_category, quicken_subcategory)
            )
        ''')
        
        # Index for faster duplicate detection
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transaction_hash ON transactions(hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_run_date ON transactions(run_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_account ON transactions(account_number)')
        
        # Budget-specific indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_budget_template_active ON budget_templates(is_active)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_monthly_budget_year_month ON monthly_budgets(budget_year, budget_month)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_monthly_budget_status ON monthly_budgets(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_budget_items_category ON monthly_budget_items(category_id, subcategory_id)')
        
        # Recurring patterns indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_recurring_patterns_account ON recurring_patterns(account_number)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_recurring_patterns_active ON recurring_patterns(is_active)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_recurring_patterns_payee ON recurring_patterns(payee)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_recurring_patterns_next_date ON recurring_patterns(next_expected_date)')
        
        # Payee extraction patterns indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_payee_patterns_active ON payee_extraction_patterns(is_active)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_payee_patterns_usage ON payee_extraction_patterns(usage_count DESC)')
        
        # QIF reconciliation indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_qif_recon_file ON qif_reconciliation_log(qif_file_path)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_qif_recon_status ON qif_reconciliation_log(reconciliation_status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_qif_recon_hash ON qif_reconciliation_log(qif_transaction_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_qif_category_mappings_quicken ON qif_category_mappings(quicken_category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_qif_category_mappings_usage ON qif_category_mappings(usage_count DESC)')
        
        conn.commit()
        conn.close()
    
    # Quicken Reconciliation Methods
    
    def check_qif_transaction_processed(self, qif_hash: str) -> Optional[Dict]:
        """Check if a QIF transaction has already been processed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT qif_file_path, batch_number, reconciliation_status, 
                       matched_transaction_id, reconciled_at
                FROM qif_reconciliation_log 
                WHERE qif_transaction_hash = ?
            ''', (qif_hash,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'qif_file_path': result[0],
                    'batch_number': result[1],
                    'status': result[2],
                    'matched_transaction_id': result[3],
                    'reconciled_at': result[4]
                }
            return None
            
        except Exception as e:
            print(f"Error checking QIF transaction: {e}")
            return None
        finally:
            conn.close()
    
    def find_similar_transactions(self, date: str, amount: float, payee: str = "", 
                                tolerance_days: int = 3) -> List[Dict]:
        """Find similar transactions in the main database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Convert date string to date object for comparison
            from datetime import datetime, timedelta
            search_date = datetime.fromisoformat(date).date()
            start_date = search_date - timedelta(days=tolerance_days)
            end_date = search_date + timedelta(days=tolerance_days)
            
            # Search for similar transactions
            cursor.execute('''
                SELECT id, run_date, amount, payee, action, description, 
                       account_number, category_id, subcategory_id
                FROM transactions 
                WHERE DATE(run_date) BETWEEN ? AND ?
                AND ABS(amount - ?) < 0.01
                AND (payee LIKE ? OR action LIKE ? OR description LIKE ?)
                ORDER BY run_date DESC
                LIMIT 10
            ''', (start_date.isoformat(), end_date.isoformat(), amount, 
                  f"%{payee}%", f"%{payee}%", f"%{payee}%"))
            
            results = cursor.fetchall()
            similar = []
            
            for row in results:
                similar.append({
                    'id': row[0],
                    'date': row[1],
                    'amount': row[2],
                    'payee': row[3],
                    'action': row[4],
                    'description': row[5],
                    'account': row[6],
                    'category_id': row[7],
                    'subcategory_id': row[8]
                })
            
            return similar
            
        except Exception as e:
            print(f"Error finding similar transactions: {e}")
            return []
        finally:
            conn.close()
    
    def log_qif_transaction(self, qif_file_path: str, batch_number: int, 
                          qif_transaction: Dict, qif_hash: str, 
                          status: str = 'pending') -> bool:
        """Log a QIF transaction for reconciliation tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO qif_reconciliation_log 
                (qif_file_path, batch_number, qif_transaction_hash, qif_date, 
                 qif_amount, qif_payee, qif_category, qif_memo, reconciliation_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                qif_file_path, batch_number, qif_hash, qif_transaction['date'],
                qif_transaction['amount'], qif_transaction.get('payee'),
                qif_transaction.get('category'), qif_transaction.get('memo'),
                status
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error logging QIF transaction: {e}")
            return False
        finally:
            conn.close()
    
    def save_category_mapping(self, quicken_category: str, quicken_subcategory: str,
                            app_category_id: int, app_subcategory_id: int = None,
                            confidence: float = 1.0, mapping_type: str = 'llm_learned') -> bool:
        """Save a learned category mapping rule"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO qif_category_mappings 
                (quicken_category, quicken_subcategory, app_category_id, 
                 app_subcategory_id, confidence, mapping_type, usage_count, 
                 last_used, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 
                        COALESCE((SELECT usage_count FROM qif_category_mappings 
                                WHERE quicken_category = ? AND quicken_subcategory = ?), 0) + 1,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (
                quicken_category, quicken_subcategory, app_category_id,
                app_subcategory_id, confidence, mapping_type,
                quicken_category, quicken_subcategory
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error saving category mapping: {e}")
            return False
        finally:
            conn.close()
    
    def get_category_mapping(self, quicken_category: str, quicken_subcategory: str = None) -> Optional[Dict]:
        """Get existing category mapping for a Quicken category"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT app_category_id, app_subcategory_id, confidence, mapping_type
                FROM qif_category_mappings 
                WHERE quicken_category = ? 
                AND (quicken_subcategory = ? OR (quicken_subcategory IS NULL AND ? IS NULL))
                ORDER BY confidence DESC, usage_count DESC
                LIMIT 1
            ''', (quicken_category, quicken_subcategory, quicken_subcategory))
            
            result = cursor.fetchone()
            if result:
                return {
                    'app_category_id': result[0],
                    'app_subcategory_id': result[1],
                    'confidence': result[2],
                    'mapping_type': result[3]
                }
            return None
            
        except Exception as e:
            print(f"Error getting category mapping: {e}")
            return None
        finally:
            conn.close()
    
    def get_reconciliation_progress(self, qif_file_path: str = None) -> Dict:
        """Get reconciliation progress summary"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            where_clause = ""
            params = []
            if qif_file_path:
                where_clause = "WHERE qif_file_path = ?"
                params.append(qif_file_path)
            
            cursor.execute(f'''
                SELECT reconciliation_status, COUNT(*) 
                FROM qif_reconciliation_log 
                {where_clause}
                GROUP BY reconciliation_status
            ''', params)
            
            status_counts = dict(cursor.fetchall())
            
            # Get category mapping stats
            cursor.execute('SELECT COUNT(*) FROM qif_category_mappings')
            mapping_count = cursor.fetchone()[0]
            
            return {
                'transaction_counts': status_counts,
                'total_transactions': sum(status_counts.values()),
                'category_mappings_learned': mapping_count,
                'completion_rate': (status_counts.get('imported', 0) + 
                                  status_counts.get('matched', 0) + 
                                  status_counts.get('skipped', 0)) / 
                                 sum(status_counts.values()) if status_counts else 0
            }
            
        except Exception as e:
            print(f"Error getting reconciliation progress: {e}")
            return {}
        finally:
            conn.close()
    
    def get_all_categories(self) -> List[Tuple]:
        """Get all categories with subcategories for reconciliation context"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT c.id, c.name, s.id, s.name
                FROM categories c
                LEFT JOIN subcategories s ON c.id = s.category_id
                ORDER BY c.name, s.name
            ''')
            
            return cursor.fetchall()
            
        except Exception as e:
            print(f"Error getting categories: {e}")
            return []
        finally:
            conn.close()
    
    def get_recent_payees(self, limit: int = 100) -> List[str]:
        """Get recent payees for reconciliation context"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT DISTINCT payee
                FROM transactions 
                WHERE payee IS NOT NULL AND payee != ''
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
            
            return [row[0] for row in cursor.fetchall()]
            
        except Exception as e:
            print(f"Error getting payees: {e}")
            return []
        finally:
            conn.close()
    
    def enhance_existing_transaction(self, transaction_id: int, enhancements: Dict, 
                                   qif_hash: str, notes: str = None) -> bool:
        """Apply enhancements to an existing transaction and log the changes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get current transaction state for audit
            cursor.execute('SELECT payee, note, category_id, subcategory_id FROM transactions WHERE id = ?', 
                          (transaction_id,))
            current_state = cursor.fetchone()
            if not current_state:
                return False
            
            current_payee, current_memo, current_cat_id, current_sub_id = current_state
            
            # Apply enhancements
            update_fields = []
            update_values = []
            changes_made = {}
            
            if 'payee' in enhancements:
                update_fields.append('payee = ?')
                update_values.append(enhancements['payee']['to'])
                changes_made['payee'] = {
                    'from': current_payee,
                    'to': enhancements['payee']['to'],
                    'reason': enhancements['payee']['reason']
                }
            
            if 'memo' in enhancements:
                update_fields.append('note = ?')  # Assuming note field stores memo
                update_values.append(enhancements['memo']['to'])
                changes_made['memo'] = {
                    'from': current_memo,
                    'to': enhancements['memo']['to'],
                    'reason': enhancements['memo']['reason']
                }
            
            if 'category' in enhancements:
                cat_info = enhancements['category']['to']
                update_fields.append('category_id = ?')
                update_values.append(cat_info['app_category_id'])
                changes_made['category_id'] = {
                    'from': current_cat_id,
                    'to': cat_info['app_category_id'],
                    'reason': enhancements['category']['reason']
                }
                
                if cat_info.get('app_subcategory_id'):
                    update_fields.append('subcategory_id = ?')
                    update_values.append(cat_info['app_subcategory_id'])
                    changes_made['subcategory_id'] = {
                        'from': current_sub_id,
                        'to': cat_info['app_subcategory_id'],
                        'reason': enhancements['category']['reason']
                    }
            
            if not update_fields:
                return False
            
            # Update transaction
            update_values.append(transaction_id)
            update_sql = f"UPDATE transactions SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(update_sql, update_values)
            
            # Log the enhancement in QIF reconciliation log
            import json
            decision_json = json.dumps({
                'action': 'enhance_existing',
                'transaction_id': transaction_id,
                'changes_applied': changes_made,
                'timestamp': self._get_current_timestamp()
            })
            
            # Get the original transaction date and amount for logging
            cursor.execute('SELECT run_date, amount FROM transactions WHERE id = ?', (transaction_id,))
            txn_info = cursor.fetchone()
            txn_date, txn_amount = txn_info if txn_info else ('1970-01-01', 0.0)
            
            cursor.execute('''
                INSERT INTO qif_reconciliation_log 
                (qif_file_path, batch_number, qif_transaction_hash, qif_date, 
                 qif_amount, reconciliation_status, matched_transaction_id, 
                 import_decision, notes, reconciled_at, reconciled_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            ''', (
                'interactive_session',  # qif_file_path
                1,  # batch_number - we'll track interactive sessions as batch 1
                qif_hash,
                txn_date,  # qif_date - use original transaction date
                txn_amount,  # qif_amount - use original transaction amount
                'pending',  # reconciliation_status - use 'pending' since 'enhanced' not in constraint
                transaction_id,  # matched_transaction_id
                decision_json,  # import_decision
                notes or f"Enhanced via interactive reconciliation: {', '.join(changes_made.keys())}",  # notes
                'claude_code_interactive'  # reconciled_by
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error enhancing transaction {transaction_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def generate_transaction_hash(self, transaction: Dict) -> str:
        """Generate a unique hash for a transaction to detect duplicates"""
        # Use key fields that should uniquely identify a transaction
        run_date = transaction.get('run_date', '')
        hash_data = f"{run_date}-{transaction.get('account_number', '')}-{transaction.get('action', '')}-{transaction.get('amount', 0)}-{transaction.get('description', '')}"
        return hashlib.md5(hash_data.encode()).hexdigest()
    
    def insert_transaction(self, transaction: Dict, source_file: str) -> bool:
        """Insert a transaction if it doesn't already exist"""
        transaction_hash = self.generate_transaction_hash(transaction)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO transactions (
                    run_date, account, account_number, action, symbol, description,
                    type, exchange_quantity, exchange_currency, quantity, currency,
                    price, exchange_rate, commission, fees, accrued_interest,
                    amount, settlement_date, payee, category_id, subcategory_id, note, hash, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                transaction.get('run_date'),
                transaction.get('account'),
                transaction.get('account_number'),
                transaction.get('action'),
                transaction.get('symbol'),
                transaction.get('description'),
                transaction.get('type'),
                transaction.get('exchange_quantity'),
                transaction.get('exchange_currency'),
                transaction.get('quantity'),
                transaction.get('currency'),
                transaction.get('price'),
                transaction.get('exchange_rate'),
                transaction.get('commission'),
                transaction.get('fees'),
                transaction.get('accrued_interest'),
                transaction.get('amount'),
                transaction.get('settlement_date'),
                transaction.get('payee'),
                transaction.get('category_id'),
                transaction.get('subcategory_id'),
                transaction.get('note'),
                transaction_hash,
                source_file
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Duplicate transaction
            return False
        finally:
            conn.close()
    
    def mark_file_processed(self, filename: str, file_hash: str, record_count: int):
        """Mark a file as processed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO processed_files (filename, file_hash, record_count)
            VALUES (?, ?, ?)
        ''', (filename, file_hash, record_count))
        
        conn.commit()
        conn.close()
    
    def is_file_processed(self, filename: str, file_hash: str) -> bool:
        """Check if a file has already been processed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 1 FROM processed_files 
            WHERE filename = ? AND file_hash = ?
        ''', (filename, file_hash))
        
        result = cursor.fetchone() is not None
        conn.close()
        return result
    
    def get_transaction_count(self) -> int:
        """Get total number of transactions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM transactions')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    def get_account_summary(self) -> List[Tuple]:
        """Get summary by account"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT account, account_number, COUNT(*) as transaction_count, 
                   SUM(amount) as total_amount
            FROM transactions 
            GROUP BY account, account_number
            ORDER BY account
        ''')
        
        results = cursor.fetchall()
        conn.close()
        return results
    
    def learn_classification_pattern(self, pattern: str, pattern_type: str, 
                                   category_id: int, subcategory_id: int = None, 
                                   confidence: float = 0.8) -> bool:
        """Learn a new classification pattern or update existing one"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if pattern exists
            cursor.execute('''
                SELECT id, usage_count FROM classification_patterns 
                WHERE pattern = ? AND pattern_type = ?
            ''', (pattern, pattern_type))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing pattern
                pattern_id, usage_count = existing
                cursor.execute('''
                    UPDATE classification_patterns 
                    SET usage_count = ?, last_used = CURRENT_TIMESTAMP,
                        confidence = MAX(confidence, ?),
                        category_id = ?, subcategory_id = ?
                    WHERE id = ?
                ''', (usage_count + 1, confidence, category_id, subcategory_id, pattern_id))
            else:
                # Create new pattern
                cursor.execute('''
                    INSERT INTO classification_patterns 
                    (pattern, pattern_type, category_id, subcategory_id, confidence)
                    VALUES (?, ?, ?, ?, ?)
                ''', (pattern, pattern_type, category_id, subcategory_id, confidence))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error learning pattern: {e}")
            return False
        finally:
            conn.close()
    
    def find_matching_pattern(self, description: str, action: str, payee: str = None) -> Optional[Tuple]:
        """Find a matching classification pattern for transaction text"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get all patterns ordered by confidence and usage
            cursor.execute('''
                SELECT p.pattern, p.pattern_type, p.category_id, p.subcategory_id, 
                       p.confidence, c.name as category_name, s.name as subcategory_name
                FROM classification_patterns p
                JOIN categories c ON p.category_id = c.id
                LEFT JOIN subcategories s ON p.subcategory_id = s.id
                ORDER BY p.confidence DESC, p.usage_count DESC
            ''')
            
            patterns = cursor.fetchall()
            
            # Check each pattern against the transaction text
            for pattern, pattern_type, cat_id, sub_id, confidence, cat_name, sub_name in patterns:
                text_to_check = ""
                
                if pattern_type == "description":
                    text_to_check = description.lower()
                elif pattern_type == "action":
                    text_to_check = action.lower()
                elif pattern_type == "both":
                    text_to_check = f"{description} {action}".lower()
                
                if pattern.lower() in text_to_check:
                    # Update usage count
                    cursor.execute('''
                        UPDATE classification_patterns 
                        SET usage_count = usage_count + 1, 
                            last_used = CURRENT_TIMESTAMP 
                        WHERE pattern = ? AND pattern_type = ?
                    ''', (pattern, pattern_type))
                    conn.commit()
                    
                    return (cat_id, sub_id, confidence, cat_name, sub_name)
            
            return None
            
        except Exception as e:
            print(f"Error finding pattern match: {e}")
            return None
        finally:
            conn.close()
    
    def extract_and_learn_patterns(self, description: str, action: str, 
                                 category_id: int, subcategory_id: int = None,
                                 confidence: float = 0.8):
        """Extract useful patterns from a classified transaction and learn them"""
        patterns_learned = []
        
        # Extract patterns from description
        desc_patterns = self._extract_patterns_from_text(description)
        for pattern in desc_patterns:
            if self.learn_classification_pattern(pattern, "description", category_id, subcategory_id, confidence):
                patterns_learned.append(f"description:{pattern}")
        
        # Extract patterns from action  
        action_patterns = self._extract_patterns_from_text(action)
        for pattern in action_patterns:
            if self.learn_classification_pattern(pattern, "action", category_id, subcategory_id, confidence):
                patterns_learned.append(f"action:{pattern}")
        
        return patterns_learned
    
    def _extract_patterns_from_text(self, text: str) -> List[str]:
        """Extract useful patterns from transaction text"""
        if not text:
            return []
        
        patterns = []
        text_upper = text.upper()
        
        # Common merchant patterns
        merchant_keywords = [
            "AMAZON", "STARBUCKS", "WALMART", "TARGET", "CVS", "WALGREENS",
            "MCDONALD", "BURGER KING", "SUBWAY", "PIZZA", "SHELL", "EXXON",
            "CHEVRON", "BP", "HOME DEPOT", "LOWES", "COSTCO", "KROGER",
            "SAFEWAY", "PUBLIX", "NETFLIX", "SPOTIFY", "UBER", "LYFT"
        ]
        
        for keyword in merchant_keywords:
            if keyword in text_upper:
                patterns.append(keyword)
        
        # Investment-specific patterns
        investment_keywords = [
            "DIVIDEND", "ETF", "FUND", "CORP", "INC", "BOUGHT", "SOLD",
            "SHARE", "STOCK", "MUTUAL", "BOND", "REIT"
        ]
        
        for keyword in investment_keywords:
            if keyword in text_upper:
                patterns.append(keyword)
        
        # Extract domain names (Amazon.com, etc.)
        import re
        domains = re.findall(r'([a-zA-Z0-9-]+\.[a-zA-Z]{2,})', text)
        for domain in domains:
            patterns.append(domain.lower())
        
        # Extract specific merchant codes/names
        # Look for patterns like "DEBIT CARD PURCHASE [MERCHANT]"
        merchant_match = re.search(r'PURCHASE\s+([A-Z][A-Z0-9\s&.]+?)(?:\s+\d|\s+[A-Z]{2}\d|$)', text_upper)
        if merchant_match:
            merchant = merchant_match.group(1).strip()
            if len(merchant) > 3 and merchant not in patterns:
                patterns.append(merchant)
        
        return patterns[:5]  # Limit to top 5 patterns per text
    
    def get_pattern_stats(self) -> List[Tuple]:
        """Get statistics about learned patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT p.pattern, p.pattern_type, c.name as category, 
                   COALESCE(s.name, '') as subcategory,
                   p.confidence, p.usage_count, p.created_at, p.last_used
            FROM classification_patterns p
            JOIN categories c ON p.category_id = c.id
            LEFT JOIN subcategories s ON p.subcategory_id = s.id
            ORDER BY p.usage_count DESC, p.confidence DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_or_create_category(self, category_name: str) -> int:
        """Get category ID or create new category"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('INSERT OR IGNORE INTO categories (name) VALUES (?)', (category_name,))
            cursor.execute('SELECT id FROM categories WHERE name = ?', (category_name,))
            category_id = cursor.fetchone()[0]
            conn.commit()
            return category_id
        finally:
            conn.close()
    
    def get_or_create_subcategory(self, category_id: int, subcategory_name: str) -> int:
        """Get subcategory ID or create new subcategory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO subcategories (category_id, name) 
                VALUES (?, ?)
            ''', (category_id, subcategory_name))
            cursor.execute('''
                SELECT id FROM subcategories 
                WHERE category_id = ? AND name = ?
            ''', (category_id, subcategory_name))
            subcategory_id = cursor.fetchone()[0]
            conn.commit()
            return subcategory_id
        finally:
            conn.close()
    
    def update_transaction_category(self, transaction_id: int, category: str = None, 
                                  subcategory: str = None, note: str = None) -> bool:
        """Update category, subcategory, and/or note for a specific transaction"""
        try:
            updates = []
            values = []
            
            category_id = None
            subcategory_id = None
            
            if category is not None:
                category_id = self.get_or_create_category(category)
                updates.append("category_id = ?")
                values.append(category_id)
                
                if subcategory is not None:
                    subcategory_id = self.get_or_create_subcategory(category_id, subcategory)
                    updates.append("subcategory_id = ?")
                    values.append(subcategory_id)
            elif subcategory is not None:
                print("Error: Cannot set subcategory without category")
                return False
                
            if note is not None:
                updates.append("note = ?")
                values.append(note)
            
            if not updates:
                return False
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            values.append(transaction_id)
            sql = f"UPDATE transactions SET {', '.join(updates)} WHERE id = ?"
            
            cursor.execute(sql, values)
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            print(f"Error updating transaction: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def update_transaction_payee(self, transaction_id: int, payee: str) -> bool:
        """Update payee for a specific transaction"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("UPDATE transactions SET payee = ? WHERE id = ?", (payee, transaction_id))
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            print(f"Error updating transaction payee: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def bulk_categorize_by_description(self, description_pattern: str, category: str, 
                                     subcategory: str = None, case_sensitive: bool = False) -> int:
        """Bulk categorize transactions based on description pattern"""
        conn = None
        try:
            # Get or create category and subcategory IDs
            category_id = self.get_or_create_category(category)
            subcategory_id = None
            if subcategory is not None:
                subcategory_id = self.get_or_create_subcategory(category_id, subcategory)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if case_sensitive:
                where_clause = "description LIKE ?"
            else:
                where_clause = "LOWER(description) LIKE LOWER(?)"
            
            pattern_value = f"%{description_pattern}%"
            values = [category_id]
            updates = ["category_id = ?"]
            
            if subcategory_id is not None:
                updates.append("subcategory_id = ?")
                values.append(subcategory_id)
            
            values.append(pattern_value)
            
            sql = f"UPDATE transactions SET {', '.join(updates)} WHERE {where_clause}"
            cursor.execute(sql, values)
            
            rowcount = cursor.rowcount
            conn.commit()
            conn.close()
            conn = None  # Mark as closed
            
            # Learn pattern from this bulk categorization (after closing connection)
            self.learn_classification_pattern(description_pattern, "description", category_id, subcategory_id, 0.8)
            
            return rowcount
            
        except Exception as e:
            print(f"Error bulk categorizing by description: {e}")
            return 0
        finally:
            if conn:
                conn.close()
    
    def bulk_categorize_by_action(self, action_pattern: str, category: str, 
                                subcategory: str = None, case_sensitive: bool = False) -> int:
        """Bulk categorize transactions based on action pattern"""
        conn = None
        try:
            # Get or create category and subcategory IDs
            category_id = self.get_or_create_category(category)
            subcategory_id = None
            if subcategory is not None:
                subcategory_id = self.get_or_create_subcategory(category_id, subcategory)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if case_sensitive:
                where_clause = "action LIKE ?"
            else:
                where_clause = "LOWER(action) LIKE LOWER(?)"
            
            pattern_value = f"%{action_pattern}%"
            values = [category_id]
            updates = ["category_id = ?"]
            
            if subcategory_id is not None:
                updates.append("subcategory_id = ?")
                values.append(subcategory_id)
            
            values.append(pattern_value)
            
            sql = f"UPDATE transactions SET {', '.join(updates)} WHERE {where_clause}"
            cursor.execute(sql, values)
            
            rowcount = cursor.rowcount
            conn.commit()
            conn.close()
            conn = None  # Mark as closed
            
            # Learn pattern from this bulk categorization (after closing connection)
            self.learn_classification_pattern(action_pattern, "action", category_id, subcategory_id, 0.8)
            
            return rowcount
            
        except Exception as e:
            print(f"Error bulk categorizing by action: {e}")
            return 0
        finally:
            if conn:
                conn.close()
    
    def get_transactions_by_category(self, category: str = None, subcategory: str = None) -> List[Tuple]:
        """Get transactions filtered by category and/or subcategory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        where_conditions = []
        values = []
        joins = []
        
        if category is not None or subcategory is not None:
            joins.append("LEFT JOIN categories c ON t.category_id = c.id")
            joins.append("LEFT JOIN subcategories s ON t.subcategory_id = s.id")
            
            if category is not None:
                where_conditions.append("c.name = ?")
                values.append(category)
            if subcategory is not None:
                where_conditions.append("s.name = ?")
                values.append(subcategory)
        
        join_clause = " ".join(joins)
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        cursor.execute(f'''
            SELECT t.id, t.run_date, t.account, t.description, t.amount, 
                   c.name as category, s.name as subcategory, t.note
            FROM transactions t {join_clause} {where_clause}
            ORDER BY t.run_date DESC
        ''', values)
        
        results = cursor.fetchall()
        conn.close()
        return results
    
    def learn_classification_pattern(self, pattern: str, pattern_type: str, 
                                   category_id: int, subcategory_id: int = None, 
                                   confidence: float = 0.8) -> bool:
        """Learn a new classification pattern or update existing one"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if pattern exists
            cursor.execute('''
                SELECT id, usage_count FROM classification_patterns 
                WHERE pattern = ? AND pattern_type = ?
            ''', (pattern, pattern_type))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing pattern
                pattern_id, usage_count = existing
                cursor.execute('''
                    UPDATE classification_patterns 
                    SET usage_count = ?, last_used = CURRENT_TIMESTAMP,
                        confidence = MAX(confidence, ?),
                        category_id = ?, subcategory_id = ?
                    WHERE id = ?
                ''', (usage_count + 1, confidence, category_id, subcategory_id, pattern_id))
            else:
                # Create new pattern
                cursor.execute('''
                    INSERT INTO classification_patterns 
                    (pattern, pattern_type, category_id, subcategory_id, confidence)
                    VALUES (?, ?, ?, ?, ?)
                ''', (pattern, pattern_type, category_id, subcategory_id, confidence))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error learning pattern: {e}")
            return False
        finally:
            conn.close()
    
    def find_matching_pattern(self, description: str, action: str, payee: str = None) -> Optional[Tuple]:
        """Find a matching classification pattern for transaction text"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get all patterns ordered by confidence and usage
            cursor.execute('''
                SELECT p.pattern, p.pattern_type, p.category_id, p.subcategory_id, 
                       p.confidence, c.name as category_name, s.name as subcategory_name
                FROM classification_patterns p
                JOIN categories c ON p.category_id = c.id
                LEFT JOIN subcategories s ON p.subcategory_id = s.id
                ORDER BY p.confidence DESC, p.usage_count DESC
            ''')
            
            patterns = cursor.fetchall()
            
            # Check each pattern against the transaction text
            for pattern, pattern_type, cat_id, sub_id, confidence, cat_name, sub_name in patterns:
                text_to_check = ""
                
                if pattern_type == "description":
                    text_to_check = description.lower()
                elif pattern_type == "action":
                    text_to_check = action.lower()
                elif pattern_type == "both":
                    text_to_check = f"{description} {action}".lower()
                
                if pattern.lower() in text_to_check:
                    # Update usage count
                    cursor.execute('''
                        UPDATE classification_patterns 
                        SET usage_count = usage_count + 1, 
                            last_used = CURRENT_TIMESTAMP 
                        WHERE pattern = ? AND pattern_type = ?
                    ''', (pattern, pattern_type))
                    conn.commit()
                    
                    return (cat_id, sub_id, confidence, cat_name, sub_name)
            
            return None
            
        except Exception as e:
            print(f"Error finding pattern match: {e}")
            return None
        finally:
            conn.close()
    
    def extract_and_learn_patterns(self, description: str, action: str, 
                                 category_id: int, subcategory_id: int = None,
                                 confidence: float = 0.8):
        """Extract useful patterns from a classified transaction and learn them"""
        patterns_learned = []
        
        # Extract patterns from description
        desc_patterns = self._extract_patterns_from_text(description)
        for pattern in desc_patterns:
            if self.learn_classification_pattern(pattern, "description", category_id, subcategory_id, confidence):
                patterns_learned.append(f"description:{pattern}")
        
        # Extract patterns from action  
        action_patterns = self._extract_patterns_from_text(action)
        for pattern in action_patterns:
            if self.learn_classification_pattern(pattern, "action", category_id, subcategory_id, confidence):
                patterns_learned.append(f"action:{pattern}")
        
        return patterns_learned
    
    def _extract_patterns_from_text(self, text: str) -> List[str]:
        """Extract useful patterns from transaction text"""
        if not text:
            return []
        
        patterns = []
        text_upper = text.upper()
        
        # Common merchant patterns
        merchant_keywords = [
            "AMAZON", "STARBUCKS", "WALMART", "TARGET", "CVS", "WALGREENS",
            "MCDONALD", "BURGER KING", "SUBWAY", "PIZZA", "SHELL", "EXXON",
            "CHEVRON", "BP", "HOME DEPOT", "LOWES", "COSTCO", "KROGER",
            "SAFEWAY", "PUBLIX", "NETFLIX", "SPOTIFY", "UBER", "LYFT"
        ]
        
        for keyword in merchant_keywords:
            if keyword in text_upper:
                patterns.append(keyword)
        
        # Investment-specific patterns
        investment_keywords = [
            "DIVIDEND", "ETF", "FUND", "CORP", "INC", "BOUGHT", "SOLD",
            "SHARE", "STOCK", "MUTUAL", "BOND", "REIT"
        ]
        
        for keyword in investment_keywords:
            if keyword in text_upper:
                patterns.append(keyword)
        
        # Extract domain names (Amazon.com, etc.)
        import re
        domains = re.findall(r'([a-zA-Z0-9-]+\.[a-zA-Z]{2,})', text)
        for domain in domains:
            patterns.append(domain.lower())
        
        # Extract specific merchant codes/names
        # Look for patterns like "DEBIT CARD PURCHASE [MERCHANT]"
        merchant_match = re.search(r'PURCHASE\s+([A-Z][A-Z0-9\s&.]+?)(?:\s+\d|\s+[A-Z]{2}\d|$)', text_upper)
        if merchant_match:
            merchant = merchant_match.group(1).strip()
            if len(merchant) > 3 and merchant not in patterns:
                patterns.append(merchant)
        
        return patterns[:5]  # Limit to top 5 patterns per text
    
    def get_pattern_stats(self) -> List[Tuple]:
        """Get statistics about learned patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT p.pattern, p.pattern_type, c.name as category, 
                   COALESCE(s.name, '') as subcategory,
                   p.confidence, p.usage_count, p.created_at, p.last_used
            FROM classification_patterns p
            JOIN categories c ON p.category_id = c.id
            LEFT JOIN subcategories s ON p.subcategory_id = s.id
            ORDER BY p.usage_count DESC, p.confidence DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_category_summary(self) -> List[Tuple]:
        """Get spending summary by category"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COALESCE(c.name, 'Uncategorized') as category,
                COALESCE(s.name, '') as subcategory,
                COUNT(*) as transaction_count,
                SUM(t.amount) as total_amount,
                AVG(t.amount) as avg_amount
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN subcategories s ON t.subcategory_id = s.id
            GROUP BY c.name, s.name
            ORDER BY total_amount DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        return results
    
    def learn_classification_pattern(self, pattern: str, pattern_type: str, 
                                   category_id: int, subcategory_id: int = None, 
                                   confidence: float = 0.8) -> bool:
        """Learn a new classification pattern or update existing one"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if pattern exists
            cursor.execute('''
                SELECT id, usage_count FROM classification_patterns 
                WHERE pattern = ? AND pattern_type = ?
            ''', (pattern, pattern_type))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing pattern
                pattern_id, usage_count = existing
                cursor.execute('''
                    UPDATE classification_patterns 
                    SET usage_count = ?, last_used = CURRENT_TIMESTAMP,
                        confidence = MAX(confidence, ?),
                        category_id = ?, subcategory_id = ?
                    WHERE id = ?
                ''', (usage_count + 1, confidence, category_id, subcategory_id, pattern_id))
            else:
                # Create new pattern
                cursor.execute('''
                    INSERT INTO classification_patterns 
                    (pattern, pattern_type, category_id, subcategory_id, confidence)
                    VALUES (?, ?, ?, ?, ?)
                ''', (pattern, pattern_type, category_id, subcategory_id, confidence))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error learning pattern: {e}")
            return False
        finally:
            conn.close()
    
    def find_matching_pattern(self, description: str, action: str, payee: str = None) -> Optional[Tuple]:
        """Find a matching classification pattern for transaction text"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get all patterns ordered by confidence and usage
            cursor.execute('''
                SELECT p.pattern, p.pattern_type, p.category_id, p.subcategory_id, 
                       p.confidence, c.name as category_name, s.name as subcategory_name
                FROM classification_patterns p
                JOIN categories c ON p.category_id = c.id
                LEFT JOIN subcategories s ON p.subcategory_id = s.id
                ORDER BY p.confidence DESC, p.usage_count DESC
            ''')
            
            patterns = cursor.fetchall()
            
            # Check each pattern against the transaction text
            for pattern, pattern_type, cat_id, sub_id, confidence, cat_name, sub_name in patterns:
                text_to_check = ""
                
                if pattern_type == "description":
                    text_to_check = description.lower()
                elif pattern_type == "action":
                    text_to_check = action.lower()
                elif pattern_type == "both":
                    text_to_check = f"{description} {action}".lower()
                
                if pattern.lower() in text_to_check:
                    # Update usage count
                    cursor.execute('''
                        UPDATE classification_patterns 
                        SET usage_count = usage_count + 1, 
                            last_used = CURRENT_TIMESTAMP 
                        WHERE pattern = ? AND pattern_type = ?
                    ''', (pattern, pattern_type))
                    conn.commit()
                    
                    return (cat_id, sub_id, confidence, cat_name, sub_name)
            
            return None
            
        except Exception as e:
            print(f"Error finding pattern match: {e}")
            return None
        finally:
            conn.close()
    
    def extract_and_learn_patterns(self, description: str, action: str, 
                                 category_id: int, subcategory_id: int = None,
                                 confidence: float = 0.8):
        """Extract useful patterns from a classified transaction and learn them"""
        patterns_learned = []
        
        # Extract patterns from description
        desc_patterns = self._extract_patterns_from_text(description)
        for pattern in desc_patterns:
            if self.learn_classification_pattern(pattern, "description", category_id, subcategory_id, confidence):
                patterns_learned.append(f"description:{pattern}")
        
        # Extract patterns from action  
        action_patterns = self._extract_patterns_from_text(action)
        for pattern in action_patterns:
            if self.learn_classification_pattern(pattern, "action", category_id, subcategory_id, confidence):
                patterns_learned.append(f"action:{pattern}")
        
        return patterns_learned
    
    def _extract_patterns_from_text(self, text: str) -> List[str]:
        """Extract useful patterns from transaction text"""
        if not text:
            return []
        
        patterns = []
        text_upper = text.upper()
        
        # Common merchant patterns
        merchant_keywords = [
            "AMAZON", "STARBUCKS", "WALMART", "TARGET", "CVS", "WALGREENS",
            "MCDONALD", "BURGER KING", "SUBWAY", "PIZZA", "SHELL", "EXXON",
            "CHEVRON", "BP", "HOME DEPOT", "LOWES", "COSTCO", "KROGER",
            "SAFEWAY", "PUBLIX", "NETFLIX", "SPOTIFY", "UBER", "LYFT"
        ]
        
        for keyword in merchant_keywords:
            if keyword in text_upper:
                patterns.append(keyword)
        
        # Investment-specific patterns
        investment_keywords = [
            "DIVIDEND", "ETF", "FUND", "CORP", "INC", "BOUGHT", "SOLD",
            "SHARE", "STOCK", "MUTUAL", "BOND", "REIT"
        ]
        
        for keyword in investment_keywords:
            if keyword in text_upper:
                patterns.append(keyword)
        
        # Extract domain names (Amazon.com, etc.)
        import re
        domains = re.findall(r'([a-zA-Z0-9-]+\.[a-zA-Z]{2,})', text)
        for domain in domains:
            patterns.append(domain.lower())
        
        # Extract specific merchant codes/names
        # Look for patterns like "DEBIT CARD PURCHASE [MERCHANT]"
        merchant_match = re.search(r'PURCHASE\s+([A-Z][A-Z0-9\s&.]+?)(?:\s+\d|\s+[A-Z]{2}\d|$)', text_upper)
        if merchant_match:
            merchant = merchant_match.group(1).strip()
            if len(merchant) > 3 and merchant not in patterns:
                patterns.append(merchant)
        
        return patterns[:5]  # Limit to top 5 patterns per text
    
    def get_pattern_stats(self) -> List[Tuple]:
        """Get statistics about learned patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT p.pattern, p.pattern_type, c.name as category, 
                   COALESCE(s.name, '') as subcategory,
                   p.confidence, p.usage_count, p.created_at, p.last_used
            FROM classification_patterns p
            JOIN categories c ON p.category_id = c.id
            LEFT JOIN subcategories s ON p.subcategory_id = s.id
            ORDER BY p.usage_count DESC, p.confidence DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_uncategorized_transactions(self, limit: int = None) -> List[Tuple]:
        """Get transactions that haven't been categorized yet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        cursor.execute(f'''
            SELECT id, run_date, account, description, amount, action, payee
            FROM transactions 
            WHERE category_id IS NULL
            ORDER BY run_date DESC
            {limit_clause}
        ''')
        
        results = cursor.fetchall()
        conn.close()
        return results
    
    def learn_classification_pattern(self, pattern: str, pattern_type: str, 
                                   category_id: int, subcategory_id: int = None, 
                                   confidence: float = 0.8) -> bool:
        """Learn a new classification pattern or update existing one"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if pattern exists
            cursor.execute('''
                SELECT id, usage_count FROM classification_patterns 
                WHERE pattern = ? AND pattern_type = ?
            ''', (pattern, pattern_type))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing pattern
                pattern_id, usage_count = existing
                cursor.execute('''
                    UPDATE classification_patterns 
                    SET usage_count = ?, last_used = CURRENT_TIMESTAMP,
                        confidence = MAX(confidence, ?),
                        category_id = ?, subcategory_id = ?
                    WHERE id = ?
                ''', (usage_count + 1, confidence, category_id, subcategory_id, pattern_id))
            else:
                # Create new pattern
                cursor.execute('''
                    INSERT INTO classification_patterns 
                    (pattern, pattern_type, category_id, subcategory_id, confidence)
                    VALUES (?, ?, ?, ?, ?)
                ''', (pattern, pattern_type, category_id, subcategory_id, confidence))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error learning pattern: {e}")
            return False
        finally:
            conn.close()
    
    def find_matching_pattern(self, description: str, action: str, payee: str = None) -> Optional[Tuple]:
        """Find a matching classification pattern for transaction text"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get all patterns ordered by confidence and usage
            cursor.execute('''
                SELECT p.pattern, p.pattern_type, p.category_id, p.subcategory_id, 
                       p.confidence, c.name as category_name, s.name as subcategory_name
                FROM classification_patterns p
                JOIN categories c ON p.category_id = c.id
                LEFT JOIN subcategories s ON p.subcategory_id = s.id
                ORDER BY p.confidence DESC, p.usage_count DESC
            ''')
            
            patterns = cursor.fetchall()
            
            # Check each pattern against the transaction text
            for pattern, pattern_type, cat_id, sub_id, confidence, cat_name, sub_name in patterns:
                text_to_check = ""
                
                if pattern_type == "description":
                    text_to_check = description.lower()
                elif pattern_type == "action":
                    text_to_check = action.lower()
                elif pattern_type == "both":
                    text_to_check = f"{description} {action}".lower()
                
                if pattern.lower() in text_to_check:
                    # Update usage count
                    cursor.execute('''
                        UPDATE classification_patterns 
                        SET usage_count = usage_count + 1, 
                            last_used = CURRENT_TIMESTAMP 
                        WHERE pattern = ? AND pattern_type = ?
                    ''', (pattern, pattern_type))
                    conn.commit()
                    
                    return (cat_id, sub_id, confidence, cat_name, sub_name)
            
            return None
            
        except Exception as e:
            print(f"Error finding pattern match: {e}")
            return None
        finally:
            conn.close()
    
    def extract_and_learn_patterns(self, description: str, action: str, 
                                 category_id: int, subcategory_id: int = None,
                                 confidence: float = 0.8):
        """Extract useful patterns from a classified transaction and learn them"""
        patterns_learned = []
        
        # Extract patterns from description
        desc_patterns = self._extract_patterns_from_text(description)
        for pattern in desc_patterns:
            if self.learn_classification_pattern(pattern, "description", category_id, subcategory_id, confidence):
                patterns_learned.append(f"description:{pattern}")
        
        # Extract patterns from action  
        action_patterns = self._extract_patterns_from_text(action)
        for pattern in action_patterns:
            if self.learn_classification_pattern(pattern, "action", category_id, subcategory_id, confidence):
                patterns_learned.append(f"action:{pattern}")
        
        return patterns_learned
    
    def _extract_patterns_from_text(self, text: str) -> List[str]:
        """Extract useful patterns from transaction text"""
        if not text:
            return []
        
        patterns = []
        text_upper = text.upper()
        
        # Common merchant patterns
        merchant_keywords = [
            "AMAZON", "STARBUCKS", "WALMART", "TARGET", "CVS", "WALGREENS",
            "MCDONALD", "BURGER KING", "SUBWAY", "PIZZA", "SHELL", "EXXON",
            "CHEVRON", "BP", "HOME DEPOT", "LOWES", "COSTCO", "KROGER",
            "SAFEWAY", "PUBLIX", "NETFLIX", "SPOTIFY", "UBER", "LYFT"
        ]
        
        for keyword in merchant_keywords:
            if keyword in text_upper:
                patterns.append(keyword)
        
        # Investment-specific patterns
        investment_keywords = [
            "DIVIDEND", "ETF", "FUND", "CORP", "INC", "BOUGHT", "SOLD",
            "SHARE", "STOCK", "MUTUAL", "BOND", "REIT"
        ]
        
        for keyword in investment_keywords:
            if keyword in text_upper:
                patterns.append(keyword)
        
        # Extract domain names (Amazon.com, etc.)
        import re
        domains = re.findall(r'([a-zA-Z0-9-]+\.[a-zA-Z]{2,})', text)
        for domain in domains:
            patterns.append(domain.lower())
        
        # Extract specific merchant codes/names
        # Look for patterns like "DEBIT CARD PURCHASE [MERCHANT]"
        merchant_match = re.search(r'PURCHASE\s+([A-Z][A-Z0-9\s&.]+?)(?:\s+\d|\s+[A-Z]{2}\d|$)', text_upper)
        if merchant_match:
            merchant = merchant_match.group(1).strip()
            if len(merchant) > 3 and merchant not in patterns:
                patterns.append(merchant)
        
        return patterns[:5]  # Limit to top 5 patterns per text
    
    def get_pattern_stats(self) -> List[Tuple]:
        """Get statistics about learned patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT p.pattern, p.pattern_type, c.name as category, 
                   COALESCE(s.name, '') as subcategory,
                   p.confidence, p.usage_count, p.created_at, p.last_used
            FROM classification_patterns p
            JOIN categories c ON p.category_id = c.id
            LEFT JOIN subcategories s ON p.subcategory_id = s.id
            ORDER BY p.usage_count DESC, p.confidence DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        return results
    
    def normalize_account_data(self, account: str, account_number: str) -> tuple:
        """Normalize account name and number using same logic as CSV parser"""
        import re
        
        if not account:
            return account, account_number
        
        # Extract account number from account name if it's embedded
        account_num_patterns = [
            r'\(([Z]?\d+)\)',  # Match (Z23693697) or (239574793)
            r'\s+([Z]?\d+)\s+\(\)',  # Match Z06431462 ()
            r'\s+([Z]?\d+)$',  # Match trailing Z06431462
        ]
        
        extracted_number = None
        clean_account = account.strip()
        
        for pattern in account_num_patterns:
            match = re.search(pattern, account)
            if match:
                extracted_number = match.group(1)
                # Remove the matched pattern from account name
                clean_account = re.sub(pattern, '', account).strip()
                break
        
        # Use extracted number if we found one, otherwise use provided account_number
        final_account_number = extracted_number or account_number or ''
        
        # Clean up account name
        clean_account = re.sub(r'\s+', ' ', clean_account)  # Normalize whitespace
        clean_account = clean_account.strip()
        
        return clean_account, final_account_number
    
    # Budget Management Methods
    
    def create_budget_template(self, name: str, description: str = None) -> int:
        """Create a new budget template and return its ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO budget_templates (name, description)
                VALUES (?, ?)
            ''', (name, description))
            
            template_id = cursor.lastrowid
            conn.commit()
            return template_id
            
        except Exception as e:
            print(f"Error creating budget template: {e}")
            return None
        finally:
            conn.close()
    
    def add_budget_template_item(self, template_id: int, category: str, subcategory: str = None, 
                                budget_amount: float = 0.0, budget_type: str = 'expense') -> int:
        """Add a category/subcategory item to a budget template"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get or create category and subcategory IDs
            category_id = self.get_or_create_category(category)
            subcategory_id = None
            if subcategory:
                subcategory_id = self.get_or_create_subcategory(category_id, subcategory)
            
            cursor.execute('''
                INSERT INTO budget_template_items 
                (template_id, category_id, subcategory_id, budget_amount, budget_type)
                VALUES (?, ?, ?, ?, ?)
            ''', (template_id, category_id, subcategory_id, budget_amount, budget_type))
            
            item_id = cursor.lastrowid
            conn.commit()
            return item_id
            
        except Exception as e:
            print(f"Error adding budget template item: {e}")
            return None
        finally:
            conn.close()
    
    def create_monthly_budget(self, template_id: int, year: int, month: int) -> int:
        """Create a monthly budget instance from a template"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Create monthly budget record
            cursor.execute('''
                INSERT INTO monthly_budgets (template_id, budget_year, budget_month, status)
                VALUES (?, ?, ?, 'active')
            ''', (template_id, year, month))
            
            monthly_budget_id = cursor.lastrowid
            
            # Copy template items to monthly budget items
            cursor.execute('''
                INSERT INTO monthly_budget_items 
                (monthly_budget_id, category_id, subcategory_id, budgeted_amount, budget_type)
                SELECT ?, bti.category_id, bti.subcategory_id, bti.budget_amount, bti.budget_type
                FROM budget_template_items bti
                WHERE bti.template_id = ?
            ''', (monthly_budget_id, template_id))
            
            conn.commit()
            return monthly_budget_id
            
        except Exception as e:
            print(f"Error creating monthly budget: {e}")
            return None
        finally:
            conn.close()
    
    def get_monthly_budget(self, year: int, month: int, template_id: int = None) -> Optional[Tuple]:
        """Get monthly budget for a specific year/month"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if template_id:
                cursor.execute('''
                    SELECT id, template_id, budget_year, budget_month, status, created_at
                    FROM monthly_budgets
                    WHERE budget_year = ? AND budget_month = ? AND template_id = ?
                ''', (year, month, template_id))
            else:
                cursor.execute('''
                    SELECT id, template_id, budget_year, budget_month, status, created_at
                    FROM monthly_budgets
                    WHERE budget_year = ? AND budget_month = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (year, month))
            
            result = cursor.fetchone()
            return result
            
        except Exception as e:
            print(f"Error getting monthly budget: {e}")
            return None
        finally:
            conn.close()
    
    def get_monthly_budget_items(self, monthly_budget_id: int) -> List[Tuple]:
        """Get all budget items for a monthly budget"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT mbi.id, mbi.budgeted_amount, mbi.actual_amount, mbi.budget_type,
                       c.name as category, s.name as subcategory
                FROM monthly_budget_items mbi
                JOIN categories c ON mbi.category_id = c.id
                LEFT JOIN subcategories s ON mbi.subcategory_id = s.id
                WHERE mbi.monthly_budget_id = ?
                ORDER BY c.name, s.name
            ''', (monthly_budget_id,))
            
            results = cursor.fetchall()
            return results
            
        except Exception as e:
            print(f"Error getting monthly budget items: {e}")
            return []
        finally:
            conn.close()
    
    def update_actual_amounts(self, year: int, month: int) -> int:
        """Update actual amounts for all budget items in a given month"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get monthly budget for this year/month
            monthly_budget = self.get_monthly_budget(year, month)
            if not monthly_budget:
                return 0
            
            monthly_budget_id = monthly_budget[0]
            
            # Update actual amounts for expense items
            cursor.execute('''
                UPDATE monthly_budget_items 
                SET actual_amount = (
                    SELECT COALESCE(SUM(ABS(t.amount)), 0)
                    FROM transactions t
                    WHERE t.category_id = monthly_budget_items.category_id
                    AND (monthly_budget_items.subcategory_id IS NULL OR t.subcategory_id = monthly_budget_items.subcategory_id)
                    AND strftime('%Y', t.run_date) = ?
                    AND strftime('%m', t.run_date) = ?
                    AND t.amount < 0
                ),
                last_calculated_at = CURRENT_TIMESTAMP
                WHERE monthly_budget_id = ? AND budget_type = 'expense'
            ''', (str(year), f"{month:02d}", monthly_budget_id))
            
            # Update actual amounts for income items
            cursor.execute('''
                UPDATE monthly_budget_items 
                SET actual_amount = (
                    SELECT COALESCE(SUM(ABS(t.amount)), 0)
                    FROM transactions t
                    WHERE t.category_id = monthly_budget_items.category_id
                    AND (monthly_budget_items.subcategory_id IS NULL OR t.subcategory_id = monthly_budget_items.subcategory_id)
                    AND strftime('%Y', t.run_date) = ?
                    AND strftime('%m', t.run_date) = ?
                    AND t.amount > 0
                ),
                last_calculated_at = CURRENT_TIMESTAMP
                WHERE monthly_budget_id = ? AND budget_type = 'income'
            ''', (str(year), f"{month:02d}", monthly_budget_id))
            
            updated_rows = cursor.rowcount
            conn.commit()
            return updated_rows
            
        except Exception as e:
            print(f"Error updating actual amounts: {e}")
            return 0
        finally:
            conn.close()
    
    def calculate_historical_average(self, category_id: int, subcategory_id: int = None, 
                                   target_year: int = None, target_month: int = None, 
                                   lookback_months: int = 12) -> Optional[Dict]:
        """Calculate 12-month rolling average for budget auto-calculation with data smoothing
        
        Args:
            category_id: Category ID to analyze
            subcategory_id: Optional subcategory ID (None for entire category)
            target_year: Year to calculate for (defaults to current year)
            target_month: Month to calculate for (defaults to current month)
            lookback_months: Number of months to look back (default 12)
            
        Returns:
            Dict with 'amount', 'confidence', 'months_used', 'outliers_removed' or None if insufficient data
        """
        if target_year is None or target_month is None:
            now = datetime.now()
            target_year = target_year or now.year
            target_month = target_month or now.month
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Generate list of (year, month) tuples for the lookback period
            months_to_check = []
            current_year, current_month = target_year, target_month
            
            for _ in range(lookback_months):
                current_month -= 1
                if current_month < 1:
                    current_month = 12
                    current_year -= 1
                months_to_check.append((current_year, current_month))
            
            # Get monthly spending amounts for each month
            monthly_amounts = []
            for year, month in months_to_check:
                cursor.execute('''
                    SELECT COALESCE(SUM(ABS(t.amount)), 0) as monthly_total
                    FROM transactions t
                    WHERE t.category_id = ?
                    AND (? IS NULL OR t.subcategory_id = ?)
                    AND strftime('%Y', t.run_date) = ?
                    AND strftime('%m', t.run_date) = ?
                    AND t.amount != 0
                ''', (category_id, subcategory_id, subcategory_id, str(year), f"{month:02d}"))
                
                result = cursor.fetchone()
                amount = result[0] if result else 0
                if amount > 0:  # Only include months with actual spending
                    monthly_amounts.append(amount)
            
            # Require minimum data points for reliability
            if len(monthly_amounts) < 3:
                return None
            
            # Calculate basic statistics
            monthly_amounts.sort()
            n = len(monthly_amounts)
            
            # Calculate median and quartiles for outlier detection
            if n % 2 == 0:
                median = (monthly_amounts[n//2 - 1] + monthly_amounts[n//2]) / 2
            else:
                median = monthly_amounts[n//2]
            
            q1_idx = n // 4
            q3_idx = 3 * n // 4
            q1 = monthly_amounts[q1_idx]
            q3 = monthly_amounts[q3_idx]
            iqr = q3 - q1
            
            # Remove outliers using IQR method (1.5 * IQR)
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            cleaned_amounts = [amt for amt in monthly_amounts 
                             if lower_bound <= amt <= upper_bound]
            
            # Calculate smoothed average
            if len(cleaned_amounts) >= 2:
                average = sum(cleaned_amounts) / len(cleaned_amounts)
                outliers_removed = len(monthly_amounts) - len(cleaned_amounts)
            else:
                # If too many outliers removed, use original data
                average = sum(monthly_amounts) / len(monthly_amounts)
                outliers_removed = 0
                cleaned_amounts = monthly_amounts
            
            # Calculate confidence based on data availability and consistency
            months_used = len(monthly_amounts)
            data_consistency = 1.0 - (outliers_removed / months_used) if months_used > 0 else 0
            sample_confidence = min(months_used / 6.0, 1.0)  # 6+ months = full confidence
            confidence = (data_consistency + sample_confidence) / 2
            
            return {
                'amount': round(average, 2),
                'confidence': round(confidence, 2),
                'months_used': months_used,
                'outliers_removed': outliers_removed,
                'median': round(median, 2),
                'raw_amounts': monthly_amounts
            }
            
        except Exception as e:
            print(f"Error calculating historical average: {e}")
            return None
        finally:
            conn.close()
    
    def update_budget_item_amount(self, monthly_budget_item_id: int, new_amount: float) -> bool:
        """Update the budgeted amount for a specific budget item
        
        Args:
            monthly_budget_item_id: ID of the monthly budget item to update
            new_amount: New budgeted amount
            
        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE monthly_budget_items
                SET budgeted_amount = ?
                WHERE id = ?
            ''', (new_amount, monthly_budget_item_id))
            
            success = cursor.rowcount > 0
            conn.commit()
            return success
            
        except Exception as e:
            print(f"Error updating budget item amount: {e}")
            return False
        finally:
            conn.close()
    
    def get_default_template_id(self) -> Optional[int]:
        """Get the default template ID (first active template)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id FROM budget_templates 
                WHERE is_active = 1 
                ORDER BY created_at ASC 
                LIMIT 1
            ''')
            
            result = cursor.fetchone()
            return result[0] if result else None
            
        except Exception as e:
            print(f"Error getting default template: {e}")
            return None
        finally:
            conn.close()
    
    # Recurring Pattern Detection Methods
    
    def detect_recurring_patterns(self, account_number: str = None, lookback_days: int = 365, 
                                min_occurrences: int = 3) -> List[Dict]:
        """
        Detect recurring transaction patterns using multi-pass algorithm
        
        Args:
            account_number: Specific account to analyze (None for all accounts)
            lookback_days: How far back to analyze transactions
            min_occurrences: Minimum occurrences to consider a pattern
            
        Returns:
            List of detected patterns with confidence scores
        """
        from datetime import datetime, timedelta
        import statistics
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Calculate cutoff date
            cutoff_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
            
            # Get existing saved patterns to avoid duplicates
            existing_patterns_query = '''
                SELECT DISTINCT payee, account_number, typical_amount, frequency_type
                FROM recurring_patterns 
                WHERE is_active = 1
            '''
            if account_number:
                existing_patterns_query += ' AND account_number = ?'
                existing_patterns = cursor.execute(existing_patterns_query, (account_number,)).fetchall()
            else:
                existing_patterns = cursor.execute(existing_patterns_query).fetchall()
            
            # Create a set of existing pattern keys for quick lookup
            existing_pattern_keys = set()
            for pattern in existing_patterns:
                # Create a key based on payee, account, and approximate amount (within $1)
                payee_key = pattern['payee'].lower().strip() if pattern['payee'] else ''
                account_key = pattern['account_number']
                amount_key = round(float(pattern['typical_amount']), 0)  # Round to nearest dollar
                freq_key = pattern['frequency_type']
                existing_pattern_keys.add((payee_key, account_key, amount_key, freq_key))
            
            # Get transactions for analysis
            where_clause = "WHERE run_date >= ?"
            params = [cutoff_date]
            
            if account_number:
                where_clause += " AND account_number = ?"
                params.append(account_number)
            
            cursor.execute(f'''
                SELECT id, run_date, account_number, payee, amount, action, description,
                       category_id, subcategory_id
                FROM transactions
                {where_clause}
                AND payee IS NOT NULL 
                AND payee != ''
                AND (symbol IS NULL OR symbol = '')
                AND action NOT LIKE '%YOU BOUGHT%'
                AND action NOT LIKE '%YOU SOLD%' 
                AND action NOT LIKE '%DIVIDEND RECEIVED%'
                AND action NOT LIKE '%REINVESTMENT%'
                ORDER BY run_date ASC
            ''', params)
            
            transactions = cursor.fetchall()
            detected_patterns = []
            
            # Pass 1: Exact amount matching
            exact_patterns = self._detect_exact_amount_patterns(transactions, min_occurrences)
            detected_patterns.extend(exact_patterns)
            
            # Pass 2: Fuzzy amount matching (for varying bills)
            fuzzy_patterns = self._detect_fuzzy_amount_patterns(transactions, min_occurrences, exact_patterns)
            detected_patterns.extend(fuzzy_patterns)
            
            # Pass 3: Date pattern analysis
            date_patterns = self._detect_date_patterns(transactions, min_occurrences, 
                                                     exact_patterns + fuzzy_patterns)
            detected_patterns.extend(date_patterns)
            
            # Filter out patterns that already exist
            filtered_patterns = []
            for pattern in detected_patterns:
                if not self._pattern_already_exists(pattern, existing_pattern_keys):
                    filtered_patterns.append(pattern)
            
            return filtered_patterns
            
        except Exception as e:
            print(f"Error detecting recurring patterns: {e}")
            return []
        finally:
            conn.close()
    
    def _pattern_already_exists(self, pattern: Dict, existing_keys: set) -> bool:
        """Check if a detected pattern already exists in saved patterns"""
        payee_key = pattern['payee'].lower().strip() if pattern['payee'] else ''
        account_key = pattern['account_number']
        amount_key = round(float(pattern['typical_amount']), 0)  # Round to nearest dollar
        freq_key = pattern['frequency_type']
        
        pattern_key = (payee_key, account_key, amount_key, freq_key)
        return pattern_key in existing_keys
    
    def _detect_exact_amount_patterns(self, transactions: List, min_occurrences: int) -> List[Dict]:
        """Pass 1: Detect patterns with exact amount matches"""
        from collections import defaultdict
        from datetime import datetime, timedelta
        import statistics
        
        # Group by payee + exact amount
        groups = defaultdict(list)
        for tx in transactions:
            tx_id, run_date, account_number, payee, amount, action, description, category_id, subcategory_id = tx
            key = (payee.lower().strip(), float(amount))
            groups[key].append({
                'id': tx_id,
                'date': datetime.strptime(run_date, '%Y-%m-%d'),
                'account_number': account_number,
                'payee': payee,
                'amount': float(amount),
                'action': action,
                'description': description,
                'category_id': category_id,
                'subcategory_id': subcategory_id
            })
        
        patterns = []
        for (payee, amount), occurrences in groups.items():
            if len(occurrences) < min_occurrences:
                continue
                
            # Calculate intervals between occurrences
            dates = sorted([occ['date'] for occ in occurrences])
            intervals = []
            for i in range(1, len(dates)):
                interval = (dates[i] - dates[i-1]).days
                intervals.append(interval)
            
            if not intervals:
                continue
                
            # Determine frequency pattern
            avg_interval = statistics.mean(intervals)
            interval_std = statistics.stdev(intervals) if len(intervals) > 1 else 0
            
            frequency_type, confidence = self._classify_frequency(avg_interval, interval_std)
            if confidence < 0.3:  # Skip low-confidence patterns
                continue
                
            # Calculate next expected date
            last_date = max(dates)
            next_expected = last_date + timedelta(days=int(avg_interval))
            
            # Ensure next expected date is in the future
            today = datetime.now().date()
            while next_expected.date() <= today:
                next_expected = next_expected + timedelta(days=int(avg_interval))
            
            pattern = {
                'pattern_name': f"{payee} - ${abs(amount):.2f} ({frequency_type})",
                'account_number': occurrences[0]['account_number'],
                'payee': payee,
                'typical_amount': abs(amount),
                'amount_variance': 0.0,  # Exact match
                'frequency_type': frequency_type,
                'frequency_interval': 1,
                'next_expected_date': next_expected.strftime('%Y-%m-%d'),
                'last_occurrence_date': last_date.strftime('%Y-%m-%d'),
                'confidence': confidence,
                'occurrence_count': len(occurrences),
                'category_id': occurrences[0]['category_id'],
                'subcategory_id': occurrences[0]['subcategory_id'],
                'pattern_type': 'exact_amount',
                'raw_intervals': intervals
            }
            patterns.append(pattern)
        
        return patterns
    
    def _detect_fuzzy_amount_patterns(self, transactions: List, min_occurrences: int, 
                                    existing_patterns: List[Dict]) -> List[Dict]:
        """Pass 2: Detect patterns with varying amounts (utilities, credit cards)"""
        from collections import defaultdict
        from datetime import datetime, timedelta
        import statistics
        
        # Skip transactions already matched in exact patterns
        existing_payees = {p['payee'].lower().strip() for p in existing_patterns}
        
        # Group by payee only (allowing amount variance)
        groups = defaultdict(list)
        for tx in transactions:
            tx_id, run_date, account_number, payee, amount, action, description, category_id, subcategory_id = tx
            payee_key = payee.lower().strip()
            
            if payee_key in existing_payees:
                continue  # Skip already detected exact patterns
                
            groups[payee_key].append({
                'id': tx_id,
                'date': datetime.strptime(run_date, '%Y-%m-%d'),
                'account_number': account_number,
                'payee': payee,
                'amount': float(amount),
                'action': action,
                'description': description,
                'category_id': category_id,
                'subcategory_id': subcategory_id
            })
        
        patterns = []
        for payee, occurrences in groups.items():
            if len(occurrences) < min_occurrences:
                continue
            
            # Analyze amount variance
            amounts = [abs(occ['amount']) for occ in occurrences]
            avg_amount = statistics.mean(amounts)
            amount_std = statistics.stdev(amounts) if len(amounts) > 1 else 0
            amount_cv = amount_std / avg_amount if avg_amount > 0 else 1  # Coefficient of variation
            
            # Skip if amounts vary too much (>50% CV typically indicates non-recurring)
            if amount_cv > 0.5:
                continue
            
            # Calculate date intervals
            dates = sorted([occ['date'] for occ in occurrences])
            intervals = []
            for i in range(1, len(dates)):
                interval = (dates[i] - dates[i-1]).days
                intervals.append(interval)
            
            if not intervals:
                continue
                
            avg_interval = statistics.mean(intervals)
            interval_std = statistics.stdev(intervals) if len(intervals) > 1 else 0
            
            frequency_type, base_confidence = self._classify_frequency(avg_interval, interval_std)
            if base_confidence < 0.3:
                continue
            
            # Reduce confidence for fuzzy patterns
            confidence = base_confidence * (1 - min(amount_cv, 0.3))  # Penalize amount variance
            
            if confidence < 0.4:  # Higher threshold for fuzzy patterns
                continue
            
            last_date = max(dates)
            next_expected = last_date + timedelta(days=int(avg_interval))
            
            # Ensure next expected date is in the future
            today = datetime.now().date()
            while next_expected.date() <= today:
                next_expected = next_expected + timedelta(days=int(avg_interval))
            
            pattern = {
                'pattern_name': f"{occurrences[0]['payee']} - ~${avg_amount:.2f} ({frequency_type})",
                'account_number': occurrences[0]['account_number'],
                'payee': occurrences[0]['payee'],
                'typical_amount': avg_amount,
                'amount_variance': amount_std,
                'frequency_type': frequency_type,
                'frequency_interval': 1,
                'next_expected_date': next_expected.strftime('%Y-%m-%d'),
                'last_occurrence_date': last_date.strftime('%Y-%m-%d'),
                'confidence': confidence,
                'occurrence_count': len(occurrences),
                'category_id': occurrences[0]['category_id'],
                'subcategory_id': occurrences[0]['subcategory_id'],
                'pattern_type': 'fuzzy_amount',
                'amount_cv': amount_cv,
                'raw_intervals': intervals
            }
            patterns.append(pattern)
        
        return patterns
    
    def _detect_date_patterns(self, transactions: List, min_occurrences: int, 
                            existing_patterns: List[Dict]) -> List[Dict]:
        """Pass 3: Detect day-of-month patterns (rent on 1st, salary on 15th)"""
        from collections import defaultdict
        from datetime import datetime, timedelta
        import statistics
        
        existing_payees = {p['payee'].lower().strip() for p in existing_patterns}
        
        # Group by payee + day of month
        day_groups = defaultdict(list)
        for tx in transactions:
            tx_id, run_date, account_number, payee, amount, action, description, category_id, subcategory_id = tx
            payee_key = payee.lower().strip()
            
            if payee_key in existing_payees:
                continue
                
            date_obj = datetime.strptime(run_date, '%Y-%m-%d')
            day_of_month = date_obj.day
            
            # Group by day of month (allowing ±2 days variance)
            for day_range in range(max(1, day_of_month-2), min(32, day_of_month+3)):
                key = (payee_key, day_range)
                day_groups[key].append({
                    'id': tx_id,
                    'date': date_obj,
                    'account_number': account_number,
                    'payee': payee,
                    'amount': float(amount),
                    'action': action,
                    'description': description,
                    'category_id': category_id,
                    'subcategory_id': subcategory_id,
                    'day_of_month': day_of_month
                })
        
        patterns = []
        for (payee, target_day), occurrences in day_groups.items():
            if len(occurrences) < min_occurrences:
                continue
            
            # Check if occurrences actually cluster around target day
            actual_days = [occ['day_of_month'] for occ in occurrences]
            day_variance = statistics.stdev(actual_days) if len(actual_days) > 1 else 0
            
            if day_variance > 3:  # Too much day variance
                continue
            
            # Check if roughly monthly intervals
            dates = sorted([occ['date'] for occ in occurrences])
            intervals = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
            
            if not intervals:
                continue
                
            avg_interval = statistics.mean(intervals)
            # Look for monthly patterns (25-35 days)
            if not (25 <= avg_interval <= 35):
                continue
            
            amounts = [abs(occ['amount']) for occ in occurrences]
            avg_amount = statistics.mean(amounts)
            amount_std = statistics.stdev(amounts) if len(amounts) > 1 else 0
            
            # Higher confidence for consistent day-of-month patterns
            day_consistency = 1 - (day_variance / 10)  # Normalize day variance
            interval_consistency = 1 - abs(30 - avg_interval) / 10  # Closeness to 30 days
            confidence = min(day_consistency * interval_consistency * 0.8, 0.9)
            
            if confidence < 0.5:
                continue
            
            last_date = max(dates)
            # Project to same day next month
            next_month = last_date.replace(day=1) + timedelta(days=32)
            next_month = next_month.replace(day=1)  # First of next month
            try:
                next_expected = next_month.replace(day=int(statistics.mean(actual_days)))
            except ValueError:
                # Handle end-of-month edge cases
                next_expected = next_month + timedelta(days=27)
            
            # Ensure next expected date is in the future
            today = datetime.now().date()
            while next_expected.date() <= today:
                # Move to same day next month
                try:
                    next_month = next_expected.replace(day=1) + timedelta(days=32)
                    next_month = next_month.replace(day=1)
                    next_expected = next_month.replace(day=int(statistics.mean(actual_days)))
                except ValueError:
                    next_expected = next_expected + timedelta(days=30)  # Fallback
            
            pattern = {
                'pattern_name': f"{occurrences[0]['payee']} - Day {int(statistics.mean(actual_days))} (monthly)",
                'account_number': occurrences[0]['account_number'],
                'payee': occurrences[0]['payee'],
                'typical_amount': avg_amount,
                'amount_variance': amount_std,
                'frequency_type': 'monthly',
                'frequency_interval': 1,
                'next_expected_date': next_expected.strftime('%Y-%m-%d'),
                'last_occurrence_date': last_date.strftime('%Y-%m-%d'),
                'confidence': confidence,
                'occurrence_count': len(occurrences),
                'category_id': occurrences[0]['category_id'],
                'subcategory_id': occurrences[0]['subcategory_id'],
                'pattern_type': 'day_of_month',
                'typical_day': int(statistics.mean(actual_days)),
                'day_variance': day_variance
            }
            patterns.append(pattern)
        
        return patterns
    
    def _classify_frequency(self, avg_interval: float, interval_std: float) -> Tuple[str, float]:
        """Classify frequency type based on average interval and calculate confidence"""
        
        # Define frequency ranges with some tolerance
        frequency_ranges = [
            ('weekly', 7, 2),      # 5-9 days
            ('biweekly', 14, 3),   # 11-17 days
            ('monthly', 30, 5),    # 25-35 days
            ('quarterly', 90, 15), # 75-105 days
            ('annual', 365, 30),   # 335-395 days
        ]
        
        best_match = None
        best_confidence = 0
        
        for freq_type, target_days, tolerance in frequency_ranges:
            if abs(avg_interval - target_days) <= tolerance:
                # Calculate confidence based on how close to target and how consistent
                distance_factor = 1 - (abs(avg_interval - target_days) / tolerance)
                consistency_factor = 1 - min(interval_std / target_days, 0.5)  # Cap at 50% penalty
                confidence = distance_factor * consistency_factor * 0.9  # Max 90% confidence
                
                if confidence > best_confidence:
                    best_match = freq_type
                    best_confidence = confidence
        
        return best_match or 'irregular', best_confidence
    
    def save_recurring_pattern(self, pattern: Dict) -> int:
        """Save a detected recurring pattern to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO recurring_patterns (
                    pattern_name, account_number, payee, category_id, subcategory_id,
                    typical_amount, amount_variance, frequency_type, frequency_interval,
                    next_expected_date, last_occurrence_date, confidence, occurrence_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                pattern['pattern_name'],
                pattern['account_number'],
                pattern['payee'],
                pattern.get('category_id'),
                pattern.get('subcategory_id'),
                pattern['typical_amount'],
                pattern['amount_variance'],
                pattern['frequency_type'],
                pattern['frequency_interval'],
                pattern['next_expected_date'],
                pattern['last_occurrence_date'],
                pattern['confidence'],
                pattern['occurrence_count']
            ))
            
            pattern_id = cursor.lastrowid
            conn.commit()
            return pattern_id
            
        except Exception as e:
            print(f"Error saving recurring pattern: {e}")
            return None
        finally:
            conn.close()
    
    def get_recurring_patterns(self, account_number: str = None, active_only: bool = True) -> List[Tuple]:
        """Get stored recurring patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            where_conditions = []
            params = []
            
            if account_number:
                where_conditions.append("account_number = ?")
                params.append(account_number)
                
            if active_only:
                where_conditions.append("is_active = 1")
            
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            cursor.execute(f'''
                SELECT rp.id, rp.pattern_name, rp.account_number, rp.payee, rp.typical_amount, 
                       rp.amount_variance, rp.frequency_type, rp.frequency_interval,
                       rp.next_expected_date, rp.last_occurrence_date, rp.confidence,
                       rp.occurrence_count, rp.is_active, rp.created_at,
                       c.name as category, s.name as subcategory
                FROM recurring_patterns rp
                LEFT JOIN categories c ON rp.category_id = c.id
                LEFT JOIN subcategories s ON rp.subcategory_id = s.id
                {where_clause}
                ORDER BY rp.confidence DESC, rp.occurrence_count DESC
            ''', params)
            
            results = cursor.fetchall()
            return results
            
        except Exception as e:
            print(f"Error getting recurring patterns: {e}")
            return []
        finally:
            conn.close()
    
    def update_pattern_next_date(self, pattern_id: int, next_date: str) -> bool:
        """Update the next expected date for a recurring pattern"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE recurring_patterns 
                SET next_expected_date = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (next_date, pattern_id))
            
            success = cursor.rowcount > 0
            conn.commit()
            return success
            
        except Exception as e:
            print(f"Error updating pattern next date: {e}")
            return False
        finally:
            conn.close()
    
    def update_pattern(self, pattern_id: int, updates: Dict) -> bool:
        """Update multiple fields of a recurring pattern"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Build dynamic update query
            allowed_fields = {
                'pattern_name', 'typical_amount', 'amount_variance', 
                'frequency_type', 'frequency_interval', 'next_expected_date',
                'is_active', 'confidence'
            }
            
            # Filter to only allowed fields
            filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
            
            if not filtered_updates:
                return False
                
            # Build SET clause
            set_clauses = []
            values = []
            
            for field, value in filtered_updates.items():
                set_clauses.append(f"{field} = ?")
                values.append(value)
            
            # Always update the timestamp
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(pattern_id)
            
            query = f'''
                UPDATE recurring_patterns 
                SET {', '.join(set_clauses)}
                WHERE id = ?
            '''
            
            cursor.execute(query, values)
            success = cursor.rowcount > 0
            conn.commit()
            return success
            
        except Exception as e:
            print(f"Error updating pattern: {e}")
            return False
        finally:
            conn.close()

    def deactivate_pattern(self, pattern_id: int) -> bool:
        """Deactivate a recurring pattern"""
        return self.update_pattern(pattern_id, {'is_active': 0})
