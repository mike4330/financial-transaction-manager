# How Auto-Categorization Works

## The System Uses **Learned Patterns**

The LLM ingestion doesn't directly categorize transactions. Instead, it uses the **same pattern-matching system** as the regex method - patterns learned from previously categorized transactions.

## How It Works

### 1. Pattern Learning (Happens Over Time)

When you categorize a transaction (manually or via AI):

```sql
-- Pattern is stored in database
INSERT INTO classification_patterns (
  pattern,           -- "WALMART" or "Amazon.com" etc
  pattern_type,      -- 'description', 'action', 'payee'
  category_id,       -- e.g., 171 (Food & Dining)
  subcategory_id,    -- e.g., 171 (Groceries)
  confidence         -- 0.8
)
```

### 2. Auto-Categorization (During Import)

When importing new transactions, the system:

```python
# For each new transaction:
pattern_match = db.find_matching_pattern(
    transaction['description'],  # e.g., "No Description"
    transaction['action'],        # e.g., "DEBIT CARD PURCHASE WALMART..."
    transaction['payee']          # e.g., "Walmart"
)

if pattern_match:
    # Automatically assign category
    transaction['category_id'] = matched_category
    transaction['subcategory_id'] = matched_subcategory
```

### 3. Example Flow

```
First Time Importing Amazon Purchase:
→ No pattern exists
→ Transaction imported as UNCATEGORIZED
→ You categorize it: Shopping/Online
→ Pattern learned: "Amazon" → Shopping/Online

Next Time Amazon Transaction Appears:
→ Pattern exists!
→ Automatically categorized as Shopping/Online
→ No manual work needed
```

## Why You Still See "X transactions need categorization"

### Reason 1: New Merchants/Patterns

```
If CSV contains:
  - 30 Walmart transactions → Auto-categorized (pattern exists)
  - 4 new "ACME CORP" transactions → Need categorization (no pattern)

Output:
  Auto-categorized: 30 (using learned patterns)
  Needs categorization: 4
```

### Reason 2: First-Time Use

If you just started using the system:
- **No patterns exist yet** → All transactions uncategorized
- After first AI categorization run → Patterns learned
- Future imports → Auto-categorized!

### Reason 3: Ambiguous Patterns

Some transaction text is too generic:
```
Action: "DEBIT CARD PURCHASE POS1234"
Payee: "POS1234"
→ Can't auto-categorize (pattern too generic)
```

## The Workflow

### Initial Setup (First CSV Import)

```bash
# Import transactions
./test_llm_ingest.sh
→ Imported: 50 transactions
→ Auto-categorized: 0 (no patterns yet)
→ Needs categorization: 50

# Categorize with AI
python3 main.py --ai-classify 50 --ai-auto-apply
→ Categorized 50 transactions
→ Learned 15 unique patterns
```

### Subsequent Imports

```bash
# Import new CSV (overlapping data)
./test_llm_ingest.sh
→ Imported: 25 new transactions
→ Auto-categorized: 20 (patterns exist!)
→ Needs categorization: 5 (new merchants)

# Only categorize the remaining 5
python3 main.py --ai-classify 5 --ai-auto-apply
→ Categorized 5 transactions
→ Learned 3 new patterns
```

## Building Your Pattern Library

Over time, the system learns:

```
After 3 months of use:
  Patterns learned: ~50
  Auto-categorization rate: ~85%
  Manual work needed: ~15% (only new merchants)

After 6 months:
  Patterns learned: ~80
  Auto-categorization rate: ~95%
  Manual work needed: ~5%
```

## Viewing Learned Patterns

```bash
sqlite3 transactions.db "
  SELECT pattern, category_id, subcategory_id, usage_count, confidence
  FROM classification_patterns
  ORDER BY usage_count DESC
  LIMIT 20
"
```

## The LLM's Role

### What LLM Does:
- ✅ Analyzes CSV structure (column mapping)
- ✅ Infers account information
- ✅ Extracts payee names
- ✅ Identifies transaction types

### What LLM Doesn't Do:
- ❌ Doesn't directly categorize during import
- ❌ Doesn't create categories on the fly

### Why This Design?

1. **Cost Efficiency**
   - 1 API call per CSV file (not per transaction)
   - ~$0.02 per file vs ~$1.00 if categorizing each transaction

2. **Consistency**
   - Uses learned patterns (deterministic)
   - Same merchant always gets same category
   - No LLM variance between runs

3. **Speed**
   - Pattern matching is instant
   - No API latency for each transaction

4. **Learning System**
   - Patterns improve over time
   - Manual corrections teach the system
   - Eventually becomes fully automatic

## Expected Output

### First Import Ever:
```
✓ Processing complete!
  Total rows in CSV: 50
  New transactions: 50
  Auto-categorized: 0 (using learned patterns)
  Needs categorization: 50

💡 Categorize remaining 50: python3 main.py --ai-classify 50 --ai-auto-apply
```

### After Pattern Learning:
```
✓ Processing complete!
  Total rows in CSV: 50
  New transactions: 50
  Auto-categorized: 45 (using learned patterns)
  Needs categorization: 5

💡 Categorize remaining 5: python3 main.py --ai-classify 5 --ai-auto-apply
```

### With Mature Pattern Library:
```
✓ Processing complete!
  Total rows in CSV: 50
  New transactions: 50
  Auto-categorized: 50 (using learned patterns)

💡 Next steps:
  ✓ All transactions auto-categorized!
```

## TL;DR

The message "X transactions need categorization" is **normal and expected**:

- It's referring to **NEW transactions** just imported
- Only appears for merchants/patterns not seen before
- As you categorize more, auto-categorization rate increases
- After a few months, most imports are 90%+ auto-categorized
- The LLM helps with CSV structure, not categorization (by design - saves cost!)
