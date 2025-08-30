# QIF Reconciliation Logic

## Overview
When processing QIF transactions, we follow a two-phase approach: detect duplicates first, then enhance existing data rather than create duplicates.

## Duplicate Detection Process

### 1. Exact Match Detection
- **Date matching**: ±3 days tolerance
- **Amount matching**: Exact match required  
- **Payee similarity**: Fuzzy string matching (>70% similarity)
- **Account context**: Consider multi-account transfer patterns

### 2. When Duplicate Found: ENHANCE Instead of Skip

#### A. Payee Normalization
```
If existing payee is generic/empty:
  - "No Description" → Use QIF payee
  - "" (empty) → Use QIF payee
  - Very short payee → Use longer, more descriptive QIF payee

If both payees exist and are similar (fuzzy match >80%):
  - Choose more descriptive version
  - Standardize merchant names (BJ'S vs Bjs.Com)
```

#### B. Category/Subcategory Enhancement  
```
If existing transaction is uncategorized:
  - Apply QIF category mapping if available
  - Use learned mapping rules

If both are categorized and similar:
  - Keep existing unless QIF is clearly more specific
  - Learn mapping rule for future use
```

#### C. Field Enrichment
```
Copy QIF fields to existing transaction if:
  - memo: QIF has memo, existing is null/empty
  - description: QIF has better description
  - payee: QIF payee is more descriptive
  - category: QIF provides missing categorization
```

## Implementation Logic

### Phase 1: Duplicate Analysis
```python
duplicate_status = analyze_transaction(qif_txn, existing_txn):
  if exact_match(date, amount, payee_similarity):
    return {
      'action': 'enhance_existing',
      'existing_id': existing_txn.id,
      'enhancements': {
        'payee': improved_payee_if_better(qif_txn, existing_txn),
        'category': improved_category_if_better(qif_txn, existing_txn), 
        'memo': qif_txn.memo if existing_txn.memo is null,
        'description': better_description(qif_txn, existing_txn)
      }
    }
  else:
    return {'action': 'import_new'}
```

### Phase 2: Enhancement Rules

#### Payee Enhancement Rules
```python
def improved_payee_if_better(qif_txn, existing_txn):
  qif_payee = qif_txn.payee
  existing_payee = existing_txn.payee
  
  # Clear wins for QIF
  if existing_payee in ['No Description', '', None]:
    return qif_payee
    
  # Length-based preference (more descriptive usually better)
  if len(qif_payee) > len(existing_payee) * 1.5:
    return qif_payee
    
  # Fuzzy match - keep existing if very similar, otherwise flag for review
  if fuzzy_match(qif_payee, existing_payee) > 0.85:
    return existing_payee  # Keep what we have
  else:
    return None  # Flag for manual review
```

#### Category Enhancement Rules
```python
def improved_category_if_better(qif_txn, existing_txn):
  # Existing is uncategorized - use QIF if we can map it
  if existing_txn.category_id is None:
    mapped = map_quicken_category(qif_txn.category)
    if mapped and mapped.confidence > 0.7:
      return mapped
      
  # Both categorized - prefer existing unless QIF is clearly more specific
  # (e.g., "Food & Dining:Groceries" vs "Food & Dining")
  return None  # Keep existing
```

## Decision Matrix

| QIF Status | Existing Status | Action | Enhancement Fields |
|------------|----------------|---------|-------------------|
| Has better payee | "No Description" | Enhance | payee |
| Has memo | No memo | Enhance | memo |
| Has category | Uncategorized | Enhance | category, subcategory |
| Categorized | Different category | Review | Flag for manual decision |
| Same basic data | Same basic data | Skip | None |

## Example Scenarios

### Scenario 1: Generic → Specific Payee
```
QIF: "Bjs.Com #5490 800-257-2582 Ma"
DB:  "No Description"
→ Action: Enhance payee to "BJ's Wholesale" (standardized)
```

### Scenario 2: Missing Memo
```
QIF: memo="groceries", category="Food & Dining:Groceries"  
DB:  memo=null, category_id=null
→ Action: Enhance memo and category
```

### Scenario 3: Category Conflict
```
QIF: "Auto & Transport:Gas & Fuel"
DB:  category="Shopping:General"  
→ Action: Flag for manual review (user decides)
```

## Tracking and Audit

### Enhancement Log
Every enhancement is logged in `qif_reconciliation_log`:
```sql
INSERT INTO qif_reconciliation_log (
  qif_transaction_hash,
  reconciliation_status, -- 'enhanced'
  matched_transaction_id,
  import_decision,        -- JSON of what was changed
  notes
)
```

### Learning from Enhancements
Successful enhancements create mapping rules:
```sql
INSERT INTO qif_category_mappings (
  quicken_category,
  app_category_id, 
  confidence,
  mapping_type='enhancement_learned'
)
```

## Quality Assurance

### Enhancement Confidence Scoring
- **High confidence (>90%)**: Auto-apply enhancement
- **Medium confidence (70-90%)**: Show user for approval
- **Low confidence (<70%)**: Flag for manual review

### Rollback Capability  
All enhancements are tracked with before/after values for potential rollback:
```json
{
  "enhancement_id": "uuid",
  "transaction_id": 9473,
  "changes": {
    "payee": {"before": "No Description", "after": "BJ's Wholesale"},
    "memo": {"before": null, "after": "groceries"}
  },
  "timestamp": "2024-08-30T12:00:00Z"
}
```

This approach maximizes data quality while maintaining audit trails and user control.