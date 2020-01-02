import asyncio

import hbmqtt.client
import hbmqtt.mqtt.constants
import typing

from .JsonPatchDict import JsonPatchOperation


class MqttStateSync:
    def __init__(self,
                 mqtt_uri: str = "mqtt://localhost",
                 mqtt_topic_prefix: str = "",
                 ):
        self.mqtt_uri = mqtt_uri
        self.mqtt_topic_prefix = mqtt_topic_prefix
        self.connection = hbmqtt.client.MQTTClient()

    async def connect(self):
        await self.connection.connect(uri=self.mqtt_uri)

    def __hash__(self) -> int:
        return hash((self.mqtt_uri, self.mqtt_topic_prefix))

    def __eq__(self, other) -> bool:
        if not isinstance(other, MqttStateSync):
            return False
        return (self.mqtt_uri, self.mqtt_topic_prefix) == (other.mqtt_uri, other.mqtt_topic_prefix)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(mqtt_uri={repr(self.mqtt_uri)}, " \
               f"mqtt_topic_prefix={repr(self.mqtt_topic_prefix)})"

    async def publish(self, op: JsonPatchOperation) -> None:
        if op.op == JsonPatchOperation.Operation.remove:
            return await self.publish_single(path=op.path, value=b"")
        # else:  # replace or add

        coroutines = []
        for simple_op in op.decompose():
            coroutines.append(self.publish_single(path=simple_op.path, value=str(simple_op.value).encode('utf-8')))
        await asyncio.gather(*coroutines)

    async def publish_single(self, path: typing.List[str], value: bytes) -> None:
        topic = self.mqtt_topic_prefix + '/' + '/'.join(path)
        await self.connection.publish(topic=topic, message=value, qos=hbmqtt.mqtt.constants.QOS_2, retain=True)
