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

# Optional: Enable LLM payee extraction (requires ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY='sk-ant-api03-...'
python3 main.py --monitor --enable-llm-payee

# Start web interface
python3 api_server.py          # Terminal 1 - Backend on :5000
cd frontend && pnpm run dev     # Terminal 2 - Frontend on :3001
```

## Service Management

**IMPORTANT:** The app runs as systemd services in production. Always use these commands to restart properly.

### Proper Restart Procedure

```bash
# Full clean restart (RECOMMENDED - prevents port conflicts)
sudo systemctl stop financial-tracker-backend
sudo systemctl stop financial-tracker-frontend
sudo pkill -f api_server.py    # Kill any lingering backend processes
sudo pkill -f vite              # Kill any lingering Vite processes
sleep 2
sudo systemctl start financial-tracker-backend
sudo systemctl start financial-tracker-frontend

# Verify services are running correctly
sudo systemctl status financial-tracker-backend --no-pager
sudo systemctl status financial-tracker-frontend --no-pager

# Frontend should show: "➜  Network: http://5.78.137.108:3001/"
# If it shows port 3002, there's a port conflict - run the full restart again
```

### Quick Restart (if no port conflicts)

```bash
# Restart both services
sudo systemctl restart financial-tracker-backend
sudo systemctl restart financial-tracker-frontend
```

### Service Status & Logs

```bash
# Check service status
sudo systemctl status financial-tracker-backend
sudo systemctl status financial-tracker-frontend

# View recent logs
sudo journalctl -u financial-tracker-backend -n 50
sudo journalctl -u financial-tracker-frontend -n 50

# Follow logs in real-time
sudo journalctl -u financial-tracker-backend -f
sudo journalctl -u financial-tracker-frontend -f

# Check for port conflicts
sudo ss -tulpn | grep -E ":(3001|5000)"
sudo lsof -i :3001 -i :5000
```

### Common Issues

- **Port 3001 conflict**: Frontend starts on port 3002 instead of 3001
  - **Fix**: Use the full clean restart procedure above

- **Backend port 5000 conflict**: API server fails to start
  - **Fix**: `sudo pkill -f api_server.py` then restart service

- **Service won't stop**: Process remains after systemctl stop
  - **Fix**: Use `sudo pkill -f` to force kill, then restart

## Key Development Standards

### Frontend
- **Package Manager:** Use `pnpm` (not npm) - npm has installation issues on this system
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

# Payee extraction (regex-based)
python3 payee_extractor.py --dry-run
python3 payee_extractor.py --apply

# LLM payee extraction (NEW - requires ANTHROPIC_API_KEY)
python3 llm_payee_fix.py --dry-run --limit 50      # Preview
python3 llm_payee_fix.py --apply --limit 50        # Fix missing payees
python3 llm_payee_fix.py --stats                   # Show statistics

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
- **LLM Payee Extraction:** NEW - Intelligent fallback using Claude API when regex fails (90-95% success rate)
- **Multi-Account:** Tracks multiple investment/checking accounts
- **Dashboard:** Configurable 2x2 grid with timeseries/stat/summary cards
- **Balance Projections:** Quicken-style forecasting using recurring patterns

## Development Notes

- Proxy config: Vite proxies `/api` to Flask backend (port 5000)
- Date format: MM/DD/YYYY for database compatibility
- All visualizations use Recharts for consistency
- LLM logging: `llm_payee_extraction.log` for detailed API call logs
- Main logging: `transaction_parser.log` for general system logs
- See `INTERNALS.md` for comprehensive technical documentation
- See `LLM_PAYEE_EXTRACTION.md` for LLM payee extraction details
