#!/usr/bin/env python3
"""QMI over QRTR client for WMS (SMS) on Qualcomm SoC modems.
Works without ModemManager/ofono: raw QMUX/QMI over AF_QIPCRTR.
"""
import socket, struct, select, time

AF_QIPCRTR = 42
QRTR_CTRL = 0xfffffffe
SVC_CTL, SVC_WDS, SVC_DMS, SVC_NAS, SVC_WMS, SVC_UIM = 0, 1, 2, 3, 5, 10

GSM7 = ('@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ !"#¤%&\'()*+,-./0123456789:;<=>?'
        '¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà')
GSM7_EXT = {'\f': 10, '^': 20, '{': 40, '}': 41, '\\': 47, '[': 60, '~': 61, ']': 62, '|': 64, '€': 101}

def bcd_decode(data, ndigits):
    out = []
    for b in data:
        for nib in (b & 0x0f, b >> 4):
            if len(out) >= ndigits:
                break
            out.append('0123456789*#abc' [nib] if nib < 13 else '')
    return ''.join(out)

def bcd_encode(number):
    digits = number.replace('+', '').replace(' ', '').replace('-', '')
    if len(digits) % 2:
        digits += 'F'
    out = bytearray()
    for i in range(0, len(digits), 2):
        lo = '0123456789*#abc'.index(digits[i].lower()) if digits[i].lower() in '0123456789*#abc' else 15
        hi = '0123456789*#abc'.index(digits[i+1].lower()) if digits[i+1].lower() in '0123456789*#abc' else 15
        out.append(lo | (hi << 4))
    return bytes(out), len(digits) - (1 if digits.endswith('F') else 0)

def gsm7_pack(text):
    septets = []
    for ch in text:
        if ch in GSM7_EXT:
            septets.extend([27, GSM7_EXT[ch]])
        elif ch in GSM7:
            septets.append(GSM7.index(ch))
        else:
            return None
    out = bytearray()
    acc = 0
    nbits = 0
    for s in septets:
        acc |= s << nbits
        nbits += 7
        while nbits >= 8:
            out.append(acc & 0xff)
            acc >>= 8
            nbits -= 8
    if nbits:
        out.append(acc & 0xff)
    return bytes(out), len(septets)

def gsm7_unpack(data, nseptets):
    acc = 0
    nbits = 0
    out = []
    i = 0
    while i < nseptets:
        while nbits < 7 and len(data):
            acc |= data[0] << nbits
            data = data[1:]
            nbits += 8
        s = acc & 0x7f
        acc >>= 7
        nbits -= 7
        if s == 27 and i + 1 < nseptets:
            while nbits < 7 and len(data):
                acc |= data[0] << nbits
                data = data[1:]
                nbits += 8
            e = acc & 0x7f
            acc >>= 7
            nbits -= 7
            rev = {v: k for k, v in GSM7_EXT.items()}
            out.append(rev.get(e, ' '))
            i += 2
        else:
            out.append(GSM7[s] if s < len(GSM7) else '?')
            i += 1
    return ''.join(out)

def decode_pdu(pdu):
    """Decode SMS-DELIVER PDU -> dict(number, text, time, smsc)."""
    try:
        p = 0
        smsc_len = pdu[p]; p += 1
        smsc = ''
        if smsc_len:
            stype = pdu[p]
            sbcd, sn = bcd_decode(pdu[p+1:p+smsc_len], (smsc_len-1)*2), (smsc_len-1)*2
            smsc = ('+' if stype == 0x91 else '') + bcd_decode(pdu[p+1:p+smsc_len], (smsc_len-1)*2)
            p += smsc_len
        first = pdu[p]; p += 1
        oa_len = pdu[p]; p += 1
        oa_type = pdu[p]; p += 1
        oa_bytes = (oa_len + 1) // 2
        number = ('+' if oa_type == 0x91 else '') + bcd_decode(pdu[p:p+oa_bytes], oa_len)
        p += oa_bytes
        pid = pdu[p]; p += 1
        dcs = pdu[p]; p += 1
        scts = pdu[p:p+7]; p += 7
        def sw(b): return (b & 0x0f) * 10 + (b >> 4)
        ts = '%02d-%02d-%02d %02d:%02d:%02d' % (sw(scts[0]), sw(scts[1]), sw(scts[2]),
                                                 sw(scts[3]), sw(scts[4]), sw(scts[5]))
        udl = pdu[p]; p += 1
        ud = pdu[p:p+udl]
        if dcs & 0x0c == 0x08:
            text = ud.decode('utf-16-be', errors='replace')
        elif dcs & 0x0c == 0x04:
            text = ud.decode('latin-1', errors='replace')
        else:
            text = gsm7_unpack(ud, udl)
        return {'number': number, 'text': text, 'time': ts, 'smsc': smsc, 'dcs': dcs}
    except Exception as e:
        return {'number': '?', 'text': '<decode error: %s>' % e, 'time': '', 'smsc': '', 'raw': pdu.hex()}

def encode_pdu(number, text):
    """Encode SMS-SUBMIT PDU. SMSC len 0 = use SIM default SMSC."""
    packed = gsm7_pack(text)
    if packed:
        ud, udl = packed
        dcs = 0x00
    else:
        ud = text.encode('utf-16-be')
        udl = len(ud)
        dcs = 0x08
    international = number.startswith('+')
    bcd, ndig = bcd_encode(number)
    da_type = 0x91 if international else 0x81
    return bytes([0x00, 0x11, 0x00, ndig, da_type]) + bcd + bytes([0x00, dcs, 0xa7, udl]) + ud

class QmiError(Exception):
    pass

class Qmi:
    def __init__(self, local_node=1):
        self.local_node = local_node
        self.txn = 0
        self.socks = {}
        self.ports = {}
        self.ns = socket.socket(AF_QIPCRTR, socket.SOCK_DGRAM)

    def lookup(self, service, wait=2.0):
        if service in self.ports:
            return self.ports[service]
        pkt = struct.pack('<IIIII', 10, service, 0, 0, 0)
        self.ns.sendto(pkt, (self.local_node, QRTR_CTRL))
        end = time.time() + wait
        while time.time() < end:
            r, _, _ = select.select([self.ns], [], [], 0.3)
            if not r:
                continue
            data, addr = self.ns.recvfrom(4096)
            if len(data) >= 20:
                cmd, svc, inst, node, port = struct.unpack('<IIIII', data[:20])
                if cmd == 4 and svc == service:
                    self.ports[service] = (node, port)
                    return (node, port)
        raise QmiError('QRTR lookup failed for service %d' % service)

    def _sock(self, service):
        if service not in self.socks:
            self.socks[service] = socket.socket(AF_QIPCRTR, socket.SOCK_DGRAM)
        return self.socks[service]

    def _txn(self):
        self.txn = (self.txn + 1) & 0xff
        return self.txn

    def command(self, service, client, msg, tlvs=b'', timeout=5.0):
        # raw QMI over QRTR: no QMUX header; client arg ignored (port-based)
        node, port = self.lookup(service)
        s = self._sock(service)
        t = self._txn()
        pkt = struct.pack('<BBHH', 0, t, msg, len(tlvs)) + tlvs
        s.sendto(pkt, (node, port))
        end = time.time() + timeout
        while time.time() < end:
            r, _, _ = select.select([s], [], [], 0.3)
            if not r:
                continue
            data, addr = s.recvfrom(4096)
            if len(data) < 6:
                continue
            qflags, qt, qmsg, qlen = struct.unpack('<BBHH', data[:6])
            if qt != t or qmsg != msg:
                continue
            tl = data[6:6+qlen]
            out = {}
            p = 0
            while p + 3 <= len(tl):
                tt, ln = tl[p], struct.unpack('<H', tl[p+1:p+3])[0]
                out[tt] = tl[p+3:p+3+ln]
                p += 3 + ln
            if 0x02 in out and len(out[0x02]) >= 4:
                err, status = struct.unpack('<HH', out[0x02][:4])
                if err != 0:
                    raise QmiError('QMI error 0x%04x status %d (msg 0x%04x)' % (err, status, msg))
            return out
        raise QmiError('QMI timeout (msg 0x%04x)' % msg)

    def client(self, service):
        return 0  # CID is local bookkeeping; modem tracks by source port

    # ---- WMS ----
    def sms_list(self, storage=0):
        out = self.command(SVC_WMS, self.client(SVC_WMS), 0x0035,
                           bytes([0x01, 0x01, 0x00, storage]))
        entries = []
        ml = out.get(0x01, b'')
        p = 0
        while p + 5 <= len(ml):
            idx = struct.unpack('<I', ml[p:p+4])[0]
            tag = ml[p+4]
            entries.append((idx, tag))
            p += 5
        return entries

    def sms_read(self, index, storage=0):
        tlvs = bytes([0x01, 0x01, 0x00, storage]) + struct.pack('<BII', 0x02, 4, index)
        out = self.command(SVC_WMS, self.client(SVC_WMS), 0x0022, tlvs)
        raw = out.get(0x01, b'')
        return decode_pdu(raw) if raw else None

    def sms_send(self, number, text):
        pdu = encode_pdu(number, text)
        tlvs = bytes([0x01]) + struct.pack('<H', len(pdu)) + pdu
        out = self.command(SVC_WMS, self.client(SVC_WMS), 0x0020, tlvs, timeout=30)
        mid = struct.unpack('<H', out[0x01][:2])[0] if 0x01 in out else 0
        return mid

    def sms_delete(self, index, storage=0):
        tlvs = bytes([0x01, 0x01, 0x00, storage]) + struct.pack('<BII', 0x02, 4, index)
        self.command(SVC_WMS, self.client(SVC_WMS), 0x0034, tlvs)

if __name__ == '__main__':
    q = Qmi()
    print('WMS port:', q.lookup(SVC_WMS))
    cid = q.client(SVC_WMS)
    print('WMS client id:', cid)
    for storage in (0, 1):
        try:
            lst = q.sms_list(storage)
            print('storage %d: %d messages: %s' % (storage, len(lst), lst[:10]))
            for idx, tag in lst[:5]:
                m = q.sms_read(idx, storage)
                print('  [%d] %s %s: %s' % (idx, m.get('time'), m.get('number'), m.get('text')[:80]))
        except QmiError as e:
            print('storage %d error: %s' % (storage, e))
    print('QMI-SMS-TEST-DONE')