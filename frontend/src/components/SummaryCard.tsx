import React, { useEffect, useState } from 'react';
import { useTimeRange } from '../contexts/TimeRangeContext';

interface SummaryCardProps {
  title: string;
  category: string;
  subcategory?: string;
}

interface SummaryItem {
  name: string;
  value: number;
  count?: number;
}

const SummaryCard: React.FC<SummaryCardProps> = ({ title, category, subcategory }) => {
  const { timeRange, getDateFilter } = useTimeRange();
  const [data, setData] = useState<SummaryItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchSummaryData = async () => {
    setLoading(true);
    try {
      const dateFilter = getDateFilter();
      let endpoint = '';
      
      switch (category) {
        case 'categories':
          endpoint = `/api/categories/summary?start_date=${dateFilter.startDate}&end_date=${dateFilter.endDate}&limit=5`;
          break;
        case 'payees':
          endpoint = `/api/payees/top?start_date=${dateFilter.startDate}&end_date=${dateFilter.endDate}&limit=5`;
          break;
        default:
          endpoint = `/api/summary/${category}?start_date=${dateFilter.startDate}&end_date=${dateFilter.endDate}&limit=5`;
          if (subcategory) {
            endpoint += `&subcategory=${encodeURIComponent(subcategory)}`;
          }
      }

      const response = await fetch(endpoint);
      if (!response.ok) throw new Error('Failed to fetch summary data');
      
      const result = await response.json();
      setData(result);
    } catch (error) {
      console.error('Error fetching summary data:', error);
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummaryData();
  }, [timeRange, category, subcategory]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '1rem' }}>
        <div>Loading...</div>
      </div>
    );
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <h3 style={{ 
        margin: '0 0 0.5rem 0', 
        fontSize: '1rem', 
        fontWeight: '600',
        color: '#374151'
      }}>
        {title}
      </h3>
      
      <div style={{ flex: 1, overflow: 'auto' }}>
        {data.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {data.map((item, index) => (
              <div key={item.name} style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                padding: '0.25rem',
                backgroundColor: index === 0 ? '#f3f4f6' : 'transparent',
                borderRadius: '4px'
              }}>
                <span style={{ 
                  fontSize: '0.9rem',
                  color: '#374151',
                  fontWeight: index === 0 ? '600' : '400'
                }}>
                  {item.name}
                </span>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ 
                    fontSize: '0.9rem',
                    fontWeight: '600',
                    color: item.value < 0 ? '#dc2626' : '#059669'
                  }}>
                    ${Math.abs(item.value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                  {item.count && (
                    <div style={{ 
                      fontSize: '0.75rem',
                      color: '#6b7280'
                    }}>
                      {item.count} transactions
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ 
            textAlign: 'center', 
            color: '#6b7280',
            fontSize: '0.9rem',
            marginTop: '1rem'
          }}>
            No data available
          </div>
        )}
      </div>
    </div>
  );
};

export default SummaryCard;