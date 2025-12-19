# What the LLM Does - Current Implementation

## Two LLM API Calls Per Import

### API Call #1: CSV Structure Analysis
**Location:** `process_csv_with_llm()` → `build_llm_prompt()` → `call_claude_api()`

**Input:**
- 10 sample rows from CSV
- Known accounts from database
- Available categories (first 30)
- Sample existing transactions (10)

**What LLM Analyzes:**
```json
{
  "column_mapping": {
    "date_column": "Run Date",
    "action_column": "Action", 
    "amount_column": "Amount",
    "symbol_column": "Symbol",
    "description_column": "Description"
  },
  "account_inference": {
    "account": "Individual - TOD",
    "account_number": "Z06431462",
    "source": "filename"
  },
  "extraction_logic": {
    "payee_extraction_pattern": "Extract merchant after 'DEBIT CARD PURCHASE'",
    "pending_transaction_indicator": "OUTSTAND AUTH",
    "date_format": "MM/DD/YYYY"
  }
}
```

**What LLM DOESN'T Do:**
- ❌ Does NOT categorize individual transactions
- ❌ Does NOT normalize payee names yet
- ❌ Does NOT process the full CSV

**Cost:** ~$0.01-0.02 (3,000-4,000 tokens)


### Between API Calls: Local Processing
**Location:** `process_csv_with_llm()` main loop

**What Happens Locally (No API Calls):**
1. Apply LLM's column mappings to ALL rows in CSV
2. Extract payee/type using simple regex patterns
3. Check each transaction hash against database (duplicate detection)
4. Try to auto-categorize using learned patterns from DB
5. Collect NEW uncategorized transactions for LLM

**Example:**
```
Total rows: 150
  → 100 duplicates (skip)
  → 5 pending (skip)
  → 45 NEW transactions
    → 20 matched learned patterns (auto-categorized, FREE)
    → 25 need LLM categorization
```


### API Call #2: Categorization & Normalization
**Location:** `process_csv_with_llm()` → `build_categorization_prompt()` → `call_claude_api()`

**Input:**
- Only NEW uncategorized transactions (max 50 at a time)
- Available categories (all of them, organized by category)
- Sample existing transactions for reference

**What LLM Does:**
```json
{
  "categorized_transactions": [
    {
      "index": 0,
      "category_id": 171,
      "subcategory_id": 171,
      "normalized_payee": "Walmart",
      "confidence": 0.95,
      "reasoning": "Grocery store purchase based on merchant and amount"
    },
    {
      "index": 1, 
      "category_id": 249,
      "subcategory_id": 476,
      "normalized_payee": "State Farm",
      "confidence": 0.92,
      "reasoning": "Recurring insurance payment"
    }
  ]
}
```

**For Each Transaction:**
1. Assigns category_id and subcategory_id
2. Normalizes payee name (e.g., "WALMART SUPER #1234" → "Walmart")
3. Provides confidence score
4. Explains reasoning

**After Categorization:**
- Updates transactions in database
- Learns patterns for future (if confidence > 0.7)
- Pattern saved: "Walmart" → Food & Dining/Groceries

**Cost:** ~$0.01-0.03 (2,000-5,000 tokens depending on # of transactions)


## Complete Flow Example

### Input CSV:
```
150 rows total:
  - 100 exact duplicates of existing transactions
  - 5 pending (OUTSTAND AUTH)
  - 45 new transactions
```

### Step 1: CSV Analysis (LLM Call #1)
```
Samples 10 rows → Sends to LLM → Gets mappings
Cost: $0.02
```

### Step 2: Local Processing
```
Applies mappings to all 150 rows:
  - Identifies 100 duplicates → SKIP
  - Identifies 5 pending → SKIP  
  - Processes 45 new transactions:
    - Extracts payee using regex
    - Checks learned patterns:
      * 20 match existing patterns (Walmart, Amazon, etc.) → AUTO-CATEGORIZED
      * 25 don't match any pattern → NEED LLM
Cost: $0 (local)
```

### Step 3: LLM Categorization (LLM Call #2)
```
Sends 25 uncategorized to LLM:
  - Gets category/subcategory for each
  - Gets normalized payee names
  - Updates database
  - Learns 15 new patterns (some merchants repeat)
Cost: $0.02
```

### Total Cost: ~$0.04


## What Gets Learned

After this import, database now has patterns like:
```sql
INSERT INTO classification_patterns (pattern, category_id, subcategory_id)
VALUES 
  ('Walmart', 171, 171),           -- Food & Dining/Groceries
  ('State Farm', 249, 476),        -- Bills/Insurance
  ('Amazon', 1, 1),                -- Shopping/Online
  ...
```

### Next Import:
```
45 new transactions:
  - 35 match learned patterns → AUTO-CATEGORIZED (FREE)
  - 10 new merchants → LLM categorize ($0.01)

Total cost: $0.02 (structure) + $0.01 (categorization) = $0.03
```


## Summary Table

| Task | Who Does It | Cost | When |
|------|-------------|------|------|
| Analyze CSV structure | LLM Call #1 | ~$0.02 | Every import |
| Map columns to database | LLM Call #1 | (included) | Every import |
| Infer account from filename | LLM Call #1 | (included) | Every import |
| Process full CSV | Local code | $0 | Every import |
| Extract payee (basic) | Local regex | $0 | Every import |
| Detect duplicates | Local DB check | $0 | Every import |
| Auto-categorize via patterns | Local DB check | $0 | Every import |
| **Categorize new transactions** | **LLM Call #2** | **~$0.01-0.03** | **Only for uncategorized** |
| **Normalize payee names** | **LLM Call #2** | **(included)** | **Only for uncategorized** |
| Learn patterns | Local DB insert | $0 | After categorization |


## Key Points

1. **LLM only categorizes NEW transactions** that don't match existing patterns
2. **Pattern matching is free and instant** (local database lookup)
3. **Cost decreases over time** as more patterns are learned
4. **Batch processing** - categorizes up to 50 transactions per API call
5. **Payee normalization** happens during categorization (same API call)


## What You Get

**First Import (no patterns):**
```
50 new transactions
  → LLM categorizes: 50 ($0.03)
  → Learns: ~30 unique merchant patterns
```

**Second Import (some patterns):**
```
45 new transactions  
  → Pattern matched: 25 (FREE)
  → LLM categorizes: 20 ($0.02)
  → Learns: ~10 more patterns
```

**Sixth Import (mature patterns):**
```
50 new transactions
  → Pattern matched: 48 (FREE)
  → LLM categorizes: 2 ($0.01)
  → Learns: ~1 new pattern
```

The system gets smarter and cheaper over time!
