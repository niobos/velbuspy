"""
Custom types to use in VelbusMessages

For a type to be usable as field type, it needs several methods:

* return the number of bits this field consumes or produces:
      cls.bits() -> int

* decode data. Either of these (in order of preference):
      cls.from_int(data: int) -> cls
      cls.from_bytes(data: bytes) -> cls
  Note: the data in from_bytes is left-aligned (only relevant if bits() % 8 != 0)

* encode data. Either of these (in order of preference):
      obj.to_int() -> int
      obj.to_bytes() -> bytes
  Note: the data from to_bytes must be left-aligned (only relevant if bits() % 8 != 0)
"""
import enum
import functools


@functools.lru_cache(maxsize=None)
def Enum(bits: int):
    """
    Returns a Enum-like class with the needed methods
    """
    class EnumBits(enum.Enum):
        @classmethod
        def bits(cls):
            return bits

        @classmethod
        def from_int(cls, data: int):
            return cls(data)

        def to_int(self) -> int:
            return self.value

        def to_json_able(self) -> dict:
            return {'name': self.name, 'value': self.value}

    return EnumBits


@functools.lru_cache(maxsize=None)
def Bytes(num_bytes: int):
    """
    Returns a class holding the specified number of bytes
    """
    class Bytes(bytes):
        @classmethod
        def bits(cls):
            return num_bytes * 8

        @classmethod
        def from_bytes(cls, data: bytes):
            return data

        def to_bytes(self) -> bytes:
            return self

        def to_json_able(self):
            return self.decode(encoding='utf-8')

    return Bytes


@functools.lru_cache(maxsize=None)
def Bitmap(bits: int):
    """
    Returns a class holding a list of booleans for the given number of bits
    """
    class Bitmap(list):
        @classmethod
        def bits(cls):
            return bits

        @classmethod
        def from_int(cls, data: int):
            v = list()
            for i in range(bits):
                v.append(bool(data & 1))
                data >>= 1
            return list(reversed(v))

        def to_int(self) -> int:
            out = 0
            for v in self:
                out <<= 1
                out |= int(v)
            return out

        @classmethod
        def zero(cls):
            return cls.from_int(0)

    return Bitmap


@functools.lru_cache(maxsize=None)
def UInt(bits: int):
    """
    Returns a class holding a fixed width integer
    """
    class UInt(int):
        @classmethod
        def bits(cls):
            return bits

        @classmethod
        def from_int(cls, data: int):
            return cls(data)

        def to_int(self):
            return self

        def __new__(cls, number):
            if number < 0:
                raise ValueError("UInt does not support negative numbers")
            if number >= 2 ** bits:
                raise ValueError("Value too large to fit in {i} bits".format(
                    i=bits,
                ))
            return super().__new__(cls, number)

    return UInt


Bool = UInt(1)


@functools.lru_cache(maxsize=None)
def FixedPointSInt(integer_bits: int = None,
                   fractional_bits: int = None,
                   total_bits: int = None):
    """
    Returns a class holding a fixed point integer with the given precission
    """
    if integer_bits is not None and fractional_bits is not None and total_bits is not None:
        if total_bits != integer_bits + fractional_bits:
            raise ArithmeticError(
                "total_bits ({t}) must equal integer_bits ({i}) + fractional_bits ({f})".format(
                    t=total_bits,
                    i=integer_bits,
                    f=fractional_bits,
            ))
    elif integer_bits is not None and fractional_bits is not None:
        total_bits = integer_bits + fractional_bits
    elif total_bits is not None and fractional_bits is not None:
        integer_bits = total_bits - fractional_bits
    elif total_bits is not None and integer_bits is not None:
        fractional_bits = total_bits - integer_bits
    else:
        raise ArithmeticError(
            "At least 2 of (integer_bits, fractional_bits, total_bits) must be specified"
        )

    class FixedPointSInt(float):
        @classmethod
        def bits(cls):
            return total_bits

        @classmethod
        def from_signed_int(cls, data: int):
            return cls(data / 2. ** fractional_bits)

        def to_signed_int(self):
            return int(self * 2. ** fractional_bits)

        def __new__(cls, number):
            if number >= 2 ** (integer_bits - 1):  # -1 for sign bit
                raise ValueError("Value too large to fit in {i} integer bits".format(
                    i=integer_bits,
                ))
            return super().__new__(cls, number)

    return FixedPointSInt


@functools.lru_cache(maxsize=None)
def Index(bits: int, max_bits: int = None):
    """
    Returns a class holding a bit index (1-based):
     0b0100 -> 3
     0b0001 -> 1
     0b0011 -> raises ValueError

    :param max_bits: Additional limit on the highest allowed bit to be set
    """
    if max_bits is None:
        max_bits = bits

    class Index(int):
        @classmethod
        def bits(cls):
            return bits

        @classmethod
        def from_int(cls, data: int):
            for i in range(0, max_bits):
                if data == 1 << i:
                    return cls(i + 1)  # 1-based indexing!
            raise ValueError("0x{:x} does not have exactly 1 bit set".format(data))

        def to_int(self) -> int:
            return int(1 << (self - 1))  # 1-based indexing
    return Index


class DisableInhibitForced(Enum(8)):
    Normal = 0
    Inhibited = 1
    ForcedOn = 2
    Disabled = 3


class LedStatus(Enum(8)):
    Off = 0x00
    On = 0x80
    SlowBlink = 0x40
    FastBlink = 0x20
    VeryFastBlink = 0x10


class BlindNumber(int):
    @classmethod
    def bits(cls):
        return 8

    @classmethod
    def from_int(cls, data):
        if data == 0b0011:
            return cls(1)
        elif data == 0b1100:
            return cls(2)
        else:
            raise ValueError()

    def to_int(self) -> int:
        return 0b11 << 2*(self - 1)


class BlindTimeout(Enum(2)):
    t15sec = 0
    t30sec = 1
    t1min = 2
    t2min = 3

    @classmethod
    def to_secs(cls, v):
        if v == cls.t15sec: return 15
        if v == cls.t30sec: return 30
        if v == cls.t1min: return 60
        if v == cls.t2min: return 120
        raise ValueError()
