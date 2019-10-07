import attr

from ._registry import command_registry
from ._types import UInt
from .VelbusMessage import VelbusMessage
from .UnknownMessage import UnknownMessage
from .ModuleTypeRequest import ModuleTypeRequest


@attr.s(slots=True)
class VelbusFrame:
    address = attr.ib(converter=UInt(8))
    message = attr.ib()

    @classmethod
    def from_bytes(cls, frame: 'Union[bytes, bytearray]') -> 'VelbusFrame':
        """
        Parse the given bytes in to a VelbusFrame

        if message supports item deletion (`del message[0:5]`), the
        consumed message is removed from `message`.

        :raises BufferError when the message is incomplete
        :raises ValueError when the message can not be decoded
        """
        if len(frame) < 6:
            raise BufferError("Not enough data to decode message")

        if frame[0] != 0x0f:
            raise ValueError("data[0] != 0x0f")

        if frame[1] & 0xfc != 0xf8:
            raise ValueError("data[1] & 0xfc != 0xf8")
        prio = frame[1] & 0x03

        addr = frame[2]

        if frame[3] & 0xb0 != 0x00:
            raise ValueError("data[3] & 0xb0 != 0x00")
        rtr = bool(frame[3] & 0x40)
        dlen = frame[3] & 0x0f

        if len(frame) < 4 + dlen + 2:
            raise BufferError("Not enough data to read data bytes")

        data = frame[4:(4 + dlen)]

        checksum_my = 0
        for b in frame[0:(4 + dlen)]:
            checksum_my += b
        checksum_my = (-checksum_my) & 0xff

        checksum_msg = frame[4 + dlen]
        if checksum_my != checksum_msg:
            raise ValueError("Checksum mismatch: got 0x{msg:x}, expected 0x{my:x}".format(
                my=checksum_my,
                msg=checksum_msg
            ))

        if frame[4 + dlen + 1] != 0x04:
            raise ValueError("data[-1] != 0x04")

        try:
            del frame[0:(4 + dlen + 1 + 1)]
        except TypeError:
            # message is bytes, not bytearray. ignore
            pass

        # attempt to decode
        try:
            if len(data) == 0:
                if rtr:
                    data = ModuleTypeRequest(
                        priority=prio,
                        remote_transmit_request=rtr,
                    )

            else:
                command = data[0]
                try:
                    candidates = command_registry[command]
                except KeyError:
                    # Could not decode
                    raise ValueError()

                for c in candidates:
                    try:
                        data = c.from_bytes(
                            priority=prio,
                            remote_transmit_request=rtr,
                            data=data,
                        )
                        break
                    except ValueError as e:
                        pass

            if not isinstance(data, VelbusMessage):
                raise ValueError()

        except ValueError:
            # Something went wrong with the decoding, fall back to UnknownMessage
            data = UnknownMessage(
                priority=prio,
                remote_transmit_request=rtr,
                data=data,
            )

        return cls(
            address=addr,
            message=data,
        )

    def to_bytes(self) -> bytes:
        """
        Reconstruct the VelbusFrame
        """
        m = bytearray(b'\x0f')
        m.append(0xf8 | self.message._priority)
        m.append(self.address)
        b = 0
        b |= 0x40 if self.message._remote_transmit_request else 0

        data = self.message.data()
        assert len(data) <= 8
        b |= len(data)
        m.append(b)

        m += data

        checksum = 0
        for b in m:
            checksum += b
        m.append((-checksum) & 0xff)

        m.append(0x04)

        return m

    def to_json_able(self):
        return {
            'address': self.address,
            'message': self.message.to_json_able(),
        }