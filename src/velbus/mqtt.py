import typing
import asyncio
import queue

import paho.mqtt.client as mqtt

from .JsonPatchDict import JsonPatchOperation


class MqttStateSync:
    def __init__(self,
                 mqtt_host: str = "localhost",
                 mqtt_port: int = 1883,
                 mqtt_topic_prefix: str = "",
                 ):
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.mqtt_topic_prefix = mqtt_topic_prefix
        self.connection = mqtt.Client()
        self._loop = asyncio.get_event_loop()
        self._connected = asyncio.Future()

    async def connect(self):
        self.connection.on_connect = self._mqtt_thread_on_connect
        self.connection.connect(host=self.mqtt_host, port=self.mqtt_port)
        self.connection.loop_start()  # in separate thread
        await self._connected

    def _mqtt_thread_on_connect(self, client, userdata, flags, rc):
        self._loop.call_soon_threadsafe(self._on_connect, client, userdata, flags, rc)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected.set_result(True)
        else:
            self._connected.set_exception(RuntimeError("connection failed"))

    def __hash__(self) -> int:
        return hash((self.mqtt_host, self.mqtt_port, self.mqtt_topic_prefix))

    def __eq__(self, other) -> bool:
        if not isinstance(other, MqttStateSync):
            return False
        return (self.mqtt_host, self.mqtt_port, self.mqtt_topic_prefix) \
            == (other.mqtt_host, other.mqtt_port, other.mqtt_topic_prefix)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(mqtt_host={repr(self.mqtt_host)}, " \
               f"mqtt_port={repr(self.mqtt_port)}, " \
               f"mqtt_topic_prefix={repr(self.mqtt_topic_prefix)})"

    async def publish(self, op: JsonPatchOperation) -> None:
        if op.op == JsonPatchOperation.Operation.remove:
            return self.publish_single(path=op.path, value=b"")
        # else:  # replace or add

        for simple_op in op.decompose():
            self.publish_single(path=simple_op.path, value=str(simple_op.value).encode('utf-8'))

    def publish_single(self, path: typing.List[str], value: bytes) -> None:
        topic = self.mqtt_topic_prefix + '/' + '/'.join(path)
        self.connection.publish(topic=topic, payload=value, qos=2, retain=True)
