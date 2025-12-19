"""
Migration 001: Add split transaction support

Adds:
- transaction_splits table for storing split line items
- is_split column to transactions table
- Indexes for performance
"""

import sqlite3
import sys
from pathlib import Path


def migrate_up(db_path='transactions.db'):
    """Add split transaction support"""
    print(f"Running migration 001_add_splits on {db_path}...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if migration already applied
        cursor.execute("PRAGMA table_info(transactions)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'is_split' in columns:
            print("Migration already applied (is_split column exists)")
            conn.close()
            return True

        # Add is_split column to transactions
        print("Adding is_split column to transactions table...")
        cursor.execute("""
            ALTER TABLE transactions
            ADD COLUMN is_split BOOLEAN DEFAULT 0
        """)

        # Create transaction_splits table
        print("Creating transaction_splits table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transaction_splits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                subcategory_id INTEGER,
                amount REAL NOT NULL,
                note TEXT,
                split_order INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (transaction_id) REFERENCES transactions (id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories (id),
                FOREIGN KEY (subcategory_id) REFERENCES subcategories (id)
            )
        """)

        # Create indexes
        print("Creating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transaction_splits_txn
            ON transaction_splits(transaction_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transaction_splits_category
            ON transaction_splits(category_id, subcategory_id)
        """)

        conn.commit()
        print("Migration 001_add_splits completed successfully!")
        return True

    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def migrate_down(db_path='transactions.db'):
    """Rollback split transaction support"""
    print(f"Rolling back migration 001_add_splits on {db_path}...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Drop splits table
        print("Dropping transaction_splits table...")
        cursor.execute("DROP TABLE IF EXISTS transaction_splits")

        # Note: SQLite doesn't support DROP COLUMN easily in older versions
        # The is_split column will remain but be unused
        print("Note: is_split column remains in transactions table (SQLite limitation)")
        print("It will be ignored and cause no issues.")

        conn.commit()
        print("Rollback completed successfully!")
        return True

    except Exception as e:
        print(f"Rollback failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def verify_migration(db_path='transactions.db'):
    """Verify migration was applied correctly"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check is_split column exists
    cursor.execute("PRAGMA table_info(transactions)")
    columns = [col[1] for col in cursor.fetchall()]
    has_is_split = 'is_split' in columns

    # Check transaction_splits table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='transaction_splits'
    """)
    has_splits_table = cursor.fetchone() is not None

    # Check indexes exist
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='index' AND name LIKE 'idx_transaction_splits%'
    """)
    indexes = cursor.fetchall()
    has_indexes = len(indexes) >= 2

    conn.close()

    print("\nMigration Verification:")
    print(f"  is_split column: {'✓' if has_is_split else '✗'}")
    print(f"  transaction_splits table: {'✓' if has_splits_table else '✗'}")
    print(f"  indexes: {'✓' if has_indexes else '✗'} ({len(indexes)} found)")

    return has_is_split and has_splits_table and has_indexes


if __name__ == '__main__':
    # Default to transactions.db in parent directory
    db_path = Path(__file__).parent.parent / 'transactions.db'

    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'down':
            success = migrate_down(str(db_path))
        elif command == 'verify':
            success = verify_migration(str(db_path))
        else:
            print(f"Unknown command: {command}")
            print("Usage: python 001_add_splits.py [up|down|verify]")
            sys.exit(1)
    else:
        # Default to migrate up
        success = migrate_up(str(db_path))
        if success:
            verify_migration(str(db_path))

    sys.exit(0 if success else 1)
