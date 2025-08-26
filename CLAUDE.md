# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a comprehensive financial transaction parser and management system, similar to Quicken. It processes CSV files from banks/brokerages and provides categorization, analysis, and monitoring capabilities through both command-line tools and a modern web interface.

**Important:** All dates in this project are assumed to be in EDT/EST timezone. When parsing date strings in JavaScript, use explicit date construction (e.g., `new Date(year, month-1, day)`) to avoid timezone conversion issues that can cause off-by-one errors in month grouping.

## Development Commands

### Core Operations
```bash
# Install dependencies
pip install -r requirements.txt

# Process existing CSV files
python3 main.py --process-existing --stats

# Start file monitoring mode
python3 main.py --monitor

# Run with verbose logging for debugging
python3 main.py --monitor --verbose
```

### Database and Category Management
```bash
# View database statistics and account summaries
python3 main.py --stats

# Show category breakdown and spending analysis
python3 main.py --categories

# View uncategorized transactions
python3 main.py --uncategorized 50

# Bulk categorize transactions by pattern (learns patterns for future use)
python3 main.py --categorize "PATTERN" "Category" "Subcategory"

# AI-powered classification with pattern learning
python3 main.py --ai-classify 25 --ai-auto-apply

# Initial setup: Build pattern cache with larger batch
python3 main.py --ai-classify 50 --ai-auto-apply --categories

# Ongoing: Only new patterns need AI classification
python3 main.py --ai-classify 10 --ai-auto-apply
```

### Payee Extraction
```bash
# Extract payees from transaction action column (dry run)
python3 payee_extractor.py --dry-run

# Apply payee extractions to database
python3 payee_extractor.py --apply
```

### Database Operations
```bash
# Inspect database tables
sqlite3 transactions.db ".schema"
sqlite3 transactions.db "SELECT * FROM categories;"
sqlite3 transactions.db "SELECT COUNT(*) FROM transactions WHERE category_id IS NULL;"

# Budget-specific database queries
sqlite3 transactions.db "SELECT * FROM monthly_budgets ORDER BY budget_year DESC, budget_month DESC;"
sqlite3 transactions.db "SELECT mbi.*, c.name as category, sc.name as subcategory FROM monthly_budget_items mbi JOIN categories c ON mbi.category_id = c.id LEFT JOIN subcategories sc ON mbi.subcategory_id = sc.id;"
```

### Recurring Pattern Detection
```bash
# Detect recurring patterns from transaction history
python3 main.py --detect-recurring --lookback-days 365

# Save detected patterns to database for balance projections
python3 main.py --detect-recurring --save-patterns --lookback-days 365

# Show saved recurring patterns
python3 main.py --show-patterns
```

### Web Interface
```bash
# Start Flask API backend (Terminal 1)
python3 api_server.py

# Start React frontend (Terminal 2) 
cd frontend && npm run dev

# Access web interface at http://localhost:3001
```

## Architecture Overview

### Core Components

1. **database.py**: SQLite database management with normalized schema
   - `TransactionDB` class handles all database operations
   - Automatic migration system for schema changes
   - Foreign key relationships for categories/subcategories

2. **csv_parser.py**: CSV file parsing and validation
   - `CSVParser` class handles brokerage CSV format
   - Account normalization (removes duplicate account formats)
   - Payee extraction from action column
   - Transaction type extraction from action patterns
   - Duplicate detection via transaction hashing

3. **file_monitor.py**: File system monitoring and automation
   - `FileMonitor` class uses watchdog for real-time monitoring
   - Automatic processing of new CSV files
   - File management (moving processed files)

4. **ai_classifier.py**: Rule-based transaction classification
   - `AITransactionClassifier` class with pattern matching
   - Transaction type-first classification (95% confidence)
   - Payee-based categorization
   - Confidence scoring and auto-apply functionality

5. **main.py**: Command-line interface and orchestration
   - Argument parsing and command dispatch
   - Logging configuration and error handling
   - Display functions for reports and summaries

6. **html_generator.py**: HTML report generation
   - Account, category, payee, and transaction type summaries
   - Uncategorized transaction listings with payee info

7. **api_server.py**: Flask REST API server
   - RESTful endpoints for transactions, categories, and statistics
   - CORS support for React frontend integration
   - Date filtering and pagination support
   - Bulk categorization operations

8. **payee_extractor.py**: Intelligent payee extraction utility
   - Extracts merchant names from transaction action column
   - Comprehensive pattern library for major retailers, restaurants, utilities
   - Smart fallback algorithms for unknown transaction formats
   - Batch processing with dry-run capability

9. **Recurring Pattern Detection**: Advanced pattern analysis system
   - Multi-pass detection algorithm for different pattern types
   - Exact amount patterns (subscriptions, salary, fixed payments)
   - Fuzzy amount patterns (utilities with variance, credit cards)
   - Day-of-month patterns (regular spending on specific dates)
   - Confidence scoring and pattern classification
   - Database storage for balance projection integration

### Frontend Components

10. **frontend/**: React TypeScript web application
    - Modern single-page application with component-based architecture
    - Real-time transaction management and visualization
    - Global time range controls for all charts and data views
    - Responsive design with professional styling
    - Recurring patterns management interface for balance projections

**Key Frontend Features:**
- **Configurable Dashboard**: 2x2 grid layout with flexible card positioning system
- **Multiple Visualization Types**: Timeseries charts, stat cards, and summary cards
- **LLM-Friendly Configuration**: JSON-based dashboard config designed for AI modification
- **Global Time Controls**: Unified time range selector affects all dashboard cards
- **Pre-built Analytics**: Grocery spending, fast food, income tracking, and Amazon purchase analysis
- **Backend Integration**: Seamless Flask API communication with automatic proxy configuration

**Important Chart Library Standard:**
- **Always use Recharts**: All data visualizations should use the Recharts library for consistency
- **LLM-Friendly**: Recharts provides a more predictable and AI-friendly API compared to custom SVG
- **Built-in Features**: Recharts handles tooltips, responsive design, and accessibility automatically
- **Existing Components**: Reference GenericChart.tsx and Budget.tsx for Recharts implementation examples

### Database Schema

**Core Tables:**
- `transactions`: Main transaction data with foreign keys to categories
- `categories`: Normalized category definitions (Shopping, Food, etc.)
- `subcategories`: Subcategory definitions linked to parent categories
- `classification_patterns`: Learned patterns for instant transaction classification
- `processed_files`: Tracks processed CSV files to prevent reprocessing
- `recurring_patterns`: Detected recurring transaction patterns for balance projections

**Budget System Tables:**
- `budget_templates`: Budget template definitions for creating monthly budgets
- `budget_template_items`: Template items with categories, subcategories, and default amounts
- `monthly_budgets`: Monthly budget instances created from templates
- `monthly_budget_items`: **IMPORTANT**: Individual budget line items (NOT `budget_items`)
- `budget_adjustments`: Manual adjustments to budget amounts

**Key Features:**
- Hash-based duplicate detection
- Foreign key constraints for data integrity
- Pattern learning cache eliminates repeat AI calls
- Automatic migration preserves existing data
- Indexes on hash, date, and account for performance

## CSV File Format

Expected columns from brokerage CSV files:
- Run Date, Account, Account Number, Action, Symbol, Description
- Type, Exchange Quantity, Exchange Currency, Quantity, Currency  
- Price, Exchange Rate, Commission, Fees, Accrued Interest
- Amount, Settlement Date

## Transaction Types (Auto-Extracted from Action Column)

- **Investment Trade**: YOU BOUGHT, YOU SOLD
- **Dividend**: DIVIDEND RECEIVED  
- **Reinvestment**: REINVESTMENT
- **Transfer**: TRANSFERRED FROM/TO, CASH CONTRIBUTION
- **Direct Deposit**: DIRECT DEPOSIT (salary, government payments)
- **Direct Debit**: DIRECT DEBIT (insurance, utilities, subscriptions)
- **Debit Card**: DEBIT CARD PURCHASE
- **ACH Debit/Credit**: ACH transactions
- **Other**: Wire Transfer, Check, ATM, Fee, Interest

## CSV Import Process: Payee, Category, and Subcategory Assignment

During CSV import (`python3 main.py --process-existing`), the system processes each transaction through multiple stages to extract and assign payee, category, and subcategory information:

### Stage 1: Initial CSV Parsing (`csv_parser.py`)

**Payee Extraction:**
- **Automatic**: Payee is extracted from the `Action` column using regex patterns
- **Investment Exception**: Investment transactions (with symbols) get `payee = None`
- **Pattern Matching**: Extracts merchant names from common transaction formats:
  - `DIRECT DEBIT STATE FARM` → "State Farm"
  - `DEBIT CARD PURCHASE WALMART SUPERCENTER` → "Walmart"
  - `PAYPAL *Roetto Julie` → "PayPal (Roetto Julie)"
  - `POS1825 WAL-MART #1825` → "Walmart"
- **Name Standardization**: Converts extracted names to consistent formats using `payee_mapping`
- **Result**: Most transactions get a standardized payee name, some remain `None`

**Category/Subcategory Assignment:**
- **Pattern Cache Lookup**: Checks `classification_patterns` table for previously learned patterns
- **Auto-Classification**: If pattern match found with high confidence, assigns category/subcategory automatically
- **Default State**: Most transactions initially remain uncategorized (`category_id = NULL, subcategory_id = NULL`)
- **Note Added**: Pattern-classified transactions get notes like "Auto-classified from pattern (confidence: 0.85)"

### Stage 2: Post-Import Payee Enhancement (Optional)

**Enhanced Payee Extraction (`payee_extractor.py`):**
```bash
# Preview payee improvements
python3 payee_extractor.py --dry-run

# Apply payee improvements to database
python3 payee_extractor.py --apply
```

- **Advanced Patterns**: Uses more sophisticated regex patterns for merchant extraction
- **Fallback Logic**: Handles cases where initial extraction failed or was generic
- **Merchant Database**: Contains patterns for 100+ major retailers, restaurants, utilities
- **Updates Existing**: Can improve payee names that were set to "No Description" or generic values

### Stage 3: AI-Powered Classification (Manual)

**Category/Subcategory Assignment (`ai_classifier.py`):**
```bash
# Classify sample of uncategorized transactions
python3 main.py --ai-classify 25 --ai-auto-apply

# Classify specific transaction IDs
python3 main.py --ai-classify-ids 1234,5678 --ai-auto-apply
```

- **Uses Existing Payee**: Leverages payee information from Stages 1-2 for better accuracy
- **Multi-Factor Analysis**: Considers payee, action patterns, transaction type, amount
- **High Confidence Auto-Apply**: Automatically applies classifications with >70% confidence
- **Pattern Learning**: Successful classifications are stored in `classification_patterns` for future imports
- **Manual Review**: Lower confidence suggestions require manual approval

### Stage 4: Manual Categorization (Ongoing)

**Bulk and Individual Assignment:**
```bash
# Bulk categorize by pattern
python3 main.py --categorize "AMAZON" "Shopping" "Online"

# Web interface for individual transactions
python3 api_server.py  # Start backend
cd frontend && npm run dev  # Start frontend
```

- **Pattern-Based**: Bulk assign categories to transactions matching description/payee patterns
- **Web Interface**: Individual transaction editing with dropdown selection
- **Pattern Learning**: Manual assignments also feed into the pattern cache

### Summary: What Gets Set When

| Stage | Payee | Category | Subcategory | Typical State After |
|-------|-------|----------|-------------|-------------------|
| **CSV Import** | ✅ Extracted | ⚠️ Pattern match only | ⚠️ Pattern match only | 70% have payee, 10% categorized |
| **Payee Enhancement** | ✅ Improved | ➖ No change | ➖ No change | 90% have payee, 10% categorized |
| **AI Classification** | ➖ No change | ✅ AI suggested | ✅ AI suggested | 90% have payee, 80% categorized |
| **Manual Review** | ✅ Can edit | ✅ Manual assignment | ✅ Manual assignment | 95% have payee, 95% categorized |

### Key Points:

1. **Payee extraction happens immediately** during CSV import
2. **Category assignment is mostly deferred** to post-processing steps
3. **Pattern learning accelerates** future imports by remembering successful classifications
4. **Investment transactions intentionally have no payee** (symbol is the identifier)
5. **Manual work decreases over time** as the pattern cache grows

## Recurring Pattern Detection System

The system automatically detects recurring transactions to enable accurate balance projections and future financial planning.

### Pattern Detection Algorithm

**Multi-Pass Detection Strategy:**
1. **Pass 1: Exact Amount Matching**
   - Groups transactions by payee + exact amount
   - Calculates intervals between occurrences
   - Identifies frequency patterns (weekly, biweekly, monthly, quarterly, annual)
   - Best for: Subscriptions, salary, fixed bills

2. **Pass 2: Fuzzy Amount Matching**
   - Groups by payee with amount variance tolerance (≤50% coefficient of variation)
   - Handles varying bills like utilities, credit card payments
   - Applies confidence penalties for amount inconsistency
   - Best for: Utilities, insurance, variable recurring bills

3. **Pass 3: Day-of-Month Patterns**
   - Detects transactions occurring on consistent calendar days (±2 day tolerance)
   - Focuses on monthly patterns (25-35 day intervals)
   - High confidence for consistent day-of-month spending
   - Best for: Rent, salary, monthly subscriptions on specific dates

### Pattern Classification

**Confidence Levels:**
- **High (≥70%)**: Green indicator - Consistent historical data, reliable for projections
- **Medium (50-69%)**: Yellow indicator - Some variation, moderate reliability
- **Low (<50%)**: Red indicator - Inconsistent data, manual review recommended

**Pattern Types:**
- `exact_amount`: Fixed payments (subscriptions, salary)
- `fuzzy_amount`: Variable amounts with low variance (utilities)
- `day_of_month`: Regular spending on specific calendar days

### Usage Workflow

**Command Line:**
```bash
# Detect patterns (analysis only)
python3 main.py --detect-recurring --lookback-days 365

# Detect and save patterns to database
python3 main.py --detect-recurring --save-patterns --lookback-days 365

# View saved patterns
python3 main.py --show-patterns
```

**Web Interface:**
1. Navigate to "Patterns" page in web interface
2. Click "Detect New Patterns" and set lookback period
3. Review detected patterns with confidence scores
4. Use "Select High Confidence" for quick approval of reliable patterns
5. Click "Save Selected" to store patterns for balance projections
6. Manage active patterns in "Saved Patterns" view

### Pattern Examples from Real Data

**High Confidence Patterns:**
- Direct Deposit: $4,320.24 biweekly (76.7% confidence)
- Spotify: $19.99 monthly (90.0% confidence)
- Netflix: $17.99 monthly (71.5% confidence)
- Regular Transfers: $45.00 biweekly (71.2% confidence)

**Medium Confidence Patterns:**
- State Farm Insurance: ~$281.28 monthly ±$0.61 (61.7% confidence)
- Verizon: $163.00 monthly (58.5% confidence)
- PayPal Transfers: $200.00 on 3rd of month (67.8% confidence)

**Variable Patterns:**
- Taco Bell: ~$24.16 biweekly ±$2.04 (54.4% confidence)
- Gas Stations: Day-of-month patterns with amount variance

### Database Storage

**recurring_patterns Table Schema:**
- Pattern identification (name, payee, account)
- Amount details (typical_amount, amount_variance)
- Frequency data (frequency_type, frequency_interval)
- Prediction data (next_expected_date, last_occurrence_date)
- Quality metrics (confidence, occurrence_count)
- Management fields (is_active, created_at, updated_at)

### API Integration

**Recurring Pattern Endpoints:**
- `POST /api/recurring-patterns/detect` - Detect patterns with configurable lookback period
- `GET /api/recurring-patterns` - Retrieve saved active patterns
- `POST /api/recurring-patterns/save` - Save individual detected pattern
- `PUT /api/recurring-patterns/<id>` - Update pattern (activate/deactivate)
- `DELETE /api/recurring-patterns/<id>` - Deactivate pattern

All endpoints return JSON with confidence levels, pattern metadata, and proper error handling.

## Classification Rules

### Merchant-Specific Rules
- **Food Lion**: Always categorize as Food & Dining/Groceries
- **Walmart**: Transactions > $100 categorize as Food & Dining/Groceries (bulk shopping)
- **Walmart**: Transactions ≤ $100 categorize as Shopping/General

## Development Guidelines

### Code Patterns
- All database operations go through `TransactionDB` class methods
- Use proper error handling and logging throughout
- Transaction hashing prevents duplicates: date + account + action + amount + description
- Foreign key IDs are managed by `get_or_create_category/subcategory` methods
- **Data Visualization Standard**: Always use Recharts library for charts and graphs - it's more LLM-friendly with predictable APIs, built-in responsiveness, and automatic tooltip management
- **UI Dialogs Standard**: NEVER use `alert()`, `confirm()`, or `prompt()` - always use custom Dialog components for professional user experience. The project has a reusable Dialog component that supports both simple messages and custom content.

### Testing
- Test with existing `transactions.db` to verify migration compatibility
- Use `--verbose` flag for detailed logging during development
- Sample data available in `processed/` directory after initial processing

### Common Tasks
- **Adding new categories**: Use `get_or_create_category()` method
- **Bulk operations**: Use `bulk_categorize_by_description()` for pattern matching
- **Schema changes**: Update `_migrate_database()` method for backward compatibility
- **New CSV formats**: Modify `parse_csv_file()` method in csv_parser.py
- **Payee extraction**: Run `payee_extractor.py --apply` after processing new CSV files
- **Web development**: Frontend uses Vite for fast development with hot reload
- **API extensions**: Add new endpoints to `api_server.py` for frontend features

## File Organization

```
/var/www/html/bank/
├── main.py                 # CLI interface and main application
├── database.py             # Database operations and schema management
├── csv_parser.py           # CSV file parsing and validation
├── file_monitor.py         # File system monitoring
├── ai_classifier.py        # AI classification system
├── api_server.py           # Flask REST API server
├── payee_extractor.py      # Payee extraction utility
├── html_generator.py       # HTML report generation
├── requirements.txt        # Python dependencies
├── README.md              # User documentation
├── START_WEB_APP.md       # Web interface quick start guide
├── transactions.db        # SQLite database file
├── transactions/          # Directory for new CSV files
│   └── processed/         # Processed files moved here
├── transaction_parser.log # Application log file
└── frontend/              # React TypeScript web application
    ├── src/
    │   ├── components/    # React components (Dashboard, GenericChart, TimeRangeSelector)
    │   │   ├── Dashboard.tsx       # Main dashboard container with CSS Grid
    │   │   ├── DashboardCard.tsx   # Individual card wrapper component
    │   │   ├── StatCard.tsx        # Single-number display cards
    │   │   ├── SummaryCard.tsx     # Top-N list cards
    │   │   ├── GenericChart.tsx    # Timeseries chart component
    │   │   └── RecurringPatterns.tsx # Pattern detection and management interface
    │   ├── contexts/      # React contexts (TimeRangeContext)
    │   ├── types/         # TypeScript interfaces (dashboard.ts)
    │   ├── config/        # Configuration files (dashboardConfig.ts, chartConfig.ts)
    │   ├── App.simple.tsx # Main application component
    │   ├── main.tsx       # React entry point
    │   └── index.css      # Global styles
    ├── package.json       # Node.js dependencies and scripts
    ├── vite.config.ts     # Vite build configuration
    └── tsconfig.json      # TypeScript configuration
```

## Troubleshooting

### Common Issues
- **Migration errors**: Check database permissions and existing schema
- **CSV parsing errors**: Verify file encoding (handles UTF-8-BOM) and column headers
- **File monitoring**: Ensure `transactions/` directory exists and is writable
- **Duplicate detection**: Hash collisions are rare but possible with identical transactions
- **Web interface connection**: Ensure Flask API is running on port 5000 before starting React app
- **CORS errors**: Flask API includes CORS headers; check browser developer console for issues
- **Date filtering**: Database dates are in MM/DD/YYYY format; API handles conversion
- **Budget table confusion**: Budget data is stored in `monthly_budget_items` table, NOT `budget_items`

### Debugging
- Use `--verbose` for detailed logging
- Check `transaction_parser.log` for historical errors
- Inspect database directly with sqlite3 for data issues
- Use `--stats` to verify transaction counts after operations
- **Web debugging**: Use browser developer tools to inspect API calls and responses
- **React development**: Vite provides detailed error messages and hot reload for quick iteration

## Dashboard System Architecture

### Component Structure
```
Dashboard System:
├── types/dashboard.ts           # TypeScript interfaces for cards and config
├── config/dashboardConfig.ts    # Main dashboard layout configuration
├── components/
│   ├── Dashboard.tsx           # Main dashboard container with CSS Grid
│   ├── DashboardCard.tsx       # Individual card wrapper component
│   ├── StatCard.tsx            # Single-number display cards
│   ├── SummaryCard.tsx         # Top-N list cards
│   └── GenericChart.tsx        # Existing timeseries chart component
└── contexts/TimeRangeContext.tsx # Global time range state management
```

### Configuration System
The dashboard uses a JSON-based configuration system designed for LLM modification:

**DashboardCard Interface:**
- `id`: Unique identifier for the card
- `title`: Display title
- `visualization`: 'timeseries' | 'summary' | 'stat'
- `data`: Category, subcategory, and endpoint configuration
- `layout`: Grid position (row, col, width, height)
- `config`: Visual styling and behavior options

**Example Card Configuration:**
```typescript
{
  id: 'grocery-spending',
  title: 'Grocery Spending',
  visualization: 'timeseries',
  data: { category: 'Food & Dining', subcategory: 'Groceries' },
  layout: { row: 1, col: 1, width: 1, height: 1 },
  config: { chartType: 'line', color: '#2563eb', currency: true }
}
```

### Layout System
- **CSS Grid**: Uses CSS Grid for precise card positioning
- **Configurable Grid**: Grid dimensions set in config (currently 2x2)
- **Responsive Design**: Cards maintain aspect ratio across screen sizes
- **LLM-Friendly**: Grid positions use simple row/col coordinates

### Time Range Integration
- **Global State**: TimeRangeContext provides unified time control
- **Automatic Updates**: All cards automatically update when time range changes
- **Date Formatting**: Consistent MM/DD/YYYY format for database compatibility
- **Adaptive Binning**: Charts automatically switch between weekly/monthly grouping

### Current Dashboard Cards
The default 2x2 dashboard includes:
1. **Grocery Spending** (Row 1, Col 1): Line chart of Food & Dining/Groceries over time
2. **Fast Food Spending** (Row 1, Col 2): Bar chart of Food & Dining/Fast Food over time
3. **Income Over Time** (Row 2, Col 1): Line chart of Income/Salary over time
4. **Amazon Spending** (Row 2, Col 2): Bar chart of Amazon purchases over time

### Adding New Cards
To add a new dashboard card:

1. **Add to config**: Modify `dashboardConfig.ts` with new card definition
2. **Choose visualization**: Select timeseries, stat, or summary type
3. **Set layout**: Specify grid position (row, col, width, height)
4. **Configure data source**: Set category/subcategory or custom endpoint
5. **Style**: Choose colors, chart type, and display options

### API Integration
- **Proxy Configuration**: Vite proxies `/api` requests to Flask backend (port 5000)
- **Frontend Port**: React app runs on port 3001 for remote tunneling
- **Relative URLs**: All fetch calls use relative paths (e.g., `/api/transactions`)
- **Date Parameters**: TimeRangeContext automatically adds date filters

### Missing API Endpoints
Some dashboard card types require additional Flask endpoints:
- `/api/stats/total-transactions` - For transaction count stat cards
- `/api/stats/uncategorized` - For uncategorized count stat cards  
- `/api/stats/total-spending` - For spending total stat cards
- `/api/categories/summary` - For top categories summary cards
- `/api/payees/top` - For top payees summary cards

### Card Types

#### Timeseries Cards
- Use existing `GenericChart` component with Recharts
- Support line, bar, and area chart types
- Automatic time range filtering and adaptive binning
- Category/subcategory or payee-based filtering

#### Stat Cards
- Display single numerical values (counts, totals, averages)
- Support currency formatting and percentage changes
- Color-coded indicators for positive/negative values
- Require specific stat API endpoints

#### Summary Cards
- Show top-N lists (categories, payees, accounts)
- Sortable by amount, count, or other metrics
- Expandable/collapsible for space efficiency
- Require summary API endpoints with limit parameters

### Development Best Practices
- **Component Reuse**: Leverage existing GenericChart for new timeseries cards
- **Configuration First**: Add cards via config before building custom components
- **TypeScript**: Maintain strict typing for all interfaces and components
- **Testing**: Test cards with different time ranges and data scenarios
- **Performance**: Use React.memo() for expensive chart components
- **Accessibility**: Ensure proper ARIA labels and keyboard navigation

### Future Enhancements
- **Drag & Drop**: Card repositioning via mouse/touch interface
- **Card Templates**: Pre-built card configurations for common use cases
- **Export/Import**: Save and load custom dashboard configurations
- **Real-time Updates**: WebSocket integration for live data updates
- **Custom Endpoints**: Support for user-defined API endpoints and queries
- **Responsive Breakpoints**: Different layouts for mobile/tablet/desktop
- **Card Resizing**: Dynamic width/height adjustment within grid constraints

## Display Preferences System

The application features a comprehensive, context-dependent preferences system that allows users to customize their experience. Preferences are automatically saved to localStorage and persist across browser sessions.

### Accessing Preferences

Click the gear icon (⚙️) in the navigation bar to open the Display Preferences modal. The content changes based on your current page:
- **Home page**: Dashboard and account filtering preferences
- **Transactions page**: Table display and behavior preferences

### Home Page Preferences (Dashboard)

#### Account Filter
```typescript
// Select which accounts to display in dashboard charts
selectedAccounts: string[]  // Array of account names to include
```

**Features:**
- **Dynamic loading**: Fetches available accounts from `/api/filters` endpoint
- **Multi-select interface**: Grid layout with checkboxes for each account
- **Real-time filtering**: Dashboard charts update immediately when selections change
- **Show all behavior**: Leave all unchecked to display data from all accounts

**Usage:**
- Check specific accounts to filter dashboard to only those accounts
- Useful for focusing on specific investment accounts, checking accounts, etc.
- Charts automatically refresh with filtered data

#### Dashboard Layout
```typescript
dashboardLayout: '2x2' | '3x2' | '4x2' | 'custom'  // Grid configuration
compactView: boolean           // Reduces card padding and spacing
autoRefresh: boolean          // Enables automatic data refresh
refreshInterval: number       // Refresh frequency in seconds (15, 30, 60, 300)
```

**Features:**
- **Grid layouts**: Choose from predefined grid sizes or custom configuration
- **Compact mode**: Reduces visual clutter for information-dense viewing
- **Auto-refresh**: Keep data current without manual page refresh
- **Configurable intervals**: Balance freshness with performance

### Transactions Page Preferences

#### Table Display
```typescript
defaultPageSize: number       // Number of transactions per page (25, 50, 100, 200)
defaultSortColumn: string     // Initial sort field ('date', 'amount', 'payee', 'category')
defaultSortDirection: 'asc' | 'desc'  // Sort order preference
compactRows: boolean          // Reduces row height for denser table view
highlightUncategorized: boolean       // Visual emphasis on uncategorized transactions
```

**Features:**
- **Performance tuning**: Adjust page size based on browser performance
- **Default sorting**: Set preferred initial sort order for consistency
- **Visual density**: Compact rows show more data in limited screen space
- **Categorization workflow**: Highlight uncategorized items for easier processing

### Global Preferences

Applied across all pages and components:

```typescript
// Appearance
theme: 'light' | 'dark' | 'auto'     // Color scheme preference
animationsEnabled: boolean           // Enable/disable UI animations

// Localization  
currency: 'USD' | 'EUR' | 'GBP' | 'CAD'     // Display currency
dateFormat: 'MM/DD/YYYY' | 'DD/MM/YYYY' | 'YYYY-MM-DD' | 'MMM DD, YYYY'
timeZone: string                     // Time zone for date display
defaultTimeRange: string             // Initial time range selection

// Behavior
showTooltips: boolean               // Enable helpful tooltip displays
```

### Technical Implementation

#### PreferencesContext Architecture
```typescript
// Main context provider with three preference categories
interface PreferencesContextType {
  homePreferences: HomePreferences;
  transactionsPreferences: TransactionsPreferences;
  globalPreferences: GlobalPreferences;
  updateHomePreferences: (prefs: Partial<HomePreferences>) => void;
  updateTransactionsPreferences: (prefs: Partial<TransactionsPreferences>) => void;
  updateGlobalPreferences: (prefs: Partial<GlobalPreferences>) => void;
  resetToDefaults: (page?: 'home' | 'transactions' | 'global') => void;
}
```

#### Component Integration
- **App.simple.tsx**: Wraps application with PreferencesProvider
- **DisplayPreferences.tsx**: Context-dependent modal content based on currentPage prop
- **GenericChart.tsx**: Respects account filtering preferences with client-side filtering
- **TransactionsList.tsx**: Can integrate transaction preferences for default behavior

#### Data Flow
1. **Preference changes** → Immediately saved to localStorage via context actions
2. **Account filtering** → useEffect dependency triggers chart re-rendering
3. **Page context** → Modal displays relevant preference sections
4. **Persistence** → useEffect loads saved preferences on app initialization

#### Performance Considerations
- **Client-side filtering**: Account filtering happens after API fetch to avoid complex backend changes
- **Efficient updates**: useEffect dependencies prevent unnecessary re-renders
- **localStorage caching**: Preferences load instantly on app startup
- **Selective updates**: Only changed preference categories trigger updates

### Development Guidelines

#### Adding New Preferences
1. **Define interface**: Add new properties to appropriate preference interface
2. **Update defaults**: Set sensible default values in context provider
3. **Add UI controls**: Create form elements in DisplayPreferences component
4. **Implement behavior**: Use preferences in relevant components via usePreferences hook
5. **Handle persistence**: Context automatically manages localStorage

#### Account Filtering Integration
```typescript
// Example: Adding account filtering to new components
const { homePreferences } = usePreferences();

// Filter data by selected accounts
const filteredData = rawData.filter(item => 
  homePreferences.selectedAccounts.length === 0 || 
  homePreferences.selectedAccounts.includes(item.account)
);
```

#### Context-Dependent Preferences
```typescript
// Example: Different preferences per page
{currentPage === 'home' && (
  <AccountFilterSection />
)}
{currentPage === 'transactions' && (
  <TableDisplaySection />
)}
// Global preferences shown on all pages
<GlobalSettingsSection />
```

### File Organization

```
frontend/src/
├── contexts/
│   └── PreferencesContext.tsx      # Main preferences context and types
├── components/
│   ├── DisplayPreferences.tsx      # Context-dependent preferences modal
│   ├── DisplayPreferences.module.css  # Modal styling
│   └── GenericChart.tsx           # Updated with account filtering
└── App.simple.tsx                 # Provider integration and modal trigger
```

### API Integration

The preferences system integrates with existing API endpoints:
- **Account loading**: `GET /api/filters` for available account names
- **Data filtering**: Client-side filtering of API responses by selected accounts
- **Future enhancement**: Server-side account filtering for improved performance

### Troubleshooting

#### Common Issues
- **Preferences not saving**: Check browser localStorage permissions
- **Charts not updating**: Verify useEffect dependencies include preference changes  
- **Modal not opening**: Ensure currentPage prop is passed correctly
- **Account list empty**: Check `/api/filters` endpoint connectivity

#### Debug Tools
- **Browser DevTools**: Inspect localStorage for saved preferences
- **React DevTools**: Monitor context state changes
- **Console logging**: PreferencesContext logs errors during localStorage operations
- **Network tab**: Verify `/api/filters` response for account data

### Best Practices
- **Minimal preferences**: Only add settings that significantly impact user workflow
- **Sensible defaults**: Choose defaults that work for majority of users
- **Context awareness**: Show only relevant preferences per page
- **Immediate feedback**: Apply changes instantly when possible
- **Reset functionality**: Always provide way to restore defaults

## Recent System Enhancements

### Balance Projection System
Complete implementation of Quicken-style balance forecasting:

- **Interactive Chart**: SVG-based balance projection with transaction event markers
- **Smart Markers**: Shows colored dots only on days with projected transactions
- **Rich Tooltips**: Hover over markers to see transaction details, amounts, and confidence
- **Account-Specific**: Focuses on Individual TOD account (Z06431462) for accurate projections
- **API Integration**: Real-time calculation using stored recurring patterns

### Enhanced Pattern Detection
Improved recurring transaction detection with investment filtering:

- **Investment Exclusion**: Automatically filters out stock trades, dividends, and reinvestments
- **Payee Data Quality**: Fixed 20+ mortgage payments and 46+ utility transactions with missing payee data
- **Mortgage Detection**: Now properly identifies "Select Portfolio Servicing" mortgage payments as recurring
- **Utility Patterns**: NOVEC and other bill payments now detected as fuzzy amount patterns
- **Fuzzy Matching**: Handles varying amounts (mortgage: $1500-$1581, utilities with seasonal variation)

### Data Quality Improvements
Database cleanup for better pattern recognition:

- **Payee Standardization**: Updated "No Description" payees to meaningful names
- **Investment Filtering**: Added SQL filters to exclude symbol-based transactions
- **Pattern Count**: Increased from 37 to 48+ detected patterns after cleanup

**Key Files Updated:**
- `database.py`: Enhanced pattern detection SQL with investment filters
- `RecurringPatterns.tsx`: Interactive chart with transaction markers and tooltips
- `RecurringPatterns.module.css`: Tooltip styling and responsive design
- `api_server.py`: Fixed DELETE endpoint parameter handling

## Multi-Account Architecture

The system tracks transactions across multiple accounts with specific roles:

### Account Structure
- **Primary Account (Z06431462)**: Individual TOD account - main account for balance projections
- **Secondary Account (Z23693697)**: Wife's account - intermediate account for specific spending categories

### Money Flow Pattern
```
Primary Account (Z06431462) → Wife's Account (Z23693697) → Actual Purchases
```

**Key Insight**: Money transfers from the primary account to the wife's account, who then makes the actual purchases (especially groceries and food). This creates a "pass-through" effect where:

1. **Transfer Out**: Money leaves the primary account (shows as expense)
2. **Intermediate Stop**: Money arrives in wife's account 
3. **Final Purchase**: Wife's account makes the actual purchase

### Balance Projection Implications

**Problem**: Traditional analysis would double-count this activity:
- Primary account shows money leaving (transfer to wife)
- Wife's account shows money leaving (actual purchase)
- This creates artificial expense inflation in projections

**Solution**: The system handles this through:
- **Estimated Patterns**: Analyze spending across BOTH accounts (Z06431462 + Z23693697) to capture actual spending patterns
- **Balance Projections**: Apply patterns only to PRIMARY account (Z06431462) since that's where the money originates
- **Pattern Storage**: Save estimated patterns to primary account for consistency

### Implementation Details

**Estimated Pattern Creation**:
```javascript
// Analyzes spending across both accounts
WHERE t.account_number IN ('Z06431462', 'Z23693697')

// But stores pattern to primary account
account_number: 'Z06431462'
```

**Why This Works**:
- Captures true spending velocity (wife's purchasing patterns)
- Avoids double-counting in balance projections
- Reflects reality: money leaves primary account at the rate groceries are purchased
- Provides accurate cashflow forecasting for the primary account

**Visual Indicators**:
- Balance charts show blue triangles for estimated patterns
- Estimated patterns marked with "(Estimated)" badge
- Clear distinction from detected recurring patterns

This architecture ensures accurate balance projections while accounting for the multi-account spending workflow.