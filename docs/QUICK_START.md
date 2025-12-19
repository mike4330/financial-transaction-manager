# Quick Start: LLM CSV Ingestion

## Setup (One Time)

```bash
# 1. Install dependencies
pip install anthropic

# 2. Set API key
export ANTHROPIC_API_KEY='sk-ant-api03-...'
```

## Import New Transactions

```bash
# 1. Copy your CSV file
cp ~/Downloads/History_for_Account_*.csv ./test-transactions.csv

# 2. Run the import script
./test_llm_ingest.sh
```

## What You'll See

### Step 1: Dry Run Analysis
```
Current database stats:
  Total transactions: 5,432

================================================================================
LLM-BASED CSV INGESTION
================================================================================

File: ./test-transactions.csv
Mode: DRY RUN (no database changes)

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
```

### Step 2: Preview Table
```
================================================================================
New Transactions (45 transactions)
================================================================================
Date         Amount        Type               Payee                     Action
--------------------------------------------------------------------------------
2025-11-01   -$25.00       Debit Card         Walmart                   DEBIT CARD PURCHASE WALMART...
2025-11-01   -$5.99        Debit Card         Amazon                    DEBIT CARD PURCHASE Amazon.com...
2025-11-02   -$150.00      Direct Debit       State Farm                DIRECT DEBIT STATE FARM RO...
2025-11-03   $2,500.00     Direct Deposit     Employer                  DIRECT DEPOSIT PAYROLL...
...
--------------------------------------------------------------------------------
Total:                     $1,234.56
================================================================================

Summary by Transaction Type
================================================================================
Type                      Count          Total
--------------------------------------------------------------------------------
Debit Card                   35      -$1,245.32
Direct Debit                  5      -$1,234.56
Direct Deposit                3       $5,000.00
Transfer                      2         $500.00

Summary by Month
================================================================================
Month           Count          Total
--------------------------------------------------------------------------------
2025-11          45       $1,234.56
================================================================================

💡 45 transactions need categorization
   Run: python3 main.py --ai-classify 25 --ai-auto-apply
```

### Step 3: Confirmation
```
Review the LLM analysis:
  • Column mappings: ./test-transactions_llm_response.json
  • Import results: ./test-transactions_import_result.json

Proceed with actual import? (y/N)
```

### Step 4: Live Import (if you press 'y')
```
================================================================================
STEP 2: Live Import
================================================================================

[Processing happens...]

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

## Files Created

After running, you'll have:

- `test-transactions_llm_response.json` - LLM's analysis (column mappings, patterns)
- `test-transactions_import_result.json` - Import results (new transactions list)

## Manual Commands

### Dry run only
```bash
python3 llm_csv_ingest.py ./test-transactions.csv --dry-run
```

### View results table
```bash
python3 show_new_transactions.py ./test-transactions_import_result.json
```

### Live import
```bash
python3 llm_csv_ingest.py ./test-transactions.csv
```

## After Import

### View all transactions
```bash
python3 main.py --stats
```

### See uncategorized
```bash
python3 main.py --uncategorized 20
```

### Auto-categorize with AI
```bash
python3 main.py --ai-classify 25 --ai-auto-apply
```

### Start web interface
```bash
# Terminal 1
python3 api_server.py

# Terminal 2
cd frontend && npm run dev
```

## Cost

- **~$0.02 per CSV file** (one API call regardless of file size)
- For dozens of transactions/month: **~$0.10/month total**

## Safety Features

✅ **Duplicate Detection** - Won't import same transactions twice
✅ **Dry Run Mode** - Preview before importing
✅ **Pending Skip** - Automatically skips uncleared transactions
✅ **Hash-based** - Same deduplication as regex method

## Troubleshooting

### No new transactions shown?
- All transactions are already in database (duplicates)
- Or all are pending/uncleared (check CSV for "OUTSTAND AUTH")

### Want to re-categorize existing transactions?
```bash
python3 main.py --ai-classify 50 --ai-auto-apply
```

### Need to check what's in the database?
```bash
sqlite3 transactions.db "SELECT COUNT(*) FROM transactions"
sqlite3 transactions.db "SELECT run_date, payee, amount FROM transactions ORDER BY run_date DESC LIMIT 10"
```
