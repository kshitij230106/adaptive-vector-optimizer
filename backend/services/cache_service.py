import time
import threading

from collections import OrderedDict


# ============================================================
# SMART CACHING SERVICE
# ============================================================
#
# In-memory LRU cache for search queries and results.
# Features:
#   - Configurable max size and TTL (time-to-live)
#   - Thread-safe operations
#   - Auto-invalidation when new documents are uploaded
#   - Hit/miss statistics tracking
# ============================================================


# ============================================================
# CACHE ENTRY
# ============================================================


class CacheEntry:
    """
    A single cache entry storing the result, creation
    timestamp, and access metadata.
    """

    def __init__(self, key, value):

        self.key = key
        self.value = value
        self.created_at = time.time()
        self.last_accessed = time.time()
        self.access_count = 0

    def is_expired(self, ttl_seconds):
        """
        Checks whether this entry has expired.
        """

        if ttl_seconds <= 0:
            return False

        return (time.time() - self.created_at) > ttl_seconds


# ============================================================
# SMART CACHE
# ============================================================


class SmartCache:
    """
    Thread-safe LRU cache with TTL expiration.

    Parameters:
        max_size:     Maximum number of entries.
        ttl_seconds:  Time-to-live per entry in seconds.
                      0 = no expiration.
    """

    def __init__(self, max_size=100, ttl_seconds=3600):

        self.max_size = max_size
        self.ttl_seconds = ttl_seconds

        # OrderedDict preserves insertion order for LRU

        self._cache = OrderedDict()

        self._lock = threading.Lock()

        # Statistics

        self._hits = 0
        self._misses = 0
        self._evictions = 0

    # --------------------------------------------------------
    # NORMALIZE KEY
    # --------------------------------------------------------

    @staticmethod
    def _normalize_key(query, **kwargs):
        """
        Creates a normalized cache key from the query
        and any additional parameters.
        """

        normalized_query = " ".join(query.lower().split())

        # Include search parameters in the key

        param_parts = []

        for k, v in sorted(kwargs.items()):

            param_parts.append(f"{k}={v}")

        param_string = "|".join(param_parts)

        return f"{normalized_query}||{param_string}"

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    def get(self, query, **kwargs):
        """
        Retrieves a cached result for the given query.
        Returns None if not found or expired.
        """

        key = self._normalize_key(query, **kwargs)

        with self._lock:

            if key not in self._cache:

                self._misses += 1

                return None

            entry = self._cache[key]

            # Check expiration

            if entry.is_expired(self.ttl_seconds):

                del self._cache[key]

                self._misses += 1

                return None

            # Move to end (most recently used)

            self._cache.move_to_end(key)

            entry.last_accessed = time.time()

            entry.access_count += 1

            self._hits += 1

            return entry.value

    # --------------------------------------------------------
    # SET
    # --------------------------------------------------------

    def set(self, query, value, **kwargs):
        """
        Stores a result in the cache.
        Evicts the least recently used entry if full.
        """

        key = self._normalize_key(query, **kwargs)

        with self._lock:

            # If key already exists, update it

            if key in self._cache:

                self._cache[key] = CacheEntry(key, value)

                self._cache.move_to_end(key)

                return

            # Evict LRU entries if at capacity

            while len(self._cache) >= self.max_size:

                self._cache.popitem(last=False)

                self._evictions += 1

            # Insert new entry

            self._cache[key] = CacheEntry(key, value)

    # --------------------------------------------------------
    # INVALIDATE ALL
    # --------------------------------------------------------

    def invalidate_all(self):
        """
        Clears the entire cache. Called when new documents
        are uploaded to ensure stale results are not served.
        """

        with self._lock:

            self._cache.clear()

    # --------------------------------------------------------
    # INVALIDATE BY PATTERN
    # --------------------------------------------------------

    def invalidate_by_pattern(self, pattern):
        """
        Removes all cache entries whose keys contain
        the given pattern string.
        """

        with self._lock:

            keys_to_remove = [
                key for key in self._cache
                if pattern.lower() in key.lower()
            ]

            for key in keys_to_remove:

                del self._cache[key]

    # --------------------------------------------------------
    # CLEANUP EXPIRED
    # --------------------------------------------------------

    def cleanup_expired(self):
        """
        Removes all expired entries from the cache.
        """

        with self._lock:

            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired(self.ttl_seconds)
            ]

            for key in expired_keys:

                del self._cache[key]

            return len(expired_keys)

    # --------------------------------------------------------
    # STATISTICS
    # --------------------------------------------------------

    def get_stats(self):
        """
        Returns cache performance statistics.
        """

        with self._lock:

            total_requests = self._hits + self._misses

            hit_rate = (
                (self._hits / total_requests * 100)
                if total_requests > 0
                else 0.0
            )

            return {
                "cache_size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds,
                "total_requests": total_requests,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_percent": round(hit_rate, 2),
                "evictions": self._evictions,
            }

    # --------------------------------------------------------
    # GET CACHED QUERIES
    # --------------------------------------------------------

    def get_cached_queries(self):
        """
        Returns a list of currently cached query keys
        and their access metadata.
        """

        with self._lock:

            entries = []

            for key, entry in self._cache.items():

                # Extract the original query from the key

                query_part = key.split("||")[0]

                entries.append({
                    "query": query_part,
                    "access_count": entry.access_count,
                    "created_at": entry.created_at,
                    "last_accessed": entry.last_accessed,
                    "is_expired": entry.is_expired(self.ttl_seconds),
                })

            return entries


# ============================================================
# GLOBAL CACHE INSTANCE
# ============================================================

# Default: 200 entries, 1 hour TTL

search_cache = SmartCache(max_size=200, ttl_seconds=3600)
