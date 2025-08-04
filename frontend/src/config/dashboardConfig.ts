import { DashboardConfig } from '../types/dashboard';

export const defaultDashboardConfig: DashboardConfig = {
  cards: [
    {
      id: 'grocery-spending',
      title: 'Grocery Spending',
      visualization: 'timeseries',
      data: { 
        category: 'Food & Dining', 
        subcategory: 'Groceries' 
      },
      layout: { row: 1, col: 1, width: 1, height: 1 },
      config: { 
        chartType: 'line', 
        color: '#2563eb',
        showTotal: true,
        showAverage: true,
        currency: true
      }
    },
    {
      id: 'fast-food-spending',
      title: 'Fast Food Spending', 
      visualization: 'timeseries',
      data: { 
        category: 'Food & Dining', 
        subcategory: 'Fast Food' 
      },
      layout: { row: 1, col: 2, width: 1, height: 1 },
      config: { 
        chartType: 'bar', 
        color: '#dc2626',
        showTotal: true,
        showAverage: true,
        currency: true
      }
    },
    {
      id: 'income-over-time',
      title: 'Income Over Time',
      visualization: 'timeseries',
      data: { 
        category: 'Income', 
        subcategory: 'Salary'
      },
      layout: { row: 2, col: 1, width: 1, height: 1 },
      config: { 
        chartType: 'line', 
        color: '#10b981',
        showTotal: true,
        showAverage: true,
        currency: true
      }
    },
    {
      id: 'amazon-spending',
      title: 'Amazon Spending Over Time',
      visualization: 'timeseries',
      data: { 
        category: 'Shopping', 
        subcategory: 'Online',
        endpoint: '/api/transactions?payee=Amazon'
      },
      layout: { row: 2, col: 2, width: 1, height: 1 },
      config: { 
        chartType: 'bar', 
        color: '#f59e0b',
        showTotal: true,
        showAverage: true,
        currency: true
      }
    },
    {
      id: 'food-percentage-of-income',
      title: 'Food & Dining as % of Income',
      visualization: 'percentage',
      data: { 
        numeratorCategory: 'Food & Dining',
        denominatorCategory: 'Income',
        denominatorSubcategory: 'Salary'
      },
      layout: { row: 3, col: 1, width: 1, height: 1 },
      config: { 
        chartType: 'bar', 
        color: '#8b5cf6',
        showTotal: false,
        showAverage: true,
        percentage: true
      }
    },
    {
      id: 'transportation-percentage-of-income',
      title: 'Transportation as % of Income',
      visualization: 'percentage',
      data: { 
        numeratorCategory: 'Transportation',
        denominatorCategory: 'Income',
        denominatorSubcategory: 'Salary'
      },
      layout: { row: 3, col: 2, width: 1, height: 1 },
      config: { 
        chartType: 'bar', 
        color: '#ef4444',
        showTotal: false,
        showAverage: true,
        percentage: true
      }
    },
    {
      id: 'utilities-spending',
      title: 'Utilities Over Time',
      visualization: 'timeseries',
      data: { 
        category: 'Utilities'
      },
      layout: { row: 4, col: 1, width: 1, height: 1 },
      config: { 
        chartType: 'line', 
        color: '#06b6d4',
        showTotal: true,
        showAverage: true,
        currency: true
      }
    },
    {
      id: 'mortgage-percentage-of-income',
      title: 'Mortgage as % of Income',
      visualization: 'percentage',
      data: { 
        numeratorCategory: 'Home',
        numeratorSubcategory: 'Mortgage',
        denominatorCategory: 'Income',
        denominatorSubcategory: 'Salary'
      },
      layout: { row: 4, col: 2, width: 1, height: 1 },
      config: { 
        chartType: 'bar', 
        color: '#84cc16',
        showTotal: false,
        showAverage: true,
        percentage: true
      }
    }
  ],
  grid: {
    columns: 2,
    rows: 4,
    gap: '1rem'
  }
};