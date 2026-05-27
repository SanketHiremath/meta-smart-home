SUMMARY = "WiFi credentials and systemd-networkd DHCP config for wlan0"
PR = "r0"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://wpa_supplicant-wlan0.conf \
    file://20-wlan.network \
"

S = "${WORKDIR}"

# wpa-supplicant must be installed so the template unit
# /lib/systemd/system/wpa_supplicant@.service exists at boot.
RDEPENDS:${PN} = "wpa-supplicant"

do_install() {
    # wpa_supplicant credentials — 0600 so only root can read the PSK
    install -d ${D}${sysconfdir}/wpa_supplicant
    install -m 0600 ${S}/wpa_supplicant-wlan0.conf \
        ${D}${sysconfdir}/wpa_supplicant/wpa_supplicant-wlan0.conf

    # systemd-networkd DHCP config for wlan0
    install -d ${D}${sysconfdir}/systemd/network
    install -m 0644 ${S}/20-wlan.network \
        ${D}${sysconfdir}/systemd/network/20-wlan.network

    # Enable wpa_supplicant@wlan0 by creating the systemd enable symlink.
    # The template unit wpa_supplicant@.service is shipped by wpa-supplicant.
    # This is equivalent to: systemctl enable wpa_supplicant@wlan0
    install -d ${D}${sysconfdir}/systemd/system/multi-user.target.wants
    ln -sf ${systemd_system_unitdir}/wpa_supplicant@.service \
        ${D}${sysconfdir}/systemd/system/multi-user.target.wants/wpa_supplicant@wlan0.service
}

FILES:${PN} = " \
    ${sysconfdir}/wpa_supplicant/wpa_supplicant-wlan0.conf \
    ${sysconfdir}/systemd/network/20-wlan.network \
    ${sysconfdir}/systemd/system/multi-user.target.wants/wpa_supplicant@wlan0.service \
"
