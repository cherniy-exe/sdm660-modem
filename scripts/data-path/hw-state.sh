#!/bin/sh
{
echo "=== DATE ==="; date
echo "=== IPA SYSFS ==="; find /sys/bus/platform/devices/147c0000.ipa -maxdepth 3 -type f | sort
for f in /sys/bus/platform/devices/147c0000.ipa/version /sys/bus/platform/devices/147c0000.ipa/feature/*; do echo "-- $f = $(cat $f 2>&1)"; done
echo "=== DEBUGFS TOP ==="; find /sys/kernel/debug -maxdepth 2 \( -iname '*ipa*' -o -iname '*bam*' -o -iname '*rmnet*' -o -iname '*qrtr*' \) 2>/dev/null
echo "=== DEBUGFS IPA FILES ==="; find /sys/kernel/debug/ipa /sys/kernel/debug/bam-dma -maxdepth 3 -type f 2>/dev/null | head -80
echo "=== ENDPOINT ATTRS ==="; find /sys/bus/platform/devices/147c0000.ipa -maxdepth 3 -type d | head -60
echo "=== LINK ==="; ip -s -s link show rmnet_ipa0; ip -s -s link show qmapmux0.0
echo "=== DONE ==="
} > /tmp/hw-state.txt 2>&1
chmod 644 /tmp/hw-state.txt
