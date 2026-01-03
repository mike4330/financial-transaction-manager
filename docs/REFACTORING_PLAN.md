# Codebase Refactoring Plan

**Date**: 2026-01-03
**Status**: Proposed

## Executive Summary

The codebase has grown to a point where **refactoring is recommended** to maintain long-term maintainability. We have 6 files exceeding 1,000 lines, with two critical files (api_server.py and database.py) exceeding 3,000 lines each.

## Files Requiring Immediate Attention (>1000 lines)

### Backend (Python)
1. **api_server.py** - 3,126 lines ⚠️ CRITICAL
   - 52 API endpoints across multiple domains
   - Covers: transactions, budget, categories, patterns, payees, reports, file monitoring
   - Average: 60 lines per endpoint

2. **database.py** - 3,007 lines ⚠️ CRITICAL
   - Single TransactionDB class with 73 methods
   - All database operations in one monolithic file

3. **database_backup.py** - 1,210 lines ⚠️
   - Backup and restore functionality
   - Could benefit from modularization

### Frontend (TypeScript/React)
1. **Budget.tsx** - 1,428 lines ⚠️ CRITICAL
   - Budget management, editing, projections
2. **RecurringPatterns.tsx** - 1,257 lines ⚠️ CRITICAL
   - Pattern detection, management, testing
3. **TransactionsList.tsx** - 1,207 lines ⚠️ CRITICAL
   - Transaction display, filtering, bulk operations

## Recommended Refactoring Strategy

### Phase 1: Backend API Refactoring (HIGH PRIORITY)

**Problem**: api_server.py is a monolith with 3,126 lines and 52 endpoints mixed together

**Solution**: Split into Flask Blueprints by domain

```
backend/
├── api_server.py (main app, ~200 lines)
│   - Flask app initialization
│   - CORS setup
│   - Blueprint registration
│   - File monitoring startup
│
├── routes/
│   ├── __init__.py
│   ├── transactions.py (~400 lines, 10 endpoints)
│   │   - GET /api/transactions
│   │   - PUT /api/transactions/<id>
│   │   - POST /api/transactions/bulk-categorize
│   │   - DELETE /api/transactions/bulk-delete
│   │   - POST /api/transactions/<id>/splits
│   │   - etc.
│   │
│   ├── budget.py (~300 lines, 6 endpoints)
│   │   - GET /api/budget/<year>/<month>
│   │   - POST/PUT/DELETE budget items
│   │   - GET /api/budget/available-months
│   │   - etc.
│   │
│   ├── categories.py (~200 lines, 8 endpoints)
│   │   - CRUD for categories and subcategories
│   │   - GET /api/categories-with-spending
│   │   - etc.
│   │
│   ├── patterns.py (~400 lines, 9 endpoints)
│   │   - Recurring pattern detection
│   │   - Pattern management
│   │   - Monthly projections
│   │
│   ├── payees.py (~300 lines, 9 endpoints)
│   │   - Payee pattern management
│   │   - Pattern testing and application
│   │
│   ├── reports.py (~200 lines, expandable)
│   │   - GET /api/reports/yearly-category-totals
│   │   - Future: budget variance reports
│   │   - Future: custom reports
│   │
│   └── monitoring.py (~200 lines, 5 endpoints)
│       - File monitoring control
│       - Health checks
│       - System status
```

**Implementation Steps**:
1. Create `routes/` directory
2. Start with smallest domain (reports, monitoring)
3. Extract one blueprint at a time
4. Update imports in api_server.py
5. Test each extraction
6. Move on to next blueprint

**Benefits**:
- Each domain is self-contained and independently testable
- Easier to navigate (500 lines vs 3000 lines)
- Clear separation of concerns
- Multiple developers can work simultaneously without conflicts
- Easy to add new endpoints to existing domains

**Testing Strategy**:
- Ensure all existing tests pass after each blueprint extraction
- No functional changes, only structural reorganization

---

### Phase 2: Database Layer Refactoring (HIGH PRIORITY)

**Problem**: database.py has 3,007 lines with 73 methods in a single TransactionDB class

**Solution**: Split into domain-specific database classes with composition

```
backend/
├── database/
│   ├── __init__.py
│   │   - Export unified TransactionDB interface (composition)
│   │
│   ├── base.py (~100 lines)
│   │   - Database connection management
│   │   - Common utilities
│   │   - Schema initialization
│   │
│   ├── transactions.py (~600 lines)
│   │   - add_transaction()
│   │   - get_transactions()
│   │   - update_transaction()
│   │   - delete_transaction()
│   │   - bulk operations
│   │   - split transaction handling
│   │
│   ├── budget.py (~400 lines)
│   │   - get_budget()
│   │   - save_budget_item()
│   │   - delete_budget_item()
│   │   - calculate_historical_average()
│   │
│   ├── categories.py (~300 lines)
│   │   - Category and subcategory CRUD
│   │   - Category statistics
│   │   - Category spending analysis
│   │
│   ├── patterns.py (~500 lines)
│   │   - detect_recurring_patterns()
│   │   - get_recurring_patterns()
│   │   - save_pattern()
│   │   - Pattern projections
│   │
│   ├── payees.py (~300 lines)
│   │   - Payee management
│   │   - Payee extraction patterns
│   │   - Pattern matching
│   │
│   └── analytics.py (~400 lines)
│       - Category spending analysis
│       - Trend calculations
│       - Reporting queries
```

**Implementation Pattern** (Composition):
```python
# database/__init__.py
from .base import DatabaseBase
from .transactions import TransactionOps
from .budget import BudgetOps
# ... etc

class TransactionDB:
    """Main database interface using composition"""
    def __init__(self, db_path):
        self.base = DatabaseBase(db_path)
        self.transactions = TransactionOps(self.base)
        self.budget = BudgetOps(self.base)
        self.categories = CategoryOps(self.base)
        # ... etc

    # Delegate methods to appropriate component
    def add_transaction(self, *args, **kwargs):
        return self.transactions.add(*args, **kwargs)
```

**Benefits**:
- Much easier to test individual components
- Clear responsibility boundaries
- Reusable across different contexts
- Easier to optimize specific operations
- Better code navigation and discoverability

---

### Phase 3: Frontend Component Refactoring (MEDIUM PRIORITY)

**Problem**: Budget, RecurringPatterns, and TransactionsList components are 1200+ lines each

**Solutions**:

#### Budget.tsx (1,428 lines) → Multiple Components
```
components/
├── Budget.tsx (~200 lines)
│   - Main layout and orchestration
│   - Uses: useBudget hook
│
├── budget/
│   ├── BudgetSummary.tsx (~100 lines)
│   │   - Income/expense/net display
│   │   - Month navigation
│   │
│   ├── BudgetTable.tsx (~300 lines)
│   │   - Main budget items table
│   │   - Inline editing
│   │
│   ├── BudgetItemEditor.tsx (~150 lines)
│   │   - Add/edit budget items
│   │   - Auto-calculate integration
│   │
│   ├── UnbudgetedCategories.tsx (~200 lines)
│   │   - Modal showing unbudgeted spending
│   │   - Quick add functionality
│   │
│   ├── PatternProjections.tsx (~200 lines)
│   │   - Recurring pattern projections
│   │   - Expected vs budgeted
│   │
│   └── SpendingChart.tsx (~150 lines)
│       - Pie chart visualization
│
├── hooks/
│   ├── useBudget.ts (~150 lines)
│   │   - Budget data fetching
│   │   - CRUD operations
│   │
│   └── useBudgetCalculations.ts (~100 lines)
│       - Total calculations
│       - Variance calculations
```

#### RecurringPatterns.tsx (1,257 lines) → Multiple Components
```
components/
├── RecurringPatterns.tsx (~150 lines)
│   - Main layout
│   - Uses: usePatterns hook
│
├── patterns/
│   ├── PatternList.tsx (~200 lines)
│   │   - Display all patterns
│   │   - Pattern cards
│   │
│   ├── PatternEditor.tsx (~200 lines)
│   │   - Add/edit patterns
│   │   - Form validation
│   │
│   ├── PatternDetector.tsx (~250 lines)
│   │   - Auto-detection UI
│   │   - Detection results
│   │
│   ├── PatternTestResults.tsx (~200 lines)
│   │   - Test pattern modal
│   │   - Match preview
│   │
│   └── PatternProjections.tsx (~150 lines)
│       - Monthly projections
│       - Pattern forecasting
│
├── hooks/
│   ├── usePatterns.ts (~150 lines)
│   │   - Pattern CRUD
│   │   - Detection triggering
│   │
│   └── usePatternDetection.ts (~100 lines)
│       - Detection state
│       - Auto-save logic
```

#### TransactionsList.tsx (1,207 lines) → Multiple Components
```
components/
├── TransactionsList.tsx (~150 lines)
│   - Main layout
│   - Uses: useTransactions hook
│
├── transactions/
│   ├── TransactionTable.tsx (~250 lines)
│   │   - Table display
│   │   - Column configuration
│   │
│   ├── TransactionRow.tsx (~150 lines)
│   │   - Individual row
│   │   - Inline actions
│   │
│   ├── TransactionFilters.tsx (~200 lines)
│   │   - Date range, category filters
│   │   - Search, sort options
│   │
│   ├── BulkActions.tsx (~150 lines)
│   │   - Selection toolbar
│   │   - Bulk categorize/delete
│   │
│   └── TransactionStats.tsx (~100 lines)
│       - Summary statistics
│       - Count, totals
│
├── hooks/
│   ├── useTransactions.ts (~200 lines)
│   │   - Fetch, update, delete
│   │   - Bulk operations
│   │
│   └── useTransactionFilters.ts (~150 lines)
│       - Filter state management
│       - URL synchronization
```

---

## Suggested Implementation Priority

### Week 1-2: Split api_server.py into Blueprints ✅ **START HERE**
**Rationale**:
- Immediate benefit in maintainability
- Makes adding new endpoints much easier (like our reports endpoint)
- Reduces merge conflicts if multiple features developed
- Low risk (structural change only)

**Order**:
1. Reports blueprint (newest, smallest)
2. Monitoring blueprint
3. Categories blueprint
4. Budget blueprint
5. Patterns blueprint
6. Payees blueprint
7. Transactions blueprint (largest, do last)

### Week 3-4: Refactor database.py
**Rationale**:
- Improves testability significantly
- Makes DB operations more discoverable
- Reduces coupling between different domains
- Prepares for future optimizations

**Order**:
1. Create base.py with connection management
2. Extract analytics.py (no dependencies)
3. Extract categories.py
4. Extract budget.py
5. Extract payees.py
6. Extract patterns.py
7. Extract transactions.py (most complex, do last)

### Week 5+: Refactor large frontend components
**Rationale**:
- Improves component reusability
- Makes testing much easier
- Better code organization
- Can be done incrementally (one component at a time)

**Order**:
1. Reports.tsx (already small, good template)
2. TransactionsList.tsx
3. Budget.tsx
4. RecurringPatterns.tsx

---

## Current Codebase Statistics

### Overall
- **Total Python LOC**: ~16,595 (excluding .venv)
- **Total Frontend LOC**: ~11,869
- **Total LOC**: ~28,464

### Problem Files
- **Files > 1000 lines**: 6 (3 backend, 3 frontend)
- **Files > 500 lines**: 15+
- **Largest file**: api_server.py (3,126 lines)

### API Endpoint Distribution
- **Total endpoints**: 52
- **Transactions**: 10 endpoints
- **Budget**: 6 endpoints
- **Categories**: 8 endpoints
- **Patterns**: 9 endpoints
- **Payees**: 9 endpoints
- **Reports**: 1 endpoint
- **Monitoring**: 5 endpoints
- **Other**: 4 endpoints

---

## Target Metrics

### File Size Goals
- **Max file size**: 500 lines (strict), 800 lines (acceptable)
- **Max function/method**: 50 lines
- **Max class**: 400 lines
- **Max component**: 300 lines

### Code Quality Goals
- Cyclomatic complexity < 10 per function
- Test coverage > 70% (after refactoring)
- All exports documented
- Type hints on all Python functions

---

## Risk Assessment

### Low Risk
- API Blueprint refactoring (structural only, no logic changes)
- Frontend component extraction (if done incrementally)

### Medium Risk
- Database layer refactoring (need comprehensive testing)
- Moving shared utilities

### Mitigation Strategies
1. **Comprehensive testing** before and after each refactoring
2. **Incremental approach** - one module/blueprint at a time
3. **Feature freeze** during major refactoring
4. **Backup branch** before starting each phase
5. **Smoke tests** on production-like environment

---

## Decision Needed

Before proceeding with refactoring, we need to decide:

1. **When to start?** (Suggest: After current feature development cycle)
2. **Feature freeze?** (Suggest: Soft freeze, critical bugs only)
3. **Testing strategy?** (Suggest: Add integration tests first)
4. **Rollback plan?** (Suggest: Git branches + deployment tags)

---

## Notes

- This refactoring is **recommended but not urgent**
- Current codebase is functional, just becoming harder to maintain
- Best done **before** adding more major features
- Estimated effort: 4-6 weeks with careful, incremental approach
- Can be done in parallel with bug fixes and minor features
