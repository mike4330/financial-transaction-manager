import React, { createContext, useContext, useState, ReactNode } from 'react';

export type TimeRange = '1M' | '3M' | '6M' | '1Y' | '2Y' | 'ALL';

interface TimeRangeContextType {
  timeRange: TimeRange;
  setTimeRange: (range: TimeRange) => void;
  getDateFilter: () => { startDate?: string; endDate?: string };
  startFromZero: boolean;
  setStartFromZero: (startFromZero: boolean) => void;
}

const TimeRangeContext = createContext<TimeRangeContextType | undefined>(undefined);

export const useTimeRange = () => {
  const context = useContext(TimeRangeContext);
  if (!context) {
    throw new Error('useTimeRange must be used within a TimeRangeProvider');
  }
  return context;
};

interface TimeRangeProviderProps {
  children: ReactNode;
}

export const TimeRangeProvider: React.FC<TimeRangeProviderProps> = ({ children }) => {
  const [timeRange, setTimeRange] = useState<TimeRange>('6M');
  const [startFromZero, setStartFromZero] = useState<boolean>(false);

  const getDateFilter = () => {
    // Simple day-based subtraction approach
    const now = new Date();
    let daysToSubtract: number;

    switch (timeRange) {
      case '1M':
        daysToSubtract = 30;
        break;
      case '3M':
        daysToSubtract = 90;
        break;
      case '6M':
        daysToSubtract = 180;
        break;
      case '1Y':
        daysToSubtract = 365;
        break;
      case '2Y':
        daysToSubtract = 730;
        break;
      case 'ALL':
        return {}; // No date filter for 'ALL'
      default:
        daysToSubtract = 180; // Default to 6 months
    }

    const startDate = new Date(now);
    startDate.setDate(startDate.getDate() - daysToSubtract);

    // Format dates as YYYY-MM-DD (ISO format)
    const formatDate = (date: Date) => {
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    };

    return {
      startDate: formatDate(startDate)
      // No end date - let it include everything up to now
    };
  };

  return (
    <TimeRangeContext.Provider value={{ timeRange, setTimeRange, getDateFilter, startFromZero, setStartFromZero }}>
      {children}
    </TimeRangeContext.Provider>
  );
};