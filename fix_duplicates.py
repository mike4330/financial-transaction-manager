#!/usr/bin/env python3
"""
Script to fix duplicate detection by regenerating all transaction hashes
and removing duplicates.
"""

import sqlite3
import hashlib
from typing import Dict, Optional
from datetime import datetime

class DuplicateFixer:
    def __init__(self, db_path: str = 'transactions.db'):
        self.db_path = db_path
    
    def _convert_date_to_iso(self, date_str: str) -> Optional[str]:
        """Convert MM/DD/YYYY date format to YYYY-MM-DD (ISO format)"""
        if not date_str or not date_str.strip():
            return None
        try:
            date_obj = datetime.strptime(date_str.strip(), '%m/%d/%Y')
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            try:
                date_obj = datetime.strptime(date_str.strip(), '%m/%d/%y')
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                # Assume it's already in ISO format or handle other formats
                return date_str.strip()
    
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
    
    def regenerate_all_hashes(self):
        """Regenerate hashes for all transactions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get all transactions
            cursor.execute('''
                SELECT id, run_date, account_number, action, amount, description 
                FROM transactions
            ''')
            transactions = cursor.fetchall()
            
            print(f"Regenerating hashes for {len(transactions)} transactions...")
            
            updated_count = 0
            for row in transactions:
                transaction_id, run_date, account_number, action, amount, description = row
                
                # Create transaction dict for hash generation
                transaction = {
                    'run_date': run_date,
                    'account_number': account_number,
                    'action': action,
                    'amount': amount,
                    'description': description
                }
                
                # Generate new hash
                new_hash = self.generate_transaction_hash(transaction)
                
                # Update the hash
                cursor.execute('UPDATE transactions SET hash = ? WHERE id = ?', (new_hash, transaction_id))
                updated_count += 1
                
                if updated_count % 100 == 0:
                    print(f"Updated {updated_count} hashes...")
            
            conn.commit()
            print(f"Hash regeneration complete: {updated_count} transactions updated")
            
        except Exception as e:
            print(f"Error regenerating hashes: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def find_duplicates(self):
        """Find transactions with identical hashes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT hash, COUNT(*) as count, GROUP_CONCAT(id) as ids
                FROM transactions 
                GROUP BY hash 
                HAVING COUNT(*) > 1
                ORDER BY count DESC
            ''')
            
            duplicates = cursor.fetchall()
            print(f"Found {len(duplicates)} sets of duplicate transactions:")
            
            total_duplicates = 0
            for hash_val, count, ids in duplicates:
                total_duplicates += count - 1  # Subtract 1 to keep one copy
                print(f"Hash {hash_val}: {count} copies (IDs: {ids})")
            
            print(f"Total duplicate transactions to remove: {total_duplicates}")
            return duplicates
            
        except Exception as e:
            print(f"Error finding duplicates: {e}")
            return []
        finally:
            conn.close()
    
    def remove_duplicates(self):
        """Remove duplicate transactions, keeping the first occurrence of each"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Find duplicates
            cursor.execute('''
                SELECT hash, MIN(id) as keep_id, GROUP_CONCAT(id) as all_ids, COUNT(*) as count
                FROM transactions 
                GROUP BY hash 
                HAVING COUNT(*) > 1
            ''')
            
            duplicates = cursor.fetchall()
            removed_count = 0
            
            for hash_val, keep_id, all_ids, count in duplicates:
                ids_to_remove = [int(id_str) for id_str in all_ids.split(',') if int(id_str) != keep_id]
                
                print(f"Hash {hash_val}: Keeping ID {keep_id}, removing IDs {ids_to_remove}")
                
                for remove_id in ids_to_remove:
                    cursor.execute('DELETE FROM transactions WHERE id = ?', (remove_id,))
                    removed_count += 1
            
            conn.commit()
            print(f"Duplicate removal complete: {removed_count} transactions removed")
            
            # Show final count
            cursor.execute('SELECT COUNT(*) FROM transactions')
            final_count = cursor.fetchone()[0]
            print(f"Final transaction count: {final_count}")
            
        except Exception as e:
            print(f"Error removing duplicates: {e}")
            conn.rollback()
        finally:
            conn.close()

def main():
    fixer = DuplicateFixer()
    
    print("=== Duplicate Detection Fix ===")
    print("Step 1: Regenerating all transaction hashes...")
    fixer.regenerate_all_hashes()
    
    print("\nStep 2: Finding duplicates...")
    duplicates = fixer.find_duplicates()
    
    if duplicates:
        print(f"\nStep 3: Removing {len(duplicates)} sets of duplicates...")
        fixer.remove_duplicates()
    else:
        print("\nNo duplicates found after hash regeneration!")
    
    print("\n=== Fix Complete ===")

if __name__ == '__main__':
    main()