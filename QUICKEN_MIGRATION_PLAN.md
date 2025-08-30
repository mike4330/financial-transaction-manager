# Quicken Migration Plan - Simplified Approach

## Overview
This document outlines a simplified migration plan from Quicken to our financial management system, focusing on two core features:
1. **Bill Calendar UI** - Monthly view of recurring patterns with payment status
2. **Transaction Import** - Basic QIF import with category mapping

## 1. Bill Calendar Feature

### Requirements
- Monthly calendar view (one month at a time)
- Show recurring patterns as expected bills on calculated due dates
- Payment status indicators: Paid ✅ / Unpaid ❌ / Overdue 🔴
- Click-to-view details popup
- Month navigation

### Technical Design

#### A. Data Flow
```
recurring_patterns table → Calculate due dates → Match with transactions → Display status
```

#### B. Payment Matching Algorithm
```javascript
function findPaymentForBill(expectedBill, transactions) {
  return transactions.find(t => 
    // Date proximity (±3 days)
    Math.abs(daysBetween(t.date, expectedBill.expectedDate)) <= 3 &&
    // Payee similarity (fuzzy match)
    payeeSimilarity(t.payee, expectedBill.pattern.payee) > 0.8 &&
    // Amount within variance
    Math.abs(t.amount - expectedBill.expectedAmount) <= expectedBill.pattern.amount_variance
  );
}
```

#### C. Due Date Calculation
```javascript
function calculateDueDates(pattern, month, year) {
  const dates = [];
  const startDate = new Date(year, month - 1, 1);
  const endDate = new Date(year, month, 0);
  
  // Calculate based on frequency_type and last_occurrence_date
  switch(pattern.frequency_type) {
    case 'monthly':
      // Add monthly occurrences within the month
      break;
    case 'biweekly':
      // Add biweekly occurrences within the month
      break;
    // ... other frequencies
  }
  
  return dates;
}
```

#### D. Component Structure
```typescript
// BillCalendar.tsx
interface ExpectedBill {
  pattern: RecurringPattern;
  expectedDate: Date;
  expectedAmount: number;
  matchedTransaction?: Transaction;
  status: 'paid' | 'unpaid' | 'overdue';
  daysOverdue?: number;
}

interface CalendarDay {
  date: Date;
  expectedBills: ExpectedBill[];
  isCurrentMonth: boolean;
  isToday: boolean;
}

interface BillCalendarProps {
  month: number;
  year: number;
  onMonthChange: (month: number, year: number) => void;
}
```

#### E. API Endpoints Needed
```javascript
// New endpoint in api_server.py
GET /api/bills/calendar?month=12&year=2023
{
  "month": 12,
  "year": 2023,
  "calendar_days": [
    {
      "date": "2023-12-01",
      "expected_bills": [
        {
          "pattern_id": 123,
          "pattern_name": "Mortgage Payment",
          "payee": "Select Portfolio Servicing",
          "expected_amount": 1500.00,
          "expected_date": "2023-12-01",
          "status": "paid",
          "matched_transaction": {
            "id": 5678,
            "amount": 1581.28,
            "date": "2023-12-01",
            "payee": "Select Portfolio Servicing"
          }
        }
      ]
    }
  ]
}
```

#### F. UI Layout
```
┌─────────────────────────────────────┐
│  ← December 2023 →                  │
├─────────────────────────────────────┤
│ Sun Mon Tue Wed Thu Fri Sat         │
├─────────────────────────────────────┤
│     1   2   3   4   5   6   7       │
│     🟢  ❌      🔴              │
│  8   9  10  11  12  13  14          │
│      🟢                             │
│ 15  16  17  18  19  20  21          │
│ 22  23  24  25  26  27  28          │
│ 29  30  31                          │
└─────────────────────────────────────┘

Legend:
🟢 = Paid bill
❌ = Unpaid bill (not due yet)  
🔴 = Overdue bill
```

## 2. Quicken Data Reconciliation (LLM-Assisted)

### Requirements
- Parse QIF transaction files into structured format
- **NO automated database insertion** - LLM-driven reconciliation instead
- Batch processing with human-level intent understanding
- Interactive reconciliation workflow with Claude Code

### Technical Design

#### A. QIF File Parser (Parse Only)
```python
# quicken_reconciler.py
class QIFParser:
    def parse_file(self, qif_file_path):
        """Parse QIF file and return structured transaction data"""
        transactions = []
        
        # QIF format example:
        # !Type:Bank
        # D12/1/2023
        # T-1500.00
        # PSelect Portfolio Servicing
        # LHousing:Mortgage
        # ^
        
        return transactions
    
    def export_batch_json(self, transactions, batch_size=50, output_dir="qif_batches/"):
        """Export transactions in reviewable JSON batches"""
        # Creates batch_001.json, batch_002.json, etc.
        pass
    
    def create_reconciliation_report(self, transactions):
        """Generate summary for LLM review"""
        return {
            'total_transactions': len(transactions),
            'date_range': f"{min_date} to {max_date}",
            'unique_payees': list(unique_payees),
            'quicken_categories': list(unique_categories),
            'account_types': list(account_types),
            'potential_issues': self.identify_issues(transactions)
        }
```

#### B. LLM-Assisted Reconciliation Workflow
```python
class ReconciliationSession:
    def __init__(self, db, batch_file):
        self.db = db
        self.batch = self.load_batch(batch_file)
        
    def analyze_batch_for_llm(self):
        """Prepare batch analysis for Claude Code review"""
        return {
            'transactions': self.batch,
            'existing_categories': self.db.get_all_categories(),
            'existing_payees': self.db.get_recent_payees(limit=100),
            'duplicate_candidates': self.find_potential_duplicates(),
            'mapping_suggestions': self.suggest_mappings()
        }
    
    def apply_llm_decisions(self, decisions):
        """Apply Claude Code's reconciliation decisions to database"""
        # Only executes after LLM review and approval
        pass
```

#### C. Interactive Reconciliation Process
```bash
# Step 1: Parse QIF into reviewable batches
python3 quicken_reconciler.py --parse transactions.qif --batch-size 25

# Step 2: Claude Code analyzes each batch
# - Reviews transaction data and context
# - Suggests category mappings based on payee patterns
# - Identifies potential duplicates
# - Makes reconciliation recommendations

# Step 3: Apply approved decisions
python3 quicken_reconciler.py --apply-batch batch_001_decisions.json

# Step 4: Generate reconciliation report
python3 quicken_reconciler.py --reconcile-report --date-range 2023-01-01,2023-12-31
```

#### D. Reconciliation Report
```python
def generate_reconciliation_report(start_date, end_date):
    """Compare imported data with expectations"""
    return {
        'period': f"{start_date} to {end_date}",
        'transactions_imported': 1234,
        'categories_mapped': 45,
        'categories_unmapped': 3,
        'potential_duplicates': 2,
        'balance_differences': [
            {'month': '2023-01', 'expected': 5000.00, 'actual': 5000.00, 'diff': 0.00}
        ]
    }
```

## Implementation Plan

### Phase 1: Bill Calendar (Priority 1)
**Files to create/modify:**
- `frontend/src/components/BillCalendar.tsx`
- `frontend/src/components/BillCalendar.module.css`
- `frontend/src/components/BillDetails.tsx`
- `api_server.py` (add `/api/bills/calendar` endpoint)
- `main.tsx` or routing (add Bills page)

**Estimated effort:** 2-3 days

### Phase 2: QIF Reconciliation (Priority 2)  
**Files to create/modify:**
- `quicken_reconciler.py` (new parser and batch utility)
- `qif_batches/` (directory for batch JSON files)
- `reconciliation_sessions/` (directory for LLM decision files)

**Estimated effort:** 1-2 days for parser, then iterative LLM sessions

## File Structure
```
/var/www/html/bank/
├── quicken_reconciler.py      # QIF parser and batch processor
├── qif_batches/               # JSON batch files for LLM review
├── reconciliation_sessions/   # LLM decision files and logs
├── api_server.py              # Add bills/calendar endpoint
└── frontend/src/
    ├── components/
    │   ├── BillCalendar.tsx          # Monthly calendar component
    │   ├── BillCalendar.module.css   # Calendar styling
    │   └── BillDetails.tsx           # Bill detail popup
    └── App.simple.tsx         # Add Bills navigation
```

## Success Criteria

### Bill Calendar
- [x] ✅ Monthly calendar view with navigation
- [x] ✅ Shows recurring patterns as expected bills
- [x] ✅ Payment status indicators (paid/unpaid/overdue)
- [x] ✅ Click to view bill and payment details
- [x] ✅ Handles multiple bills per day

### QIF Reconciliation (LLM-Assisted)
- [x] ✅ Parses standard QIF transaction files into structured JSON
- [x] ✅ Exports transactions in reviewable batches (25-50 per batch)
- [x] ✅ Provides context for LLM decision-making (existing categories, payees, patterns)
- [x] ✅ Supports iterative batch processing with Claude Code
- [x] ✅ Applies LLM-approved decisions safely to database
- [x] ✅ Generates reconciliation reports with human insight

## Technical Notes

### Existing System Integration
- **Leverages existing `recurring_patterns` table** - no schema changes needed
- **Uses existing transaction hash logic** for duplicate detection
- **Integrates with existing category system** - no new category structure
- **Follows existing API patterns** - consistent with current endpoints

### Calendar Implementation Strategy
- **CSS Grid or Flexbox** for calendar layout (not a complex calendar library)
- **React state management** for month navigation and bill data
- **Portal-based popups** for bill details (using existing Dialog patterns)
- **Responsive design** for mobile/desktop viewing

### Import Implementation Strategy  
- **Streaming parser** for large QIF files
- **Batch processing** for database inserts
- **Progress reporting** for long import operations
- **Rollback capability** for failed imports

## LLM-Assisted Reconciliation Advantages

### Why This Approach Works Better
- **Human-level intent understanding**: LLM can interpret ambiguous payee names, categorization context, and user spending patterns
- **Contextual decision-making**: Reviews transaction batches with full knowledge of existing categories and historical patterns  
- **Safety through review**: No automated database changes - all decisions reviewed before application
- **Handles edge cases**: Complex scenarios (split transactions, category changes, merchant name variations) handled intelligently
- **Learning from patterns**: LLM recognizes spending patterns and applies consistent categorization logic
- **Flexible batch sizes**: Can adjust batch size based on complexity (25 for complex periods, 50+ for routine transactions)

### Example LLM Reconciliation Session
```
Claude Code analyzes batch_001.json (25 transactions from Jan 2023):

"I see 3 Walmart transactions with different amounts ($45, $128, $67). Based on your existing patterns:
- $128 transaction → 'Food & Dining/Groceries' (bulk shopping pattern)  
- $45, $67 transactions → 'Shopping/General' (smaller purchases)

Also found 2 new payees:
- 'AMZN MKTP US*123456' → Maps to existing 'Amazon' payee, 'Shopping/Online' category
- 'SQ *LOCAL COFFEE' → New payee 'Square (Local Coffee)', suggest 'Food & Dining/Coffee' subcategory

Potential duplicate: Transaction #1247 matches existing transaction from 1/15/2023. Skip import."
```

This plan provides a focused, implementable path to achieve Quicken feature parity without over-engineering while leveraging LLM intelligence for complex reconciliation decisions.