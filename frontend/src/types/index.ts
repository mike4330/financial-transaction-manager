export interface Transaction {
  id: number;
  date: string;
  account: string;
  account_number: string;
  amount: number;
  payee: string | null;
  description: string;
  transaction_type: string;
  category: string | null;
  subcategory: string | null;
  category_id: number | null;
  subcategory_id: number | null;
}

export interface Category {
  id: number;
  name: string;
}

export interface Subcategory {
  id: number;
  name: string;
  category_id: number;
  category_name: string;
}

export interface FilterOptions {
  accounts: string[];
  transaction_types: string[];
  categories: string[];
}

export interface TransactionFilters {
  page: number;
  limit: number;
  account?: string;
  category?: string;
  type?: string;
  start_date?: string;
  end_date?: string;
  uncategorized?: boolean;
}

export interface TransactionResponse {
  transactions: Transaction[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
}

export interface Stats {
  summary: {
    total_transactions: number;
    categorized: number;
    uncategorized: number;
    total_amount: number;
  };
  accounts: Array<{
    account: string;
    count: number;
    total_amount: number;
  }>;
  categories: Array<{
    category: string;
    subcategory: string | null;
    count: number;
    total_amount: number;
  }>;
}