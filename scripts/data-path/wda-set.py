#!/usr/bin/env python3
"""Vendor-exact WDA_SET_DATA_FORMAT: DL=QMAPv3(7), UL=QMAPv1(5)."""
import sys, struct
sys.path.insert(0, '/usr/local/bin')
from qmi_sms import Qmi

EP_INFO = bytes([4,0,0,0, 1,0,0,0])
def tlv(t, v):
    return bytes([t, len(v) & 0xff, (len(v) >> 8) & 0xff]) + v
def u32(v): return struct.pack('<I', v)
def u8(v): return bytes([v])

tlvs = (tlv(0x11, u32(2)) + tlv(0x12, u32(5)) + tlv(0x13, u32(7)) +
        tlv(0x15, u32(10)) + tlv(0x16, u32(8192)) + tlv(0x17, EP_INFO) +
        tlv(0x19, u32(0)) + tlv(0x1A, u8(1)) + tlv(0x1B, u32(0)) +
        tlv(0x1C, u32(0)))

q = Qmi()
print('WDA_PORT', q.lookup(0x1a))
try:
    r = q.command(0x1a, 0, 0x0020, tlvs, timeout=6)
    print('RESP_TLVS', {k: v.hex() for k, v in r.items()})
    for t in (0x12, 0x13, 0x15, 0x16):
        if t in r and len(r[t]) >= 4:
            print('ECHO', hex(t), struct.unpack('<I', r[t][:4])[0])
except Exception as e:
    print('WDA_ERR', repr(e))
