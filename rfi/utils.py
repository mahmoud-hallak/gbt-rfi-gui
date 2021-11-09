class ModelCache:
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
                        "Should not be possible to receiver "
                        f"{num_instances} {self.model_class} objects!"
                    )
            else:
                instance, created = self.model_class.objects.get_or_create(**get_kwargs)
            self._cache[key] = instance
            self.misses += 1
            self.creations += bool(created)

        return instance

    def __str__(self):
        return (
            f"{self.model_class.__name__} Cache ({len(self._cache)} items; "
            f"{self.hits} hits; {self.misses} misses)"
        )
