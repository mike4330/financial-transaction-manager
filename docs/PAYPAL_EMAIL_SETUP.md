# PayPal Pay in 4 Email Parser Setup

This tool extracts PayPal Pay in 4 transaction data from your email and converts it to CSV format compatible with your existing transaction parser.

## Quick Start

### 1. Gmail Setup (Recommended)

**Enable App Passwords:**
1. Go to [Google Account Settings](https://myaccount.google.com/)
2. Security → 2-Step Verification (must be enabled)
3. Security → App passwords
4. Generate an app password for "Mail"
5. Save this 16-character password

### 2. Run the Parser

```bash
# Basic usage (will prompt for password)
python3 paypal_email_parser.py --email your-email@gmail.com

# With password (less secure)
python3 paypal_email_parser.py --email your-email@gmail.com --password your-app-password

# Search last 90 days
python3 paypal_email_parser.py --email your-email@gmail.com --days 90

# Dry run to see what would be extracted
python3 paypal_email_parser.py --email your-email@gmail.com --dry-run

# Custom output filename
python3 paypal_email_parser.py --email your-email@gmail.com --output my_paypal_transactions.csv
```

### 3. Process the Generated CSV

```bash
# Process the generated CSV file
python3 main.py --process-existing

# Or manually move to transactions folder
mv paypal_payin4_transactions_*.csv transactions/
python3 main.py --process-existing
```

## Advanced Usage

### Other Email Providers

```bash
# Outlook/Hotmail
python3 paypal_email_parser.py --email you@outlook.com --server outlook.office365.com --port 993

# Yahoo Mail
python3 paypal_email_parser.py --email you@yahoo.com --server imap.mail.yahoo.com --port 993

# Custom IMAP server
python3 paypal_email_parser.py --email you@example.com --server mail.example.com --port 993
```

### Command Line Options

```
--email          Email address (required)
--password       Email password (will prompt if not provided)
--server         IMAP server (default: imap.gmail.com)
--port           IMAP port (default: 993)
--days           Days back to search (default: 30)
--output         Output CSV filename
--dry-run        Show what would be extracted without creating CSV
--verbose        Enable verbose logging
```

## What It Extracts

The parser looks for PayPal Pay in 4 emails and extracts:

- **Transaction Amount** - From email body
- **Merchant Name** - Store/company name
- **Transaction Date** - When the purchase was made
- **Email Metadata** - For debugging and verification

### Email Search Patterns

The tool searches for emails with:
- **From:** service@paypal.com, paypal@paypal.com, noreply@paypal.com
- **Subject/Body:** "Pay in 4", "PayPal Pay in 4", "installment", "payment plan"
- **Date Range:** Last 30 days (configurable)

## CSV Output Format

Generated CSV files are compatible with your existing transaction parser:

```csv
Run Date,Account,Action,Description,Amount,Type,Currency
01/15/2024,PayPal Pay in 4,DEBIT CARD PURCHASE AMAZON,PayPal Pay in 4 - Amazon,-125.99,Debit Card,USD
01/20/2024,PayPal Pay in 4,DEBIT CARD PURCHASE TARGET,PayPal Pay in 4 - Target,-89.50,Debit Card,USD
```

## Troubleshooting

### Common Issues

**Authentication Failed:**
- Ensure 2FA is enabled
- Use App Password, not regular password
- Check email address spelling

**No Emails Found:**
- Check date range with `--days 90`
- PayPal might use different subject lines
- Try `--verbose` to see search details

**Invalid Amount:**
- Some email formats might not be recognized
- Check the raw email content with `--dry-run`
- May need to adjust regex patterns

### Gmail Security

**"Less secure app access" Error:**
- Don't use "less secure apps"
- Use App Passwords instead (more secure)
- Ensure 2FA is enabled first

### Testing

```bash
# Test connection only
python3 paypal_email_parser.py --email your-email@gmail.com --days 1 --dry-run --verbose

# Test with recent emails
python3 paypal_email_parser.py --email your-email@gmail.com --days 7 --dry-run
```

## Security Notes

- **App Passwords** are safer than regular passwords
- **Never commit passwords** to version control
- Consider using environment variables:
  ```bash
  export PAYPAL_EMAIL="your-email@gmail.com"
  export PAYPAL_PASSWORD="your-app-password"
  ```
- The tool only **reads** emails, never modifies or deletes

## Integration with Existing System

Once you have the CSV file:

1. **Move to transactions folder:**
   ```bash
   mv paypal_payin4_transactions_*.csv transactions/
   ```

2. **Process with existing system:**
   ```bash
   python3 main.py --process-existing --stats
   ```

3. **Categorize as needed:**
   ```bash
   python3 main.py --uncategorized 50
   python3 main.py --categorize "AMAZON" "Shopping" "Online"
   ```

The extracted transactions will appear as "PayPal Pay in 4" account with proper merchant names and amounts.