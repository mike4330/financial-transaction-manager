# Production Testing Guide - LLM Payee Extraction

## Pre-Test Checklist

### 1. Environment Setup

```bash
# Set API key
export ANTHROPIC_API_KEY='sk-ant-api03-...'

# Verify it's set
echo $ANTHROPIC_API_KEY

# Test basic extraction
python3 llm_payee_extractor.py --test-action "DEBIT CARD PURCHASE COSTCO WHOLESALE"
```

### 2. Backup Database

```bash
# Create backup before testing
cp transactions.db transactions.db.backup.$(date +%Y%m%d_%H%M%S)

# Verify backup
ls -lh transactions.db*
```

### 3. Check Current State

```bash
# Count transactions with missing payees
sqlite3 transactions.db "SELECT COUNT(*) FROM transactions WHERE (payee IS NULL OR payee = '' OR payee = 'No Description') AND symbol IS NULL;"

# Sample transactions that need fixing
sqlite3 transactions.db "SELECT id, run_date, action, payee FROM transactions WHERE (payee IS NULL OR payee = 'No Description') AND symbol IS NULL LIMIT 10;"
```

## Test Scenarios

### Scenario 1: Dry Run Test (Safe)

```bash
# Preview what LLM would extract (no database changes)
python3 llm_payee_fix.py --dry-run --limit 10

# Expected output:
# - Table showing TX ID, date, extracted payee, confidence
# - High confidence count (≥0.7)
# - Message: "DRY RUN - No changes made to database"
```

**What to check in logs:**
```bash
# Main log
tail -50 transaction_parser.log

# LLM-specific log (detailed)
tail -100 llm_payee_extraction.log
```

### Scenario 2: Small Batch Test (Real)

```bash
# Apply to 10 transactions only
python3 llm_payee_fix.py --apply --limit 10

# Verify updates
sqlite3 transactions.db "SELECT id, action, payee, updated_at FROM transactions WHERE updated_at > datetime('now', '-1 minute');"
```

**What to verify:**
- Updated payee names look correct
- Confidence scores were ≥0.7
- `updated_at` timestamp is recent
- Pattern caching occurred (check logs)

### Scenario 3: File Monitor Integration Test

```bash
# Start monitor with LLM enabled
python3 main.py --monitor --enable-llm-payee --verbose

# In another terminal, drop a test CSV
cp test-transactions.csv transactions/

# Watch the logs
tail -f transaction_parser.log | grep -E "LLM|payee|Regex"
```

**Expected flow:**
1. "Running regex-based payee extraction..."
2. "Regex payee extraction completed: extracted X payees"
3. "Running LLM fallback for missing payees..."
4. "Found Y transactions with missing payees"
5. "LLM payee extraction completed: extracted Z/Y payees"

### Scenario 4: Larger Batch Test

```bash
# Process 50 transactions
python3 llm_payee_fix.py --apply --limit 50 --verbose

# Check statistics
python3 llm_payee_fix.py --stats
```

## Logging Analysis

### Log Files Created

1. **transaction_parser.log** - Main system log
   - High-level events
   - Error summaries
   - Integration points

2. **llm_payee_extraction.log** - Detailed LLM operations
   - API call details (tokens used)
   - Individual extraction results
   - Pattern caching events
   - Full error traces

### Key Log Patterns to Look For

#### Success Pattern
```
INFO - STARTING LLM PAYEE EXTRACTION FALLBACK
INFO - Found 25 transactions with missing payees
INFO - Initializing LLM payee extractor...
INFO - LLM extractor initialized (caching: enabled, max_batch: 20)
INFO - Processing batch of 20 transactions
INFO - API call successful - Usage: 1250 input tokens, 450 output tokens
INFO - Batch complete: 18/20 payees extracted, 16 high confidence (≥0.7)
INFO - LLM PAYEE EXTRACTION SUMMARY:
INFO -   Total processed: 25
INFO -   Successfully updated: 22
INFO -   Low confidence (skipped): 2
INFO -   Failed: 1
INFO -   Patterns cached: 15 total
```

#### Individual Extraction Logs (llm_payee_extraction.log)
```
DEBUG - TX#12345: 'Target' (confidence: 0.92) - Clear merchant name in action
DEBUG - TX#12346: 'Starbucks' (confidence: 0.88) - Common coffee chain
INFO - Cached new pattern: 'TARGET' → 'Target' (from TX#12345)
```

#### Error Pattern (API Issue)
```
ERROR - Anthropic API error: RateLimitError: Rate limit exceeded
WARNING - LLM payee extraction disabled: API key not found
ERROR - Unexpected error in batch processing: [stack trace]
```

### Log Commands for Analysis

```bash
# Count successful extractions
grep "Successfully updated:" transaction_parser.log | tail -1

# See all cached patterns
grep "Cached new pattern:" llm_payee_extraction.log

# Check API token usage
grep "API call successful" llm_payee_extraction.log | grep -oP '\d+ input tokens' | awk '{sum+=$1} END {print "Total input tokens:", sum}'

# Find errors
grep -E "ERROR|WARNING" llm_payee_extraction.log | tail -20

# See extraction confidence distribution
grep "confidence:" llm_payee_extraction.log | grep -oP 'confidence: \d\.\d+' | sort | uniq -c

# Monitor real-time (during file monitor test)
tail -f llm_payee_extraction.log | grep -E "TX#|Batch|API call"
```

## Validation Checks

### After Each Test

1. **Database Integrity**
```bash
# Check for NULLs that shouldn't exist
sqlite3 transactions.db "SELECT COUNT(*) FROM transactions WHERE payee IS NULL AND symbol IS NULL AND type NOT LIKE '%Investment%';"

# Verify updated_at timestamps
sqlite3 transactions.db "SELECT COUNT(*) FROM transactions WHERE updated_at > datetime('now', '-1 hour');"
```

2. **Pattern Cache Growth**
```bash
# Count cached patterns
sqlite3 transactions.db "SELECT COUNT(*) FROM payee_extraction_patterns WHERE is_active = 1;"

# Top patterns by usage
sqlite3 transactions.db "SELECT pattern, replacement, usage_count FROM payee_extraction_patterns ORDER BY usage_count DESC LIMIT 20;"
```

3. **Cost Tracking**
```bash
# Extract token usage from logs
grep "API call successful" llm_payee_extraction.log | tail -10
# Calculate: ~$3 per 1M input tokens, ~$15 per 1M output tokens
```

## Troubleshooting

### Issue: "ANTHROPIC_API_KEY required"

```bash
# Check if set
env | grep ANTHROPIC

# Set it
export ANTHROPIC_API_KEY='your-key-here'

# Persist (add to ~/.bashrc or .env)
echo "export ANTHROPIC_API_KEY='your-key-here'" >> ~/.bashrc
```

### Issue: Low Confidence Results

Check logs for why:
```bash
grep "Low confidence" llm_payee_extraction.log
```

Common reasons:
- Ambiguous action text
- Generic descriptors ("TRANSFER", "PAYMENT")
- Missing context

### Issue: API Rate Limits

```bash
# Check for rate limit errors
grep "RateLimitError" llm_payee_extraction.log

# Solution: Reduce batch size or add delays
```

### Issue: JSON Parse Errors

```bash
# Find parse errors
grep "JSON parse error" llm_payee_extraction.log

# See the failed response
grep -A 5 "Failed response text:" llm_payee_extraction.log
```

## Rollback Procedure

If something goes wrong:

```bash
# Stop any running processes
pkill -f "main.py.*monitor"

# Restore from backup
cp transactions.db.backup.YYYYMMDD_HHMMSS transactions.db

# Verify restoration
sqlite3 transactions.db "SELECT COUNT(*) FROM transactions;"
```

## Success Metrics

After testing, evaluate:

1. **Extraction Rate**: Should be 85-95% for high confidence
2. **Accuracy**: Manually review 10-20 extractions
3. **Performance**: Check API latency in logs
4. **Cost**: Calculate from token usage
5. **Caching**: Verify patterns are being reused

## Next Steps After Successful Test

1. Enable for production file monitoring
2. Schedule periodic batch fixes for historical data
3. Monitor costs weekly
4. Review and approve cached patterns monthly

## Emergency Contacts

- API Issues: Check Anthropic status page
- Database Issues: Restore from backup
- Code Issues: Check GitHub issues or logs
