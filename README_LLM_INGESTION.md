# LLM-Based CSV Ingestion

## Quick Start

### 1. Set up your API key

```bash
# Option A: Environment variable
export ANTHROPIC_API_KEY='sk-ant-api03-...'

# Option B: Create .env file
cp .env.example .env
# Edit .env and add your key
source .env
```

Get your API key from: https://console.anthropic.com/settings/keys

### 2. Place your CSV file

```bash
# Copy your transaction CSV to the project directory
cp ~/Downloads/History_for_Account_*.csv ./test-transactions.csv
```

### 3. Run the test script

```bash
./test_llm_ingest.sh
```

This will:
1. Run a dry-run analysis (no database changes)
2. Show you the LLM's interpretation
3. Ask for confirmation before importing

## Manual Usage

### Dry run (analyze only)
```bash
python3 llm_csv_ingest.py ./test-transactions.csv --dry-run
```

### Live import
```bash
python3 llm_csv_ingest.py ./test-transactions.csv
```

### Custom database
```bash
python3 llm_csv_ingest.py ./test-transactions.csv --db custom.db
```

### Pass API key directly
```bash
python3 llm_csv_ingest.py ./test-transactions.csv --api-key sk-ant-...
```

## How It Works

1. **Context Gathering** - Reads sample transactions, categories, and known accounts from your database
2. **CSV Analysis** - Samples 10 rows from the CSV file
3. **LLM Mapping** - Sends context to Claude API to determine:
   - Column mappings (date, amount, action, etc.)
   - Account inference (from filename or CSV data)
   - Payee extraction patterns
   - Transaction type classification
   - Pending transaction detection
4. **Processing** - Applies LLM's mapping to entire CSV file
5. **Import** - Inserts transactions to database (with duplicate detection)

## Output Files

- `test-transactions_llm_response.json` - Full LLM analysis for debugging

## Cost Estimation

For a typical CSV with 50 transactions:
- Input tokens: ~3,000 (context + sample)
- Output tokens: ~1,500 (mapping response)
- Total cost: **~$0.02 per file**

For your anticipated volume (dozens of transactions per month):
- Monthly cost: **~$0.05 - $0.10**

## Advantages Over Regex Method

✅ **No hardcoded rules** - Adapts to CSV format changes automatically
✅ **Intelligent normalization** - Better merchant name extraction
✅ **Account inference** - Extracts account from filename patterns
✅ **Explainable** - Shows reasoning for decisions
✅ **Pattern learning** - Uses existing transactions as examples
✅ **Data quality** - Identifies pending/invalid transactions

## Checking Results

```bash
# View statistics
python3 main.py --stats

# View uncategorized transactions
python3 main.py --uncategorized 20

# Categorize with AI
python3 main.py --ai-classify 25 --ai-auto-apply
```

## Troubleshooting

### "API key required" error
```bash
# Check if key is set
echo $ANTHROPIC_API_KEY

# Set it
export ANTHROPIC_API_KEY='your-key-here'
```

### "No valid header found" error
The CSV format may be unusual. Check:
- File encoding (should be UTF-8)
- Header row location
- Column names (should contain "Date", "Amount", etc.)

### "Failed to parse API response" error
Rare, but if it happens:
1. Check `test-transactions_llm_response.json` for raw response
2. The LLM may have returned explanation text instead of pure JSON
3. Try with fewer sample rows: edit `num_rows=10` to `num_rows=5` in the script

## Files Created

- `llm_csv_ingest.py` - Main ingestion script
- `test_llm_ingest.sh` - Interactive test script
- `.env.example` - API key template
- `README_LLM_INGESTION.md` - This file

## Next Steps

After successful import:
1. Review transactions: `python3 main.py --uncategorized 20`
2. Categorize with AI: `python3 main.py --ai-classify 25 --ai-auto-apply`
3. Start web interface: `python3 api_server.py` + `cd frontend && npm run dev`
