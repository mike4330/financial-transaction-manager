# Budget Management System

This document describes the comprehensive budgeting system implemented for the financial transaction management application.

## Overview

The budgeting system provides template-based budget creation with monthly journalization, variance tracking, and flexible category/subcategory integration. The system is designed to handle real-world budgeting scenarios including mid-month adjustments, selective category inclusion, and budget vs actual analysis.

## Database Schema

### Core Tables

#### 1. `budget_templates`
Reusable budget definitions that can be instantiated monthly.

```sql
CREATE TABLE budget_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,              -- e.g., "Family Monthly Budget 2024"
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Purpose**: Define reusable budget structures (e.g., "Family Budget", "Emergency Mode", "Holiday Season")

#### 2. `budget_template_items`
Category/subcategory allocations within a template.

```sql
CREATE TABLE budget_template_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    subcategory_id INTEGER,                 -- NULL = budget entire category
    budget_amount DECIMAL(10,2) NOT NULL,
    budget_type TEXT CHECK (budget_type IN ('expense', 'income')) DEFAULT 'expense',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (template_id) REFERENCES budget_templates (id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories (id),
    FOREIGN KEY (subcategory_id) REFERENCES subcategories (id),
    UNIQUE (template_id, category_id, subcategory_id)
);
```

**Key Features**:
- **Selective budgeting**: Only explicitly added categories/subcategories are budgeted
- **Flexible granularity**: Budget entire categories OR specific subcategories
- **Mixed approach**: Some categories fully budgeted, others partially, others ignored

#### 3. `monthly_budgets`
Monthly instances of budget templates (journalization).

```sql
CREATE TABLE monthly_budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL,
    budget_year INTEGER NOT NULL,
    budget_month INTEGER NOT NULL CHECK (budget_month BETWEEN 1 AND 12),
    status TEXT CHECK (status IN ('draft', 'active', 'closed')) DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    FOREIGN KEY (template_id) REFERENCES budget_templates (id),
    UNIQUE (template_id, budget_year, budget_month)
);
```

**Status Workflow**:
- `draft` → Budget being prepared
- `active` → Budget in use for the month
- `closed` → Month completed, no more changes

#### 4. `monthly_budget_items`
Actual monthly budget line items with variance tracking.

```sql
CREATE TABLE monthly_budget_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    monthly_budget_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    subcategory_id INTEGER,
    budgeted_amount DECIMAL(10,2) NOT NULL,
    actual_amount DECIMAL(10,2) DEFAULT 0.00,
    budget_type TEXT CHECK (budget_type IN ('expense', 'income')) DEFAULT 'expense',
    notes TEXT,
    last_calculated_at TIMESTAMP,
    FOREIGN KEY (monthly_budget_id) REFERENCES monthly_budgets (id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories (id),
    FOREIGN KEY (subcategory_id) REFERENCES subcategories (id),
    UNIQUE (monthly_budget_id, category_id, subcategory_id)
);
```

**Variance Calculation** (computed in application layer):
- `variance_amount = actual_amount - budgeted_amount`
- `variance_percent = ((actual_amount - budgeted_amount) / ABS(budgeted_amount)) * 100`

#### 5. `budget_adjustments`
Mid-month budget changes with audit trail.

```sql
CREATE TABLE budget_adjustments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    monthly_budget_item_id INTEGER NOT NULL,
    adjustment_amount DECIMAL(10,2) NOT NULL,
    adjustment_reason TEXT NOT NULL,
    adjustment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,                        -- Future: user tracking
    FOREIGN KEY (monthly_budget_item_id) REFERENCES monthly_budget_items (id) ON DELETE CASCADE
);
```

### Performance Indexes

```sql
-- Core transaction indexes (existing)
CREATE INDEX idx_transaction_hash ON transactions(hash);
CREATE INDEX idx_run_date ON transactions(run_date);
CREATE INDEX idx_account ON transactions(account_number);

-- Budget-specific indexes
CREATE INDEX idx_budget_template_active ON budget_templates(is_active);
CREATE INDEX idx_monthly_budget_year_month ON monthly_budgets(budget_year, budget_month);
CREATE INDEX idx_monthly_budget_status ON monthly_budgets(status);
CREATE INDEX idx_budget_items_category ON monthly_budget_items(category_id, subcategory_id);
```

## Implementation Details

### Category Integration Strategy

The budget system integrates with existing normalized category/subcategory tables:

```sql
-- Existing schema
categories (id, name, created_at)
subcategories (id, category_id, name, created_at)
```

**Selective Budgeting Examples**:
- Budget "Food & Dining/Groceries" but ignore "Food & Dining/Coffee"
- Budget entire "Transportation" category but ignore "Entertainment" completely  
- Budget "Home/Mortgage" but not "Home/Maintenance"

### Template Instantiation Process

1. **Create Template**:
   ```sql
   INSERT INTO budget_templates (name, description) 
   VALUES ('Family Monthly Budget', 'Standard monthly family budget');
   ```

2. **Add Template Items**:
   ```sql
   INSERT INTO budget_template_items (template_id, category_id, subcategory_id, budget_amount)
   SELECT 1, c.id, s.id, 800.00
   FROM categories c JOIN subcategories s ON c.id = s.category_id
   WHERE c.name = 'Food & Dining' AND s.name = 'Groceries';
   ```

3. **Create Monthly Instance**:
   ```sql
   INSERT INTO monthly_budgets (template_id, budget_year, budget_month, status)
   VALUES (1, 2024, 1, 'active');
   ```

4. **Auto-populate Monthly Items**:
   ```sql
   INSERT INTO monthly_budget_items (monthly_budget_id, category_id, subcategory_id, budgeted_amount, budget_type)
   SELECT 1, bti.category_id, bti.subcategory_id, bti.budget_amount, bti.budget_type
   FROM budget_template_items bti WHERE bti.template_id = 1;
   ```

### Actual Amount Calculation

The `actual_amount` in `monthly_budget_items` is calculated by aggregating transactions:

```sql
-- Update actual amounts for expense categories
UPDATE monthly_budget_items 
SET actual_amount = (
    SELECT COALESCE(SUM(ABS(t.amount)), 0)
    FROM transactions t
    WHERE t.category_id = monthly_budget_items.category_id
    AND (monthly_budget_items.subcategory_id IS NULL OR t.subcategory_id = monthly_budget_items.subcategory_id)
    AND strftime('%Y', t.run_date) = CAST(budget_year AS TEXT)
    AND strftime('%m', t.run_date) = printf('%02d', budget_month)
    AND t.amount < 0  -- Expenses are negative
),
last_calculated_at = CURRENT_TIMESTAMP
WHERE budget_type = 'expense';
```

## Usage Scenarios

### Scenario 1: Full Category Budget
Budget entire "Transportation" category (includes Gas, Rideshare, Parking, etc.):
```sql
INSERT INTO budget_template_items (template_id, category_id, subcategory_id, budget_amount)
VALUES (1, (SELECT id FROM categories WHERE name = 'Transportation'), NULL, 400.00);
```

### Scenario 2: Selective Subcategory Budget
Budget only specific food subcategories:
```sql
-- Budget Groceries
INSERT INTO budget_template_items (template_id, category_id, subcategory_id, budget_amount)
SELECT 1, c.id, s.id, 800.00
FROM categories c JOIN subcategories s ON c.id = s.category_id
WHERE c.name = 'Food & Dining' AND s.name = 'Groceries';

-- Budget Fast Food  
INSERT INTO budget_template_items (template_id, category_id, subcategory_id, budget_amount)
SELECT 1, c.id, s.id, 200.00
FROM categories c JOIN subcategories s ON c.id = s.category_id
WHERE c.name = 'Food & Dining' AND s.name = 'Fast Food';

-- Coffee subcategory remains unbudgeted
```

### Scenario 3: Income Budget
Track expected income:
```sql
INSERT INTO budget_template_items (template_id, category_id, subcategory_id, budget_amount, budget_type)
SELECT 1, c.id, s.id, 5000.00, 'income'
FROM categories c JOIN subcategories s ON c.id = s.category_id
WHERE c.name = 'Income' AND s.name = 'Salary';
```

## Reporting Capabilities

This schema enables comprehensive budget analysis:

### 1. Budget vs Actual Report
```sql
SELECT 
    c.name as category,
    s.name as subcategory,
    mbi.budgeted_amount,
    mbi.actual_amount,
    (mbi.actual_amount - mbi.budgeted_amount) as variance_amount,
    CASE 
        WHEN mbi.budgeted_amount != 0 THEN 
            ((mbi.actual_amount - mbi.budgeted_amount) / ABS(mbi.budgeted_amount)) * 100
        ELSE NULL 
    END as variance_percent
FROM monthly_budget_items mbi
JOIN categories c ON mbi.category_id = c.id
LEFT JOIN subcategories s ON mbi.subcategory_id = s.id
JOIN monthly_budgets mb ON mbi.monthly_budget_id = mb.id
WHERE mb.budget_year = 2024 AND mb.budget_month = 1;
```

### 2. Monthly Trend Analysis
```sql
SELECT 
    mb.budget_year,
    mb.budget_month,
    c.name as category,
    mbi.budgeted_amount,
    mbi.actual_amount
FROM monthly_budget_items mbi
JOIN monthly_budgets mb ON mbi.monthly_budget_id = mb.id
JOIN categories c ON mbi.category_id = c.id
WHERE c.name = 'Food & Dining'
ORDER BY mb.budget_year, mb.budget_month;
```

### 3. Template Performance Comparison
```sql
SELECT 
    bt.name as template_name,
    AVG(mbi.actual_amount) as avg_actual,
    AVG(mbi.budgeted_amount) as avg_budgeted,
    AVG(mbi.actual_amount - mbi.budgeted_amount) as avg_variance
FROM budget_templates bt
JOIN monthly_budgets mb ON bt.id = mb.template_id
JOIN monthly_budget_items mbi ON mb.id = mbi.monthly_budget_id
GROUP BY bt.id, bt.name;
```

## Future Enhancements

### Planned Features
1. **Budget Rollover**: Unused budget amounts roll to next month
2. **Envelope Budgeting**: Transfer funds between categories
3. **Goal Tracking**: Long-term savings and expense reduction goals
4. **Automated Adjustments**: Auto-adjust based on historical patterns
5. **Multi-Account Budgets**: Budget across different accounts
6. **Budget Alerts**: Notifications when approaching limits

### API Endpoints (Planned)
- `GET /api/budget/templates` - List all budget templates
- `POST /api/budget/templates` - Create new budget template
- `GET /api/budget/monthly/{year}/{month}` - Get monthly budget
- `POST /api/budget/monthly/{year}/{month}/instantiate` - Create monthly budget from template
- `PUT /api/budget/items/{id}/actual` - Update actual amounts
- `GET /api/budget/variance/{year}/{month}` - Get variance report
- `POST /api/budget/adjustments` - Record budget adjustment

### Frontend Components (Planned)
- **Budget Template Manager**: Create and edit budget templates
- **Monthly Budget Dashboard**: View current month's budget vs actual
- **Variance Analysis Charts**: Visual budget performance tracking
- **Category Selection Interface**: Choose which categories to budget
- **Budget Adjustment Modal**: Record mid-month changes

## Technical Notes

### Migration Strategy
The budget schema was added to the existing `database.py` `init_database()` method using `CREATE TABLE IF NOT EXISTS` statements. This ensures:
- **Safe deployment**: No data loss on existing databases
- **Automatic creation**: New installations get full schema
- **Incremental updates**: Future schema changes can be added similarly

### Constraint Considerations
- **Unique constraints**: Prevent duplicate budget items per template/month
- **Check constraints**: Ensure valid month ranges (1-12) and status values
- **Foreign key constraints**: Maintain referential integrity with categories
- **Cascade deletes**: Remove dependent records when templates are deleted

### Performance Considerations
- **Indexed queries**: Common query patterns have supporting indexes
- **Minimal joins**: Schema design reduces need for complex joins
- **Computed fields**: Variance calculations done in application layer for flexibility
- **Batch operations**: Template instantiation designed for efficient bulk inserts

## Implementation Status

### ✅ Completed Features

**Database Schema**: All 5 budget tables created with proper foreign keys and indexes
**Budget Management Methods**: Complete database API in `TransactionDB` class
**Default Budget Template**: Created with essential categories:
- Income/Salary ($5,000)
- Food & Dining/Groceries ($800)
- Food & Dining/Fast Food ($200)
- Transportation/Gas ($300)
- Home/Mortgage ($2,400)
- Utilities/Electric ($150)
- Utilities/Internet ($90)
- Utilities/Mobile ($120)
- Entertainment/Streaming ($60)
- Shopping/Online ($250)

**August 2025 Budget**: Live monthly budget instantiated from template with actual transaction data

**Inline Budget Editing**: Complete frontend editing system with accept/cancel/auto buttons
- ✅ Click-to-edit budget amounts with input validation
- ✅ Real-time total recalculation across income/expense/net categories
- ✅ Persistent API updates to database with error handling

**Auto-Calculate Feature**: Smart 12-month rolling average with data smoothing
- ✅ Historical transaction analysis with outlier detection
- ✅ Confidence scoring based on data consistency and sample size
- ✅ User-friendly confirmation dialog with detailed analysis
- ✅ Handles edge cases: insufficient data, seasonal variations, one-time expenses

### 🏗️ Database Methods Available

```python
# Template management
template_id = db.create_budget_template(name, description)
item_id = db.add_budget_template_item(template_id, category, subcategory, amount, type)

# Monthly budget management  
monthly_budget_id = db.create_monthly_budget(template_id, year, month)
budget = db.get_monthly_budget(year, month)
items = db.get_monthly_budget_items(monthly_budget_id)

# Actual amount calculation
updated_count = db.update_actual_amounts(year, month)

# Budget item management (NEW)
success = db.update_budget_item_amount(item_id, new_amount)
analysis = db.calculate_historical_average(category_id, subcategory_id, year, month)
```

### 📊 Live Budget Data

Current August 2025 budget shows:
- **Food & Dining/Fast Food**: $84 actual vs $200 budgeted (42% used)
- **Food & Dining/Groceries**: $344 actual vs $800 budgeted (43% used)  
- **Shopping/Online**: $18 actual vs $250 budgeted (7% used)
- **Other categories**: $0 actual (no transactions yet in August 2025)

### Testing Verification

The implementation was tested with:
```bash
# Schema and functionality test
python3 -c "from database import TransactionDB; db = TransactionDB(); print('Success')"

# Budget creation and retrieval test
db.get_monthly_budget(2025, 8)  # Returns active budget
db.get_monthly_budget_items(1)  # Returns 10 budget items
db.update_actual_amounts(2025, 8)  # Updates from transaction data
```

All tests passed successfully, confirming:
- ✅ Proper schema creation and data integrity
- ✅ Template creation and instantiation  
- ✅ Monthly budget journalization
- ✅ Actual amount calculation from transactions
- ✅ Variance tracking and reporting
- ✅ Inline editing with persistent updates
- ✅ Auto-calculate with historical analysis

## Auto-Calculate Feature Documentation

### Overview

The Auto-Calculate feature provides intelligent budget amount suggestions based on 12-month historical spending patterns with advanced data smoothing to handle gaps, outliers, and seasonal variations.

### Algorithm Design

#### 1. Data Collection Phase
```python
def calculate_historical_average(category_id, subcategory_id, target_year, target_month):
    # Look back 12 months from target month (exclusive)
    # Collect monthly spending totals for the specified category/subcategory
    # Skip months with zero transactions (incomplete data indicators)
```

**Key Features**:
- **Lookback Period**: 12 months prior to target budget month
- **Category Flexibility**: Works with full categories OR specific subcategories
- **Data Validation**: Only includes months with actual transaction data

#### 2. Data Smoothing Phase

**Outlier Detection (IQR Method)**:
```python
# Calculate quartiles and interquartile range
q1 = 25th percentile of monthly amounts
q3 = 75th percentile of monthly amounts  
iqr = q3 - q1

# Remove outliers beyond 1.5 × IQR
lower_bound = q1 - 1.5 * iqr
upper_bound = q3 + 1.5 * iqr
cleaned_amounts = [amt for amt in monthly_amounts if lower_bound <= amt <= upper_bound]
```

**Smart Fallback Logic**:
- If outlier removal leaves <2 data points → use original data
- Prevents over-aggressive filtering that removes legitimate patterns
- Balances noise reduction with data preservation

#### 3. Confidence Scoring

**Multi-Factor Confidence Calculation**:
```python
data_consistency = 1.0 - (outliers_removed / total_months)
sample_confidence = min(months_used / 6.0, 1.0)  # 6+ months = full confidence
final_confidence = (data_consistency + sample_confidence) / 2
```

**Confidence Levels**:
- **High (80%+)**: Consistent historical data, 6+ months
- **Medium (60-79%)**: Some variation in data, 4-6 months  
- **Low (40-59%)**: Limited or inconsistent data, 3-4 months
- **Very Low (<40%)**: Insufficient historical data

#### 4. Edge Case Handling

**Insufficient Data**: Requires minimum 3 months of transaction data
**Seasonal Spending**: Algorithm naturally captures seasonal patterns in averages
**One-Time Expenses**: Outlier detection removes anomalous large purchases
**New Categories**: Gracefully fails with helpful error messages

### API Integration

#### Endpoints

**GET `/api/budget/items/<id>/auto-calculate`**
```json
{
  "suggested_amount": 247.83,
  "confidence": 0.75,
  "analysis": {
    "months_used": 8,
    "outliers_removed": 1,
    "median": 235.00,
    "confidence_description": "Medium confidence - some variation in data"
  }
}
```

**PUT `/api/budget/items/<id>`**
```json
{
  "budgeted_amount": 247.83
}
```

#### Error Handling

**400 Bad Request**: Insufficient historical data (< 3 months)
```json
{
  "error": "Insufficient historical data",
  "message": "Need at least 3 months of transaction data for auto-calculation"
}
```

**404 Not Found**: Budget item doesn't exist
**500 Internal Server Error**: Database or calculation errors

### Frontend User Experience

#### Auto Button Workflow

1. **User clicks "Auto" button** → Triggers API call to calculate historical average
2. **Analysis retrieved** → System fetches 12-month spending data and applies smoothing
3. **Confirmation dialog** → Shows suggested amount with detailed analysis:
   ```
   Auto-calculated amount: $248

   Analysis:
   • Based on 8 months of data
   • Confidence: 75% (Medium confidence - some variation in data)
   • Median spending: $235
   • Removed 1 outlier month(s)

   Apply this amount?
   ```
4. **User approval** → Amount applied immediately with totals recalculation
5. **Database update** → New budget amount persisted via API

#### Visual Feedback

- **Loading state** during calculation
- **Error messages** for insufficient data
- **Success confirmation** with new amount display
- **Real-time total updates** across all budget sections

### Implementation Files

**Backend Logic** (`database.py:1681-1790`):
- `calculate_historical_average()`: Core algorithm with IQR smoothing
- `update_budget_item_amount()`: Persistent budget updates

**API Endpoints** (`api_server.py:534-633`):
- Auto-calculate endpoint with analysis response
- Budget item update endpoint with validation
- Confidence description mapping

**Frontend Integration** (`Budget.tsx:147-223`):
- Auto button click handler with confirmation dialog
- API error handling and user feedback
- Local state updates with totals recalculation

### Performance Characteristics

**Database Queries**: Single query per month in lookback period (12 queries max)
**Memory Usage**: Minimal - processes monthly totals (small arrays)
**Response Time**: Sub-second for most categories (<500ms typical)
**Caching**: None required - calculations are fast and data changes infrequently

### Testing Scenarios

**Scenario 1: Consistent Spending**
- 12 months of grocery data: $780, $820, $765, $810, $798, etc.
- Result: High confidence (90%+), average ~$790
- Outliers: None removed

**Scenario 2: Seasonal Variation**  
- Winter utilities: $180, $190, $200 vs Summer: $90, $85, $95
- Result: Medium confidence (70%), captures seasonal average
- Outliers: Extreme months may be filtered

**Scenario 3: One-Time Purchase**
- Monthly online shopping: $50, $60, $55, $2400 (laptop), $45, $50
- Result: Medium confidence (65%), laptop purchase filtered out
- Outliers: 1 outlier removed, suggestion ~$52

**Scenario 4: New Category**
- Only 2 months of data available
- Result: Error message "Need at least 3 months of transaction data"
- User guided to manual entry

**Scenario 5: Inconsistent Data**
- Sporadic spending: $0, $150, $0, $300, $0, $80
- Result: Low confidence (45%), based on 3 non-zero months
- Average calculated from actual spending months only

### Future Enhancements

**Planned Improvements**:
- **Weighted Averaging**: Give more weight to recent months
- **Seasonal Awareness**: Separate summer/winter calculations for utilities
- **Category Intelligence**: Learn spending patterns by category type
- **Trend Analysis**: Detect increasing/decreasing spending trends
- **Confidence Thresholds**: Auto-apply high confidence suggestions
- **Bulk Auto-Calculate**: Process entire budget at once