# Financial Transaction Parser

A comprehensive financial transaction management system with both command-line tools and a modern web interface for parsing and managing CSV files from banks and brokerages, similar to Quicken.

## Features

### Core Processing
- **Automated CSV Processing**: Monitors directory for new CSV files and processes them automatically
- **Duplicate Detection**: Uses transaction hashing to prevent duplicate entries
- **File Management**: Moves processed files to `processed/` directory to avoid reprocessing
- **SQLite Database**: Normalized database with proper foreign key relationships and indexing

### Transaction Categorization
- **Normalized Categories**: Separate tables for categories and subcategories with foreign key relationships
- **Manual Categorization**: Add categories, subcategories, and notes to individual transactions
- **Bulk Categorization**: Auto-categorize multiple transactions based on description/action patterns
- **AI Classification**: AI-powered transaction classification with confidence scoring and auto-apply
- **Category Analysis**: View spending summaries and reports by category and subcategory

### Advanced Features
- **Real-time Monitoring**: File system monitoring for automatic processing of new CSV files
- **Recurring Pattern Detection**: Multi-pass algorithm detects recurring transactions for balance forecasting
- **Balance Projections**: Quicken-style balance forecasting using detected recurring patterns
- **Budget Management**: Template-based budgeting with actual vs budgeted tracking
- **Hybrid Classification**: Pattern learning system eliminates AI calls for repeat transactions
- **Comprehensive Logging**: Detailed logging for monitoring and debugging operations

### Web Interface
- **Modern React Frontend**: TypeScript-based single-page application with professional UI
- **Real-time Dashboard**: Live statistics cards with backend connection status
- **Interactive Visualizations**: Time-series charts with global time range controls
- **Budget Dashboard**: Monthly budget vs actual tracking with pie charts and variance analysis
- **Recurring Patterns Management**: Interactive pattern detection and balance projection charts
- **Display Preferences**: Context-dependent preferences system with account filtering
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **RESTful API**: Flask backend provides comprehensive REST endpoints for all operations

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Process existing CSV files**:
   ```bash
   python main.py --process-existing --transactions-dir ./transactions
   ```

3. **Start monitoring for new files**:
   ```bash
   python main.py --monitor --transactions-dir ./transactions
   ```

4. **View database statistics**:
   ```bash
   python main.py --stats
   ```

5. **Start web interface** (see [Web Interface Quick Start](#web-interface-quick-start))

## Web Interface Quick Start

For the modern React web interface:

1. **Start Flask API backend**:
   ```bash
   python3 api_server.py
   ```

2. **Start React frontend** (in a new terminal):
   ```bash
   cd frontend
   pnpm install  # First time only
   pnpm run dev
   ```

3. **Access the web interface**:
   Open your browser to **http://localhost:3001**
   
   The React app automatically proxies API calls to the Flask backend, so both services work together seamlessly.

See [START_WEB_APP.md](START_WEB_APP.md) for detailed web interface documentation.

## Usage Examples

### Basic Operations
```bash
# Process existing CSV files and show statistics
python3 main.py --process-existing --stats

# Start monitoring directory for new files
python3 main.py --monitor

# Monitor with verbose logging
python3 main.py --monitor --verbose

# Use custom database and directory
python3 main.py -p --database my_transactions.db --transactions-dir /path/to/csvs
```

### Category Management
```bash
# Show category breakdown and spending summary
python3 main.py --categories

# View uncategorized transactions (default 20, specify limit)
python3 main.py --uncategorized 50

# Bulk categorize transactions by pattern matching
python3 main.py --categorize "Amazon.com" "Shopping" "Online"
python3 main.py --categorize "STARBUCKS" "Food" "Coffee"
```

### AI-Powered Classification with Pattern Learning
```bash
# Get AI suggestions for 10 random uncategorized transactions
python3 main.py --ai-classify 10

# Auto-apply high-confidence AI classifications AND learn patterns for future use
python3 main.py --ai-classify 25 --ai-auto-apply

# Initial learning phase: Process larger batch to build pattern cache
python3 main.py --ai-classify 50 --ai-auto-apply --categories

# Ongoing maintenance: Smaller batches for new patterns only
python3 main.py --ai-classify 10 --ai-auto-apply
```

### Payee Extraction
```bash
# Extract merchant names from transaction action column (dry run)
python3 payee_extractor.py --dry-run

# Apply payee extractions to database
python3 payee_extractor.py --apply
```

### Recurring Pattern Detection and Balance Projections
```bash
# Detect recurring patterns from transaction history
python3 main.py --detect-recurring --lookback-days 365

# Save detected patterns to database for balance projections
python3 main.py --detect-recurring --save-patterns --lookback-days 365

# View saved recurring patterns
python3 main.py --show-patterns
```

### Budget Management
```bash
# View database statistics with budget focus
python3 main.py --stats

# Create and manage budgets through web interface
python3 api_server.py  # Start backend
cd frontend && pnpm run dev  # Start frontend
```

### Pattern Learning Workflow
The system uses a hybrid approach that learns from classifications:

1. **Initial Setup**: Run AI classification on a large batch (50-100 transactions) to build initial pattern cache
2. **Automatic Learning**: Every successful AI classification extracts and caches patterns (merchants, keywords, etc.)
3. **Instant Classification**: Future transactions check pattern cache first - no AI calls for known patterns
4. **Batch Processing**: Only truly new/unknown transactions need AI classification
5. **Continuous Improvement**: Pattern cache grows smarter over time

## CSV Format

The system expects CSV files with these columns:
- Run Date, Account, Account Number, Action, Symbol, Description
- Type, Exchange Quantity, Exchange Currency, Quantity, Currency
- Price, Exchange Rate, Commission, Fees, Accrued Interest
- Amount, Settlement Date

## Database Schema

### Core Tables
- **transactions**: Main transaction data with hash-based deduplication
  - Financial data: date, account, amount, description, etc.
  - Foreign keys to categories and subcategories
  - Notes field for manual annotations
  - Source file tracking

- **categories**: Category definitions (Shopping, Food, Investment, etc.)
  - Normalized to prevent typos and enable easy renaming

- **subcategories**: Subcategory definitions linked to parent categories
  - Enforces proper hierarchy (Online → Shopping, Coffee → Food)

- **processed_files**: Tracks processed CSV files to prevent reprocessing
  - File hash checking for change detection

- **classification_patterns**: Learned classification patterns for instant matching
  - Caches successful patterns with confidence scores and usage statistics
  - Enables zero-AI-call classification for repeat merchants and transaction types

- **recurring_patterns**: Detected recurring transaction patterns for balance projections
  - Stores pattern metadata including frequency, amounts, and confidence levels
  - Enables Quicken-style balance forecasting and financial planning

### Budget System Tables
- **budget_templates**: Budget template definitions for creating monthly budgets
- **budget_template_items**: Template items with categories and default amounts  
- **monthly_budgets**: Monthly budget instances created from templates
- **monthly_budget_items**: Individual budget line items with actual vs budgeted tracking
- **budget_adjustments**: Manual adjustments to budget amounts

### Database Features
- Foreign key constraints ensure data integrity
- Optimized for production with minimal overhead initialization
- Indexes on hash, date, and account for fast queries
- Pattern learning cache for instant transaction classification
- Supports manual, bulk, and AI-powered categorization with learning
- Recurring pattern storage for balance projection functionality

## System Architecture

### File Processing Pipeline
1. **Detection**: File system monitoring detects new CSV files in `transactions/` directory
2. **Parsing**: CSV files are parsed with robust error handling for malformed data
3. **Validation**: Transactions are validated for required fields (date, amount)
4. **Deduplication**: Hash-based duplicate detection prevents reprocessing same transactions
5. **Storage**: Valid transactions are stored in normalized database structure
6. **File Management**: Processed files are moved to `processed/` subdirectory
7. **Logging**: Comprehensive logging tracks all operations and errors

### AI Classification System
- **Pattern Matching**: Uses keyword-based rules for common transaction types
- **Investment Detection**: Specialized logic for stocks, ETFs, dividends, and funds
- **Confidence Scoring**: Provides confidence levels (0-1) for each classification suggestion
- **Auto-Apply**: Automatically applies high-confidence classifications (>70%)
- **Random Sampling**: Processes random samples to avoid bias in classification

### Category Management
- **Normalized Structure**: Prevents duplicate categories from typos
- **Bulk Operations**: Pattern-based bulk categorization across all transactions  
- **Manual Override**: Individual transaction categorization with notes
- **Reporting**: Category-based spending analysis and summaries

### Payee Extraction System
- **Intelligent Extraction**: Extracts merchant names from transaction action column
- **Comprehensive Patterns**: Built-in recognition for major retailers, restaurants, gas stations, utilities
- **Smart Fallbacks**: Multiple extraction strategies for different transaction formats
- **Batch Processing**: Processes all "No Description" transactions efficiently
- **Success Rate**: Typically achieves 40-50% extraction success rate from raw transaction data

## Web Interface Features

### Dashboard
- **Real-time Statistics**: Live transaction counts, account summaries, and categorization status
- **Backend Status**: Visual indicator showing Flask API connection status
- **Responsive Cards**: Clean card-based layout with key financial metrics

### Dashboard System  
- **Configurable Grid Layout**: Flexible 2x2 dashboard grid with drag-and-drop card positioning
- **Multiple Visualization Types**: Support for timeseries charts, stat cards, and summary cards
- **LLM-Friendly Configuration**: JSON-based card configuration system designed for easy AI modification
- **Global Time Controls**: Unified time range selector affects all dashboard cards simultaneously
- **Pre-built Cards**: Grocery spending, fast food spending, income tracking, and Amazon purchase analysis

### Budget Management Interface
- **Monthly Budget Views**: Navigate between budget months with comprehensive actual vs budgeted tracking
- **Interactive Pie Charts**: Visual spending breakdown by category with drill-down capability
- **Auto-calculation**: Historical average calculation for budget line items
- **Unbudgeted Category Detection**: Automatically identifies categories with spending but no budget allocation
- **Template-based Creation**: Create new monthly budgets from reusable templates

### Recurring Patterns & Balance Projections
- **Pattern Detection Interface**: Interactive pattern discovery with confidence scoring
- **Balance Projection Charts**: SVG-based balance forecasting with transaction event markers
- **Multi-Account Support**: Handles complex money flow patterns between accounts
- **Estimated Patterns**: Create patterns for cross-account spending analysis

### Interactive Charts
- **Multiple Chart Types**: Line charts, bar charts, and area charts with consistent styling
- **Time Range Controls**: Global time range selector (1M, 3M, 6M, 1Y, 2Y, All Time) 
- **Adaptive Binning**: Automatic weekly/monthly grouping based on selected time range
- **Dynamic Updates**: All charts update automatically when time range changes
- **Professional Styling**: Built with Recharts for publication-quality visualizations
- **Category/Subcategory Filtering**: Charts can display any category/subcategory combination

### Technical Stack
- **Frontend**: React 18 + TypeScript + Vite for fast development
- **Backend**: Flask REST API with CORS support
- **Charts**: Recharts library for interactive data visualization
- **Styling**: Custom CSS with responsive design patterns
- **State Management**: React Context API for global state (time ranges)

## API Endpoints

The Flask API server provides the following REST endpoints:

- `GET /api/health` - Health check and status
- `GET /api/transactions` - List transactions with filtering and pagination
- `GET /api/categories` - Get all categories and subcategories
- `GET /api/stats` - Dashboard statistics and summaries
- `POST /api/transactions/bulk-categorize` - Bulk categorization operations

All endpoints support CORS and return JSON responses with proper error handling.

### Performance Optimization
- **Production-Ready**: Optimized database initialization for instant Flask startup
- **Singleton Pattern**: Shared database instance prevents re-initialization overhead  
- **Fast API Response**: Sub-millisecond response times for common operations
- **Minimal Bootstrap**: Removed expensive migration checks for established databases