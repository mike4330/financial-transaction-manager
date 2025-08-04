export interface DashboardCard {
  id: string;
  title: string;
  visualization: 'timeseries' | 'summary' | 'stat' | 'percentage';
  data: {
    category: string;
    subcategory?: string;
    endpoint?: string; // override default endpoint
    // For percentage charts
    numeratorCategory?: string;
    numeratorSubcategory?: string;
    denominatorCategory?: string;
    denominatorSubcategory?: string;
  };
  layout: {
    row: number;
    col: number;
    width: number; // grid columns to span
    height: number; // grid rows to span
  };
  config?: {
    chartType?: 'line' | 'bar' | 'area';
    color?: string;
    showTotal?: boolean;
    showAverage?: boolean;
    currency?: boolean;
    percentage?: boolean;
  };
}

export interface DashboardConfig {
  cards: DashboardCard[];
  grid: {
    columns: number;
    rows: number;
    gap: string;
  };
}