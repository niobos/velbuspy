import os
import typing


def list_modules(path, recurse=True):
    modules = []
    for file in os.listdir(path):
        if file.startswith('_'): continue

        full_path = os.path.join(path, file)
        if os.path.isdir(full_path) and \
                os.path.exists(os.path.join(full_path, '__init__.py')):
            # this is a package
            if recurse:
                submodules = list_modules(full_path)
                modules.extend(["{}.{}".format(file, m) for m in submodules])
        elif file.endswith('.py'):
            modules.append(file[:-3])
    return modules


def update_dict_path(d: dict, path: typing.Iterable, new_value) -> dict:
    """
    Update nested dict `d` by updating the element with key-path `path` to
    `new_value`. Intermediate dicts are created automatically when specifying
    a path that does not (yet) exist.

    :param d: dict to update (in place)
    :param path: path to update
    :param new_value: new value to set
    :return: updated dict
    """
    p = d

    previous_key = None
    for key in path:
        # Iterate over path, but lag 1 element, so we keep the final element for after the loop
        if previous_key is not None:
            if previous_key not in p:
                p[previous_key] = {}
            p = p[previous_key]
        previous_key = key

    p[previous_key] = new_value
    return d


def update_dict_paths(d: dict, updates: typing.Iterable) -> dict:
    """
    Apply a list of changes to dict, similar to update_dict_path()

    :param d: dict to update (in place)
    :param updates: list of 2-tuples (path, new_value) listing updates to perform
    :return: updated dict
    """
    for update in updates:
        update_dict_path(d, update[0], update[1])
    return d
