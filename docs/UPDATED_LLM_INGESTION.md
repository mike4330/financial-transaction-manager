# LLM CSV Ingestion - Now Processing Full Files with Deduplication

## Updates Made

### ✅ Full CSV Processing
- Now processes **entire CSV file**, not just samples
- LLM analyzes structure from sample (10 rows)
- Applies mapping to all rows in file

### ✅ Automatic Duplicate Detection
- Uses existing hash-based deduplication (date + account + action + amount)
- Compares against existing database transactions
- Shows breakdown: new vs duplicate transactions
- Safe to re-run on same file - won't create duplicates

### ✅ Improved Payee/Type Extraction
- Extracts payee names from transaction action text
- Identifies transaction types (Debit Card, ACH, Transfer, etc.)
- Handles investment transactions (sets payee=null, preserves symbol)

### ✅ Better Statistics
```
Output now shows:
  Total rows in CSV: 150
  New transactions: 45
  Duplicates (already in DB): 100
  Skipped (pending): 5
  Errors: 0
```

## How It Works

### Step 1: LLM Analysis (Sample Only)
```
• Reads 10 sample rows from CSV
• Calls Claude API once (~$0.02)
• Gets column mappings, account info, extraction patterns
```

### Step 2: Full File Processing (Local)
```
• Applies LLM's mappings to ALL rows
• Extracts payee/type using discovered patterns
• Generates hash for each transaction
• Checks database for duplicates
• Inserts only new transactions
```

### Cost: Still Dirt Cheap
- **1 API call per file** (not per transaction!)
- ~$0.02 per CSV file regardless of size
- Processing 50 transactions/file = $0.02
- Processing 500 transactions/file = still $0.02!

## Usage

### Quick Start
```bash
export ANTHROPIC_API_KEY='your-key'
./test_llm_ingest.sh
```

### Manual
```bash
# Dry run (shows duplicates, doesn't import)
python3 llm_csv_ingest.py ./test-transactions.csv --dry-run

# Live import
python3 llm_csv_ingest.py ./test-transactions.csv
```

## Overlapping Files - No Problem!

The system handles overlapping data perfectly:

```bash
# Import original file
$ python3 llm_csv_ingest.py ./history_june.csv
  New transactions: 50
  Duplicates: 0

# Import updated file with same June + new July data
$ python3 llm_csv_ingest.py ./history_june_july.csv
  New transactions: 30      # Only July transactions
  Duplicates: 50            # June already in DB
```

## Deduplication Logic

Transactions are considered duplicates if they have the same:
- Run date
- Account number
- Action text
- Amount
- Description

This matches exactly what the regex-based importer does, ensuring consistency.

## Example Output

```
================================================================================
LLM-BASED CSV INGESTION
================================================================================

File: ./test-transactions.csv
Mode: LIVE (will insert to database)

[1/5] Gathering database context...
  ✓ 15 sample transactions
  ✓ 30 categories loaded
  ✓ 8 known accounts

[2/5] Analyzing CSV structure...
  ✓ Found 17 columns
  ✓ Sampled 10 rows

[3/5] Building LLM prompt...
  ✓ Prompt size: 8543 characters

[4/5] Analyzing with Claude API...
📞 Calling Claude API...
✓ API call successful
  Tokens: 3245 in / 1823 out
  ✓ Response saved to: ./test-transactions_llm_response.json

[5/5] Processing full CSV file...

  Account: Individual - TOD (Z06431462)
  Date column: Run Date
  Amount column: Amount
  Action column: Action

✓ Processing complete!
  Total rows in CSV: 150
  New transactions: 45
  Duplicates (already in DB): 100
  Skipped (pending): 5
  Errors: 0

💡 Next steps:
  View new transactions: python3 main.py --stats
  Categorize with AI: python3 main.py --ai-classify 25 --ai-auto-apply
```

## What Gets Saved

- **Database**: New transactions only (duplicates skipped)
- **JSON Response**: Full LLM analysis saved as `{filename}_llm_response.json`
  - Column mappings
  - Account inference
  - Extraction patterns
  - Sample transaction analysis

## Advantages Over Regex Method

| Feature | Regex Method | LLM Method |
|---------|--------------|------------|
| Duplicate Detection | ✅ Hash-based | ✅ Same hash-based |
| Full File Processing | ✅ All rows | ✅ All rows |
| Column Mapping | ❌ Hardcoded | ✅ Dynamic |
| Account Inference | ❌ Hardcoded map | ✅ Auto-detected |
| Payee Extraction | ❌ 150+ lines regex | ✅ Pattern learning |
| Cost per File | $0 | ~$0.02 |
| Maintenance | ⚠️ High (636 lines) | ✅ Low (0 regex) |

## Next Steps After Import

```bash
# 1. View statistics
python3 main.py --stats

# 2. See uncategorized transactions
python3 main.py --uncategorized 20

# 3. Auto-categorize with AI
python3 main.py --ai-classify 25 --ai-auto-apply

# 4. Start web interface
python3 api_server.py  # Terminal 1
cd frontend && npm run dev  # Terminal 2
```

## Files

- `llm_csv_ingest.py` - Production ingestion script
- `test_llm_ingest.sh` - Interactive test runner
- `README_LLM_INGESTION.md` - Setup guide
- `UPDATED_LLM_INGESTION.md` - This file

## Ready to Use!

The system is production-ready for your use case (dozens of transactions):
- ✅ Handles overlapping data
- ✅ One API call per file
- ✅ Extracts payees and types
- ✅ Automatic deduplication
- ✅ Cost: ~$0.05-0.10/month
