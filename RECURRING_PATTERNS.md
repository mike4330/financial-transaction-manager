# Recurring Patterns System

## Overview

The Recurring Patterns system automatically detects recurring transactions from your financial history to enable accurate balance projections and future financial planning. This is a key component for building Quicken-like balance forecasting capabilities.

## Quick Start

### Command Line Usage

```bash
# Detect patterns (analysis only)
python3 main.py --detect-recurring --lookback-days 365

# Detect and save patterns for balance projections
python3 main.py --detect-recurring --save-patterns --lookback-days 365

# View saved patterns
python3 main.py --show-patterns
```

### Web Interface Usage

1. **Start the servers:**
   ```bash
   # Terminal 1: Start API backend
   python3 api_server.py
   
   # Terminal 2: Start React frontend
   cd frontend && npm run dev
   ```

2. **Navigate to Patterns page** at http://localhost:3001

3. **Pattern Management Workflow:**
   - Click "Detect New Patterns" 
   - Set lookback period (30-1095 days)
   - Review detected patterns with confidence scores
   - Use "Select High Confidence" for patterns ≥70% confidence
   - Click "Save Selected" to store for balance projections
   - Manage active patterns in "Saved Patterns" view

## How It Works

### Multi-Pass Detection Algorithm

**Pass 1: Exact Amount Matching**
- Groups transactions by payee + exact amount
- Identifies frequency patterns (weekly, biweekly, monthly, quarterly, annual)
- Perfect for: Subscriptions, salary, fixed bills

**Pass 2: Fuzzy Amount Matching** 
- Groups by payee with amount variance tolerance (≤50% coefficient of variation)
- Handles varying bills like utilities, credit card payments
- Best for: Utilities, insurance, variable recurring bills, mortgage payments

**Pass 3: Day-of-Month Patterns**
- Detects transactions on consistent calendar days (±2 day tolerance)
- Focuses on monthly patterns (25-35 day intervals)
- Best for: Rent, salary, monthly subscriptions on specific dates

### Investment Transaction Filtering

The system automatically excludes investment-related transactions to focus on recurring expenses and income:
- **Symbol-based transactions**: Any transaction with a stock/fund symbol
- **Investment actions**: YOU BOUGHT, YOU SOLD, DIVIDEND RECEIVED, REINVESTMENT
- **Focus**: Only analyzes actual recurring payments, transfers, and income

### Confidence Scoring

- **High (≥70%)**: 🟢 Green - Consistent historical data, reliable for projections
- **Medium (50-69%)**: 🟡 Yellow - Some variation, moderate reliability  
- **Low (<50%)**: 🔴 Red - Inconsistent data, manual review recommended

## Real Examples from Test Data

### High Confidence Patterns
- **Direct Deposit**: $4,320.24 biweekly (76.7% confidence)
- **Spotify**: $19.99 monthly (90.0% confidence)
- **Netflix**: $17.99 monthly (71.5% confidence)
- **Regular Transfers**: $45.00 biweekly (71.2% confidence)

### Medium Confidence Patterns
- **State Farm Insurance**: ~$281.28 monthly ±$0.61 (61.7% confidence)
- **Verizon**: $163.00 monthly (58.5% confidence)
- **PayPal Transfers**: $200.00 on 3rd of month (67.8% confidence)
- **Select Portfolio Servicing**: ~$1542.07 monthly (mortgage payments with amount variance)
- **NOVEC**: Utility payments with varying amounts

### Variable Patterns
- **Taco Bell**: ~$24.16 biweekly ±$2.04 (54.4% confidence)
- **Gas Stations**: Day-of-month patterns with amount variance

## API Endpoints

### Pattern Detection
```http
POST /api/recurring-patterns/detect
Content-Type: application/json

{
  "lookback_days": 365,
  "account_number": "optional-filter"
}
```

### Get Saved Patterns
```http
GET /api/recurring-patterns?active_only=true
```

### Save Pattern
```http
POST /api/recurring-patterns/save
Content-Type: application/json

{
  "pattern_name": "netflix - $17.99 (monthly)",
  "account_number": "Z06431462",
  "payee": "netflix",
  "typical_amount": 17.99,
  "amount_variance": 0,
  "frequency_type": "monthly",
  "frequency_interval": 1,
  "next_expected_date": "2025-08-13",
  "last_occurrence_date": "2025-07-14",
  "confidence": 71.5,
  "occurrence_count": 3
}
```

### Deactivate Pattern
```http
DELETE /api/recurring-patterns/{pattern_id}
```

## Database Schema

### recurring_patterns Table
- `id` - Primary key
- `pattern_name` - Human-readable pattern description
- `account_number` - Account identifier
- `payee` - Merchant/payee name
- `typical_amount` - Average transaction amount
- `amount_variance` - Standard deviation of amounts
- `frequency_type` - weekly, biweekly, monthly, quarterly, annual
- `frequency_interval` - Multiplier for frequency (default 1)
- `next_expected_date` - Predicted next occurrence
- `last_occurrence_date` - Most recent occurrence
- `confidence` - Pattern reliability score (0-1)
- `occurrence_count` - Number of historical occurrences
- `is_active` - Whether pattern is used for projections
- `created_at` - Pattern creation timestamp
- `updated_at` - Last modification timestamp

## Future Balance Projections

Saved patterns are designed to be used by a balance projection engine that:

1. **Starts with current account balance** (manual input or reconciliation)
2. **Projects recurring income** (salary, transfers, dividends) 
3. **Projects recurring expenses** (bills, subscriptions, regular spending)
4. **Calculates future balance** = current + projected income - projected expenses
5. **Shows confidence intervals** based on pattern reliability

## Development Integration

### Adding New Pattern Types

To extend the detection algorithm:

1. **Add new pass** in `database.py` → `detect_recurring_patterns()`
2. **Define pattern logic** in new `_detect_xyz_patterns()` method
3. **Update confidence scoring** in `_classify_frequency()`
4. **Add pattern_type** to results for UI differentiation

### Frontend Components

- **RecurringPatterns.tsx** - Main management interface
- **RecurringPatterns.module.css** - Component styling
- **App.simple.tsx** - Navigation integration

### CLI Commands

- `--detect-recurring` - Run pattern detection
- `--save-patterns` - Save detected patterns (use with --detect-recurring)
- `--show-patterns` - Display saved patterns
- `--lookback-days` - Configure analysis period

## Troubleshooting

### Common Issues

**No patterns detected:**
- Increase `--lookback-days` (try 180-365 days)
- Check if payee extraction completed successfully
- Verify sufficient transaction history exists
- Run payee extraction utility: `python3 payee_extractor.py --apply`

**Low confidence patterns:**
- Normal for irregular spending - review manually
- Consider seasonal adjustments for variable patterns
- Check for data quality issues (duplicate transactions)
- Mortgage/utility payments often have varying amounts (fuzzy matching)

**Pattern detection slow:**
- Large datasets may take 30-60 seconds for 365 days
- Consider smaller lookback periods for faster testing
- Database indexes optimize query performance

**Investment transactions appearing:**
- System automatically filters investment transactions
- If any slip through, check for missing symbol or action patterns

### Debug Tools

```bash
# Check pattern detection with verbose output
python3 main.py --detect-recurring --lookback-days 90 --verbose

# Inspect database directly  
sqlite3 transactions.db "SELECT * FROM recurring_patterns ORDER BY confidence DESC;"

# Test API endpoints
curl -X POST http://localhost:5000/api/recurring-patterns/detect \
  -H "Content-Type: application/json" \
  -d '{"lookback_days": 90}'
```

## Contributing

This system is designed for extensibility:

- **New pattern types** can be added via additional detection passes
- **Custom confidence algorithms** can be plugged in
- **Additional metadata** can be stored in the flexible schema
- **Frontend customization** through CSS modules and React props

The goal is building a comprehensive balance projection system that rivals commercial personal finance software while maintaining full user control and transparency.