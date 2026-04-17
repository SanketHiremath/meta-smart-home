SUMMARY = "Smart Home GTK3 Dashboard"
PR = "r7"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://my_app.py \
    file://launch-my-gtk-app.sh \
    file://my-gtk-app.service \
    "

S = "${WORKDIR}"

inherit systemd

RDEPENDS:${PN} = "python3 python3-pygobject gtk+3"

SYSTEMD_SERVICE:${PN} = "my-gtk-app.service"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"

do_install() {
    install -d ${D}/opt/my-gtk-app
    install -m 0755 ${S}/my_app.py ${D}/opt/my-gtk-app/
    install -m 0755 ${S}/launch-my-gtk-app.sh ${D}/opt/my-gtk-app/

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${S}/my-gtk-app.service ${D}${systemd_system_unitdir}/
}

FILES:${PN} = " \
    /opt/my-gtk-app \
    ${systemd_system_unitdir}/my-gtk-app.service \
"
