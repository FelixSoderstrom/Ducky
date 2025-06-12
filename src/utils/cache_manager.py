"""Generic caching utility with TTL support."""

import time
import hashlib
from typing import Dict, Any, Optional


class CacheManager:
    """Generic TTL-based cache manager for documentation and other data."""
    
    def __init__(self, ttl_seconds: int = 3600, max_entries: int = 100):
        """
        Initialize cache manager.
        
        Args:
            ttl_seconds: Time to live for cache entries (default: 1 hour)
            max_entries: Maximum cache entries before cleanup (default: 100)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
    
    def get_cache_key(self, *args: str) -> str:
        """
        Generate cache key from arguments.
        
        Args:
            *args: Arguments to hash into cache key
            
        Returns:
            MD5 hash cache key
        """
        cache_data = "|".join(str(arg) for arg in args)
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    def get(self, cache_key: str) -> Optional[str]:
        """
        Get cached value if valid.
        
        Args:
            cache_key: Cache key to retrieve
            
        Returns:
            Cached value or None if invalid/missing
        """
        if cache_key not in self.cache:
            return None
        
        entry = self.cache[cache_key]
        if self._is_cache_valid(entry):
            return entry["value"]
        else:
            # Remove expired entry
            del self.cache[cache_key]
            return None
    
    def set(self, cache_key: str, value: str) -> None:
        """
        Cache value with timestamp.
        
        Args:
            cache_key: Cache key
            value: Value to cache
        """
        self.cache[cache_key] = {
            "value": value,
            "timestamp": time.time()
        }
        
        # Cleanup if cache is getting too big
        if len(self.cache) > self.max_entries:
            self._cleanup_oldest()
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is still valid based on TTL."""
        return time.time() - cache_entry["timestamp"] < self.ttl_seconds
    
    def _cleanup_oldest(self) -> None:
        """Remove oldest cache entry."""
        if not self.cache:
            return
        
        oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]["timestamp"])
        del self.cache[oldest_key]
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self.cache) 