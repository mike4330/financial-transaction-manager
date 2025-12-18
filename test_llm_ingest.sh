#!/bin/bash
# Test script for LLM-based CSV ingestion

set -e

echo "========================================="
echo "LLM CSV Ingestion Test"
echo "========================================="
echo ""

# Check if API key is set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "Error: ANTHROPIC_API_KEY environment variable not set"
    echo ""
    echo "Set your API key:"
    echo "  export ANTHROPIC_API_KEY='sk-ant-...'"
    echo ""
    echo "Or create a .env file:"
    echo "  cp .env.example .env"
    echo "  # Edit .env and add your key"
    echo "  source .env"
    exit 1
fi

# Check if test CSV exists
if [ ! -f "./test-transactions.csv" ]; then
    echo "Error: ./test-transactions.csv not found"
    echo ""
    echo "Please create test-transactions.csv with your transaction data"
    exit 1
fi

echo "Found: ./test-transactions.csv"
echo "API Key: ${ANTHROPIC_API_KEY:0:20}..."
echo ""

# Install anthropic SDK if needed
if ! python3 -c "import anthropic" 2>/dev/null; then
    echo "Installing anthropic SDK..."
    pip install anthropic
    echo ""
fi

# Check current database stats
echo "Current database stats:"
python3 main.py --stats
echo ""

# Run dry-run first
echo "========================================="
echo "STEP 1: Dry Run Analysis"
echo "========================================="
echo ""
echo "This will:"
echo "  • Call Claude API to analyze CSV structure"
echo "  • Identify column mappings and account info"
echo "  • Check for duplicates (won't insert)"
echo "  • Show what would be imported"
echo ""
python3 llm_csv_ingest.py ./test-transactions.csv --dry-run

echo ""
echo "========================================="
echo "Dry run complete!"
echo "========================================="
echo ""

# Show new transactions table
if [ -f "./test-transactions_import_result.json" ]; then
    python3 show_new_transactions.py ./test-transactions_import_result.json
else
    echo "No result file found"
fi

echo ""
echo "Review the LLM analysis:"
echo "  • Column mappings: ./test-transactions_llm_response.json"
echo "  • Import results: ./test-transactions_import_result.json"
echo ""
read -p "Proceed with actual import? (y/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "========================================="
    echo "STEP 2: Live Import"
    echo "========================================="
    echo ""
    python3 llm_csv_ingest.py ./test-transactions.csv

    echo ""
    echo "========================================="
    echo "Import complete!"
    echo "========================================="
    echo ""

    # Show final results
    if [ -f "./test-transactions_import_result.json" ]; then
        echo "Final results:"
        python3 show_new_transactions.py ./test-transactions_import_result.json
    fi
else
    echo ""
    echo "Import cancelled."
fi
