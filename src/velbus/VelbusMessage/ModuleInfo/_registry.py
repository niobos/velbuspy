module_type_registry = {}

def register(cls):
    """
    Class decorator to register a command
    :param cls: the class to register. Must contain a `Command` Enum class
    """
    modules = [cmd.value for cmd in cls.ModuleType]
    for m in modules:
        if m not in module_type_registry:
            module_type_registry[m] = []
        module_type_registry[m].append(cls)
    return cls
