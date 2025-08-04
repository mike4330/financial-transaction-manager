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
        
        # Index for faster duplicate detection
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transaction_hash ON transactions(hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_run_date ON transactions(run_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_account ON transactions(account_number)')
        
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
                
                # Step 2: Migrate existing category data
                self._migrate_category_data(cursor)
                
            # Add missing columns for databases that never had categories
            elif 'category_id' not in columns:
                cursor.execute('ALTER TABLE transactions ADD COLUMN category_id INTEGER')
            if 'subcategory_id' not in columns:
                cursor.execute('ALTER TABLE transactions ADD COLUMN subcategory_id INTEGER')
            if 'note' not in columns and 'note' not in columns:
                cursor.execute('ALTER TABLE transactions ADD COLUMN note TEXT')
                
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
    
    def generate_transaction_hash(self, transaction: Dict) -> str:
        """Generate a unique hash for a transaction to detect duplicates"""
        # Use key fields that should uniquely identify a transaction
        hash_data = f"{transaction.get('run_date', '')}-{transaction.get('account_number', '')}-{transaction.get('action', '')}-{transaction.get('amount', 0)}-{transaction.get('description', '')}"
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
                    amount, settlement_date, category_id, subcategory_id, note, hash, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    
    def find_matching_pattern(self, description: str, action: str) -> Optional[Tuple]:
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
    
    def bulk_categorize_by_description(self, description_pattern: str, category: str, 
                                     subcategory: str = None, case_sensitive: bool = False) -> int:
        """Bulk categorize transactions based on description or action pattern"""
        try:
            # Get or create category and subcategory IDs
            category_id = self.get_or_create_category(category)
            subcategory_id = None
            if subcategory is not None:
                subcategory_id = self.get_or_create_subcategory(category_id, subcategory)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if case_sensitive:
                where_clause = "(description LIKE ? OR action LIKE ?)"
            else:
                where_clause = "(LOWER(description) LIKE LOWER(?) OR LOWER(action) LIKE LOWER(?))"
            
            pattern_value = f"%{description_pattern}%"
            values = [category_id]
            updates = ["category_id = ?"]
            
            if subcategory_id is not None:
                updates.append("subcategory_id = ?")
                values.append(subcategory_id)
            
            values.extend([pattern_value, pattern_value])
            
            sql = f"UPDATE transactions SET {', '.join(updates)} WHERE {where_clause}"
            cursor.execute(sql, values)
            
            conn.commit()
            return cursor.rowcount
            
        except Exception as e:
            print(f"Error bulk categorizing: {e}")
            return 0
        finally:
            if 'conn' in locals():
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
    
    def find_matching_pattern(self, description: str, action: str) -> Optional[Tuple]:
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
    
    def find_matching_pattern(self, description: str, action: str) -> Optional[Tuple]:
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
            SELECT id, run_date, account, description, amount, action
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
    
    def find_matching_pattern(self, description: str, action: str) -> Optional[Tuple]:
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