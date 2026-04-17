SUMMARY = "Static IP and NTP configuration for STM32MP157D-DK1"
PR = "r0"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://10-eth-static.network \
    file://10-ntp.conf \
"

S = "${WORKDIR}"

# systemd-networkd and systemd-timesyncd are already enabled by the
# openstlinux-weston distribution — no need to inherit systemd here.

do_install() {
    # /etc/systemd/network/ takes precedence over /lib/systemd/network/ (vendor config)
    install -d ${D}${sysconfdir}/systemd/network
    install -m 0644 ${S}/10-eth-static.network ${D}${sysconfdir}/systemd/network/

    # Drop-in for systemd-timesyncd — avoids conflicting with systemd's own timesyncd.conf
    install -d ${D}${sysconfdir}/systemd/timesyncd.conf.d
    install -m 0644 ${S}/10-ntp.conf ${D}${sysconfdir}/systemd/timesyncd.conf.d/
}

FILES:${PN} = " \
    ${sysconfdir}/systemd/network/10-eth-static.network \
    ${sysconfdir}/systemd/timesyncd.conf.d/10-ntp.conf \
"
