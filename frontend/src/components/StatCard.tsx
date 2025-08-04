import React, { useEffect, useState } from 'react';
import { useTimeRange } from '../contexts/TimeRangeContext';

interface StatCardProps {
  title: string;
  category: string;
  subcategory?: string;
  currency?: boolean;
  color?: string;
}

interface StatData {
  value: number;
  change?: number;
  label?: string;
}

const StatCard: React.FC<StatCardProps> = ({ 
  title, 
  category, 
  subcategory, 
  currency = false, 
  color = '#2563eb' 
}) => {
  const { timeRange, getDateFilter } = useTimeRange();
  const [data, setData] = useState<StatData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchStatData = async () => {
    setLoading(true);
    try {
      const dateFilter = getDateFilter();
      let endpoint = '';
      
      switch (category) {
        case 'all':
          endpoint = `/api/stats/total-transactions?start_date=${dateFilter.startDate}&end_date=${dateFilter.endDate}`;
          break;
        case 'uncategorized':
          endpoint = `/api/stats/uncategorized?start_date=${dateFilter.startDate}&end_date=${dateFilter.endDate}`;
          break;
        case 'spending':
          endpoint = `/api/stats/total-spending?start_date=${dateFilter.startDate}&end_date=${dateFilter.endDate}`;
          break;
        default:
          endpoint = `/api/stats/category-total?category=${encodeURIComponent(category)}&start_date=${dateFilter.startDate}&end_date=${dateFilter.endDate}`;
          if (subcategory) {
            endpoint += `&subcategory=${encodeURIComponent(subcategory)}`;
          }
      }

      const response = await fetch(endpoint);
      if (!response.ok) throw new Error('Failed to fetch stat data');
      
      const result = await response.json();
      setData(result);
    } catch (error) {
      console.error('Error fetching stat data:', error);
      setData({ value: 0, label: 'Error' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatData();
  }, [timeRange, category, subcategory]);

  const formatValue = (value: number) => {
    if (currency) {
      return `$${Math.abs(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }
    return value.toLocaleString();
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '1rem' }}>
        <div>Loading...</div>
      </div>
    );
  }

  return (
    <div style={{ textAlign: 'center', height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <h3 style={{ 
        margin: '0 0 0.5rem 0', 
        fontSize: '1rem', 
        fontWeight: '600',
        color: '#374151'
      }}>
        {title}
      </h3>
      
      <div style={{ 
        fontSize: '2rem', 
        fontWeight: 'bold', 
        color: color,
        marginBottom: '0.25rem'
      }}>
        {data ? formatValue(data.value) : '—'}
      </div>
      
      {data?.label && (
        <div style={{ 
          fontSize: '0.9rem', 
          color: '#6b7280',
          marginTop: '0.25rem'
        }}>
          {data.label}
        </div>
      )}
      
      {data?.change !== undefined && (
        <div style={{ 
          fontSize: '0.9rem', 
          color: data.change >= 0 ? '#10b981' : '#ef4444',
          marginTop: '0.25rem'
        }}>
          {data.change >= 0 ? '↑' : '↓'} {Math.abs(data.change).toFixed(1)}%
        </div>
      )}
    </div>
  );
};

export default StatCard;