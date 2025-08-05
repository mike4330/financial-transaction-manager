export function debounce<T extends (...args: any[]) => any>(
  func: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: NodeJS.Timeout;
  
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func(...args), delay);
  };
}

export function useDebouncedCallback<T extends (...args: any[]) => any>(
  callback: T,
  delay: number,
  deps: React.DependencyList
): T {
  const [debouncedCallback] = React.useState(() => debounce(callback, delay));
  
  React.useEffect(() => {
    return () => {
      // Cleanup timeout on unmount
      if (debouncedCallback) {
        debouncedCallback.cancel?.();
      }
    };
  }, [debouncedCallback]);
  
  return React.useCallback(debouncedCallback, deps) as T;
}