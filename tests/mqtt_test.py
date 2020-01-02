import asyncio

import pytest
from unittest import mock

from velbus.JsonPatchDict import JsonPatchOperation
from velbus.mqtt import MqttStateSync


@pytest.mark.asyncio
async def test_publish():
    sync = MqttStateSync()
    # don't call connect

    pub_mock = mock.Mock()
    async def async_pub_mock(*args, **kwargs):
        await asyncio.sleep(0)
        return pub_mock(*args, **kwargs)
    sync.publish_single = async_pub_mock

    await sync.publish(JsonPatchOperation(JsonPatchOperation.Operation.add, ['test', '123'], 'foo'))
    pub_mock.assert_called_once_with(path=['test', '123'], value=b'foo')


@pytest.mark.asyncio
async def test_publish_decompose():
    sync = MqttStateSync()
    # don't call connect

    pub_mock = mock.Mock()
    async def async_pub_mock(*args, **kwargs):
        await asyncio.sleep(0)
        return pub_mock(*args, **kwargs)
    sync.publish_single = async_pub_mock

    await sync.publish(JsonPatchOperation(JsonPatchOperation.Operation.add,
                                          ['test', '456'],
                                          {'hello': 'world', 'foo': True}))

    pub_mock.assert_has_calls([
        mock.call(path=['test', '456', 'hello'], value=b'world'),
        mock.call(path=['test', '456', 'foo'], value=b'True'),
    ], any_order=True)
