#!/usr/bin/env python3
import re
import sys
import binascii

from velbus.VelbusMessage.VelbusFrame import VelbusFrame

__import__('velbus.VelbusMessage', globals(), level=0, fromlist=['*'])
# ^^^ equivalent of `from .VelbusMessage import *`, but without polluting the namespace


for line in sys.stdin:
    match = re.match('^(.*)VBM: \[([0-9A-Fa-f]{2}(?: [0-9A-Fa-f]{2})*)\](.*)$', line)
    if not match:
        continue

    hexdump = match.group(2)
    binary = binascii.unhexlify(hexdump.replace(' ', ''))
    vbm = VelbusFrame.from_bytes(binary)

    # optionally filter here?

    print("{}VBM: {}{}".format(
        match.group(1),
        vbm,
        match.group(3)))
