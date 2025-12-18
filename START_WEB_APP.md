# 🚀 React + Flask Transaction Manager

## Quick Start Guide

### 1. Start the Flask API Backend
```bash
# In terminal 1 (from /var/www/html/bank/)
python3 api_server.py
```
This starts the API server on **http://localhost:5000**

### 2. Start the React Frontend
```bash
# In terminal 2 (from /var/www/html/bank/)
cd frontend
pnpm run dev
# OR: npm run dev (if pnpm not installed)
```
This starts the React app on **http://localhost:3001** (or next available port)

**Note:** Use `pnpm` as the recommended package manager. If not installed: `npm install -g pnpm`

### 3. Access the Application
Open your browser to: **http://localhost:3001**

---

## 🌟 Features Available

### Dashboard (/)
- **Configurable Dashboard**: 2x2 grid layout with flexible card positioning
- **Multiple Chart Types**: Grocery spending, fast food, income tracking, Amazon purchases
- **Real-time Statistics**: Live transaction counts, account summaries, categorization status
- **Backend Status Indicator**: Green "Backend OK" pill showing Flask API connection
- **Global Time Range Controls**: 1 Month, 3 Months, 6 Months, 1 Year, 2 Years, All Time
- **Display Preferences**: Context-dependent preferences with account filtering
- **Responsive Design**: Works seamlessly on desktop and mobile

### Budget Management (/budget)
- **Monthly Budget Views**: Navigate between budget months with full CRUD operations
- **Actual vs Budgeted Tracking**: Real-time comparison with variance analysis
- **Interactive Pie Charts**: Visual spending breakdown by category with percentages
- **Auto-calculation**: Historical average calculation for budget line items based on spending patterns
- **Unbudgeted Category Detection**: Automatically identifies categories with spending but no budget
- **Template-based Creation**: Create new monthly budgets from reusable templates
- **Budget Item Management**: Add/remove categories from monthly budgets dynamically

### Recurring Patterns & Balance Projections (/patterns)
- **Pattern Detection Interface**: Interactive discovery with confidence scoring and filtering
- **Balance Projection Charts**: SVG-based forecasting with transaction event markers
- **Multi-Account Support**: Handles complex money flow patterns between accounts
- **Estimated Patterns**: Create spending patterns for cross-account analysis
- **Pattern Management**: Activate/deactivate patterns, edit amounts and frequencies
- **Category-based Analysis**: Analyze spending patterns by category with statistical metrics

### Transaction Management (/transactions)
- **Advanced Data Grid**: Professional transaction listing with sorting and pagination
- **Multi-level Filtering**: Filter by account, category, date range, transaction type, search terms
- **Bulk Operations**: Multi-select for bulk categorization and operations
- **Inline Editing**: Direct editing of transaction categories, subcategories, and notes
- **Real-time Updates**: Immediate reflection of changes across all views

### API Endpoints (http://localhost:5000/api/)
**Core Data:**
- `GET /health` - Health check and system status
- `GET /transactions` - List transactions with advanced filtering and pagination
- `GET /categories` - Categories and subcategories for dropdown menus
- `GET /stats` - Dashboard statistics and account summaries
- `GET /filters` - Available filter options (accounts, types, categories)

**Transaction Operations:**
- `PUT /transactions/<id>` - Update individual transaction categories/notes
- `POST /transactions/bulk-categorize` - Bulk categorization operations
- `DELETE /transactions/bulk-delete` - Bulk deletion operations

**Budget System:**
- `GET /budget/<year>/<month>` - Monthly budget with actual vs budgeted
- `POST /budget/<year>/<month>/update-actuals` - Refresh actual amounts
- `PUT /budget/items/<id>` - Update budgeted amounts
- `POST /budget/create-next-month` - Create next month's budget
- `POST /budget/<year>/<month>/add-category` - Add category to budget
- `DELETE /budget/<year>/<month>/remove-category` - Remove from budget

**Recurring Patterns:**
- `POST /recurring-patterns/detect` - Detect patterns with configurable lookback
- `GET /recurring-patterns` - List saved active patterns
- `POST /recurring-patterns/save` - Save detected patterns
- `PUT /recurring-patterns/<id>` - Update pattern details
- `DELETE /recurring-patterns/<id>` - Deactivate patterns
- `POST /balance-projection` - Calculate balance projections
- `GET /category-spending-analysis` - Analyze category spending patterns

---

## 🛠 Tech Stack

### Backend
- **Flask** - Python web framework with production optimizations
- **SQLite** - Your existing database with advanced query support
- **CORS** - Cross-origin requests enabled
- **Performance Optimized** - Singleton database pattern, ~200ms startup time

### Frontend  
- **React 18** - Modern UI framework with TypeScript
- **Recharts** - Professional charting library for all data visualizations
- **Context API** - Global state management (time ranges, preferences)
- **CSS Modules** - Component-scoped styling with responsive design
- **Vite** - Fast build tool with hot reload and auto-proxy to backend
- **Professional UI Components** - Custom dialogs, grids, and form controls

---

## 📁 File Structure
```
/var/www/html/bank/
├── main.py                    # Your existing CLI with recurring pattern detection
├── api_server.py             # Flask REST API server (production optimized)
├── database.py               # Database operations (migration-free for production)
├── payee_extractor.py        # Payee extraction utility
├── transactions.db           # SQLite database with budget & pattern tables
├── frontend/                 # React TypeScript application
│   ├── src/
│   │   ├── components/       # React components (40+ files)
│   │   │   ├── Dashboard.tsx         # Configurable dashboard
│   │   │   ├── Budget.tsx           # Budget management interface
│   │   │   ├── RecurringPatterns.tsx # Pattern detection & balance projections
│   │   │   ├── TransactionsList.tsx  # Advanced transaction grid
│   │   │   ├── GenericChart.tsx      # Recharts integration
│   │   │   └── DisplayPreferences.tsx # Context-dependent settings
│   │   ├── contexts/         # React contexts
│   │   │   ├── TimeRangeContext.tsx  # Global time controls
│   │   │   └── PreferencesContext.tsx # User preferences
│   │   ├── types/           # TypeScript definitions
│   │   ├── config/          # Dashboard & chart configuration
│   │   ├── App.simple.tsx   # Main application with routing
│   │   └── main.tsx         # React entry point
│   ├── package.json         # Dependencies & scripts
│   └── vite.config.ts      # Build configuration
└── (CLI tools unchanged)
```

---

## 🔧 Development Notes

### Production Ready
- **Flask startup time**: Optimized to ~200ms (was 3-5 minutes)
- **Database performance**: Removed expensive migrations for production use
- **Singleton pattern**: Shared database instance prevents re-initialization overhead
- **CORS enabled**: Frontend and backend work seamlessly together

### Development Workflow
- **Your existing Python CLI tools remain fully functional**
- Flask API runs independently from main.py
- React dev server auto-reloads on changes
- API calls automatically proxied through Vite dev server
- All existing CSV processing, AI classification, pattern detection works unchanged

### Key Integration Points
- **Database**: Same `transactions.db` used by CLI and web interface
- **Categories**: Web interface reads/writes same category structure as CLI
- **Patterns**: Recurring patterns created by CLI are visualized in web interface
- **Budget data**: Template-based budgets integrate with transaction categorization

---

## 🎯 Next Steps

### Data Enhancement
1. **Extract payees**: Run `python3 payee_extractor.py --apply` to improve transaction data quality
2. **Detect patterns**: Use `python3 main.py --detect-recurring --save-patterns --lookback-days 365` to enable balance projections
3. **Classify transactions**: Run `python3 main.py --ai-classify 50 --ai-auto-apply` to categorize uncategorized transactions

### System Optimization  
4. **Create budgets**: Use the web interface `/budget` to set up monthly budgets from templates
5. **Configure dashboard**: Customize the dashboard cards and time ranges via Display Preferences
6. **Set up monitoring**: Use file monitoring with `python3 main.py --monitor` for automatic CSV processing

### Production Deployment
7. **Security**: Add authentication if deploying outside local network
8. **Database backup**: Set up regular backups of `transactions.db`
9. **Process automation**: Set up cron jobs for recurring tasks (pattern detection, categorization)
10. **Performance monitoring**: Monitor Flask startup time and API response times

---

**Happy coding! 🎉**