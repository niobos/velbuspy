import pytest
from unittest import mock

from velbus.JsonPatchDict import JsonPatchOperation
from velbus.mqtt import MqttStateSync


@pytest.mark.asyncio
async def test_publish():
    sync = MqttStateSync()
    # don't call connect

    sync.publish_single = mock.Mock()

    await sync.publish(JsonPatchOperation(JsonPatchOperation.Operation.add, ['test', '123'], 'foo'))
    sync.publish_single.assert_called_once_with(path=['test', '123'], value=b'foo')


@pytest.mark.asyncio
async def test_publish_decompose():
    sync = MqttStateSync()
    # don't call connect

    sync.publish_single = mock.Mock()

    await sync.publish(JsonPatchOperation(JsonPatchOperation.Operation.add,
                                          ['test', '456'],
                                          {'hello': 'world', 'foo': True}))

    sync.publish_single.assert_has_calls([
        mock.call(path=['test', '456', 'hello'], value=b'world'),
        mock.call(path=['test', '456', 'foo'], value=b'True'),
    ], any_order=True)
