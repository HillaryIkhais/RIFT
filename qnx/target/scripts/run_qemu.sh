#!/bin/sh
#
# RIFT-QNX: boot QNX 8.0 in QEMU (x86_64) and run the resource-manager demo.
#
# Intended to run on a QNX SDP 8.0 development host (x86_64 Linux/Windows)
# with QEMU and a QNX 8.0 x86_64 boot image available.
#
# Usage: QNX_SDP=/opt/qnx800 ./run_qemu.sh
#
set -eu

QEMU="${QEMU:=qemu-system-x86_64}"
QNX_IMAGE="${QNX_IMAGE:=qnx800-x86_64.img}"
MEM="${MEM:=2048}"
SMP="${SMP:=2}"

echo "[rift-qnx] Booting QNX 8.0 QEMU target (x86_64, ${MEM} MB, ${SMP} vCPUs)..."

"$QEMU" -machine q35 -cpu host -m "$MEM" -smp "$SMP" \
    -drive "file=$QNX_IMAGE,format=raw,if=virtio" \
    -netdev user,id=net0,hostfwd=tcp::2222-:22 \
    -device virtio-net-pci,netdev=net0 \
    -serial stdio -display sdl,gl=off \
    "$@"
