#!/bin/sh
{
echo "=== BEFORE ==="
ip -o -4 addr show qmapmux0.0 2>&1
mmcli -b 1 2>&1 | grep -iE "ip type|interface|address|gateway"
echo "=== DISCONNECT ==="
mmcli -m 0 --simple-disconnect 2>&1
sleep 3
echo "=== CONNECT IPV4 ==="
mmcli -m 0 --simple-connect="apn=internet.yota,ip-type=ipv4" 2>&1
sleep 8
echo "=== AFTER ==="
ip -o -4 addr show qmapmux0.0 2>&1
ip -s link show qmapmux0.0 2>&1 | grep -A2 "RX:"
mmcli -b 1 2>&1 | grep -iE "ip type|interface|address|gateway|connected"
echo "=== PING ==="
ping -I qmapmux0.0 -c 4 -W 2 1.1.1.1 2>&1 | tail -4
ip -s link show qmapmux0.0 2>&1 | grep -A2 "RX:"
echo "=== DONE ==="
} > /tmp/ipv4call.out 2>&1
chmod 644 /tmp/ipv4call.out
