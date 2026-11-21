#!/bin/sh
# Run after vendor-call.py has written /tmp/vendor-call.state.
for i in $(seq 1 90); do [ -f /tmp/vendor-call.state ] && break; sleep 1; done
. /tmp/vendor-call.state
echo "Applying mobile: ip=$ip gw=$gw prefix=$prefix mtu=$mtu"

ip link set rmnet_ipa0 up 2>/dev/null
ip link del qmapmux0.0 2>/dev/null
ip link add qmapmux0.0 type rmnet mux_id 1 ingress-deaggregation ingress-mapv4-checksum
ip link set qmapmux0.0 up
ip addr flush dev qmapmux0.0
ip addr add ${ip}/${prefix} dev qmapmux0.0
[ -n "$mtu" ] && [ "$mtu" != "0" ] && ip link set qmapmux0.0 mtu $mtu

ip route del default dev qmapmux0.0 2>/dev/null
ip route add default via ${gw} dev qmapmux0.0 metric 50

{
  [ -n "$dns1" ] && echo "nameserver $dns1"
  [ -n "$dns2" ] && echo "nameserver $dns2"
} > /etc/resolv.conf

echo "=== VERIFY ==="
ip -br link | grep -E 'rmnet|qmap'
ip -s link show qmapmux0.0 | grep -A2 'RX:'
ip route get 1.1.1.1
