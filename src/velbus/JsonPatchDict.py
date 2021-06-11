import json
import re
import typing
import weakref
from enum import Enum
from typing import List

import attr


@attr.s(slots=True, auto_attribs=True)
class JsonPatchOperation:
    class Operation(Enum):
        add = 'add'
        remove = 'remove'
        replace = 'replace'
    op: Operation
    path: List[str]
    value: object

    def to_json_able(self):
        o = {
            'op': self.op.value,
            'path': '/'.join([JsonPatchOperation.escape_path(p) for p in ['', *self.path]]),
        }
        if self.op in (JsonPatchOperation.Operation.add, JsonPatchOperation.Operation.replace):
            o['value'] = self.value

        return o

    @staticmethod
    def escape_path(path):
        path = re.sub(r'~', '~0', path)
        path = re.sub(r'/', '~1', path)
        return path

    @staticmethod
    def unescape_path(path):
        path = re.sub(r'~1', '/', path)
        path = re.sub(r'~0', '~', path)
        return path

    def decompose(self) -> typing.Generator["JsonPatchOperation", None, None]:
        """
        Decompose into simple-value assignments
        """
        if self.op == JsonPatchOperation.Operation.remove:
            yield [self]
            return
        # else:  add/replace

        if isinstance(self.value, dict):
            for k, v in self.value.items():
                sub_op = JsonPatchOperation(self.op, [*self.path, str(k)], v)
                for sub_sub_op in sub_op.decompose():
                    yield sub_sub_op
        else:
            yield self


class JsonPatch(list):
    def to_json_able(self):
        return [o.to_json_able() for o in self]

    def prefixed(self, path: List[str]) -> "JsonPatch":
        """
        Return a new JsonPatch with the same operations prefixed by the given path
        """
        return JsonPatch([
            JsonPatchOperation(
                op=op.op,
                path=[*path, *op.path],
                value=op.value)
            for op in self
        ])


class JsonPatchDict(dict):
    """
    Nested dict with callback on update.

    Non-existing keys are automatically created: e.g. you can do
        a = JsonPatchDict()
        a['foo']['bar'] = 42

    Changes are notified to registered callbacks with the following signature:
        cb(op: JsonPatch)

    Note that keys are automatically converted to strings (as required by JSON)
    """

    __slots__ = ['_parent', 'callback', '__weakref__']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callback = set()
        self._parent = None

    def _operation(self, op: JsonPatchOperation):
        if self._parent is not None:
            self._parent(op)

        for cb in self.callback:
            cb(JsonPatch([op]))

    def __missing__(self, key: str):
        key = str(key)

        sub = JsonPatchDict()

        weakself = weakref.proxy(self)  # avoid circular reference

        def child_operation(op: JsonPatchOperation):
            try:
                return weakself._operation(JsonPatchOperation(op=op.op, path=[key, *op.path], value=op.value))
            except ReferenceError:
                pass

        sub._parent = child_operation

        self[key] = sub
        self._operation(JsonPatchOperation(JsonPatchOperation.Operation.add, [key], {}))
        return self[key]

    def __setitem__(self, key: str, value: typing.Any):
        key = str(key)

        if not isinstance(value, JsonPatchDict):
            # validate JSON-ability
            if hasattr(value, 'to_json_able'):
                value = value.to_json_able()
            else:
                # Try to convert to JSON to catch non-json-able objects
                _ = json.dumps(value)  # may raise

            self._operation(JsonPatchOperation(JsonPatchOperation.Operation.add, [key], value))
            # add is defined as UPSERT, so works for replace as well

        # elif isinstance(value, JsonPatchDict):
            # self._operation() is called by child

        return super().__setitem__(key, value)

    def __delitem__(self, key: str):
        key = str(key)

        self._operation(JsonPatchOperation(JsonPatchOperation.Operation.remove, [key]))

        return super().__delitem__(key)

    def clear(self):
        self._operation(JsonPatchOperation(JsonPatchOperation.Operation.replace, [], {}))
        return super().clear()

    def pop(self, key: str, **kwargs):
        key = str(key)

        if key in self:
            self._operation(JsonPatchOperation(JsonPatchOperation.Operation.remove, [key]))

        return super().pop(key, **kwargs)

    def popitem(self):
        _ = super().popitem()
        self._operation(JsonPatchOperation(JsonPatchOperation.Operation.remove, [_[0]]))
        return _

    def setdefault(self, key: str, default=None):
        key = str(key)

        if key not in self:
            self._operation(JsonPatchOperation(JsonPatchOperation.Operation.add, [key], default))

        return super().setdefault(key, default)

    def update(self, *args, **kwargs):
        other = dict(*args, **kwargs)
        other_str = {
            str(k): v
            for k, v in other.items()
        }
        for key, value in other_str.items():
            self._operation(JsonPatchOperation(JsonPatchOperation.Operation.add, [key], value))
            # add is UPSERT, so works for replace as well

        return super().update(other_str)

    def replace(self, *args, **kwargs) -> None:
        """
        Equivalent to self.clear(); self.update(*args, **kwargs)
        But implemented more efficiently in the emitted operations
        """
        super().clear()
        other = dict(*args, **kwargs)
        other_str = {
            str(k): v
            for k, v in other.items()
        }
        super().update(other_str)
        self._operation(JsonPatchOperation(JsonPatchOperation.Operation.replace, [], other_str))
