#!/usr/bin/env python3
"""Vendor-style cellular bearer bringup (X00TD recipe) on SDM660 IPA v2.6L.
No ModemManager. Holds the WDS socket open for the lifetime of the call.
Run as root after a cold boot with MM disabled.
"""
import socket, struct, select, time, sys, os

AF_QIPCRTR = 42
QRTR_CTRL = 0xfffffffe
SVC_WDS, SVC_DMS, SVC_NAS, SVC_WDA, SVC_DPM = 1, 2, 3, 0x1a, 0x2f
MSG_WDA_SET = 0x20
MSG_DPM_OPEN = 0x20
MSG_BIND_MUX = 0xa2
MSG_AF_MODE = 0xaf
MSG_IPFAM = 0x4d
MSG_START = 0x20
MSG_GET_SETTINGS = 0x2d

class Qmi:
    def __init__(self):
        self.ns = socket.socket(AF_QIPCRTR, socket.SOCK_DGRAM)
        self.txn = 0
        self.socks = {}
        self.ports = {}

    def lookup(self, service, instance=None, wait=3.0):
        pkt = struct.pack('<IIIII', 10, service, 0, 0, 0)
        self.ns.sendto(pkt, (1, QRTR_CTRL))
        found = []
        end = time.time() + wait
        while time.time() < end:
            r, _, _ = select.select([self.ns], [], [], 0.3)
            if not r: continue
            data, _ = self.ns.recvfrom(4096)
            if len(data) < 20: continue
            cmd, svc, inst, node, port = struct.unpack('<IIIII', data[:20])
            if cmd == 4 and svc == service:
                found.append((inst, node, port))
                if instance is None or (inst & 0xff) == instance:
                    break
        if not found:
            raise RuntimeError('QRTR lookup failed for service 0x%x' % service)
        found.sort()
        inst, node, port = found[0]
        print('LOOKUP svc=0x%x inst=0x%x node=%d port=%d' % (service, inst, node, port), flush=True)
        return node, port

    def sock(self, service):
        if service not in self.socks:
            s = socket.socket(AF_QIPCRTR, socket.SOCK_DGRAM)
            node, port = self.lookup(service, 1 if service == SVC_WDS else None)
            self.socks[service] = (s, node, port)
        return self.socks[service]

    def request(self, service, msg, tlvs, timeout=6, persistent=False):
        s, node, port = self.sock(service)
        self.txn = (self.txn + 1) & 0xff
        t = self.txn
        s.sendto(struct.pack('<BBHH', 0, t, msg, len(tlvs)) + tlvs, (node, port))
        end = time.time() + timeout
        while time.time() < end:
            r, _, _ = select.select([s], [], [], 0.3)
            if not r: continue
            data, _ = s.recvfrom(8192)
            if len(data) < 14: continue
            flags, qt, qm, qlen = struct.unpack('<BBHH', data[:6])
            if qt != t or qm != msg: continue
            res = data[10:14]
            result, err = struct.unpack('<HH', res) if len(res) >= 4 else (0xffff, 0xffff)
            print('RX msg=0x%04x result=%d err=%d raw=%s' % (msg, result, err, data.hex()), flush=True)
            return data, result, err
        raise TimeoutError('msg 0x%04x' % msg)

def L(t, v): return bytes([t, len(v) & 255, (len(v) >> 8) & 255]) + v
def U(v): return struct.pack('<I', v)
def B(v): return bytes([v])

q = Qmi()

# 1. WDA SET_DATA_FORMAT (own socket): DL=QMAPv3, UL=QMAPv1, ep IPA.
ep = bytes([4,0,0,0, 1,0,0,0])
wda = (L(0x11,U(2)) + L(0x12,U(5)) + L(0x13,U(7)) + L(0x15,U(10)) +
       L(0x16,U(8192)) + L(0x17,ep) + L(0x19,U(0)) + L(0x1a,B(1)) +
       L(0x1b,U(0)) + L(0x1c,U(0)))
_, r, e = q.request(SVC_WDA, MSG_WDA_SET, wda)
if (r, e) != (0, 0): print('WDA FAILED', r, e, flush=True)

# 2. DPM OPEN_PORT (own socket), stock byte order tx=4 rx=5.
dpm = L(0x11, bytes([1]) + U(4) + U(1) + U(4) + U(5))
_, r, e = q.request(SVC_DPM, MSG_DPM_OPEN, dpm)
if (r, e) != (0, 0): print('DPM FAILED', r, e, flush=True)

# 3. Persistent WDS socket: BIND_MUX + START_NETWORK + settings.
q.request(SVC_WDS, MSG_AF_MODE, L(0x01, U(2)))
q.request(SVC_WDS, MSG_IPFAM, L(0x01, B(1)))
q.request(SVC_WDS, MSG_BIND_MUX, L(0x10, ep) + L(0x11, B(1)))
apn = os.environ.get('APN', 'internet.yota').encode()
q.request(SVC_WDS, MSG_START, L(0x14, apn) + L(0x19, B(1)), timeout=12)
data, r, e = q.request(SVC_WDS, MSG_GET_SETTINGS, L(0x01, U(0xe330)))

# Decode TLVs by walking from byte 7 (bare QRTR result TLV lives there).
tlvs = {}
p = 7
while p + 3 <= len(data):
    tt = data[p]; ln = struct.unpack('<H', data[p+1:p+3])[0]
    if ln > len(data) - p - 3: break
    tlvs[tt] = data[p+3:p+3+ln]
    p += 3 + ln
def u32(t):
    return struct.unpack('<I', tlvs[t][:4])[0] if t in tlvs and len(tlvs[t]) >= 4 else 0
state = dict(ip=u32(0x1e), gw=u32(0x20), prefix=u32(0x21),
             dns1=u32(0x15), dns2=u32(0x16), mtu=u32(0x29), pdh=u32(0x01))
def ipstr(v): return '%d.%d.%d.%d' % ((v >> 24) & 255, (v >> 16) & 255, (v >> 8) & 255, v & 255)
with open('/tmp/vendor-call.state', 'w') as f:
    for k, v in state.items(): f.write('%s=%s\n' % (k, ipstr(v) if k in ('ip','gw','dns1','dns2') else v))
print('STATE', state, {k: ipstr(v) for k, v in state.items() if k in ('ip','gw','dns1','dns2')}, flush=True)
print('HOLDING WDS SOCKET OPEN - bearer stays up while this process runs', flush=True)
while True: time.sleep(60)
