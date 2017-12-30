#!/usr/bin/env python3
import argparse
import socket
from datetime import datetime

from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.RealTimeClockStatus import RealTimeClockStatus

parser = argparse.ArgumentParser(description='Send current time to Velbus')
parser.add_argument('--hostname', help="Hostname to connect to", default="localhost")
parser.add_argument('--port', help="Port to connect to", default=8445)
args = parser.parse_args()

s = socket.create_connection((args.hostname, args.port))

message = RealTimeClockStatus()
message.set_to(when=datetime.now())
frame = VelbusFrame(address=0x00, message=message)
pdu = frame.to_bytes()

s.send(pdu)
s.close()
