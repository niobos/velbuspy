command_registry = {}


def register(cls):
    """
    Class decorator to register a command
    :param cls: the class to register. Must contain a `Command` Enum class
    """
    commands = [cmd.value for cmd in cls.Command]
    for c in commands:
        if c not in command_registry:
            command_registry[c] = []
        command_registry[c].append(cls)
    return cls
