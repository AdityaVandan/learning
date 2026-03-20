import threading
import time


NOT_FOUND = object()


class MockDB:
    def __init__(self):
        self.store = {"user:1": {"name": "Ada"}}
        self.read_count = 0
        self.write_count = 0

    def get(self, key):
        self.read_count += 1
        return self.store.get(key)

    def set(self, key, value):
        self.write_count += 1
        self.store[key] = value


class SimpleCache:
    def __init__(self, default_ttl_seconds=3):
        self.default_ttl_seconds = default_ttl_seconds
        self.data = {}
        self.expiry = {}
        self.pending_writes = {}

    def get(self, key):
        if key not in self.data:
            return None
        exp = self.expiry.get(key)
        if exp is not None and exp < time.time():
            self.delete(key)
            return None
        return self.data[key]

    def set(self, key, value, ttl_seconds=None):
        self.data[key] = value
        ttl = self.default_ttl_seconds if ttl_seconds is None else ttl_seconds
        self.expiry[key] = time.time() + ttl

    def ttl_remaining(self, key):
        exp = self.expiry.get(key)
        if exp is None:
            return None
        return max(0, exp - time.time())

    def delete(self, key):
        self.data.pop(key, None)
        self.expiry.pop(key, None)

    def read_through_get(self, key, db):
        value = self.get(key)
        if value is not None:
            return value
        value = db.get(key)
        if value is not None:
            self.set(key, value)
        return value

    def write_through_set(self, key, value, db):
        db.set(key, value)
        self.set(key, value)

    def write_back_set(self, key, value):
        self.set(key, value)
        self.pending_writes[key] = value

    def flush_pending_writes(self, db):
        for key, value in list(self.pending_writes.items()):
            db.set(key, value)
            del self.pending_writes[key]


class L2Cache(SimpleCache):
    pass


def cache_aside(db, cache, key):
    value = cache.get(key)
    if value is not None:
        return value
    value = db.get(key)
    if value is not None:
        cache.set(key, value)
    return value


def read_through(db, cache, key):
    return cache.read_through_get(key, db)


def write_through(db, cache, key, value):
    cache.write_through_set(key, value, db)


def write_back(db, cache, key, value):
    cache.write_back_set(key, value)
    cache.flush_pending_writes(db)


def write_around(db, cache, key, value):
    db.set(key, value)
    cache.delete(key)


def refresh_ahead(db, cache, key, refresh_threshold_seconds=1):
    value = cache.get(key)
    if value is None:
        value = db.get(key)
        if value is not None:
            cache.set(key, value, ttl_seconds=2)
        return value

    remaining = cache.ttl_remaining(key)
    if remaining is not None and remaining < refresh_threshold_seconds:
        latest = db.get(key)
        if latest is not None:
            cache.set(key, latest, ttl_seconds=2)
            return latest
    return value


def ttl_expiration(cache, key, value):
    cache.set(key, value, ttl_seconds=1)
    first = cache.get(key)
    time.sleep(1.1)
    second = cache.get(key)
    return first, second


def negative_caching(db, cache, key):
    value = cache.get(key)
    if value is NOT_FOUND:
        return None
    if value is not None:
        return value

    value = db.get(key)
    if value is None:
        cache.set(key, NOT_FOUND, ttl_seconds=2)
        return None
    cache.set(key, value)
    return value


class SingleFlight:
    def __init__(self):
        self._locks = {}
        self._global = threading.Lock()

    def run(self, key, fn):
        with self._global:
            lock = self._locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._locks[key] = lock
        with lock:
            return fn()


def request_coalescing(db, cache, singleflight, key):
    value = cache.get(key)
    if value is not None:
        return value

    def load():
        cached = cache.get(key)
        if cached is not None:
            return cached
        db_value = db.get(key)
        if db_value is not None:
            cache.set(key, db_value)
        return db_value

    return singleflight.run(key, load)


def two_level_cache(db, l1_cache, l2_cache, key):
    value = l1_cache.get(key)
    if value is not None:
        return value

    value = l2_cache.get(key)
    if value is not None:
        l1_cache.set(key, value)
        return value

    value = db.get(key)
    if value is not None:
        l2_cache.set(key, value)
        l1_cache.set(key, value)
    return value


def run_all_examples():
    db = MockDB()
    cache = SimpleCache()

    print("1) cache_aside:", cache_aside(db, cache, "user:1"))
    print("2) read_through:", read_through(db, cache, "user:1"))

    write_through(db, cache, "user:2", {"name": "Grace"})
    print("3) write_through:", db.get("user:2"), cache.get("user:2"))

    write_back(db, cache, "user:3", {"name": "Linus"})
    print("4) write_back:", db.get("user:3"), cache.get("user:3"))

    write_around(db, cache, "user:4", {"name": "Ken"})
    print("5) write_around:", db.get("user:4"), cache.get("user:4"))

    print("6) refresh_ahead:", refresh_ahead(db, cache, "user:1"))
    time.sleep(1.4)
    print("   refresh again near expiry:", refresh_ahead(db, cache, "user:1"))

    print("7) ttl_expiration:", ttl_expiration(cache, "temp:key", "temp-value"))

    print("8) negative_caching first miss:", negative_caching(db, cache, "user:999"))
    print("   negative_caching second miss (cache):", negative_caching(db, cache, "user:999"))

    sf = SingleFlight()
    print("9) request_coalescing:", request_coalescing(db, cache, sf, "user:1"))

    l1 = SimpleCache()
    l2 = L2Cache()
    print("10) two_level_cache:", two_level_cache(db, l1, l2, "user:1"))

    print("\nDB reads:", db.read_count, "| DB writes:", db.write_count)


if __name__ == "__main__":
    run_all_examples()
