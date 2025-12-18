# Full LLM-Powered Import Flow

## The Complete Process

### What Happens Now:

```
1. Load CSV → Find New Transactions → Send to LLM → Categorize & Normalize
                                                              ↓
                                                    Learn Patterns for Future
```

## Step-by-Step Process

### [1/6] Gather Database Context
- Load existing categories/subcategories
- Get sample transactions for reference
- Identify known accounts

### [2/6] Analyze CSV Structure (LLM Call #1)
- Sample 10 rows from CSV
- **API Call**: Analyze structure (~$0.01-0.02)
- Determines:
  - Column mappings
  - Account inference
  - Payee extraction patterns
  - Date format
  - Pending transaction indicators

### [3-5/6] Process Full CSV
- Apply LLM's mappings to ALL rows
- Extract payee/type for each transaction
- Check for duplicates (hash-based)
- Auto-categorize using learned patterns (FREE)
- Identify new transactions needing categorization

### [6/6] LLM Categorization (LLM Call #2)
- **Only for NEW uncategorized transactions**
- **API Call**: Categorize batch (~$0.01-0.03 per 50 transactions)
- For each transaction:
  - Assigns category/subcategory
  - Normalizes payee name
  - Learns pattern for future

## Cost Analysis

### Typical Import Scenario

**File with 50 transactions, 30 new, 20 already in DB:**

```
Step 1-5: CSV Analysis
  → 1 API call
  → Cost: ~$0.02

Step 6: Categorization
  → Check learned patterns: 30 transactions
    - 15 matched existing patterns → FREE
    - 15 need LLM categorization
  → 1 API call for 15 transactions
  → Cost: ~$0.01

Total: ~$0.03 per file
```

### Monthly Cost for "Dozens of Transactions"

**Scenario: 2 imports/month, 50 transactions each**

```
Month 1 (building pattern library):
  Import 1: $0.02 (analysis) + $0.03 (categorize 50) = $0.05
  Import 2: $0.02 (analysis) + $0.02 (categorize 20*) = $0.04
  Total: $0.09
  * 30 transactions matched patterns from Import 1

Month 2 (patterns maturing):
  Import 1: $0.02 (analysis) + $0.01 (categorize 10*) = $0.03
  Import 2: $0.02 (analysis) + $0.01 (categorize 8*) = $0.03
  Total: $0.06
  * ~80% auto-categorized via patterns

Month 6 (mature patterns):
  Import 1: $0.02 (analysis) + $0.00 (all matched!) = $0.02
  Import 2: $0.02 (analysis) + $0.00 (all matched!) = $0.02
  Total: $0.04

Annual cost: ~$0.60 - $1.20
```

## What You Get

### Full Categorization
```
✓ Import complete!
  Total new transactions: 45
  Pattern-matched: 20 (using learned patterns)
  LLM-categorized: 25 (intelligent analysis)
  Fully categorized: 45/45 (100%)

💡 Summary:
  All transactions categorized automatically!
  Patterns learned for future imports
```

### Intelligent Payee Normalization

**Before:**
```
- "DEBIT CARD PURCHASE WALMART SUPER CENTER #1234 VA12345"
- "WALMART SUPERCENTER 5678"
- "WAL-MART #9012"
```

**After LLM:**
```
- "Walmart"
- "Walmart"
- "Walmart"
```

### Smart Categorization

**Transaction:** `-$150.00 | DEBIT CARD PURCHASE STATE FARM`

**LLM Analysis:**
```json
{
  "category": "Insurance",
  "subcategory": "Auto Insurance",
  "normalized_payee": "State Farm",
  "confidence": 0.95,
  "reasoning": "Recurring insurance payment to State Farm"
}
```

## Output Example

```
================================================================================
LLM-BASED CSV INGESTION WITH AUTO-CATEGORIZATION
================================================================================

File: ./test-transactions.csv
Mode: LIVE (will insert and categorize)

[1/6] Gathering database context...
  ✓ 15 sample transactions
  ✓ 30 categories loaded
  ✓ 8 known accounts

[2/6] Analyzing CSV structure...
  ✓ Found 17 columns
  ✓ Sampled 10 rows

[3/6] Building LLM prompt for CSV analysis...
  ✓ Prompt size: 8543 characters

[4/6] Calling Claude API for CSV structure analysis...
📞 Calling Claude API...
✓ API call successful
  Tokens: 3245 in / 1823 out

[5/6] Processing full CSV file...
  Account: Individual - TOD (Z06431462)

✓ CSV Processing complete!
  Total rows in CSV: 150
  New transactions: 45
  Auto-categorized: 20 (using learned patterns)
  Duplicates (already in DB): 100
  Skipped (pending): 5

[6/6] LLM Categorization of new transactions...
  Categorizing 25 uncategorized transactions...
📞 Calling Claude API for categorization...
✓ API call successful
  Tokens: 2156 in / 1432 out
  ✓ Categorized 25 transactions with LLM

✓ Import complete!
  LLM categorized: 25 transactions

💡 Summary:
  Total new transactions: 45
  Pattern-matched: 20
  LLM-categorized: 25
  Fully categorized: 45/45 (100%)

💡 Next steps:
  View transactions: python3 main.py --stats
  Web interface: python3 api_server.py && cd frontend && npm run dev
```

## Benefits

### 1. Zero Manual Work
- No need to run separate categorization command
- Everything done during import
- 100% categorization rate

### 2. Intelligent Analysis
- Context-aware categorization
- Normalized merchant names
- High confidence assignments

### 3. Learning System
- Patterns saved for future
- Auto-categorization rate increases over time
- Eventually mostly pattern-based (free & instant)

### 4. Cost Efficient
- Only categorizes NEW transactions
- Batch processing (50 at a time)
- Learns patterns to reduce future API calls
- Total cost: ~$0.60-1.20/year for typical usage

## Comparison

### Old Flow (Regex Import)
```
1. Import CSV with regex parser
2. View uncategorized: python3 main.py --uncategorized 50
3. Categorize: python3 main.py --ai-classify 50 --ai-auto-apply
4. Check results

Manual steps: 3-4
Time: 5-10 minutes
```

### New Flow (Full LLM)
```
1. ./test_llm_ingest.sh
2. Confirm import
3. Done!

Manual steps: 1
Time: 1 minute
Categorization: 100%
```

## When Patterns Are Used

The system is smart about costs:

```
Transaction comes in:
  ↓
Check learned patterns first (FREE)
  ↓
Pattern found? → Use it (instant, $0)
  ↓
No pattern? → Add to LLM batch (categorize with others)
  ↓
After categorization → Learn pattern for next time
```

After a few months, 90%+ of transactions match patterns and are categorized for free!

## Ready to Test

```bash
export ANTHROPIC_API_KEY='your-key'
cp ~/Downloads/History_*.csv ./test-transactions.csv
./test_llm_ingest.sh
```

You'll see full categorization happen automatically!
