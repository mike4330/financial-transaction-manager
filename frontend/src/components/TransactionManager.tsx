import React, { useState, useMemo, useCallback } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ColDef, GridReadyEvent, SelectionChangedEvent } from 'ag-grid-community';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';

import { useTransactions, useCategories, useFilterOptions, useBulkCategorize } from '../hooks/useTransactions';
import TransactionFilters from './TransactionFilters';
import BulkCategorization from './BulkCategorization';
import type { Transaction, TransactionFilters as FilterType } from '../types';

const TransactionManager: React.FC = () => {
  const [filters, setFilters] = useState<FilterType>({
    page: 1,
    limit: 100,
  });
  
  const [selectedTransactions, setSelectedTransactions] = useState<Transaction[]>([]);

  const { data: transactionData, isLoading, error } = useTransactions(filters);
  const { data: categoriesData } = useCategories();
  const { data: filterOptions } = useFilterOptions();
  const bulkCategorize = useBulkCategorize();

  // AG-Grid column definitions
  const columnDefs: ColDef[] = useMemo(() => [
    {
      field: 'id',
      headerName: 'ID',
      width: 80,
      hide: true,
    },
    {
      field: 'date',
      headerName: 'Date',
      width: 120,
      sortable: true,
      filter: 'agDateColumnFilter',
    },
    {
      field: 'account',
      headerName: 'Account',
      width: 200,
      sortable: true,
      filter: 'agTextColumnFilter',
    },
    {
      field: 'amount',
      headerName: 'Amount',
      width: 120,
      sortable: true,
      filter: 'agNumberColumnFilter',
      valueFormatter: (params) => {
        if (params.value === null || params.value === undefined) return '';
        return new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: 'USD',
        }).format(params.value);
      },
      cellClass: (params) => {
        if (params.value === null || params.value === undefined) return '';
        return params.value >= 0 ? 'text-green-600 font-medium' : 'text-red-600 font-medium';
      },
    },
    {
      field: 'payee',
      headerName: 'Payee',
      width: 200,
      sortable: true,
      filter: 'agTextColumnFilter',
      valueFormatter: (params) => params.value || 'N/A',
    },
    {
      field: 'description',
      headerName: 'Description',
      width: 300,
      sortable: true,
      filter: 'agTextColumnFilter',
      tooltipField: 'description',
    },
    {
      field: 'transaction_type',
      headerName: 'Type',
      width: 150,
      sortable: true,
      filter: 'agSetColumnFilter',
    },
    {
      field: 'category',
      headerName: 'Category',
      width: 150,
      sortable: true,
      filter: 'agSetColumnFilter',
      valueFormatter: (params) => params.value || 'Uncategorized',
      cellClass: (params) => {
        return params.value ? '' : 'bg-yellow-50 text-yellow-800';
      },
    },
    {
      field: 'subcategory',
      headerName: 'Subcategory',
      width: 150,
      sortable: true,
      filter: 'agSetColumnFilter',
      valueFormatter: (params) => params.value || '-',
    },
  ], []);

  // AG-Grid default column properties
  const defaultColDef = useMemo(() => ({
    resizable: true,
    sortable: true,
    filter: true,
  }), []);

  const onSelectionChanged = useCallback((event: SelectionChangedEvent) => {
    const selectedRows = event.api.getSelectedRows() as Transaction[];
    setSelectedTransactions(selectedRows);
  }, []);

  const handleBulkCategorize = async (categoryId: number, subcategoryId: number) => {
    if (selectedTransactions.length === 0) return;

    const transactionIds = selectedTransactions.map(t => t.id);
    
    try {
      await bulkCategorize.mutateAsync({
        transaction_ids: transactionIds,
        category_id: categoryId,
        subcategory_id: subcategoryId,
      });
      
      // Clear selection after successful update
      setSelectedTransactions([]);
    } catch (error) {
      console.error('Bulk categorization failed:', error);
    }
  };

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <h3 className="text-red-800 font-medium">Error loading transactions</h3>
        <p className="text-red-700 text-sm mt-1">
          {error instanceof Error ? error.message : 'Unknown error occurred'}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Transaction Management</h2>
          <p className="text-sm text-gray-600 mt-1">
            Manage and categorize your financial transactions
          </p>
        </div>

        <div className="p-6">
          {/* Filters */}
          <TransactionFilters
            filters={filters}
            onFiltersChange={setFilters}
            filterOptions={filterOptions}
            isLoading={isLoading}
          />

          {/* Summary */}
          {transactionData && (
            <div className="mb-6 p-4 bg-gray-50 rounded-lg">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="font-medium text-gray-700">Total: </span>
                  <span className="text-gray-900">{transactionData.pagination.total}</span>
                </div>
                <div>
                  <span className="font-medium text-gray-700">Page: </span>
                  <span className="text-gray-900">
                    {transactionData.pagination.page} of {transactionData.pagination.pages}
                  </span>
                </div>
                <div>
                  <span className="font-medium text-gray-700">Selected: </span>
                  <span className="text-blue-600 font-medium">{selectedTransactions.length}</span>
                </div>
                <div>
                  <span className="font-medium text-gray-700">Showing: </span>
                  <span className="text-gray-900">{transactionData.transactions.length}</span>
                </div>
              </div>
            </div>
          )}

          {/* Bulk Categorization */}
          {selectedTransactions.length > 0 && categoriesData && (
            <div className="mb-6">
              <BulkCategorization
                selectedCount={selectedTransactions.length}
                categories={categoriesData.categories}
                subcategories={categoriesData.subcategories}
                onCategorize={handleBulkCategorize}
                isLoading={bulkCategorize.isPending}
              />
            </div>
          )}

          {/* Transaction Grid */}
          <div className="ag-theme-alpine" style={{ height: '600px', width: '100%' }}>
            {isLoading ? (
              <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              </div>
            ) : (
              <AgGridReact
                rowData={transactionData?.transactions || []}
                columnDefs={columnDefs}
                defaultColDef={defaultColDef}
                rowSelection="multiple"
                onSelectionChanged={onSelectionChanged}
                pagination={false} // We handle pagination through API
                suppressRowClickSelection={false}
                rowHeight={40}
                headerHeight={48}
                animateRows={true}
                enableRangeSelection={true}
                suppressMovableColumns={false}
                tooltipShowDelay={1000}
              />
            )}
          </div>

          {/* Pagination */}
          {transactionData && transactionData.pagination.pages > 1 && (
            <div className="mt-4 flex items-center justify-between">
              <div className="text-sm text-gray-700">
                Showing {((transactionData.pagination.page - 1) * transactionData.pagination.limit) + 1} to{' '}
                {Math.min(transactionData.pagination.page * transactionData.pagination.limit, transactionData.pagination.total)} of{' '}
                {transactionData.pagination.total} results
              </div>
              
              <div className="flex space-x-2">
                <button
                  onClick={() => setFilters(prev => ({ ...prev, page: prev.page - 1 }))}
                  disabled={transactionData.pagination.page <= 1}
                  className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <span className="px-3 py-1 text-sm text-gray-700">
                  Page {transactionData.pagination.page} of {transactionData.pagination.pages}
                </span>
                <button
                  onClick={() => setFilters(prev => ({ ...prev, page: prev.page + 1 }))}
                  disabled={transactionData.pagination.page >= transactionData.pagination.pages}
                  className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TransactionManager;