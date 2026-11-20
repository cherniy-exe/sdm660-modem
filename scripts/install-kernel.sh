#!/bin/sh
# Install the freshly built kernel on the phone (run on the DEVICE as root).
# Copy arch/arm64/boot/Image -> vmlinuz, the DTB and modules into /tmp/newlite first.
set -e
echo "--- install ipa2-lite kernel"
cp /tmp/newlite/vmlinuz /boot/vmlinuz
cp /tmp/newlite/sdm660-xiaomi-lavender-tianma.dtb /boot/sdm660-xiaomi-lavender-tianma.dtb
cp /tmp/newlite/sdm660-xiaomi-lavender-tianma.dtb \
   /boot/dtbs/qcom/sdm660-xiaomi-lavender-tianma.dtb
rm -rf /lib/modules/7.2.15-sdm660
cp -a /tmp/newlite/modules/lib/modules/7.2.15-sdm660 /lib/modules/
depmod 7.2.15-sdm660
mkinitfs
echo "--- verify"
ls -la /boot/vmlinuz /boot/boot.img /boot/dtbs/qcom/sdm660-xiaomi-lavender-tianma.dtb
modinfo /lib/modules/7.2.15-sdm660/kernel/drivers/net/ipa2-lite/ipa2-lite.ko* 2>/dev/null \
  | grep -E 'vermagic|alias' | head -5
echo LITE-INSTALL-DONE
