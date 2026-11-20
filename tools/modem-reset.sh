#!/bin/sh
qmicli -d qrtr://0 --dms-set-operating-mode=reset 2>&1 | head -1
sleep 3
MODE=$(qmicli -d qrtr://0 --dms-get-operating-mode 2>&1 | grep Mode)
echo "after reset: $MODE"
if echo "$MODE" | grep -qE "offline|shutting"; then
  echo stop > /sys/class/remoteproc/remoteproc1/state
  sleep 3
  echo start > /sys/class/remoteproc/remoteproc1/state
  sleep 28
  rc-service msm-modem-uim-selection restart 2>&1 | tail -2
fi
qmicli -d qrtr://0 --dms-set-operating-mode=online 2>&1 | head -1
sleep 12
qmicli -d qrtr://0 --dms-get-operating-mode 2>&1 | grep Mode
qmicli -d qrtr://0 --nas-get-serving-system 2>&1 | grep -E "Registration|Radio" | head -3
qmicli -d qrtr://0 --nas-get-signal-strength 2>&1 | grep -A1 Current | head -3
echo RESET-DONE