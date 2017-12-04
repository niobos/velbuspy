import attr

from ._utils import AttrSerializer
from ._types import UInt, Bool


@attr.s(slots=True, auto_attribs=True)
class VelbusMessage(AttrSerializer):
    """
    Helper superclass that takes care of (de)serializing attr.ib's for you
    """

    _priority: UInt(2)
    _remote_transmit_request: Bool = False

    @classmethod
    def _data_attributes(cls):
        attributes = attr.fields(cls)

        # remove non-data attributes
        attributes = [a for a in attributes
                      if a.name != '_priority' and \
                      a.name != 'address' and \
                      a.name != '_remote_transmit_request']

        return attributes
