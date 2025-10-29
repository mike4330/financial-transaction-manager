#!/usr/bin/env python3
"""
Interactive QIF Reconciliation Script
Streamlines the QIF reconciliation process with smart filtering, batch operations, and user preference learning.
"""

import json
import os
import sys
from typing import Dict, List, Optional, Tuple
from database import TransactionDB
import sqlite3
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.prompt import Prompt, Confirm
import termios
import tty

class InteractiveReconciler:
    def __init__(self):
        self.db = TransactionDB()
        self.batch_dir = 'reconciliation_sessions/cash_mgmt_batches/'
        self.user_preferences = self.load_user_preferences()
        self.session_stats = {
            'enhanced': 0,
            'skipped': 0,
            'batch_operations': 0
        }
        self.console = Console()

    def getch(self) -> str:
        """Get a single character from stdin without requiring Enter"""
        try:
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                char = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            return char.lower()
        except:
            # Fallback for environments where termios doesn't work
            self.console.print(" [dim](Press Enter after typing)[/dim]", end="")
            user_input = input().lower().strip()
            return user_input[:1] if user_input else ''

    def load_user_preferences(self) -> Dict:
        """Load established user preferences from previous sessions"""
        preferences_file = 'reconciliation_sessions/user_preferences.json'
        default_prefs = {
            'payee_simplification': {
                'prefer_generic': True,
                'skip_location_details': True,
                'generic_names': {
                    'walmart': 'Walmart',
                    'target': 'Target', 
                    'aldi': 'Aldi',
                    'bjs': "BJ's",
                    'sheetz': 'Sheetz',
                    'taco bell': 'Taco Bell',
                    'kfc': 'KFC'
                }
            },
            'category_enhancement': {
                'apply_qif_categories': True,
                'skip_splits': True,
                'priority_uncategorized': True
            },
            'auto_skip_patterns': [
                'location_only_enhancement',
                'split_transactions'
            ]
        }
        
        try:
            if os.path.exists(preferences_file):
                with open(preferences_file, 'r') as f:
                    stored_prefs = json.load(f)
                    # Merge with defaults
                    for key, value in stored_prefs.items():
                        default_prefs[key] = value
        except:
            pass
            
        return default_prefs
    
    def save_user_preferences(self):
        """Save updated user preferences"""
        preferences_file = 'reconciliation_sessions/user_preferences.json'
        os.makedirs('reconciliation_sessions', exist_ok=True)
        with open(preferences_file, 'w') as f:
            json.dump(self.user_preferences, f, indent=2)
    
    def get_unprocessed_transactions(self, limit: int = 10) -> List[Dict]:
        """Get unprocessed transactions that need manual review from all analysis files"""
        import random

        unprocessed = []
        processed_hashes = self.get_processed_hashes()

        # Get all analysis files from all batches
        for analysis_file in os.listdir(self.batch_dir):
            if not analysis_file.endswith('_analysis.json'):
                continue

            analysis_path = os.path.join(self.batch_dir, analysis_file)

            try:
                with open(analysis_path, 'r') as f:
                    analysis = json.load(f)

                if 'duplicate_candidates' not in analysis:
                    continue

                for candidate in analysis['duplicate_candidates']:
                    duplicate_info = candidate.get('duplicate_info', {})
                    qif_hash = duplicate_info.get('qif_hash')
                    if qif_hash in processed_hashes:
                        continue

                    # Check if transaction needs processing
                    if duplicate_info.get('status') == 'enhance_existing':
                        interest_score = self.score_transaction_interest(candidate)
                        unprocessed.append({
                            'transaction': candidate,
                            'batch_file': analysis_file,
                            'score': interest_score,
                            'qif_hash': qif_hash
                        })

            except Exception as e:
                self.console.print(f"[red]Error processing {analysis_file}: {e}[/red]")
                continue

        # Randomly shuffle and return requested limit
        random.shuffle(unprocessed)
        return unprocessed[:limit]

    def _find_database_matches(self, qif_txn: Dict) -> List[Dict]:
        """Find potential database matches for a QIF transaction"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Look for transactions within 3 days and matching amount
            qif_amount = float(qif_txn.get('amount', 0))
            query = '''
                SELECT t.*, c.name as category_name, sc.name as subcategory_name
                FROM transactions t
                LEFT JOIN categories c ON t.category_id = c.id
                LEFT JOIN subcategories sc ON t.subcategory_id = sc.id
                WHERE ABS(t.amount - ?) < 0.01
                ORDER BY t.date DESC
                LIMIT 50
            '''

            cursor.execute(query, (qif_amount,))
            matches = []
            for row in cursor.fetchall():
                matches.append(dict(row))

            conn.close()
            return matches

        except Exception as e:
            self.console.print(f"[red]Error finding database matches: {e}[/red]")
            return []

    def _analyze_transaction_for_enhancement(self, qif_txn: Dict, db_txn: Dict) -> Dict:
        """Analyze if QIF transaction can enhance database transaction"""
        import hashlib
        enhancements = {}

        # Check payee enhancement
        qif_payee = qif_txn.get('payee', '').strip()
        db_payee = db_txn.get('payee', '').strip()

        # First check if custom patterns can improve the payee
        custom_payee_suggestion = self._get_custom_pattern_suggestion(db_txn.get('action', ''))

        if custom_payee_suggestion and custom_payee_suggestion != db_payee:
            enhancements['payee'] = {
                'from': db_payee,
                'to': custom_payee_suggestion,
                'reason': 'Custom pattern suggestion'
            }
        elif not custom_payee_suggestion and qif_payee and qif_payee != db_payee:
            # Only suggest QIF payee if no custom pattern applies
            if not db_payee or db_payee == 'No Description' or len(qif_payee) > len(db_payee):
                enhancements['payee'] = {
                    'from': db_payee,
                    'to': qif_payee,
                    'reason': 'More descriptive payee from QIF'
                }

        # Check category enhancement
        qif_category = qif_txn.get('category', '').strip()
        if qif_category and not db_txn.get('category_id'):
            # Try to map category
            try:
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT id, name FROM categories WHERE name LIKE ?", (f"%{qif_category}%",))
                category_match = cursor.fetchone()
                if category_match:
                    enhancements['category'] = {
                        'from': None,
                        'to': {'app_category_id': category_match[0], 'name': category_match[1]},
                        'reason': 'Category from QIF data'
                    }
                conn.close()
            except:
                pass

        if enhancements:
            return {
                'status': 'enhance_existing',
                'qif_hash': hashlib.md5(f"{qif_txn.get('date', '')}{qif_txn.get('amount', '')}{qif_txn.get('payee', '')}{qif_txn.get('category', '')}".encode()).hexdigest(),
                'details': db_txn,
                'enhancements': enhancements
            }

        return None

    def _get_custom_pattern_suggestion(self, action: str) -> Optional[str]:
        """Check if custom payee patterns can suggest a better payee"""
        if not action:
            return None

        try:
            conn = sqlite3.connect(self.db.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT pattern, replacement, is_regex
                FROM payee_extraction_patterns
                WHERE is_active = 1
                ORDER BY usage_count DESC
            ''')
            patterns = cursor.fetchall()

            for pattern_row in patterns:
                pattern = pattern_row['pattern']
                replacement = pattern_row['replacement']
                is_regex = bool(pattern_row['is_regex'])

                if is_regex:
                    # Regex pattern matching
                    try:
                        import re
                        match = re.search(pattern, action, re.IGNORECASE)
                        if match:
                            # Handle capture group substitution ($1, $2, etc.)
                            result = replacement
                            for i, group in enumerate(match.groups(), 1):
                                if group:
                                    result = result.replace(f'${i}', group)
                            conn.close()
                            return result.strip()
                    except:
                        continue
                else:
                    # Simple text matching (case-insensitive)
                    if pattern.upper() in action.upper():
                        conn.close()
                        return replacement.strip()

            conn.close()

        except Exception:
            pass

        return None

    def score_transaction_interest(self, candidate: Dict) -> int:
        """Score a transaction's interest level for manual review"""
        qif_txn = candidate['qif_transaction']
        duplicate_info = candidate['duplicate_info']
        status = duplicate_info.get('status', '')
        
        score = 0
        
        # High priority: uncategorized transactions getting categories
        if status == 'enhance_existing':
            enhancements = duplicate_info.get('enhancements', {})
            
            # Category enhancement is most interesting
            if 'category' in enhancements:
                existing_cat = enhancements['category']['from']
                if existing_cat is None:
                    score += 10  # Uncategorized getting category
                else:
                    score += 9   # Category conflict
            
            # Payee enhancements
            if 'payee' in enhancements:
                from_payee = enhancements['payee']['from'].lower()
                to_payee = enhancements['payee']['to'].lower()
                
                # Skip boring location-only changes
                if self.is_location_only_change(from_payee, to_payee):
                    score = max(1, score - 5)  # Demote location changes
                elif any(generic in to_payee for generic in self.user_preferences['payee_simplification']['generic_names'].keys()):
                    score += 3  # Known merchant
                else:
                    score += 4  # New payee pattern
        
        # Special transaction types
        amount = abs(float(qif_txn.get('amount', 0)))
        payee = qif_txn.get('payee', '').lower()
        
        if 'return' in payee or 'refund' in payee:
            score += 7  # Returns are interesting
        elif amount > 500:
            score += 6  # Large amounts
        elif 'split' in qif_txn.get('category', ''):
            return 0  # Skip splits entirely
            
        return min(score, 10)  # Cap at 10

    def get_category_name(self, category_id: int) -> str:
        """Get human-readable category name from ID"""
        if not category_id:
            return "[Uncategorized]"

        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()

            # First try as subcategory ID
            cursor.execute('''
                SELECT c.name, s.name
                FROM subcategories s
                JOIN categories c ON s.category_id = c.id
                WHERE s.id = ?
            ''', (category_id,))

            result = cursor.fetchone()
            if result:
                category, subcategory = result
                conn.close()
                return f"{category}:{subcategory}"

            # If not found, try as category ID
            cursor.execute('SELECT name FROM categories WHERE id = ?', (category_id,))
            result = cursor.fetchone()
            conn.close()

            if result:
                return result[0]
            else:
                return f"Unknown Category (ID: {category_id})"

        except Exception as e:
            return f"Category ID {category_id}"
    
    def is_location_only_change(self, from_payee: str, to_payee: str) -> bool:
        """Check if enhancement is just adding location details"""
        # Common patterns: "Walmart" -> "Walmart #1234 Location ST"
        from_words = from_payee.split()
        to_words = to_payee.split()
        
        if len(from_words) == 0 or len(to_words) == 0:
            return False
            
        base_from = from_words[0].lower()
        base_to = to_words[0].lower()
        
        # Same base merchant name
        if base_from == base_to or base_from in base_to or base_to in base_from:
            # Additional words suggest location details
            return len(to_words) > len(from_words)
            
        return False
    
    def get_processed_hashes(self) -> set:
        """Get set of already processed QIF transaction hashes"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT qif_transaction_hash FROM qif_reconciliation_log")
            hashes = {row[0] for row in cursor.fetchall()}
            conn.close()
            return hashes
        except:
            return set()
    
    def present_transaction(self, transaction_data: Dict) -> None:
        """Present transaction with beautiful Rich table formatting"""
        candidate = transaction_data['transaction']
        qif_txn = candidate['qif_transaction']
        duplicate_info = candidate['duplicate_info']

        # Header with score
        score = transaction_data['score']
        score_color = "red" if score < 3 else "yellow" if score < 7 else "green"

        title = Text("Transaction Review", style="bold blue")
        title.append(f" (Score: {score}/10)", style=f"bold {score_color}")

        self.console.print(Panel(title, box=box.DOUBLE, padding=(1, 2)))

        # Main comparison table
        if duplicate_info['status'] == 'enhance_existing':
            existing_details = duplicate_info['details']
            enhancements = duplicate_info.get('enhancements', {})

            # Create main comparison table
            table = Table(box=box.ROUNDED, title="[bold cyan]Transaction Comparison[/bold cyan]", show_header=True)
            table.add_column("Field", style="bold", min_width=8, max_width=8)
            table.add_column("QIF Transaction", style="blue", min_width=25, max_width=30)
            table.add_column("Current Database", style="magenta", min_width=25, max_width=30)
            table.add_column("Status", style="green", min_width=10, max_width=12)

            # Date row
            table.add_row(
                "Date",
                str(qif_txn['date']),
                str(existing_details['date']),
                "✓ Match"
            )

            # Amount row
            table.add_row(
                "Amount",
                f"${qif_txn['amount']:.2f}",
                f"${existing_details['amount']:.2f}",
                "✓ Match"
            )

            # Payee row with enhancement indicator
            qif_payee = qif_txn.get('payee', '(none)')
            existing_payee = existing_details.get('payee') or '(none)'
            payee_status = "📝 ENHANCE" if 'payee' in enhancements else "✓ Keep"
            payee_style = "yellow" if 'payee' in enhancements else "green"

            table.add_row(
                "Payee",
                qif_payee,
                existing_payee,
                Text(payee_status, style=payee_style)
            )

            # Category row
            qif_category = qif_txn.get('category', '(none)')
            # Handle transfer vs spending categories
            if qif_category.startswith('[') and qif_category.endswith(']'):
                # This is a transfer between accounts
                account_name = qif_category[1:-1]  # Remove brackets
                qif_category_display = f"Transfer: {account_name}"
            else:
                # Regular spending category
                qif_category_display = qif_category

            # Use subcategory_id if available, otherwise use category_id
            existing_subcat_id = existing_details.get('subcategory_id')
            existing_cat_id = existing_details.get('category_id')

            if existing_subcat_id:
                existing_category = self.get_category_name(existing_subcat_id)
            else:
                existing_category = self.get_category_name(existing_cat_id)

            category_status = "📝 ENHANCE" if 'category' in enhancements else "✓ Keep"
            category_style = "yellow" if 'category' in enhancements else "green"

            # Apply style to uncategorized items
            if existing_category == "[Uncategorized]":
                existing_category_display = Text(existing_category, style="red")
            else:
                existing_category_display = existing_category

            table.add_row(
                "Category",
                qif_category_display,
                existing_category_display,
                Text(category_status, style=category_style)
            )

            # Memo row
            qif_memo = qif_txn.get('memo') or '(none)'
            existing_memo = existing_details.get('memo') or '(none)'
            memo_status = "📝 ENHANCE" if 'memo' in enhancements else "✓ Keep"
            memo_style = "yellow" if 'memo' in enhancements else "green"

            table.add_row(
                "Memo",
                qif_memo,
                existing_memo,
                Text(memo_status, style=memo_style)
            )

            self.console.print(table)

            # Enhancement details section
            if enhancements:
                enhancement_table = Table(box=box.SIMPLE, title="[bold yellow]📝 Proposed Enhancements[/bold yellow]")
                enhancement_table.add_column("Field", style="bold")
                enhancement_table.add_column("From", style="red")
                enhancement_table.add_column("To", style="green")
                enhancement_table.add_column("Reason", style="cyan")

                for field, enhancement in enhancements.items():
                    if field == 'payee':
                        enhancement_table.add_row(
                            "Payee",
                            f'"{enhancement["from"]}"',
                            f'"{enhancement["to"]}"',
                            enhancement.get('reason', 'More descriptive')
                        )
                    elif field == 'category':
                        cat_info = enhancement['to']
                        enhancement_table.add_row(
                            "Category",
                            "None",
                            f"{qif_category_display} (ID: {cat_info['app_category_id']})",
                            enhancement.get('reason', 'Add missing category')
                        )

                self.console.print(enhancement_table)

            # Transaction ID footer
            self.console.print(f"\n[dim]Transaction ID: {existing_details['id']}[/dim]")

        else:
            # Non-enhancement status
            status_table = Table(box=box.ROUNDED)
            status_table.add_column("Status", style="bold red")
            status_table.add_column("Reason", style="yellow")
            status_table.add_row(duplicate_info['status'], duplicate_info['reason'])
            self.console.print(status_table)
    
    def get_user_decision(self) -> str:
        """Get user decision with single-letter keypresses"""
        # Create decision options table
        options_table = Table(box=box.SIMPLE, title="[bold green]Decision Options[/bold green]")
        options_table.add_column("Key", style="bold cyan", width=8)
        options_table.add_column("Command", style="bold yellow", width=15)
        options_table.add_column("Description", style="white", width=50)

        options_table.add_row("[A]", "approve", "Apply enhancement as proposed")
        options_table.add_row("[S]", "skip", "Skip this transaction")
        options_table.add_row("[M]", "modify", "Enter custom payee name")
        options_table.add_row("[B]", "batch", "Apply same decision to similar transactions")
        options_table.add_row("[T]", "stats", "Show session statistics")
        options_table.add_row("[Q]", "quit", "Exit reconciliation session")

        self.console.print(options_table)

        while True:
            self.console.print("\n[bold green]Press a key:[/bold green] ", end="")
            key = self.getch()

            # Handle special characters (Ctrl+C, etc.)
            if ord(key) == 3:  # Ctrl+C
                self.console.print("\n[yellow]Session interrupted by user.[/yellow]")
                return 'quit'

            self.console.print(f"[cyan]{key.upper()}[/cyan]")  # Show what was pressed

            if key == 'a':
                return 'approve'
            elif key == 's':
                return 'skip'
            elif key == 'm':
                # For modify, we need to get the custom payee name
                new_payee = Prompt.ask("\n[yellow]Enter new payee name[/yellow]")
                if new_payee.strip():
                    return f'modify {new_payee.strip()}'
                else:
                    self.console.print("[red]Invalid payee name. Try again.[/red]")
                    continue
            elif key == 'b':
                return 'batch'
            elif key == 't':
                return 'stats'
            elif key == 'q':
                return 'quit'
            else:
                self.console.print(f"[red]Invalid key '{key.upper()}'. Try again.[/red]")
    
    def apply_decision(self, transaction_data: Dict, decision: str) -> bool:
        """Apply user decision and return success status"""
        candidate = transaction_data['transaction']
        qif_txn = candidate['qif_transaction']
        duplicate_info = candidate['duplicate_info']

        # Store QIF transaction in context for logging
        self._current_qif_txn = qif_txn
        
        if decision == 'skip':
            qif_hash = transaction_data.get('qif_hash') or duplicate_info.get('qif_hash')
            self.log_decision(qif_hash, 'skipped', None, {'action': 'skip'}, qif_txn)
            self.session_stats['skipped'] += 1
            self.console.print("[green]✅ Transaction skipped.[/green]")
            return True
            
        elif decision == 'approve':
            if duplicate_info['status'] == 'enhance_existing':
                return self.apply_enhancement(duplicate_info)
            
        elif decision.startswith('modify '):
            new_payee = decision[7:].strip()  # Remove 'modify '
            if new_payee and duplicate_info['status'] == 'enhance_existing':
                return self.apply_modified_enhancement(duplicate_info, new_payee)
        
        return False
    
    def apply_enhancement(self, duplicate_info: Dict) -> bool:
        """Apply the proposed enhancement"""
        try:
            transaction_id = duplicate_info['details']['id']
            qif_hash = duplicate_info['qif_hash']
            enhancements = duplicate_info['enhancements']
            
            # Format enhancements for database method
            formatted_enhancements = {}
            for field, enhancement in enhancements.items():
                formatted_enhancements[field] = {
                    'from': enhancement['from'],
                    'to': enhancement['to'],
                    'reason': enhancement.get('reason', 'User approved')
                }
            
            success = self.db.enhance_existing_transaction(
                transaction_id=transaction_id,
                enhancements=formatted_enhancements,
                qif_hash=qif_hash,
                notes='Interactive reconciliation - user approved'
            )

            if success:
                # Get QIF transaction from the context (passed from apply_decision)
                qif_txn = getattr(self, '_current_qif_txn', None)
                self.log_decision(qif_hash, 'matched', transaction_id, {'action': 'approve', 'enhancements': formatted_enhancements}, qif_txn)
                self.session_stats['enhanced'] += 1
                self.console.print("[bold green]✅ Enhancement applied successfully.[/bold green]")
                return True
            else:
                self.console.print("[bold red]❌ Failed to apply enhancement.[/bold red]")
                return False

        except Exception as e:
            self.console.print(f"[bold red]❌ Error applying enhancement: {e}[/bold red]")
            return False
    
    def apply_modified_enhancement(self, duplicate_info: Dict, new_payee: str) -> bool:
        """Apply enhancement with user-modified payee"""
        try:
            transaction_id = duplicate_info['details']['id']
            qif_hash = duplicate_info['qif_hash']
            original_enhancements = duplicate_info['enhancements']
            
            # Modify payee enhancement
            formatted_enhancements = {}
            for field, enhancement in original_enhancements.items():
                if field == 'payee':
                    formatted_enhancements[field] = {
                        'from': enhancement['from'],
                        'to': new_payee,
                        'reason': 'User-modified payee name'
                    }
                else:
                    formatted_enhancements[field] = {
                        'from': enhancement['from'],
                        'to': enhancement['to'],
                        'reason': enhancement.get('reason', 'User approved')
                    }
            
            success = self.db.enhance_existing_transaction(
                transaction_id=transaction_id,
                enhancements=formatted_enhancements,
                qif_hash=qif_hash,
                notes=f'Interactive reconciliation - user modified payee to: {new_payee}'
            )
            
            if success:
                # Get QIF transaction from the context (passed from apply_decision)
                qif_txn = getattr(self, '_current_qif_txn', None)
                self.log_decision(qif_hash, 'matched', transaction_id, {'action': 'modify', 'new_payee': new_payee, 'enhancements': formatted_enhancements}, qif_txn)
                self.session_stats['enhanced'] += 1
                self.console.print(f"[bold green]✅ Enhancement applied with modified payee: {new_payee}[/bold green]")
                return True
            else:
                self.console.print("[bold red]❌ Failed to apply modified enhancement.[/bold red]")
                return False

        except Exception as e:
            self.console.print(f"[bold red]❌ Error applying modified enhancement: {e}[/bold red]")
            return False
    
    def log_decision(self, qif_hash: str, status: str, transaction_id: Optional[int], decision_data: Dict, qif_txn: Dict = None):
        """Log reconciliation decision to database"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()

            # Extract QIF transaction data if provided
            qif_date = '1970-01-01'
            qif_amount = 0.0
            qif_payee = None
            qif_category = None
            qif_memo = None

            if qif_txn:
                qif_date = qif_txn.get('date', '1970-01-01')
                qif_amount = float(qif_txn.get('amount', 0.0))
                qif_payee = qif_txn.get('payee')
                qif_category = qif_txn.get('category')
                qif_memo = qif_txn.get('memo')

            cursor.execute('''
                INSERT OR REPLACE INTO qif_reconciliation_log
                (qif_file_path, batch_number, qif_transaction_hash, qif_date,
                 qif_amount, qif_payee, qif_category, qif_memo,
                 reconciliation_status, matched_transaction_id,
                 import_decision, notes, reconciled_at, reconciled_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            ''', (
                'interactive_session',
                1,
                qif_hash,
                qif_date,
                qif_amount,
                qif_payee,
                qif_category,
                qif_memo,
                status,
                transaction_id,
                json.dumps(decision_data),
                f'Interactive reconciliation - {status}',
                'interactive_script'
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"⚠️ Warning: Could not log decision - {e}")
    
    def show_stats(self):
        """Show current session statistics with Rich formatting"""
        # Session stats table
        session_table = Table(box=box.ROUNDED, title="[bold blue]📊 Session Statistics[/bold blue]")
        session_table.add_column("Metric", style="bold")
        session_table.add_column("Count", style="cyan", justify="right")

        session_table.add_row("✅ Enhanced", str(self.session_stats['enhanced']))
        session_table.add_row("⏭️ Skipped", str(self.session_stats['skipped']))
        session_table.add_row("🔄 Batch Operations", str(self.session_stats['batch_operations']))
        session_table.add_row("📈 Total This Session", str(sum(self.session_stats.values())))

        self.console.print(session_table)

        # Overall progress
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM qif_reconciliation_log")
            total_processed = cursor.fetchone()[0]
            remaining = 1270 - total_processed
            completion_rate = (total_processed / 1270) * 100

            # Progress table
            progress_table = Table(box=box.ROUNDED, title="[bold green]📋 Overall Progress[/bold green]")
            progress_table.add_column("Progress Metric", style="bold")
            progress_table.add_column("Value", style="green", justify="right")

            progress_table.add_row("Total Processed", f"{total_processed} / 1,270")
            progress_table.add_row("Completion Rate", f"{completion_rate:.1f}%")
            progress_table.add_row("Remaining", f"{remaining:,} transactions")

            self.console.print(progress_table)

            # Progress bar
            from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn
            with Progress() as progress:
                task = progress.add_task("Overall Progress", total=1270, completed=total_processed)
                self.console.print()

            conn.close()
        except:
            pass
    
    def run_interactive_session(self):
        """Main interactive reconciliation loop"""
        # Welcome banner
        welcome_panel = Panel(
            Text("🎯 Interactive QIF Reconciliation", style="bold blue", justify="center") +
            Text("\nRandomly processing transactions from all JSON batch files.\nType 'quit' at any time to exit.",
                 style="white", justify="center"),
            box=box.DOUBLE,
            title="[bold green]Welcome[/bold green]"
        )
        self.console.print(welcome_panel)
        
        try:
            while True:
                # Get next batch of unprocessed transactions
                unprocessed = self.get_unprocessed_transactions(limit=50)

                if not unprocessed:
                    completion_panel = Panel(
                        "🎉 No more unprocessed transactions found!\n\nAll reconciliations appear to be complete.",
                        title="[bold green]Session Complete[/bold green]",
                        style="green"
                    )
                    self.console.print(completion_panel)
                    break
                
                # Present the next transaction
                transaction_data = unprocessed[0]
                self.present_transaction(transaction_data)
                
                # Get user decision
                decision = self.get_user_decision()
                
                if decision == 'quit':
                    break
                elif decision == 'stats':
                    self.show_stats()
                    continue
                elif decision == 'batch':
                    self.console.print("[yellow]🚧 Batch operations not yet implemented[/yellow]")
                    continue
                else:
                    success = self.apply_decision(transaction_data, decision)
                    if not success:
                        self.console.print("[red]❌ Failed to apply decision. Continuing...[/red]")

                # Brief pause with single keypress
                self.console.print("\n[dim]Press any key to continue to next transaction...[/dim]", end="")
                self.getch()
                self.console.print("")

        except KeyboardInterrupt:
            self.console.print("\n\n[yellow]⏹️ Session interrupted by user.[/yellow]")

        finally:
            self.show_stats()
            self.save_user_preferences()
            completion_msg = Panel(
                "✅ Session complete. User preferences saved.",
                title="[green]Session Ended[/green]",
                style="green"
            )
            self.console.print(completion_msg)

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        if sys.argv[1] == '--stats':
            reconciler = InteractiveReconciler()
            reconciler.show_stats()
            return
        elif sys.argv[1] == '--preview':
            reconciler = InteractiveReconciler()
            preview_panel = Panel(
                "🔍 Preview Mode - Next 5 unprocessed transactions",
                title="[bold blue]Preview Mode[/bold blue]",
                style="blue"
            )
            reconciler.console.print(preview_panel)

            interesting = reconciler.get_unprocessed_transactions(limit=5)
            for i, txn_data in enumerate(interesting, 1):
                reconciler.console.print(f"\n[bold cyan]--- Transaction #{i} ---[/bold cyan]")
                reconciler.present_transaction(txn_data)
            return
    
    reconciler = InteractiveReconciler()
    reconciler.run_interactive_session()

if __name__ == '__main__':
    main()