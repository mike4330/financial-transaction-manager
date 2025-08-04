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
        
        # Check if we need to migrate existing database
        self._migrate_database(cursor)
        
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
        
        # Index for faster duplicate detection
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transaction_hash ON transactions(hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_run_date ON transactions(run_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_account ON transactions(account_number)')
        
        # Budget-specific indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_budget_template_active ON budget_templates(is_active)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_monthly_budget_year_month ON monthly_budgets(budget_year, budget_month)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_monthly_budget_status ON monthly_budgets(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_budget_items_category ON monthly_budget_items(category_id, subcategory_id)')
        
        conn.commit()
        conn.close()
    
    def _migrate_database(self, cursor):
        """Migrate existing database to new schema"""
        try:
            # Check if transactions table exists and what columns it has
            cursor.execute("PRAGMA table_info(transactions)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if not columns:  # Table doesn't exist yet
                return
            
            # Check if we need to migrate from old text-based categories to new FK structure
            has_old_category = 'category' in columns and 'category_id' not in columns
            
            if has_old_category:
                # Step 1: Add new columns
                if 'category_id' not in columns:
                    cursor.execute('ALTER TABLE transactions ADD COLUMN category_id INTEGER')
                if 'subcategory_id' not in columns:
                    cursor.execute('ALTER TABLE transactions ADD COLUMN subcategory_id INTEGER')
                if 'note' not in columns:
                    cursor.execute('ALTER TABLE transactions ADD COLUMN note TEXT')
                if 'payee' not in columns:
                    cursor.execute('ALTER TABLE transactions ADD COLUMN payee TEXT')
                
                # Step 2: Migrate existing category data
                self._migrate_category_data(cursor)
                
            # Add missing columns for databases that never had categories
            elif 'category_id' not in columns:
                cursor.execute('ALTER TABLE transactions ADD COLUMN category_id INTEGER')
            if 'subcategory_id' not in columns:
                cursor.execute('ALTER TABLE transactions ADD COLUMN subcategory_id INTEGER')
            if 'note' not in columns:
                cursor.execute('ALTER TABLE transactions ADD COLUMN note TEXT')
            if 'payee' not in columns:
                cursor.execute('ALTER TABLE transactions ADD COLUMN payee TEXT')
            
            # Check if we need to migrate dates from MM/DD/YYYY to ISO format
            self._migrate_date_format(cursor)
                
        except sqlite3.OperationalError as e:
            print(f"Migration error: {e}")
            pass
    
    def _migrate_category_data(self, cursor):
        """Migrate existing text-based category data to normalized tables"""
        # Get all unique category/subcategory combinations
        cursor.execute('''
            SELECT DISTINCT category, subcategory 
            FROM transactions 
            WHERE category IS NOT NULL AND category != ''
        ''')
        
        category_data = cursor.fetchall()
        
        for category_name, subcategory_name in category_data:
            if not category_name:
                continue
                
            # Insert or get category
            cursor.execute('INSERT OR IGNORE INTO categories (name) VALUES (?)', (category_name,))
            cursor.execute('SELECT id FROM categories WHERE name = ?', (category_name,))
            category_id = cursor.fetchone()[0]
            
            subcategory_id = None
            if subcategory_name and subcategory_name.strip():
                # Insert or get subcategory
                cursor.execute('''
                    INSERT OR IGNORE INTO subcategories (category_id, name) 
                    VALUES (?, ?)
                ''', (category_id, subcategory_name))
                cursor.execute('''
                    SELECT id FROM subcategories 
                    WHERE category_id = ? AND name = ?
                ''', (category_id, subcategory_name))
                result = cursor.fetchone()
                if result:
                    subcategory_id = result[0]
            
            # Update transactions with new IDs
            if subcategory_id:
                cursor.execute('''
                    UPDATE transactions 
                    SET category_id = ?, subcategory_id = ?
                    WHERE category = ? AND subcategory = ?
                ''', (category_id, subcategory_id, category_name, subcategory_name))
            else:
                cursor.execute('''
                    UPDATE transactions 
                    SET category_id = ?
                    WHERE category = ? AND (subcategory IS NULL OR subcategory = '')
                ''', (category_id, category_name))
    
    def _migrate_date_format(self, cursor):
        """Migrate MM/DD/YYYY dates to ISO format (YYYY-MM-DD)"""
        try:
            # Check if we have any MM/DD/YYYY format dates
            cursor.execute("SELECT COUNT(*) FROM transactions WHERE run_date LIKE '%/%/%'")
            mm_dd_yyyy_count = cursor.fetchone()[0]
            
            if mm_dd_yyyy_count == 0:
                return  # No dates to migrate
            
            print(f"Migrating {mm_dd_yyyy_count} date records from MM/DD/YYYY to ISO format...")
            
            # Get all transactions with MM/DD/YYYY dates
            cursor.execute("SELECT id, run_date, settlement_date FROM transactions WHERE run_date LIKE '%/%/%'")
            rows = cursor.fetchall()
            
            migrated_count = 0
            error_count = 0
            
            for row_id, run_date, settlement_date in rows:
                try:
                    # Convert run_date
                    iso_run_date = self._convert_date_to_iso(run_date)
                    
                    # Convert settlement_date if it exists
                    iso_settlement_date = None
                    if settlement_date and '/' in settlement_date:
                        iso_settlement_date = self._convert_date_to_iso(settlement_date)
                    elif settlement_date:
                        iso_settlement_date = settlement_date  # Already in ISO format
                    
                    if iso_run_date:
                        cursor.execute('''
                            UPDATE transactions 
                            SET run_date = ?, settlement_date = ?
                            WHERE id = ?
                        ''', (iso_run_date, iso_settlement_date, row_id))
                        migrated_count += 1
                    else:
                        error_count += 1
                        print(f"Could not convert date for transaction ID {row_id}: {run_date}")
                        
                except Exception as e:
                    error_count += 1
                    print(f"Error migrating date for transaction ID {row_id}: {e}")
            
            print(f"Date migration complete: {migrated_count} records migrated, {error_count} errors")
            
        except Exception as e:
            print(f"Date migration error: {e}")
    
    def _convert_date_to_iso(self, date_str: str) -> Optional[str]:
        """Helper function to convert MM/DD/YYYY to YYYY-MM-DD"""
        if not date_str or not date_str.strip():
            return None
        
        try:
            # Parse MM/DD/YYYY format
            date_obj = datetime.strptime(date_str.strip(), '%m/%d/%Y')
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            try:
                # Try alternative format MM/DD/YY
                date_obj = datetime.strptime(date_str.strip(), '%m/%d/%y')
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                return None
    
    def generate_transaction_hash(self, transaction: Dict) -> str:
        """Generate a unique hash for a transaction to detect duplicates"""
        # Normalize date to ISO format for consistent hashing
        run_date = transaction.get('run_date', '')
        if run_date and '/' in run_date:
            # Convert MM/DD/YYYY to YYYY-MM-DD for consistent hashing
            run_date = self._convert_date_to_iso(run_date) or run_date
        
        # Use key fields that should uniquely identify a transaction
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
