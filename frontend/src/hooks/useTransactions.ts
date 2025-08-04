import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { transactionApi } from '../utils/api';
import type { TransactionFilters } from '../types';

export const useTransactions = (filters: TransactionFilters) => {
  return useQuery(
    ['transactions', filters],
    () => transactionApi.getTransactions(filters),
    {
      keepPreviousData: true,
    }
  );
};

export const useCategories = () => {
  return useQuery(
    ['categories'],
    transactionApi.getCategories,
    {
      staleTime: 10 * 60 * 1000, // 10 minutes
    }
  );
};

export const useFilterOptions = () => {
  return useQuery(
    ['filter-options'],
    transactionApi.getFilterOptions,
    {
      staleTime: 10 * 60 * 1000, // 10 minutes
    }
  );
};

export const useStats = () => {
  return useQuery(
    ['stats'],
    transactionApi.getStats,
    {
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );
};

export const useUpdateTransaction = () => {
  const queryClient = useQueryClient();
  
  return useMutation(
    ({ id, updates }: { id: number; updates: { category_id?: number; subcategory_id?: number } }) =>
      transactionApi.updateTransaction(id, updates),
    {
      onSuccess: () => {
        // Invalidate and refetch transactions
        queryClient.invalidateQueries(['transactions']);
        queryClient.invalidateQueries(['stats']);
      },
    }
  );
};

export const useBulkCategorize = () => {
  const queryClient = useQueryClient();
  
  return useMutation(
    ({ transaction_ids, category_id, subcategory_id }: {
      transaction_ids: number[];
      category_id: number;
      subcategory_id: number;
    }) => transactionApi.bulkCategorize(transaction_ids, category_id, subcategory_id),
    {
      onSuccess: () => {
        // Invalidate and refetch transactions
        queryClient.invalidateQueries(['transactions']);
        queryClient.invalidateQueries(['stats']);
      },
    }
  );
};