#!/usr/bin/env python3
"""
LLM-Powered Payee Extraction Service

Provides intelligent fallback for payee extraction when regex patterns fail.
Uses Claude API to extract merchant/payee names from transaction descriptions.

Architecture:
1. Regex patterns attempt extraction first (csv_parser.py)
2. If no match (payee is None), this service kicks in
3. LLM extracts payee with explanation
4. Successful extractions are cached as patterns for future use
5. Batch processing minimizes API calls

Usage:
    from llm_payee_extractor import LLMPayeeExtractor

    extractor = LLMPayeeExtractor(db)
    payees = extractor.extract_batch(failed_transactions)
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import anthropic
from database import TransactionDB


class LLMPayeeExtractor:
    """
    LLM-powered payee extraction with intelligent caching and batching.
    """

    def __init__(self, db: TransactionDB, api_key: Optional[str] = None,
                 enable_caching: bool = True, max_batch_size: int = 20):
        """
        Initialize LLM Payee Extractor

        Args:
            db: TransactionDB instance
            api_key: Anthropic API key (or use ANTHROPIC_API_KEY env var)
            enable_caching: Whether to cache successful extractions as patterns
            max_batch_size: Maximum transactions to process in one API call
        """
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.enable_caching = enable_caching
        self.max_batch_size = max_batch_size

        # Setup dedicated file logging for LLM operations
        self._setup_llm_logging()

        # Initialize Anthropic client
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY required. Set environment variable or pass api_key parameter.\n"
                "Get your key from: https://console.anthropic.com/settings/keys"
            )

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-3-5-sonnet-20241022"  # Fast, cost-effective model

    def _setup_llm_logging(self):
        """Setup dedicated file logging for LLM operations"""
        # Create dedicated log file for LLM operations
        llm_logger = logging.getLogger('llm_payee_extractor')
        llm_logger.setLevel(logging.DEBUG)

        # File handler for detailed LLM logs
        fh = logging.FileHandler('llm_payee_extraction.log')
        fh.setLevel(logging.DEBUG)

        # Detailed formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        fh.setFormatter(formatter)

        # Avoid duplicate handlers
        if not llm_logger.handlers:
            llm_logger.addHandler(fh)

        self.llm_logger = llm_logger

    def extract_single(self, transaction_id: int, action: str, description: str = "",
                      amount: float = 0.0) -> Optional[str]:
        """
        Extract payee for a single transaction using LLM

        Args:
            transaction_id: Transaction ID (for logging/caching)
            action: Transaction action text
            description: Transaction description text
            amount: Transaction amount

        Returns:
            Extracted payee name or None if extraction failed
        """
        result = self.extract_batch([{
            'id': transaction_id,
            'action': action,
            'description': description,
            'amount': amount
        }])

        return result[0]['payee'] if result and result[0]['payee'] else None

    def extract_batch(self, transactions: List[Dict]) -> List[Dict]:
        """
        Extract payees for multiple transactions in a single API call

        Args:
            transactions: List of dicts with keys: id, action, description, amount

        Returns:
            List of dicts with keys: id, payee, confidence, explanation
        """
        if not transactions:
            return []

        # Process in batches to respect API limits and token constraints
        all_results = []

        for i in range(0, len(transactions), self.max_batch_size):
            batch = transactions[i:i + self.max_batch_size]
            results = self._process_batch(batch)
            all_results.extend(results)

            # Cache successful extractions as patterns
            if self.enable_caching:
                self._cache_successful_extractions(batch, results)

        return all_results

    def _process_batch(self, batch: List[Dict]) -> List[Dict]:
        """Process a single batch of transactions via LLM"""

        # Build prompt
        prompt = self._build_extraction_prompt(batch)

        # Log batch processing start
        self.llm_logger.info(f"Processing batch of {len(batch)} transactions")
        self.llm_logger.debug(f"Transaction IDs: {[tx['id'] for tx in batch]}")

        try:
            # Call Claude API
            self.llm_logger.debug(f"Calling Claude API (model: {self.model})")
            self.llm_logger.debug(f"Prompt length: {len(prompt)} chars")

            message = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=0.0,  # Deterministic for consistent extractions
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Log API usage
            self.llm_logger.info(f"API call successful - Usage: {message.usage.input_tokens} input tokens, "
                                f"{message.usage.output_tokens} output tokens")

            # Parse response
            response_text = message.content[0].text
            self.llm_logger.debug(f"LLM response: {response_text[:500]}...")

            results = self._parse_llm_response(response_text, batch)

            # Log extraction results
            successful = sum(1 for r in results if r.get('payee'))
            high_confidence = sum(1 for r in results if r.get('confidence', 0) >= 0.7)

            self.llm_logger.info(f"Batch complete: {successful}/{len(batch)} payees extracted, "
                               f"{high_confidence} high confidence (≥0.7)")

            # Log individual results
            for result in results:
                if result.get('payee'):
                    self.llm_logger.debug(f"TX#{result['id']}: '{result['payee']}' "
                                        f"(confidence: {result.get('confidence', 0):.2f}) - "
                                        f"{result.get('explanation', '')}")
                else:
                    self.llm_logger.debug(f"TX#{result['id']}: No payee extracted - "
                                        f"{result.get('explanation', 'unknown')}")

            self.logger.info(f"LLM extracted payees for {len(results)}/{len(batch)} transactions")
            return results

        except anthropic.APIError as e:
            self.llm_logger.error(f"Anthropic API error: {e.__class__.__name__}: {e}")
            self.logger.error(f"LLM payee extraction failed: {e}")
            return [{'id': tx['id'], 'payee': None, 'confidence': 0.0, 'explanation': f'API error: {str(e)}'}
                    for tx in batch]
        except Exception as e:
            self.llm_logger.error(f"Unexpected error in batch processing: {e}", exc_info=True)
            self.logger.error(f"LLM payee extraction failed: {e}")
            return [{'id': tx['id'], 'payee': None, 'confidence': 0.0, 'explanation': str(e)}
                    for tx in batch]

    def _build_extraction_prompt(self, batch: List[Dict]) -> str:
        """Build prompt for LLM payee extraction"""

        transactions_text = []
        for i, tx in enumerate(batch):
            transactions_text.append(
                f"{i}. Action: {tx.get('action', '')}\n"
                f"   Description: {tx.get('description', '')}\n"
                f"   Amount: ${tx.get('amount', 0.0):.2f}"
            )

        prompt = f"""Extract the merchant/payee name from these bank transaction descriptions.

INSTRUCTIONS:
- Extract a clean, standardized merchant/payee name (e.g., "Walmart", "McDonald's", "State Farm")
- Ignore transaction codes, location codes, phone numbers, addresses
- Standardize common variations (e.g., "WAL-MART #1234" → "Walmart")
- Use proper capitalization and formatting
- If no clear payee exists (like "OUTSTANDING AUTH" or transfer between own accounts), return null
- For investment transactions (stock purchases, dividends), return null

TRANSACTIONS:
{chr(10).join(transactions_text)}

Respond with ONLY a JSON array of objects, one per transaction:
[
  {{"index": 0, "payee": "Merchant Name", "confidence": 0.95, "explanation": "brief reason"}},
  {{"index": 1, "payee": null, "confidence": 0.0, "explanation": "no clear merchant"}}
]

Return ONLY the JSON array, no other text."""

        return prompt

    def _parse_llm_response(self, response_text: str, batch: List[Dict]) -> List[Dict]:
        """Parse LLM JSON response and map back to transaction IDs"""

        try:
            # Extract JSON from response (handle potential markdown formatting)
            json_text = response_text.strip()
            self.llm_logger.debug(f"Parsing response, original format: {json_text[:100]}...")

            if json_text.startswith('```'):
                # Remove markdown code fences
                lines = json_text.split('\n')
                json_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else json_text
                json_text = json_text.replace('```json', '').replace('```', '').strip()
                self.llm_logger.debug("Removed markdown code fences")

            llm_results = json.loads(json_text)
            self.llm_logger.debug(f"Successfully parsed JSON with {len(llm_results)} results")

            # Map results back to transaction IDs
            results = []
            for result in llm_results:
                index = result.get('index', 0)
                if 0 <= index < len(batch):
                    results.append({
                        'id': batch[index]['id'],
                        'payee': result.get('payee'),
                        'confidence': result.get('confidence', 0.0),
                        'explanation': result.get('explanation', '')
                    })
                else:
                    self.llm_logger.warning(f"Invalid index {index} in LLM result (batch size: {len(batch)})")

            return results

        except json.JSONDecodeError as e:
            self.llm_logger.error(f"JSON parse error: {e}")
            self.llm_logger.error(f"Failed response text: {response_text[:500]}")
            self.logger.error(f"Failed to parse LLM response as JSON: {e}\nResponse: {response_text[:200]}")
            return [{'id': tx['id'], 'payee': None, 'confidence': 0.0, 'explanation': 'JSON parse error'}
                    for tx in batch]
        except Exception as e:
            self.llm_logger.error(f"Parse error: {e}", exc_info=True)
            self.logger.error(f"Error parsing LLM response: {e}")
            return [{'id': tx['id'], 'payee': None, 'confidence': 0.0, 'explanation': str(e)}
                    for tx in batch]

    def _cache_successful_extractions(self, batch: List[Dict], results: List[Dict]):
        """
        Cache successful LLM extractions as regex patterns for future use

        Stores patterns in payee_extraction_patterns table so regex can handle
        similar transactions in the future without LLM calls.
        """
        import sqlite3

        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()

            # Ensure table exists
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payee_extraction_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern TEXT NOT NULL,
                    replacement TEXT NOT NULL,
                    is_regex INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    usage_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(pattern, replacement)
                )
            ''')

            cached_count = 0
            skipped_count = 0

            for i, result in enumerate(results):
                # Only cache high-confidence successful extractions
                if result.get('confidence', 0.0) >= 0.8 and result.get('payee'):
                    tx = batch[i]
                    action = tx.get('action', '').strip()
                    payee = result['payee']

                    if not action or not payee:
                        skipped_count += 1
                        continue

                    # Create a simple substring pattern (not regex for now)
                    # Extract a distinctive part of the action text
                    pattern = self._extract_distinctive_pattern(action, payee)

                    if pattern:
                        try:
                            cursor.execute('''
                                INSERT OR IGNORE INTO payee_extraction_patterns
                                (pattern, replacement, is_regex, is_active, usage_count)
                                VALUES (?, ?, 0, 1, 1)
                            ''', (pattern, payee))

                            if cursor.rowcount > 0:
                                cached_count += 1
                                self.llm_logger.info(f"Cached new pattern: '{pattern}' → '{payee}' "
                                                    f"(from TX#{tx['id']})")
                                self.logger.debug(f"Cached pattern: '{pattern}' → '{payee}'")
                            else:
                                self.llm_logger.debug(f"Pattern already exists: '{pattern}' → '{payee}'")
                        except sqlite3.IntegrityError:
                            # Pattern already exists, that's fine
                            self.llm_logger.debug(f"Duplicate pattern (integrity): '{pattern}' → '{payee}'")
                    else:
                        skipped_count += 1
                        self.llm_logger.debug(f"Could not extract pattern from action: {action[:50]}")

            conn.commit()
            conn.close()

            if cached_count > 0:
                self.llm_logger.info(f"Pattern caching complete: {cached_count} new, {skipped_count} skipped")
                self.logger.info(f"Cached {cached_count} new payee extraction patterns")
            else:
                self.llm_logger.debug(f"No new patterns cached ({skipped_count} skipped)")

        except Exception as e:
            self.llm_logger.error(f"Failed to cache extraction patterns: {e}", exc_info=True)
            self.logger.warning(f"Failed to cache extraction patterns: {e}")

    def _extract_distinctive_pattern(self, action: str, payee: str) -> Optional[str]:
        """
        Extract a distinctive substring from action text that identifies the payee

        This creates simple text patterns that can be matched in future transactions
        without needing LLM calls.
        """
        import re

        # Convert to uppercase for pattern matching
        action_upper = action.upper()
        payee_upper = payee.upper()

        # Try to find the payee name or close variant in the action text
        # Look for the payee name (or parts of it) in the action
        payee_words = payee_upper.split()

        for word in payee_words:
            if len(word) >= 4 and word in action_upper:
                # Found a significant word from payee in action
                # Extract surrounding context for pattern
                match = re.search(rf'\b\w*{re.escape(word)}\w*\b', action_upper)
                if match:
                    return match.group(0)

        # If no direct match, try to extract merchant-like patterns
        # Look for words that appear to be merchant names (all caps, 3+ chars)
        merchant_pattern = r'\b([A-Z]{3,}(?:\s+[A-Z]{3,})?)\b'
        matches = re.findall(merchant_pattern, action_upper)

        # Return the first substantial match that's not a common keyword
        common_keywords = {'DEBIT', 'CREDIT', 'CARD', 'PURCHASE', 'PAYMENT', 'DEPOSIT',
                          'WITHDRAWAL', 'TRANSFER', 'DIRECT', 'ACH', 'CHECK', 'ONLINE'}

        for match in matches:
            if match not in common_keywords and len(match) >= 4:
                return match

        return None

    def get_stats(self) -> Dict:
        """Get statistics about LLM payee extraction usage"""
        import sqlite3

        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT COUNT(*), SUM(usage_count)
                FROM payee_extraction_patterns
                WHERE is_active = 1
            ''')

            row = cursor.fetchone()
            pattern_count = row[0] if row else 0
            total_usage = row[1] if row and row[1] else 0

            conn.close()

            return {
                'cached_patterns': pattern_count,
                'total_pattern_usage': total_usage,
                'cache_enabled': self.enable_caching
            }
        except Exception as e:
            self.logger.warning(f"Failed to get stats: {e}")
            return {'error': str(e)}


if __name__ == '__main__':
    """Test the LLM payee extractor"""
    import argparse

    parser = argparse.ArgumentParser(description='LLM Payee Extraction Test')
    parser.add_argument('--db', default='transactions.db', help='Database file')
    parser.add_argument('--test-action', help='Test action text to extract payee from')
    parser.add_argument('--stats', action='store_true', help='Show extraction statistics')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    db = TransactionDB(args.db)
    extractor = LLMPayeeExtractor(db)

    if args.stats:
        stats = extractor.get_stats()
        print("\nLLM Payee Extraction Statistics:")
        print(f"  Cached patterns: {stats.get('cached_patterns', 0)}")
        print(f"  Total pattern usage: {stats.get('total_pattern_usage', 0)}")
        print(f"  Cache enabled: {stats.get('cache_enabled', False)}")

    if args.test_action:
        print(f"\nTesting extraction on: {args.test_action}")
        result = extractor.extract_single(0, args.test_action, "", 0.0)
        print(f"Extracted payee: {result}")
