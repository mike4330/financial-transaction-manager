# Interactive QIF Reconciler Guide

## Overview
The Interactive QIF Reconciler streamlines the manual reconciliation process from 1,264 remaining transactions down to focused sessions on the most important conflicts and enhancements.

## Key Features

### 🎯 Smart Filtering
- **Priority Scoring**: Automatically ranks transactions by interest (1-10 scale)
- **Category Focus**: Prioritizes uncategorized transactions that QIF can categorize
- **Skip Boring Stuff**: Auto-filters location-only payee changes
- **Conflict Detection**: Surfaces category conflicts between QIF and existing data

### 🔧 User Preferences Learning
- **Payee Simplification**: Remembers your preference for generic names (Walmart vs "Walmart #1825")
- **Auto-Skip Patterns**: Learns to skip transaction types you consistently reject
- **Category Mapping**: Builds rules from your approval decisions

### 📊 Progress Tracking
- **Session Stats**: Tracks enhancements/skips per session
- **Overall Progress**: Shows completion rate across all 1,270 transactions
- **Interest Scoring**: Shows why each transaction was selected

## Usage

### Preview Mode (Recommended First Step)
```bash
python3 interactive_reconciler.py --preview
```
Shows top 5 most interesting transactions without making changes.

### Interactive Session
```bash
python3 interactive_reconciler.py
```
Starts full interactive reconciliation session.

### Statistics Only
```bash
python3 interactive_reconciler.py --stats
```
Shows current progress without processing transactions.

## Decision Options

During interactive sessions, you can:

- **`approve`** - Apply enhancement exactly as proposed
- **`skip`** - Skip this transaction (logs decision)
- **`modify [payee_name]`** - Change payee to custom name
- **`batch`** - Apply same decision to similar patterns (planned feature)
- **`stats`** - Show current session statistics
- **`quit`** - Exit session (saves preferences)

## Decision Presentation Format

**IMPORTANT**: All enhancement decisions are presented in a standardized three-row table format:

| Field | QIF Value | Current DB Value | Proposed Value |
|-------|-----------|------------------|----------------|
| **Date** | 9/20'24 | 09/20/2024 | (no change) |
| **Amount** | -250.00 | -250.00 | (no change) |
| **Payee** | Transfer To Vs Z23... | Transfer To Vs Z23... | Transfer To Wife's Account |
| **Category** | [Cash Management] | [Cash Management] | (no change) |

This format clearly shows:
- **QIF Value**: Original data from Quicken export
- **Current DB Value**: What's currently in the database
- **Proposed Value**: What will be applied if approved

The three-row comparison makes it easy to understand exactly what changes are being proposed and why.

## Interest Scoring System

| Score | Transaction Type | Example |
|-------|-----------------|---------|
| **10** | Uncategorized → QIF Category | "No category" → "Kids:Kids Activities" |
| **9** | Category Conflict | QIF: "Food" vs DB: "Shopping" |
| **8** | New Payee Pattern | First time seeing "Spotify" merchant |
| **7** | Refunds/Returns | Credit transactions |
| **6** | Large Amounts | Transactions > $500 |
| **5** | Unusual Categories | Rare category combinations |
| **2** | Payee Enhancement Only | Generic → Descriptive payee |
| **1** | Location Only | "Walmart" → "Walmart #1825 VA" |

## Established User Preferences

Based on your previous sessions, the script knows:

### Payee Preferences
- ✅ **Generic Names**: Always prefer "Walmart" over "Walmart #1825 Location"
- ✅ **Simplified Merchants**: "Cabela's" not "Cabela's Online U.S. 417-873-5000"  
- ✅ **Clear Refunds**: "Cabela's Refund" for returns
- ✅ **Location Independence**: Skip enhancements that only add location details
- ✅ **Descriptive Names**: "Transfer To Wife's Account" vs raw account numbers

### Category Preferences  
- ✅ **Apply QIF Categories**: Add categories to uncategorized transactions
- ⏭️ **Skip Split Transactions**: No split handling capability
- ✅ **Prioritize Uncategorized**: Focus on transactions missing categories

### Auto-Skip Patterns
- ⏭️ **Location Enhancements**: Skip payee changes that only add location details
- ⏭️ **Split Transactions**: Skip "--Split--" QIF entries

## Expected Efficiency Gains

### Before (Manual Process)
- **~253 sessions** at 5 transactions each
- **Many boring location-only changes**
- **Hard to find category conflicts**
- **Repetitive payee decisions**

### After (Interactive Script)
- **~20-30 focused sessions** 
- **Only high-value transactions shown**
- **Category conflicts prioritized**
- **Batch operations for patterns** (coming soon)

## File Locations

- **Script**: `interactive_reconciler.py`
- **User Preferences**: `reconciliation_sessions/user_preferences.json` (auto-created)
- **Audit Trail**: All decisions logged in `qif_reconciliation_log` table

## Troubleshooting

### "No interesting transactions found"
- All high-priority reconciliations are complete
- Use `--stats` to check overall progress
- Manual review of remaining transactions may be needed

### Database Connection Errors
- Ensure `transactions.db` exists in current directory
- Check database permissions

### Analysis Files Missing
- Run `python3 quicken_reconciler.py --analyze-batch [batch_file]` first
- Script auto-skips batches without analysis files

## Future Enhancements (Planned)

### Batch Operations
- **Skip All Location Changes**: "Found 47 Walmart location enhancements. Skip all? (y/n)"
- **Apply Pattern**: "Apply 'BJ's' payee to all BJs.Com transactions? (y/n)"
- **Category Mapping**: "Map all 'Auto & Transport:Gas' to Transportation:Gas? (y/n)"

### Enhanced Learning
- **Merchant Recognition**: Auto-detect new merchant patterns
- **Amount-Based Rules**: Handle large vs small transaction differences
- **Seasonal Patterns**: Recognize recurring vs one-time transactions

## Performance Tips

1. **Start with Preview**: Always run `--preview` first to see what's prioritized
2. **Focus Sessions**: Process 10-15 transactions per session for best efficiency
3. **Use Modify Sparingly**: Only modify payees when generic name isn't obvious
4. **Trust the Scoring**: High-scored transactions usually need attention

## Integration with Existing Workflow

The Interactive Reconciler works alongside existing tools:

1. **QIF Parser**: Still need `quicken_reconciler.py --parse` to create batches
2. **Batch Analysis**: Still need `--analyze-batch` to create analysis files  
3. **Progress Tracking**: Uses existing `qif_reconciliation_log` table
4. **Category System**: Integrates with existing category/subcategory structure

This tool transforms the reconciliation process from a manual slog into focused, high-value decision-making sessions.