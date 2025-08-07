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
        color: 'rgba(37, 99, 235, 0.8)',
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
        color: 'rgba(220, 38, 38, 0.8)',
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
        color: 'rgba(16, 185, 129, 0.8)',
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
        color: 'rgba(245, 158, 11, 0.8)',
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
        color: 'rgba(139, 92, 246, 0.8)',
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
        color: 'rgba(239, 68, 68, 0.8)',
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
        color: 'rgba(6, 182, 212, 0.8)',
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
        color: 'rgba(132, 204, 22, 0.8)',
        showTotal: false,
        showAverage: true,
        percentage: true
      }
    },
    {
      id: 'entertainment-online-services',
      title: 'Entertainment/Online Services',
      visualization: 'timeseries',
      data: { 
        category: 'Entertainment',
        subcategory: 'Online Services'
      },
      layout: { row: 5, col: 1, width: 1, height: 1 },
      config: { 
        chartType: 'bar', 
        color: 'rgba(168, 85, 247, 0.8)',
        showTotal: true,
        showAverage: true,
        currency: true
      }
    },
    {
      id: 'spaxx-dividends',
      title: 'SPAXX Dividends',
      visualization: 'timeseries',
      data: { 
        category: 'Income',
        subcategory: 'Dividends',
        endpoint: '/api/transactions?symbol=SPAXX&type=Dividend'
      },
      layout: { row: 5, col: 2, width: 1, height: 1 },
      config: { 
        chartType: 'line', 
        color: 'rgba(22, 163, 74, 0.8)',
        showTotal: true,
        showAverage: true,
        currency: true
      }
    },
    {
      id: 'kids-spending-by-subcategory',
      title: 'Kids Spending by Subcategory',
      visualization: 'stacked',
      data: { 
        category: 'Kids'
      },
      layout: { row: 6, col: 1, width: 2, height: 1 },
      config: { 
        chartType: 'bar', 
        color: 'rgba(236, 72, 153, 0.8)',
        showTotal: true,
        showAverage: false,
        currency: true,
        stacked: true
      }
    },
    {
      id: 'personal-spending-by-subcategory',
      title: 'Personal Spending by Subcategory',
      visualization: 'stacked',
      data: { 
        category: 'Personal Spending'
      },
      layout: { row: 7, col: 1, width: 2, height: 1 },
      config: { 
        chartType: 'bar', 
        color: 'rgba(139, 92, 246, 0.8)',
        showTotal: true,
        showAverage: false,
        currency: true,
        stacked: true
      }
    }
  ],
  grid: {
    columns: 2,
    rows: 7,
    gap: '1rem'
  }
};