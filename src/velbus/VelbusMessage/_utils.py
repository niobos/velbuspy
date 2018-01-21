import attr
import structattr


class AttrSerializer:
    _bitstruct_info = None

    @classmethod
    def bitstruct_info(cls):
        if cls._bitstruct_info is None:
            cls._bitstruct_info = structattr.BitStructInfo()
            for a in cls._data_attributes():
                cls._bitstruct_info.add_attr(a)
        return cls._bitstruct_info

    def validate(self):
        """
        Validate if the attributes hold valid values, and convert the to the correct type
        :raises ValueError: if the a value is not acceptable
        """
        return structattr.validate(self, True, self.bitstruct_info())

    @classmethod
    def _data_attributes(cls):
        return attr.fields(cls)

    @classmethod
    def from_bytes(cls, data, *args, **kwargs) -> 'AttrSerializer':
        """
        Factory method that gets partially parsed bytes (in kwargs and data).
        Further parse data and return appropriate VelbusMessage object
        """
        fields = structattr.deserialize(data, cls.bitstruct_info())

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
        return structattr.serialize(
            [getattr(self, a.name) for a in attributes],
            self.bitstruct_info())

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
