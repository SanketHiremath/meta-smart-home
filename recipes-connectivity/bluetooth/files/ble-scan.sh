#!/bin/sh
# =========================================================================
# ble-scan — bring up the RTL8761BU USB dongle and run a BLE advertisement
# scan.  Useful for verifying the adapter and discovering nearby BLE sensors.
#
# Usage: ble-scan [scan-duration-seconds]   (default: 10)
# =========================================================================
set -e

SCAN_SECS="${1:-10}"
TIMEOUT=15          # seconds to wait for hci0 to appear after modprobe

log()  { printf '[ble-scan] %s\n' "$*"; }
warn() { printf '[ble-scan] WARNING: %s\n' "$*" >&2; }
die()  { printf '[ble-scan] ERROR: %s\n' "$*" >&2; exit 1; }

# ── 1. Ensure btusb is loaded ─────────────────────────────────────────────
# If built into the kernel (=y) modprobe returns "not found" — that is fine.
modprobe btusb 2>/dev/null \
    && log "btusb module loaded" \
    || log "btusb is built-in or not available as a module (continuing)"

# ── 2. Wait for the HCI device to appear ─────────────────────────────────
log "Waiting for hci0 (timeout ${TIMEOUT}s) ..."
i=0
while [ ! -d /sys/class/bluetooth/hci0 ]; do
    sleep 1
    i=$((i + 1))
    if [ "$i" -ge "$TIMEOUT" ]; then
        log "--- lsusb ---"
        lsusb || true
        log "--- dmesg (BT-related) ---"
        dmesg | grep -i -E 'bluetooth|btusb|rtl|8761|hci|firmware' | tail -30 || true
        die "hci0 did not appear after ${TIMEOUT}s. Check dmesg output above."
    fi
done
log "hci0 appeared after ${i}s."

# ── 3. Bring the interface up ────────────────────────────────────────────
hciconfig hci0 up
log "hci0 is up."

# ── 4. Print adapter info ────────────────────────────────────────────────
echo ""
echo "════════ HCI adapter ════════"
hciconfig hci0

echo ""
echo "════════ HCI version ════════"
hciconfig hci0 version

echo ""
echo "════════ USB device (expect 2357:0604) ════════"
lsusb | grep -i -E '2357:0604|realtek' \
    || warn "2357:0604 not found — check 'lsusb' manually"

# ── 5. BLE advertisement scan ────────────────────────────────────────────
# hcitool lescan prints: <BD_ADDR>  <Name or (unknown)>
# --duplicates keeps printing the same address on each advertisement burst,
# useful for measuring RSSI presence/absence but noisy — remove if unwanted.
echo ""
echo "════════ BLE lescan (${SCAN_SECS}s) — Ctrl-C to abort early ════════"
timeout "${SCAN_SECS}" hcitool -i hci0 lescan --duplicates 2>/dev/null || true

echo ""
log "Scan complete."
