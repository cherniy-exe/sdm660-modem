#!/bin/sh
# Run as root ON THE PHONE before the next cold reboot.
# Purpose: make the next boot's IPA handshake fully observable and align the
# AP-side QMAP mux id with the rmnet link ModemManager creates (mux_id 1).
set -x

# 1. Align QMAP mux id. ipa_qmi_install_wan_filters() sends this value to the
#    modem, and ipa_hdr_proc_ctx_setup() stamps it into the AP's QMAP header
#    template.  The driver reads the parameter once at probe time, so a
#    reboot is required for this to take effect.
mkdir -p /etc/modprobe.d
cat > /etc/modprobe.d/ipa-qmux.conf <<'EOF'
# AP QMAP header + WAN downlink filters must match MM's qmapmux0.0 (mux 1)
options ipa qmap_mux_id=1
EOF

# 2. Enable ipa dynamic debug at module load, i.e. BEFORE the QMI handshake.
#    "module ipa +pflt" written after boot is useless: the handshake messages
#    were already emitted during boot.  The module uevent fires at modprobe.
cat > /etc/udev/rules.d/97-ipa-dyndbg.rules <<'EOF'
SUBSYSTEM=="module", KERNEL=="ipa", ACTION=="add", RUN+="/bin/sh -c 'echo \"module ipa +pflt\" > /sys/kernel/debug/dynamic_debug/control; echo IPA-DYNDBG-READY > /dev/kmsg'"
EOF

# 3. Restore the MM D-Bus activation file moved aside during debugging.
if [ -f /usr/share/dbus-1/system-services/org.freedesktop.ModemManager1.service.bak ] && \
   [ ! -f /usr/share/dbus-1/system-services/org.freedesktop.ModemManager1.service ]; then
    mv /usr/share/dbus-1/system-services/org.freedesktop.ModemManager1.service.bak \
       /usr/share/dbus-1/system-services/org.freedesktop.ModemManager1.service
fi

echo "=== VERIFY ==="
cat /etc/modprobe.d/ipa-qmux.conf
cat /etc/udev/rules.d/97-ipa-dyndbg.rules
ls -l /usr/share/dbus-1/system-services/org.freedesktop.ModemManager1.service*
