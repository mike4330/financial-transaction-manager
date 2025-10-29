import random
import logging
from typing import List, Dict, Tuple, Optional
from database import TransactionDB

class AITransactionClassifier:
    def __init__(self, db: TransactionDB):
        self.db = db
        self.logger = logging.getLogger(__name__)
        
        # Common financial categories with typical patterns
        self.category_patterns = {
            "Food & Dining": {
                "subcategories": ["Restaurants", "Fast Food", "Coffee", "Groceries", "Alcohol"],
                "keywords": ["restaurant", "food", "pizza", "burger", "coffee", "starbucks", "mcdonalds", 
                           "grocery", "supermarket", "walmart", "target", "safeway", "kroger", "publix",
                           "bar", "pub", "brewery", "wine", "liquor"],
                "payees": ["McDonald's", "Starbucks", "Subway", "Pizza Hut", "Domino's", "Walmart", 
                          "Target", "Safeway", "Kroger", "Publix", "Whole Foods"]
            },
            "Shopping": {
                "subcategories": ["Online", "Clothing", "Electronics", "General", "Home & Garden"],
                "keywords": ["amazon", "ebay", "walmart", "target", "costco", "best buy", "home depot",
                           "lowes", "ikea", "macys", "nordstrom", "clothing", "apparel"],
                "payees": ["Amazon", "eBay", "Walmart", "Target", "Costco", "Best Buy", "Home Depot",
                          "Lowe's", "IKEA", "Macy's", "Nordstrom"]
            },
            "Transportation": {
                "subcategories": ["Gas", "Public Transit", "Rideshare", "Parking", "Auto Services"],
                "keywords": ["gas", "fuel", "shell", "exxon", "chevron", "bp", "uber", "lyft", 
                           "metro", "transit", "parking", "garage", "mechanic", "oil change"],
                "payees": ["Shell", "Exxon", "Chevron", "BP", "Uber", "Lyft", "Texaco", "Mobil", "Citgo"]
            },
            "Entertainment": {
                "subcategories": ["Movies", "Music", "Games", "Sports", "Streaming"],
                "keywords": ["netflix", "spotify", "movie", "theater", "cinema", "game", "steam",
                           "xbox", "playstation", "gym", "fitness", "streaming"],
                "payees": ["Netflix", "Spotify", "Amazon Prime", "Disney+", "Hulu", "Steam", "Xbox", "PlayStation"]
            },
            "Healthcare": {
                "subcategories": ["Medical", "Dental", "Pharmacy", "Insurance"],
                "keywords": ["doctor", "hospital", "medical", "pharmacy", "cvs", "walgreens",
                           "dental", "dentist", "insurance", "health"],
                "payees": ["CVS Pharmacy", "Walgreens", "Rite Aid", "Kaiser", "Anthem", "Blue Cross"]
            },
            "Utilities": {
                "subcategories": ["Electric", "Gas", "Water", "Internet", "Phone"],
                "keywords": ["electric", "power", "gas company", "water", "internet", "phone",
                           "verizon", "att", "comcast", "utility"],
                "payees": ["Verizon", "AT&T", "Comcast", "Xfinity", "T-Mobile", "Sprint"]
            },
            "Investment": {
                "subcategories": ["Stock Purchase", "Dividend", "ETF", "Mutual Fund"],
                "keywords": ["bought", "sold", "dividend", "etf", "fund", "stock", "share"],
                "payees": ["Fidelity", "Charles Schwab", "E*Trade", "TD Ameritrade", "Robinhood"]
            },
            "Banking": {
                "subcategories": ["Fees", "Interest", "Transfer", "ATM"],
                "keywords": ["fee", "interest", "transfer", "atm", "withdrawal", "deposit"],
                "payees": ["Bank of America", "Wells Fargo", "Chase", "Citibank", "US Bank"]
            },
            "Personal Care": {
                "subcategories": ["Salon", "Spa", "Pharmacy"],
                "keywords": ["salon", "haircut", "spa", "massage", "beauty", "cosmetic"],
                "payees": ["Great Clips", "Supercuts", "CVS Pharmacy", "Walgreens"]
            },
            "Insurance": {
                "subcategories": ["Auto", "Home", "Life", "Health"],
                "keywords": ["insurance", "policy", "premium", "coverage"],
                "payees": ["State Farm", "Geico", "Progressive", "Allstate", "Farmers", "USAA"]
            },
            "Income": {
                "subcategories": ["Salary", "Other", "Interest", "Dividends"],
                "keywords": ["salary", "wages", "payroll", "deposit", "income"],
                "payees": ["Treasury", "Payroll", "Direct Deposit"]
            }
        }
    
    def _determine_subcategory_by_payee(self, payee: str, category: str, subcategories: List[str]) -> str:
        """Determine the most appropriate subcategory based on payee name"""
        if not payee:
            return subcategories[0]
        
        payee_lower = payee.lower()
        
        # Specific payee to subcategory mappings
        payee_subcategory_map = {
            "Food & Dining": {
                "starbucks": "Coffee",
                "dunkin": "Coffee", 
                "mcdonald": "Fast Food",
                "burger": "Fast Food",
                "subway": "Fast Food",
                "pizza": "Fast Food",
                "walmart": "Groceries",
                "target": "Groceries",
                "safeway": "Groceries",
                "kroger": "Groceries",
                "publix": "Groceries"
            },
            "Transportation": {
                "shell": "Gas",
                "exxon": "Gas",
                "chevron": "Gas",
                "bp": "Gas",
                "uber": "Rideshare",
                "lyft": "Rideshare"
            },
            "Entertainment": {
                "netflix": "Streaming",
                "spotify": "Music",
                "steam": "Games",
                "xbox": "Games",
                "playstation": "Games"
            },
            "Healthcare": {
                "cvs": "Pharmacy",
                "walgreens": "Pharmacy"
            },
            "Insurance": {
                "state farm": "Auto",
                "geico": "Auto",
                "progressive": "Auto"
            }
        }
        
        if category in payee_subcategory_map:
            for payee_key, subcat in payee_subcategory_map[category].items():
                if payee_key in payee_lower:
                    return subcat
        
        return subcategories[0]
    
    def _classify_by_transaction_type(self, transaction_type: str, amount: float, payee: str = None) -> Optional[Tuple[str, str, float]]:
        """Classify transaction based on transaction type with high confidence"""
        if not transaction_type:
            return None
        
        # Investment transactions
        if transaction_type in ["Investment Trade", "Dividend", "Reinvestment"]:
            if transaction_type == "Dividend":
                return ("Investment", "Dividend", 0.95)
            elif "Trade" in transaction_type:
                return ("Investment", "Stock Purchase", 0.95)
            else:  # Reinvestment
                return ("Investment", "ETF", 0.90)
        
        # Banking/Transfer transactions  
        elif transaction_type in ["Transfer", "Contribution"]:
            if amount > 0:
                return ("Banking", "Transfer", 0.90)
            else:
                return ("Banking", "Transfer", 0.90)
        
        # Direct transactions with payee-specific logic
        elif transaction_type == "Direct Deposit":
            if payee:
                # Salary/wages
                if any(word in payee.lower() for word in ["treas", "salary", "pay", "payroll"]):
                    return ("Income", "Salary", 0.95)
            return ("Income", "Other", 0.85)
        
        elif transaction_type == "Direct Debit":
            if payee:
                # Insurance companies
                if any(word in payee.lower() for word in ["state farm", "geico", "progressive", "allstate"]):
                    return ("Insurance", "Auto", 0.95)
                # Utilities  
                elif any(word in payee.lower() for word in ["electric", "gas", "water", "power"]):
                    return ("Utilities", "Electric", 0.95)
            return ("Banking", "Transfer", 0.70)
        
        # Card transactions
        elif transaction_type == "Debit Card":
            # Let payee-based classification handle these
            return None
        
        # ACH transactions
        elif transaction_type in ["ACH Debit", "ACH Credit"]:
            if payee:
                # Subscription services
                if any(word in payee.lower() for word in ["netflix", "spotify", "amazon", "apple"]):
                    return ("Entertainment", "Streaming", 0.90)
            return ("Banking", "Transfer", 0.70)
        
        # Fee transactions
        elif transaction_type == "Fee":
            return ("Banking", "Fees", 0.95)
        
        # Interest transactions  
        elif transaction_type == "Interest":
            return ("Banking", "Interest", 0.95)
        
        # ATM transactions
        elif transaction_type == "ATM":
            return ("Banking", "ATM", 0.95)
        
        # Check transactions
        elif transaction_type == "Check":
            # Let other classification methods handle checks since they vary widely
            return None
        
        return None
    
    def classify_transaction_text(self, description: str, action: str, amount: float, payee: str = None, transaction_type: str = None) -> Tuple[str, str, float]:
        """
        Use AI-like logic to classify a transaction based on description, action, amount, and payee.
        Returns (category, subcategory, confidence_score)
        
        Priority order:
        1. Transaction type (highest confidence)
        2. Payee matching (high confidence) 
        3. Action patterns (medium confidence)
        4. Description keywords (lower confidence, often "No Description")
        """
        # Build search text prioritizing payee and action over description
        # Since many transactions have "No Description", focus on meaningful fields
        search_components = []
        
        if payee and payee.strip() and payee.lower() != "no description":
            search_components.append(payee.lower())
        
        if action and action.strip():
            search_components.append(action.lower())
            
        if description and description.strip() and description.lower() != "no description":
            search_components.append(description.lower())
        
        text = " ".join(search_components)
        
        # Transaction type-based classification (highest priority)
        if transaction_type:
            type_classification = self._classify_by_transaction_type(transaction_type, amount, payee)
            if type_classification:
                return type_classification
        
        # Check for payee-based classification first (higher accuracy)
        category_scores = {}
        
        if payee and payee.strip() and payee.lower() != "no description":
            for category, data in self.category_patterns.items():
                if "payees" in data:
                    for known_payee in data["payees"]:
                        if payee.lower() == known_payee.lower() or known_payee.lower() in payee.lower():
                            # High confidence match based on payee
                            subcategory = self._determine_subcategory_by_payee(payee, category, data["subcategories"])
                            return (category, subcategory, 1.0)  # Return immediately for payee matches
        
        # Action-based classification (medium-high confidence)
        if action and action.strip():
            action_lower = action.lower()
            
            # Direct debit patterns with high confidence for known payees
            if "direct debit" in action_lower:
                if payee:
                    payee_lower = payee.lower()
                    if any(word in payee_lower for word in ["state farm", "geico", "progressive", "allstate", "farmers", "usaa"]):
                        return ("Insurance", "Auto", 0.95)
                    elif any(word in payee_lower for word in ["electric", "gas", "power", "utility", "verizon", "att", "comcast"]):
                        return ("Utilities", "Electric", 0.90)
                return ("Banking", "Transfer", 0.70)
            
            # Debit card purchase patterns
            elif "debit card purchase" in action_lower:
                if payee:
                    payee_lower = payee.lower()
                    # Food & Dining
                    if any(word in payee_lower for word in ["mcdonald", "burger", "taco", "pizza", "subway", "wendy", "kfc", "chick-fil-a", "popeyes"]):
                        return ("Food & Dining", "Fast Food", 0.90)
                    elif any(word in payee_lower for word in ["starbucks", "dunkin", "coffee"]):
                        return ("Food & Dining", "Coffee", 0.90)
                    elif any(word in payee_lower for word in ["walmart", "target", "safeway", "kroger", "publix", "aldi", "food lion"]):
                        return ("Food & Dining", "Groceries", 0.85)
                    # Shopping
                    elif any(word in payee_lower for word in ["amazon", "ebay", "walmart", "target", "costco", "best buy"]):
                        return ("Shopping", "Online", 0.85)
                    # Gas stations
                    elif any(word in payee_lower for word in ["shell", "exxon", "chevron", "bp", "mobil", "texaco", "sheetz"]):
                        return ("Transportation", "Gas", 0.90)
                    # Healthcare
                    elif any(word in payee_lower for word in ["cvs", "walgreens", "pharmacy", "medical", "doctor", "hospital", "uva hs", "spine care"]):
                        return ("Healthcare", "Medical", 0.85)
                    # Transportation/Rideshare
                    elif any(word in payee_lower for word in ["uber", "lyft"]):
                        return ("Transportation", "Rideshare", 0.95)
                    # Entertainment
                    elif any(word in payee_lower for word in ["netflix", "spotify", "amazon prime", "disney", "hulu", "steam", "apple"]):
                        return ("Entertainment", "Streaming", 0.90)
                    # Utilities/Internet/Phone
                    elif any(word in payee_lower for word in ["verizon", "att", "t-mobile", "comcast", "xfinity"]):
                        return ("Utilities", "Internet", 0.90)
                return ("Shopping", "General", 0.60)
        
        # Check for investment-related transactions (often have specific patterns)
        if any(word in text for word in ["bought", "sold", "dividend", "etf", "fund", "corp", "inc"]):
            # Don't match on .com domains for investments unless they're actually investment-related
            if "dividend" in text:
                return ("Investment", "Dividend", 0.9)
            elif any(word in text for word in ["bought", "you bought"]):
                return ("Investment", "Stock Purchase", 0.9)
            elif "etf" in text.lower():
                return ("Investment", "ETF", 0.9)
            elif any(word in text for word in ["corp", "inc"]) and not payee:
                return ("Investment", "Stock Purchase", 0.7)
        
        # Score each category based on keyword matches
        category_scores = {}
        for category, data in self.category_patterns.items():
            current_score = category_scores.get(category, {'score': 0, 'subcategory': None})
            
            for keyword in data["keywords"]:
                if keyword in text:
                    current_score['score'] += 1
                    # Try to match to specific subcategories
                    for subcat in data["subcategories"]:
                        if keyword in subcat.lower() or subcat.lower() in text:
                            current_score['subcategory'] = subcat
                            current_score['score'] += 0.5  # Bonus for subcategory match
            
            if current_score['score'] > 0:
                if not current_score['subcategory']:
                    current_score['subcategory'] = data["subcategories"][0]
                category_scores[category] = current_score
        
        # Additional heuristics based on amount and common patterns
        if abs(amount) < 10 and any(word in text for word in ["coffee", "starbucks", "dunkin"]):
            category_scores["Food & Dining"] = {'score': 10, 'subcategory': 'Coffee'}
        
        if "debit card purchase" in text:
            # Most debit card purchases are shopping or food
            if not category_scores:
                category_scores["Shopping"] = {'score': 1, 'subcategory': 'General'}
        
        # Return the highest scoring category
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1]['score'])
            category = best_category[0]
            subcategory = best_category[1]['subcategory']
            confidence = min(best_category[1]['score'] / 5.0, 1.0)  # Normalize to 0-1
            return (category, subcategory, confidence)
        
        # Default classification for unmatched transactions
        if abs(amount) > 1000:
            return ("Banking", "Transfer", 0.3)
        else:
            return ("Miscellaneous", "Other", 0.2)
    
    def get_random_uncategorized_sample(self, sample_size: int = 10) -> List[Tuple]:
        """Get a random sample of uncategorized transactions"""
        uncategorized = self.db.get_uncategorized_transactions()
        
        if len(uncategorized) <= sample_size:
            return uncategorized
        
        return random.sample(uncategorized, sample_size)
    
    def get_transactions_by_ids(self, transaction_ids: List[int]) -> List[Tuple]:
        """Get specific transactions by their IDs"""
        if not transaction_ids:
            return []
        
        import sqlite3
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        try:
            # Build placeholders for the IN clause
            placeholders = ','.join('?' * len(transaction_ids))
            
            cursor.execute(f'''
                SELECT id, run_date, account, description, amount, action, payee
                FROM transactions 
                WHERE id IN ({placeholders})
                ORDER BY run_date DESC
            ''', transaction_ids)
            
            results = cursor.fetchall()
            return results
            
        except Exception as e:
            self.logger.error(f"Error fetching transactions by IDs: {e}")
            return []
        finally:
            conn.close()
    
    def classify_transactions_by_ids(self, transaction_ids: List[int], auto_apply: bool = False) -> List[Dict]:
        """
        Classify specific transactions by their IDs and optionally auto-apply the classifications
        """
        sample_transactions = self.get_transactions_by_ids(transaction_ids)
        
        if not sample_transactions:
            self.logger.info("No transactions found for the provided IDs")
            return []
        
        return self._classify_transactions(sample_transactions, auto_apply)
    
    def classify_sample_transactions(self, sample_size: int = 10, auto_apply: bool = False) -> List[Dict]:
        """
        Classify a random sample of transactions and optionally auto-apply the classifications
        """
        sample_transactions = self.get_random_uncategorized_sample(sample_size)
        
        if not sample_transactions:
            self.logger.info("No uncategorized transactions found")
            return []
        
        return self._classify_transactions(sample_transactions, auto_apply)
    
    def _classify_transactions(self, sample_transactions: List[Tuple], auto_apply: bool = False) -> List[Dict]:
        """
        Internal method to classify a list of transactions
        """
        results = []
        
        for tx_id, run_date, account, description, amount, action, payee in sample_transactions:
            # For existing data, we don't have transaction_type yet, so pass None
            category, subcategory, confidence = self.classify_transaction_text(
                description, action, amount, payee, None
            )
            
            result = {
                'id': tx_id,
                'date': run_date,
                'account': account,
                'description': description,
                'amount': amount,
                'action': action,
                'payee': payee,
                'suggested_category': category,
                'suggested_subcategory': subcategory,
                'confidence': confidence
            }
            
            if auto_apply and confidence > 0.7:  # Only auto-apply high confidence classifications
                success = self.db.update_transaction_category(
                    tx_id, category, subcategory, None
                )
                result['applied'] = success
                if success:
                    self.logger.info(f"Auto-applied {category}/{subcategory} to transaction {tx_id}")
                    
                    # Learn patterns from this successful AI classification
                    category_id = self.db.get_or_create_category(category)
                    subcategory_id = self.db.get_or_create_subcategory(category_id, subcategory) if subcategory else None
                    patterns_learned = self.db.extract_and_learn_patterns(
                        description, action, category_id, subcategory_id, confidence
                    )
                    if patterns_learned:
                        self.logger.info(f"Learned patterns: {patterns_learned}")
            else:
                result['applied'] = False
            
            results.append(result)
        
        return results
    
    def classify_all_by_pattern(self, pattern: str, category: str, subcategory: str = None, 
                               confidence_threshold: float = 0.8) -> int:
        """
        Classify all transactions matching a pattern using AI confidence scoring
        """
        # Get all uncategorized transactions
        uncategorized = self.db.get_uncategorized_transactions()
        classified_count = 0
        
        for tx_id, run_date, account, description, amount, action, payee in uncategorized:
            text = f"{description} {action}".lower()
            
            if pattern.lower() in text:
                # Use AI to validate this classification
                suggested_cat, suggested_sub, confidence = self.classify_transaction_text(
                    description, action, amount, payee, None
                )
                
                # If AI agrees or we have high confidence in the pattern, apply it
                if (suggested_cat == category or confidence < 0.5) and confidence >= confidence_threshold:
                    success = self.db.update_transaction_category(
                        tx_id, category, subcategory, None
                    )
                    if success:
                        classified_count += 1
        
        return classified_count

    def get_problematic_transactions(self, sample_size: int = 25) -> List[Tuple]:
        """
        Get transactions that likely need fixing - poor payee extraction or misclassification
        """
        import sqlite3
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        try:
            # Look for transactions with problematic patterns
            cursor.execute('''
                SELECT DISTINCT t.id, t.run_date, t.account, t.description, t.amount, t.action, 
                       t.payee, t.type, c.name as category, s.name as subcategory
                FROM transactions t
                LEFT JOIN categories c ON t.category_id = c.id
                LEFT JOIN subcategories s ON t.subcategory_id = s.id
                WHERE 
                    -- Generic payee names that could be improved
                    (t.payee LIKE '%Chase Bank%' OR
                     t.payee LIKE '%Debit Card Purchase%' OR 
                     t.payee LIKE '%Pos%' OR
                     t.payee LIKE '%POS%' OR
                     t.payee = 'No Description' OR
                     t.payee IS NULL OR
                     -- Likely misclassifications  
                     (c.name = 'Banking' AND t.action LIKE '%DEBIT CARD PURCHASE%') OR
                     (c.name = 'Banking' AND t.action NOT LIKE '%TRANSFER%' AND t.action NOT LIKE '%FEE%' AND t.action NOT LIKE '%INTEREST%'))
                ORDER BY t.run_date DESC
                LIMIT ?
            ''', (sample_size * 2,))  # Get more to filter from
            
            results = cursor.fetchall()
            
            # Filter and limit to sample_size
            return results[:sample_size] if results else []
            
        except Exception as e:
            self.logger.error(f"Error fetching problematic transactions: {e}")
            return []
        finally:
            conn.close()

    def fix_transaction_issues(self, sample_size: int = 25, auto_apply: bool = False) -> List[Dict]:
        """
        Find and fix problematic transactions using learned patterns and LLM-like analysis
        """
        problematic_transactions = self.get_problematic_transactions(sample_size)
        
        if not problematic_transactions:
            self.logger.info("No problematic transactions found")
            return []
        
        results = []
        
        for tx_data in problematic_transactions:
            tx_id, run_date, account, description, amount, action, current_payee, tx_type, current_category, current_subcategory = tx_data
            
            # First, check if learned patterns can fix this
            pattern_match = self.db.find_matching_pattern(description, action, current_payee)
            
            if pattern_match:
                # Use learned pattern
                new_cat_id, new_sub_id, confidence, new_category, new_subcategory = pattern_match
                suggested_payee = current_payee  # Keep existing payee if pattern matched
            else:
                # Use LLM-like analysis to suggest improvements
                new_category, new_subcategory, confidence = self.classify_transaction_text(
                    description, action, amount, current_payee, tx_type
                )
                
                # Try to extract better payee name
                from csv_parser import CSVParser
                parser = CSVParser(self.db)
                suggested_payee = parser.extract_payee(action, description)
                
                # If standard extraction failed, try some specific patterns for dividends and other cases
                if not suggested_payee or suggested_payee == current_payee or suggested_payee in ['No Description', 'Chase Bank']:
                    if "DIVIDEND RECEIVED" in action and "FIDELITY" in action:
                        suggested_payee = "Fidelity Government Money Market"
                    elif "SQ *" in action:
                        # Square payment - extract merchant name
                        import re
                        sq_match = re.search(r'SQ \*([A-Z][A-Z0-9\s]+?)(?:\s+[A-Z]{2}\d|\s+[A-Z]{2}\s+\d|$)', action.upper())
                        if sq_match:
                            suggested_payee = f"Square ({sq_match.group(1).strip()})"
                        else:
                            self.logger.debug(f"SQ pattern found but no match in: {action}")
                    
                # Ensure we have a fallback
                if not suggested_payee:
                    suggested_payee = current_payee
            
            # Determine if this is actually an improvement
            needs_payee_fix = (not current_payee or 
                             current_payee in ['No Description', 'Chase Bank'] or
                             'Debit Card Purchase' in current_payee or
                             'Pos' in current_payee or
                             (suggested_payee and suggested_payee != current_payee and len(suggested_payee) > 5))
            
            needs_category_fix = (not current_category or 
                                current_category == 'Banking' and 'DEBIT CARD PURCHASE' in action)
            
            # Always show if we found problems, even if no improvements suggested
            has_problems = (not current_payee or 
                          current_payee in ['No Description', 'Chase Bank'] or
                          'Debit Card Purchase' in current_payee or
                          'Pos' in current_payee or
                          not current_category or
                          (current_category == 'Banking' and 'DEBIT CARD PURCHASE' in action))
            
            if not has_problems:
                continue  # Skip if no obvious problems
            
            result = {
                'id': tx_id,
                'date': run_date,
                'account': account,
                'description': description,
                'amount': amount,
                'action': action,
                'current_payee': current_payee,
                'current_category': current_category,
                'current_subcategory': current_subcategory,
                'suggested_payee': suggested_payee,
                'suggested_category': new_category if needs_category_fix else current_category,
                'suggested_subcategory': new_subcategory if needs_category_fix else current_subcategory,
                'confidence': confidence,
                'payee_improved': suggested_payee != current_payee,
                'category_improved': needs_category_fix
            }
            
            # Apply fixes if requested and confidence is high enough
            if auto_apply and confidence > 0.7 and (needs_payee_fix or needs_category_fix):
                success = True
                
                # Update payee if improved
                if needs_payee_fix and suggested_payee != current_payee:
                    success &= self.db.update_transaction_payee(tx_id, suggested_payee)
                
                # Update category if improved  
                if needs_category_fix:
                    success &= self.db.update_transaction_category(
                        tx_id, new_category, new_subcategory, None
                    )
                    
                    # Learn patterns from successful fixes
                    if success:
                        category_id = self.db.get_or_create_category(new_category)
                        subcategory_id = self.db.get_or_create_subcategory(category_id, new_subcategory) if new_subcategory else None
                        patterns_learned = self.db.extract_and_learn_patterns(
                            description, action, category_id, subcategory_id, confidence
                        )
                        if patterns_learned:
                            self.logger.info(f"Learned patterns from fix: {patterns_learned}")
                
                result['applied'] = success
                if success:
                    self.logger.info(f"Fixed transaction {tx_id}: payee='{suggested_payee}', category={new_category}/{new_subcategory}")
            else:
                result['applied'] = False
            
            results.append(result)
        
        return results