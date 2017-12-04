from typing import List

import attr
import bitstruct


@attr.s(slots=True)
class AttrInfo:
    name = attr.ib()
    from_func = attr.ib()
    to_func = attr.ib()


@attr.s(slots=True)
class BitstructInfo:
    bitstruct_fmt = attr.ib(default='')
    num_bits = attr.ib(default=0)
    attr_info = attr.ib(default=None)

    def __attrs_post_init__(self):
        if self.attr_info is None:
            self.attr_info = []

    @property
    def num_bytes(self):
        if self.num_bits % 8 != 0:
            raise TypeError("Attributes do not add up to a multiple of 8 bits")
        return self.num_bits // 8

    @classmethod
    def from_attrs(cls, attrs: 'List[attr.Attribute]') -> 'BitstructInfo':
        bi = cls()

        for attribute in attrs:
            value_type = attribute.type or attribute.convert  # Support both old & new style attrs
            bi.num_bits += value_type.bits()
            if hasattr(value_type, 'from_int') and hasattr(value_type, 'to_int'):
                bi.bitstruct_fmt += '>>u{}'.format(value_type.bits())
                bi.attr_info.append(AttrInfo(
                    name=attribute.name,
                    from_func=value_type.from_int,
                    to_func=value_type.to_int,
                ))
            elif hasattr(value_type, 'from_signed_int') and hasattr(value_type, 'to_signed_int'):
                bi.bitstruct_fmt += '>>s{}'.format(value_type.bits())
                bi.attr_info.append(AttrInfo(
                    name=attribute.name,
                    from_func=value_type.from_signed_int,
                    to_func=value_type.to_signed_int,
                ))
            elif hasattr(value_type, 'from_bytes') and hasattr(value_type, 'to_bytes'):
                bi.bitstruct_fmt += '>>r{}'.format(value_type.bits())
                bi.attr_info.append(AttrInfo(
                    name=attribute.name,
                    from_func=value_type.from_bytes,
                    to_func=value_type.to_bytes,
                ))
            else:
                raise TypeError("Type {t} has no from_int() or from_bytes()".format(
                    t=value_type.__name__,
                ))

        return bi


def bytes_to_attrs(data: bytes, bi: BitstructInfo) -> dict:
    if len(data) != bi.num_bytes:
        raise ValueError("Invalid length of data: got {g} bytes, expected {e} bytes".format(
            g=len(data),
            e=bi.num_bytes,
        ))

    fields = bitstruct.unpack(bi.bitstruct_fmt, data)
    fields_by_name = {}
    for i, attribute in enumerate(bi.attr_info):
        fields_by_name[attribute.name] = attribute.from_func(fields[i])

    return fields_by_name


def attrs_to_bytes(bi: BitstructInfo, values: list) -> bytes:
    assert len(bi.attr_info) == len(values)

    fields = []
    for i, attribute in enumerate(bi.attr_info):
        fields.append(attribute.to_func(values[i]))

    return bitstruct.pack(bi.bitstruct_fmt, *fields)


class AttrSerializer:
    def validate(self):
        """
        Validate if the attributes hold valid values, and convert the to the correct type
        :raises ValueError: if the a value is not acceptable
        """
        for attribute in attr.fields(self.__class__):
            try:
                value_type = attribute.type or attribute.convert
                self.__setattr__(attribute.name,
                                 value_type(getattr(self, attribute.name)))
            except TypeError:
                pass

    @classmethod
    def _data_attributes(cls):
        return attr.fields(cls)

    @classmethod
    def from_bytes(cls, data, *args, **kwargs) -> 'AttrSerializer':
        """
        Factory method that gets partially parsed bytes (in kwargs and data).
        Further parse data and return appropriate VelbusMessage object
        """
        bitstruct_info = BitstructInfo.from_attrs(cls._data_attributes())
        # TODO: cache bitstruct_info

        fields = bytes_to_attrs(data, bitstruct_info)
        fields = {k[1:] if k.startswith('_') else k: v for k, v in fields.items()}
        kwargs.update(fields)

        return cls(*args, **kwargs)

    def data(self) -> bytes:
        """
        Reconstruct the data-portion of the VelbusFrame
        :return:
        """
        self.validate()
        attributes = self._data_attributes()
        bitstruct_info = BitstructInfo.from_attrs(self._data_attributes())
        return attrs_to_bytes(
            bitstruct_info,
            [getattr(self, a.name) for a in attributes])

    def to_json_able(self):
        """
        Method to make the object JSON-serialazable.
        """
        self.validate()

        props = {}

        for attribute in attr.fields(self.__class__):
            if attribute.name.startswith('_'):
                continue
            value = getattr(self, attribute.name)
            try:
                value = value.to_json_able()
            except AttributeError:
                pass
            props[attribute.name] = value

        return {
            'type': self.__class__.__name__,
            'properties': props,
        }
