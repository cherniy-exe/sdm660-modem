#!/bin/sh
echo ---DMESG---
dmesg | grep -iE "q6v5-mss|4080000|mss" | tail -8
echo ---DISABLE-DAEMONS---
rc-service ofono stop 2>/dev/null
rc-service modemmanager stop 2>/dev/null
pkill -x ofonod 2>/dev/null
pkill -x ModemManager 2>/dev/null
rc-update del ofono default 2>/dev/null
rc-update del modemmanager default 2>/dev/null
echo ---CLEANUP-RMNET---
rm -f /etc/udev/rules.d/78-mm-rmnet-workaround.rules
udevadm control --reload-rules
i=0
while [ $i -lt 8 ]; do ip link del rmnet_data$i 2>/dev/null; i=$((i+1)); done
ip link del rmnet_ipa0 2>/dev/null
ip link del dummy0 2>/dev/null
echo ---MODEM-SETUP-SERVICE---
cat > /etc/init.d/modem-setup <<'EOF'
#!/sbin/openrc-run
description="Bring Qualcomm modem online"
depend() {
    need msm-firmware-loader rmtfs
    after msm-modem-uim-selection
}
start() {
    modprobe tun 2>/dev/null
    ebegin "Waiting for modem QMI"
    i=0
    while [ $i -lt 30 ]; do
        if qmicli -d qrtr://0 --dms-get-operating-mode >/dev/null 2>&1; then
            break
        fi
        sleep 2
        i=$((i+1))
    done
    eend 0
    ebegin "Setting modem online"
    qmicli -d qrtr://0 --dms-set-operating-mode=online >/dev/null 2>&1
    eend $?
}
EOF
chmod +x /etc/init.d/modem-setup
rc-update add modem-setup default 2>&1 | tail -1
echo SETUP-DONE