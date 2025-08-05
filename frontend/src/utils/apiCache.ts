// Simple in-memory cache for API responses
interface CacheEntry {
  data: any;
  timestamp: number;
  expiry: number;
}

class APICache {
  private cache = new Map<string, CacheEntry>();
  private readonly DEFAULT_TTL = 5 * 60 * 1000; // 5 minutes

  set(key: string, data: any, ttl: number = this.DEFAULT_TTL): void {
    const entry: CacheEntry = {
      data,
      timestamp: Date.now(),
      expiry: Date.now() + ttl
    };
    this.cache.set(key, entry);
  }

  get(key: string): any | null {
    const entry = this.cache.get(key);
    if (!entry) {
      return null;
    }

    if (Date.now() > entry.expiry) {
      this.cache.delete(key);
      return null;
    }

    return entry.data;
  }

  clear(): void {
    this.cache.clear();
  }

  delete(key: string): boolean {
    return this.cache.delete(key);
  }

  // Clear expired entries
  cleanup(): void {
    const now = Date.now();
    for (const [key, entry] of this.cache.entries()) {
      if (now > entry.expiry) {
        this.cache.delete(key);
      }
    }
  }

  // Get cache stats
  getStats(): { size: number; keys: string[] } {
    return {
      size: this.cache.size,
      keys: Array.from(this.cache.keys())
    };
  }
}

// Singleton instance
export const apiCache = new APICache();

// Auto-cleanup every 10 minutes
setInterval(() => {
  apiCache.cleanup();
}, 10 * 60 * 1000);

// Helper function to create cache keys
export const createCacheKey = (url: string, params?: Record<string, any>): string => {
  const paramString = params ? JSON.stringify(params) : '';
  return `${url}${paramString}`;
};

// Enhanced fetch with caching
export const cachedFetch = async (
  url: string, 
  options?: RequestInit, 
  ttl?: number
): Promise<any> => {
  const cacheKey = createCacheKey(url, options);
  
  // Try to get from cache first
  const cached = apiCache.get(cacheKey);
  if (cached) {
    return cached;
  }

  // Fetch from API
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`API request failed: ${response.statusText}`);
  }

  const data = await response.json();
  
  // Cache the response
  apiCache.set(cacheKey, data, ttl);
  
  return data;
};