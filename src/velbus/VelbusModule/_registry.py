module_registry = {}


def register(*args):
    def register_(cls):
        """
        Class decorator to register a module handler
        :param cls: the class to register. Must contain a `supported_modules` attribute, which is a list
                    of ModuleType's it supports
        """
        for m in args:
            if m not in module_registry:
                module_registry[m] = []
            module_registry[m].append(cls)
        return cls

    return register_
