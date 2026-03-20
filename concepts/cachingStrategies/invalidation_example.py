import time


NOT_FOUND = object()


class SimpleCache:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value

    def delete(self, key):
        self.data.pop(key, None)


class VersionedDB:
    """
    Minimal DB that increments a per-key version on every write.
    That version can act like an ETag/generation number for revalidation.
    """

    def __init__(self):
        self.store = {}
        self.versions = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value):
        self.store[key] = value
        self.versions[key] = self.versions.get(key, 0) + 1

    def version(self, key):
        return self.versions.get(key, 0)


class TaggedCache(SimpleCache):
    """
    Cache entries can belong to one or more tags.
    Invalidate a tag by deleting all keys associated with that tag.
    """

    def __init__(self):
        super().__init__()
        self.tag_to_keys = {}
        self.key_to_tags = {}

    def set(self, key, value, tags=None):
        super().set(key, value)
        tags = [] if tags is None else list(tags)

        # Remove any old tag associations for this key.
        for old_tag in self.key_to_tags.get(key, set()):
            self.tag_to_keys.get(old_tag, set()).discard(key)

        self.key_to_tags[key] = set(tags)
        for tag in tags:
            self.tag_to_keys.setdefault(tag, set()).add(key)

    def delete(self, key):
        # Also remove tag associations, so future tag invalidations stay correct.
        for tag in self.key_to_tags.get(key, set()):
            self.tag_to_keys.get(tag, set()).discard(key)
        self.key_to_tags.pop(key, None)
        super().delete(key)

    def invalidate_tag(self, tag):
        keys = list(self.tag_to_keys.get(tag, set()))
        for k in keys:
            self.delete(k)
        self.tag_to_keys.pop(tag, None)


class InvalidationBus:
    def __init__(self):
        self.subscribers = []

    def subscribe(self, fn):
        self.subscribers.append(fn)

    def publish(self, key):
        for fn in self.subscribers:
            fn(key)


def delete_on_write_invalidation(db, cache, key, new_value):
    """
    Strategy: update DB, then invalidate by deleting the cache entry.
    """
    db.set(key, new_value)
    cache.delete(key)


def write_with_versioned_keys(db, key, new_value):
    """
    Strategy: versioned keys (generation counters).
    On write, increment the DB version so reads automatically switch to a new cache key.
    """
    db.set(key, new_value)


def read_with_versioned_keys(db, cache, key):
    """
    Helper for the versioned-keys strategy:
    - Read current version from DB
    - Use `key:v<version>` as the actual cache key
    """
    ver = db.version(key)
    cache_key = f"{key}:v{ver}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    value = db.get(key)
    if value is None:
        return None
    cache.set(cache_key, value)
    return value


def tag_based_invalidation_write(cache, key, value, tags):
    """
    Strategy: tag/namespace invalidation.
    Cache the value under its tags so the caller can invalidate the tag later.
    """
    cache.set(key, value, tags=tags)


def revalidate_on_read_etag(db, cache, key):
    """
    Strategy: conditional revalidation (ETag/version).
    Cache stores (value, version). If versions mismatch, invalidate & reload.
    """
    cached = cache.get(key)
    current_ver = db.version(key)
    if cached is None:
        # Cache miss: fetch and store (value, version).
        value = db.get(key)
        if value is None:
            return None
        cache.set(key, (value, current_ver))
        return value

    cached_value, cached_ver = cached
    if cached_ver != current_ver:
        # Invalidate implicitly by overwriting with the fresh (value, version).
        value = db.get(key)
        if value is None:
            cache.delete(key)
            return None
        cache.set(key, (value, current_ver))
        return value

    return cached_value


def active_invalidation_pubsub(db, bus, caches, key, new_value):
    """
    Strategy: active invalidation across nodes (pub/sub).
    Write DB, then publish an invalidation event so other cache instances delete the key.
    """
    db.set(key, new_value)
    bus.publish(key)


def run_all_invalidation_examples():
    db = VersionedDB()
    cache = SimpleCache()

    print("1) delete_on_write_invalidation")
    db.set("user:1", "Ada")
    cache.set("user:1", "Ada")
    delete_on_write_invalidation(db, cache, "user:1", "Ada v2")
    print("   cache after delete:", cache.get("user:1"))
    # Refilling:
    if cache.get("user:1") is None:
        cache.set("user:1", db.get("user:1"))
    print("   cache after refill:", cache.get("user:1"))

    print("2) versioned keys / generation counters")
    cache = SimpleCache()
    db.set("user:2", "Grace")
    print("   initial read:", read_with_versioned_keys(db, cache, "user:2"))
    write_with_versioned_keys(db, "user:2", "Grace v2")
    print("   read after version bump:", read_with_versioned_keys(db, cache, "user:2"))

    print("3) tag-based invalidation")
    tcache = TaggedCache()
    tag_based_invalidation_write(tcache, "product:123:details", {"id": 123}, tags=["product:123"])
    tag_based_invalidation_write(tcache, "product:123:stats", {"views": 10}, tags=["product:123"])
    print("   before invalidation:", tcache.get("product:123:details"), tcache.get("product:123:stats"))
    tcache.invalidate_tag("product:123")
    print("   after invalidation:", tcache.get("product:123:details"), tcache.get("product:123:stats"))

    print("4) revalidate-on-read (ETag/version)")
    db = VersionedDB()
    cache = SimpleCache()
    db.set("user:3", "Linus")
    # First read populates cache with (value, version).
    print("   first read:", revalidate_on_read_etag(db, cache, "user:3"))
    db.set("user:3", "Linus v2")
    # Second read sees version mismatch and refreshes.
    print("   second read after update:", revalidate_on_read_etag(db, cache, "user:3"))

    print("5) active invalidation across nodes (pub/sub)")
    db = VersionedDB()
    bus = InvalidationBus()
    cache_a = SimpleCache()
    cache_b = SimpleCache()

    # Both caches subscribe to invalidation events.
    bus.subscribe(cache_a.delete)
    bus.subscribe(cache_b.delete)

    db.set("user:4", "Ken")
    cache_a.set("user:4", "Ken")
    cache_b.set("user:4", "Ken")
    print("   before invalidation:", cache_a.get("user:4"), cache_b.get("user:4"))
    active_invalidation_pubsub(db, bus, [cache_a, cache_b], "user:4", "Ken v2")
    print("   after invalidation:", cache_a.get("user:4"), cache_b.get("user:4"))

    print("\nDone.")


if __name__ == "__main__":
    run_all_invalidation_examples()

