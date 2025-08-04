export interface ChartConfig {
  id: string;
  title: string;
  emoji: string;
  category: string;
  subcategory: string;
  color: string;
  enabled: boolean;
}

export const CHART_CONFIGS: ChartConfig[] = [
  {
    id: 'groceries',
    title: 'Grocery Spending Over Time',
    emoji: '🛒',
    category: 'Food & Dining',
    subcategory: 'Groceries',
    color: '#3b82f6',
    enabled: true
  },
  {
    id: 'fastfood',
    title: 'Fast Food Spending Over Time', 
    emoji: '🍔',
    category: 'Food & Dining',
    subcategory: 'Fast Food',
    color: '#dc2626',
    enabled: true
  },
  // Add more chart configurations here as needed
  {
    id: 'restaurants',
    title: 'Restaurant Spending Over Time',
    emoji: '🍽️',
    category: 'Food & Dining', 
    subcategory: 'Restaurants',
    color: '#059669',
    enabled: false // disabled by default
  },
  {
    id: 'gas',
    title: 'Gas Spending Over Time',
    emoji: '⛽',
    category: 'Transportation',
    subcategory: 'Gas',
    color: '#f59e0b',
    enabled: false
  }
];