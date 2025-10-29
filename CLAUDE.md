# CLAUDE.md

This file provides guidance to Claude Code when working with this financial transaction management system.

## Project Overview

A Quicken-like financial transaction parser and management system. Processes CSV files from banks/brokerages and provides categorization, analysis, and monitoring through CLI tools and a React web interface.

**Important:** All dates are EDT/EST timezone. In JavaScript, use explicit date construction (`new Date(year, month-1, day)`) to avoid timezone issues.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Process CSV files
python3 main.py --process-existing --stats

# Start web interface
python3 api_server.py          # Terminal 1 - Backend on :5000
cd frontend && npm run dev      # Terminal 2 - Frontend on :3001
```

## Key Development Standards

### Frontend
- **Chart Library:** Always use Recharts (not custom SVG) - see `GenericChart.tsx` and `Budget.tsx` for examples
- **Dialogs:** Use Dialog components, never `alert()`, `confirm()`, or `prompt()`
- **App Entry:** Modify `App.router.tsx` for global changes, NOT `App.simple.tsx` (legacy/unused)
- **Theme:** Midnight Ember theme (warm amber accents) via ThemeProvider in App.router.tsx
- **No Emojis:** Banned from text/labels/buttons - only allowed in navigation icons

### Database
- **Budget Table:** Data is in `monthly_budget_items` table (NOT `budget_items`)
- **Transactions:** Hash-based duplicate detection, foreign keys for categories
- All operations through `TransactionDB` class methods

## Common Commands

```bash
# Categorization
python3 main.py --ai-classify 25 --ai-auto-apply
python3 main.py --categorize "PATTERN" "Category" "Subcategory"

# Payee extraction
python3 payee_extractor.py --dry-run
python3 payee_extractor.py --apply

# Recurring patterns
python3 main.py --detect-recurring --save-patterns --lookback-days 365

# Database inspection
sqlite3 transactions.db ".schema"
sqlite3 transactions.db "SELECT * FROM monthly_budget_items LIMIT 5;"
```

## Architecture

- **Backend:** Python/Flask API server (`api_server.py`)
- **Frontend:** React TypeScript with Vite (`frontend/`)
- **Database:** SQLite with normalized schema (`database.py`)
- **CSV Parser:** Handles brokerage format, auto-extracts payees (`csv_parser.py`)
- **AI Classifier:** Pattern-based transaction categorization (`ai_classifier.py`)

## File Structure

```
/var/www/html/bank/
├── *.py                    # Python backend modules
├── transactions.db         # SQLite database
├── requirements.txt        # Python dependencies
├── frontend/              # React TypeScript app
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── contexts/      # React contexts
│   │   ├── types/         # TypeScript interfaces
│   │   └── App.router.tsx # ACTUAL app entry (not App.simple.tsx)
│   └── package.json
└── transactions/          # CSV file drop location
    └── processed/         # Processed files
```

## Key Features

- **Pattern Learning:** Successfully categorized transactions teach the system
- **Recurring Detection:** Identifies subscription/bill patterns for balance projections
- **Multi-Account:** Tracks multiple investment/checking accounts
- **Dashboard:** Configurable 2x2 grid with timeseries/stat/summary cards
- **Balance Projections:** Quicken-style forecasting using recurring patterns

## Development Notes

- Proxy config: Vite proxies `/api` to Flask backend (port 5000)
- Date format: MM/DD/YYYY for database compatibility
- All visualizations use Recharts for consistency
- See `INTERNALS.md` for comprehensive technical documentation
