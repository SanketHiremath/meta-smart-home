SUMMARY = "NTP-synchronised time web server"
PR = "r0"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://time_server.py \
    file://time-server.service \
"

S = "${WORKDIR}"

inherit systemd

RDEPENDS:${PN} = "python3 network-config"

SYSTEMD_SERVICE:${PN} = "time-server.service"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"

do_install() {
    install -d ${D}/opt/time-server
    install -m 0755 ${S}/time_server.py ${D}/opt/time-server/

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${S}/time-server.service ${D}${systemd_system_unitdir}/
}

FILES:${PN} = " \
    /opt/time-server \
    ${systemd_system_unitdir}/time-server.service \
"
