import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
import pandas as pd
from database import TransactionDB
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@st.cache_data
def load_transaction_data():
    """Load transaction data from database with caching"""
    import sqlite3
    
    query = """
    SELECT 
        t.id,
        t.run_date as date,
        t.account,
        t.account_number,
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
    import sqlite3
    
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
        import sqlite3
        
        conn = sqlite3.connect("transactions.db")
        cursor = conn.cursor()
        
        # Update the transaction
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
        page_title="Transaction Editor",
        page_icon="💰",
        layout="wide"
    )
    
    st.title("💰 Financial Transaction Editor")
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
    
    # Transaction type filter
    transaction_types = ['All'] + sorted(df['transaction_type'].dropna().unique().tolist())
    selected_type = st.sidebar.selectbox("Transaction Type", transaction_types)
    
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
    
    if selected_type != 'All':
        filtered_df = filtered_df[filtered_df['transaction_type'] == selected_type]
    
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
    
    # Prepare data for AG-Grid
    display_df = filtered_df[[
        'id', 'date', 'account', 'amount', 'payee', 'description', 
        'transaction_type', 'category', 'subcategory'
    ]].copy()
    
    # Format date and amount columns for display
    display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
    display_df['amount'] = display_df['amount'].apply(lambda x: f"${x:,.2f}")
    
    # Configure AG-Grid
    gb = GridOptionsBuilder.from_dataframe(display_df)
    
    # Configure columns
    gb.configure_column("id", hide=True)
    gb.configure_column("date", header_name="Date", width=120, sortable=True)
    gb.configure_column("account", header_name="Account", width=200, sortable=True)
    gb.configure_column("amount", header_name="Amount", width=120, sortable=True, type=["numericColumn"])
    gb.configure_column("payee", header_name="Payee", width=200, sortable=True)
    gb.configure_column("description", header_name="Description", width=300, sortable=True)
    gb.configure_column("transaction_type", header_name="Type", width=150, sortable=True)
    gb.configure_column("category", header_name="Category", width=150, sortable=True)
    gb.configure_column("subcategory", header_name="Subcategory", width=150, sortable=True)
    
    # Configure grid options
    gb.configure_default_column(filterable=True, sortable=True, resizable=True)
    gb.configure_selection(selection_mode="multiple", use_checkbox=True)
    gb.configure_pagination(enabled=True, paginationPageSize=50)
    gb.configure_side_bar(filters_panel=True, columns_panel=True)
    
    # Build grid options
    grid_options = gb.build()
    
    # Display the grid
    st.subheader("Transactions")
    
    grid_response = AgGrid(
        display_df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        allow_unsafe_jscode=True,
        height=600,
        theme='streamlit'
    )
    
    # Bulk categorization section
    st.markdown("---")
    st.subheader("Bulk Categorization")
    
    selected_rows = grid_response.get('selected_rows', [])
    if selected_rows and len(selected_rows) > 0:
        st.write(f"Selected {len(selected_rows)} transactions")
        
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
                selected_ids = [row['id'] for row in selected_rows]
                
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
        st.info("Select transactions using the checkboxes to enable bulk categorization")

if __name__ == "__main__":
    main()