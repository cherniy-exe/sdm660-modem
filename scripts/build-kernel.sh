#!/bin/bash
# Reproducible build of the SDM660 kernel with ipa2-lite enabled.
# Run from the root of a clean kernel checkout with the patch already applied.
# Override TOOLCHAIN if your clang-19 toolchain lives elsewhere.
set -euo pipefail

TOOLCHAIN="${TOOLCHAIN:-$HOME/toolchain/root/usr}"
DEVICE_CONFIG="${DEVICE_CONFIG:-$HOME/device-config}"
JOBS="${JOBS:-8}"

export PATH="$TOOLCHAIN/bin:$PATH"
export LD_LIBRARY_PATH="$TOOLCHAIN/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export BISON_PKGDATADIR="$TOOLCHAIN/share/bison"
export M4="$TOOLCHAIN/bin/m4"
export HOSTCFLAGS="-I$TOOLCHAIN/include -I$TOOLCHAIN/include/x86_64-linux-gnu"
export HOSTLDFLAGS="-L$TOOLCHAIN/lib/x86_64-linux-gnu"

cp "$DEVICE_CONFIG" .config
./scripts/config --disable QCOM_IPA --module QCOM_IPA2_LITE
make ARCH=arm64 LLVM=-19 olddefconfig
grep -q '^CONFIG_QCOM_IPA2_LITE=m$' .config || { echo 'ipa2-lite not enabled' >&2; exit 1; }

make ARCH=arm64 LLVM=-19 -j"$JOBS" \
  Image modules qcom/sdm660-xiaomi-lavender-tianma.dtb
echo BUILD-DONE
