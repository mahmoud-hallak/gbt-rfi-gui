from time import perf_counter

from django.db import connection


class ModelCache:
    """Cache results of Django's get_or_create in memory.

    Use case: when doing large numbers of get_or_create calls, there is a huge
    amount of overhead, since we have to do a DB query for every single call.

    In situations where we expect significant numbers of our get_or_creates to _only get_
    (not create), we can drastically reduce this overhead by caching the results of every
    get_or_create in a dictionary (ModelCache._cache)

    So, the algorithm is:

    1. If `key` is in `self._cache`, return its associated model instance
    2. If not, call `model_class.objects.get_or_create`. This willand:
        1. Create the instance if needed
        2. Cache the instance in `self._cache`
        3. Return the model instance

    Note that the actual code is a bit more complicated, since we also support
    using different `create_kwargs` than `get_kwargs`(something Django's
    get_or_create does _not_ support)
    """

    def __init__(self, model_class, initial_cache=None):
        self.model_class = model_class

        if initial_cache is None:
            self._cache = {}
        self.hits = 0
        self.misses = 0
        self.gets = 0
        self.creations = 0

    def get_or_create(self, key, get_kwargs, create_kwargs=None):
        self.gets += 1
        if key in self._cache:
            instance = self._cache[key]
            self.hits += 1
        else:
            if create_kwargs:
                instances = self.model_class.objects.filter(**get_kwargs)
                num_instances = instances.count()
                if num_instances == 1:
                    instance = instances.first()
                    created = False
                elif num_instances == 0:
                    instance = self.model_class.objects.create(**create_kwargs)
                    created = True
                else:
                    raise AssertionError(
                        "Should not be possible to receive "
                        f"{num_instances} {self.model_class} objects!"
                    )
            else:
                instance, created = self.model_class.objects.get_or_create(**get_kwargs)
            self._cache[key] = instance
            self.misses += 1
            self.creations += bool(created)
            # tqdm.write(f"Miss {self.model_class} {key}")

        return instance

    def __str__(self):
        return (
            f"{self.model_class.__name__} Cache ({len(self._cache)} items; "
            f"{self.hits} hits; {self.misses} misses)"
        )


class Benchmark:
    def __init__(self, description=None, logger=None):
        self._initial_time = perf_counter()
        self._initial_queries = len(connection.queries)
        self._initial_insert_queries = len(
            [q for q in connection.queries if q["sql"].startswith("INSERT")]
        )
        self._logger = logger if logger else print
        self.description = "Did stuff" if description is None else description

    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        _queries_end = len(connection.queries)
        _insert_queries_end = len(
            [q for q in connection.queries if q["sql"].startswith("INSERT")]
        )
        _end = perf_counter()
        self._logger(
            f"{self.description} in {_end - self._initial_time} seconds "
            f"and {_queries_end - self._initial_queries} queries "
            f"({_insert_queries_end - self._initial_insert_queries} inserts)"
        )
