#!/usr/bin/env python3
"""
Script to clean up duplicate transactions in the database
"""
import sqlite3

def cleanup_duplicates():
    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()
    
    # Get all duplicate groups
    cursor.execute('''
        SELECT 
            MIN(id) as keep_id,
            GROUP_CONCAT(id) as all_ids,
            COUNT(*) as count
        FROM transactions 
        GROUP BY run_date, account, action, amount, description
        HAVING COUNT(*) > 1
    ''')
    
    duplicates = cursor.fetchall()
    deleted_count = 0
    
    print(f"Found {len(duplicates)} duplicate groups to clean up...")
    
    for keep_id, all_ids, count in duplicates:
        # Get all IDs except the one we want to keep
        all_id_list = [int(x) for x in all_ids.split(',')]
        delete_ids = [x for x in all_id_list if x != keep_id]
        
        if delete_ids:
            placeholders = ','.join(['?' for _ in delete_ids])
            cursor.execute(f'DELETE FROM transactions WHERE id IN ({placeholders})', delete_ids)
            deleted_count += len(delete_ids)
            print(f"Kept ID {keep_id}, deleted IDs: {delete_ids}")
    
    conn.commit()
    conn.close()
    
    print(f'Cleanup complete: Deleted {deleted_count} duplicate records')
    return deleted_count

if __name__ == '__main__':
    cleanup_duplicates()