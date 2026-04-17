SUMMARY = "BLE scan helper and Realtek RTL8761BUV firmware for TP-Link UB500"
DESCRIPTION = "\
Installs the ble-scan diagnostic script and pulls in:\n\
  • bluez5          — bluetoothd daemon + hciconfig / hcitool / bluetoothctl\n\
  • linux-firmware-rtl8761bu — RTL8761BU firmware blobs (rtl_bt/rtl8761bu_fw.bin\n\
                               + rtl8761bu_config.bin) needed by the btusb driver\n\
"

LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://ble-scan.sh"

S = "${WORKDIR}"

# ── Runtime dependencies ──────────────────────────────────────────────────
# bluez5        : userspace BT stack — provides hciconfig, hcitool,
#                 bluetoothctl and the bluetoothd D-Bus daemon.
# linux-firmware-rtl8761 : Realtek RTL8761 family firmware blobs
#   (includes rtl8761bu_fw.bin / rtl8761bu_config.bin for the UB500 dongle).
#   Package name verified with: bitbake -e linux-firmware | grep '^PACKAGES'
RDEPENDS:${PN} = " \
    bluez5 \
    linux-firmware-rtl8761 \
"

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${WORKDIR}/ble-scan.sh ${D}${bindir}/ble-scan
}

FILES:${PN} = "${bindir}/ble-scan"
