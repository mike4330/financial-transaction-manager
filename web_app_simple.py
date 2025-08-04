import streamlit as st
import pandas as pd
import sqlite3
from database import TransactionDB
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@st.cache_data
def load_transaction_data():
    """Load transaction data from database with caching"""
    query = """
    SELECT 
        t.id,
        t.run_date as date,
        t.account,
        t.amount,
        t.payee,
        t.description,
        t.type as transaction_type,
        c.name as category,
        s.name as subcategory,
        t.category_id,
        t.subcategory_id
    FROM transactions t
    LEFT JOIN categories c ON t.category_id = c.id
    LEFT JOIN subcategories s ON t.subcategory_id = s.id
    ORDER BY t.run_date DESC
    """
    
    conn = sqlite3.connect("transactions.db")
    df = pd.read_sql(query, conn)
    conn.close()
    return df

@st.cache_data
def load_categories():
    """Load available categories and subcategories"""
    conn = sqlite3.connect("transactions.db")
    
    # Get categories
    categories_df = pd.read_sql("SELECT id, name FROM categories ORDER BY name", conn)
    
    # Get subcategories with parent category info
    subcategories_df = pd.read_sql("""
        SELECT s.id, s.name, s.category_id, c.name as category_name
        FROM subcategories s
        JOIN categories c ON s.category_id = c.id
        ORDER BY c.name, s.name
    """, conn)
    
    conn.close()
    return categories_df, subcategories_df

def update_transaction_category(transaction_id, category_id, subcategory_id):
    """Update transaction category in database"""
    try:
        conn = sqlite3.connect("transactions.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE transactions 
            SET category_id = ?, subcategory_id = ?
            WHERE id = ?
        """, (category_id, subcategory_id, transaction_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error updating transaction {transaction_id}: {e}")
        return False

def main():
    st.set_page_config(
        page_title="Transaction Editor (Simple)",
        page_icon="💰",
        layout="wide"
    )
    
    st.title("💰 Financial Transaction Editor (Simple Version)")
    st.markdown("---")
    
    # Load data
    try:
        df = load_transaction_data()
        categories_df, subcategories_df = load_categories()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Account filter
    accounts = ['All'] + sorted(df['account'].dropna().unique().tolist())
    selected_account = st.sidebar.selectbox("Account", accounts)
    
    # Category filter
    categories = ['All', 'Uncategorized'] + sorted(df['category'].dropna().unique().tolist())
    selected_category = st.sidebar.selectbox("Category", categories)
    
    # Date range filter
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        min_date = df['date'].min().date()
        max_date = df['date'].max().date()
        
        date_range = st.sidebar.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_account != 'All':
        filtered_df = filtered_df[filtered_df['account'] == selected_account]
    
    if selected_category == 'Uncategorized':
        filtered_df = filtered_df[filtered_df['category'].isna()]
    elif selected_category != 'All':
        filtered_df = filtered_df[filtered_df['category'] == selected_category]
    
    if len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = filtered_df[
            (filtered_df['date'].dt.date >= start_date) & 
            (filtered_df['date'].dt.date <= end_date)
        ]
    
    # Display summary
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Transactions", len(filtered_df))
    with col2:
        categorized = len(filtered_df[filtered_df['category'].notna()])
        st.metric("Categorized", categorized)
    with col3:
        uncategorized = len(filtered_df[filtered_df['category'].isna()])
        st.metric("Uncategorized", uncategorized)
    with col4:
        total_amount = filtered_df['amount'].sum()
        st.metric("Total Amount", f"${total_amount:,.2f}")
    
    st.markdown("---")
    
    # Display transactions using native Streamlit dataframe
    st.subheader("Transactions")
    
    # Prepare display data
    display_df = filtered_df[[
        'id', 'date', 'account', 'amount', 'payee', 'description', 
        'transaction_type', 'category', 'subcategory'
    ]].copy()
    
    # Format for display
    display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
    display_df['amount'] = display_df['amount'].apply(lambda x: f"${x:,.2f}")
    
    # Display with selection
    selected_rows = st.dataframe(
        display_df,
        use_container_width=True,
        height=600,
        on_select="rerun",
        selection_mode="multi-row"
    )
    
    # Bulk categorization
    st.markdown("---")
    st.subheader("Bulk Categorization")
    
    if len(selected_rows.selection.rows) > 0:
        selected_indices = selected_rows.selection.rows
        selected_transactions = display_df.iloc[selected_indices]
        
        st.write(f"Selected {len(selected_transactions)} transactions:")
        st.dataframe(selected_transactions[['date', 'account', 'amount', 'payee', 'category']], use_container_width=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Category selection
            category_options = [''] + categories_df['name'].tolist()
            selected_bulk_category = st.selectbox("Category", category_options, key="bulk_category")
        
        with col2:
            # Subcategory selection (filtered by category)
            if selected_bulk_category:
                category_id = categories_df[categories_df['name'] == selected_bulk_category]['id'].iloc[0]
                filtered_subcategories = subcategories_df[subcategories_df['category_id'] == category_id]
                subcategory_options = [''] + filtered_subcategories['name'].tolist()
                selected_bulk_subcategory = st.selectbox("Subcategory", subcategory_options, key="bulk_subcategory")
            else:
                selected_bulk_subcategory = st.selectbox("Subcategory", [''], key="bulk_subcategory")
        
        if st.button("Apply to Selected Transactions"):
            if selected_bulk_category and selected_bulk_subcategory:
                # Get IDs of selected transactions
                selected_ids = selected_transactions['id'].tolist()
                
                # Get category and subcategory IDs
                category_id = categories_df[categories_df['name'] == selected_bulk_category]['id'].iloc[0]
                subcategory_id = subcategories_df[subcategories_df['name'] == selected_bulk_subcategory]['id'].iloc[0]
                
                # Update transactions
                success_count = 0
                for transaction_id in selected_ids:
                    if update_transaction_category(transaction_id, category_id, subcategory_id):
                        success_count += 1
                
                if success_count > 0:
                    st.success(f"Successfully updated {success_count} transactions!")
                    # Clear cache to reload data
                    load_transaction_data.clear()
                    st.rerun()
                else:
                    st.error("Failed to update transactions")
            else:
                st.warning("Please select both category and subcategory")
    else:
        st.info("Select transactions from the table above to enable bulk categorization")

if __name__ == "__main__":
    main()