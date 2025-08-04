import axios from 'axios';
import type { TransactionFilters, TransactionResponse, FilterOptions, Stats, Category, Subcategory } from '../types';

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
});

export const transactionApi = {
  // Get transactions with filters and pagination
  getTransactions: async (filters: TransactionFilters): Promise<TransactionResponse> => {
    const params = new URLSearchParams();
    
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.append(key, value.toString());
      }
    });

    const response = await api.get(`/transactions?${params}`);
    return response.data;
  },

  // Update a single transaction
  updateTransaction: async (id: number, updates: { category_id?: number; subcategory_id?: number }) => {
    const response = await api.put(`/transactions/${id}`, updates);
    return response.data;
  },

  // Bulk categorize transactions
  bulkCategorize: async (transaction_ids: number[], category_id: number, subcategory_id: number) => {
    const response = await api.post('/transactions/bulk-categorize', {
      transaction_ids,
      category_id,
      subcategory_id,
    });
    return response.data;
  },

  // Get categories and subcategories
  getCategories: async (): Promise<{ categories: Category[]; subcategories: Subcategory[] }> => {
    const response = await api.get('/categories');
    return response.data;
  },

  // Get filter options
  getFilterOptions: async (): Promise<FilterOptions> => {
    const response = await api.get('/filters');
    return response.data;
  },

  // Get dashboard stats
  getStats: async (): Promise<Stats> => {
    const response = await api.get('/stats');
    return response.data;
  },

  // Health check
  healthCheck: async () => {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;