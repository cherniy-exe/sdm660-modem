#!/usr/bin/env python3
"""Send vendor-exact DPM OPEN_PORT (tx=4, rx=5) to the modem.
The wip2 kernel driver sends tx=5, rx=4 (reversed vs the stock/Android
capture in postmarketos-x00td-cellular/vendor-init/stage_dpm_open.c).
"""
import sys, struct, time
sys.path.insert(0, '/usr/local/bin')
from qmi_sms import Qmi

EP_DESC = bytes([
    0x01,                          # count
    0x04, 0x00, 0x00, 0x00,        # ep_type = 4 (HSUSB/IPA)
    0x01, 0x00, 0x00, 0x00,        # if_id = 1
    0x04, 0x00, 0x00, 0x00,        # tx_endpoint = 4
    0x05, 0x00, 0x00, 0x00,        # rx_endpoint = 5
])
TLV = bytes([0x11, len(EP_DESC), 0x00]) + EP_DESC

q = Qmi()
print('NODEPORT', q.lookup(0x2f))
r = q.command(0x2f, 0, 0x0020, TLV, timeout=6)
print('RAW', r.hex() if isinstance(r, (bytes, bytearray)) else r)
