import gc

import datetime
import pytest
from JsonPatchDict import JsonPatchDict, JsonPatchOperation, JsonPatch


def test_memory_leak():
    a = JsonPatchDict()
    orig_referals = len(gc.get_referrers(a))

    a['foo']['bar'] = 42  # should create weak references only
    a['baz']['world'] = 43
    assert orig_referals == len(gc.get_referrers(a))


def test_nested():
    a = JsonPatchDict()
    a['foo'] = 42
    assert(a['foo'] == 42)

    a = JsonPatchDict()
    a['foo']['bar'] = 42
    assert(a['foo']['bar'] == 42)


def test_tracking():
    a = JsonPatchDict()

    operations = []

    def cb(op: JsonPatchOperation):
        operations.append(op)

    a.callback.add(cb)

    a['foo'] = 42
    assert(operations == [
        JsonPatch([
            JsonPatchOperation(op=JsonPatchOperation.Operation.add, path=['foo'], value=42),
        ])
    ])

    operations = []
    a['foo'] = 43
    assert(operations == [
        JsonPatch([
            JsonPatchOperation(op=JsonPatchOperation.Operation.add, path=['foo'], value=43),
        ])
    ])

    operations = []
    a['bar']['baz'] = 1
    assert(operations == [
        JsonPatch([
            JsonPatchOperation(op=JsonPatchOperation.Operation.add, path=['bar'], value={}),
        ]),
        JsonPatch([
            JsonPatchOperation(op=JsonPatchOperation.Operation.add, path=['bar', 'baz'], value=1),
        ])
    ])

    a = JsonPatchDict()
    a.callback.add(cb)
    operations = []
    a['test~123/456'] = 42
    assert(operations == [
        JsonPatch([
            JsonPatchOperation(op=JsonPatchOperation.Operation.add, path=['test~123/456'], value=42),
        ])
    ])
    assert(operations[0][0].to_json_able() == {'op': 'add', 'path': '/test~0123~1456', 'value': 42})


def test_non_jsonable():
    a = JsonPatchDict()
    with pytest.raises(TypeError):
        a['now'] = datetime.datetime.now()


def test_bool():
    a = JsonPatchDict()
    a[0] = True
    assert a['0'] == True
