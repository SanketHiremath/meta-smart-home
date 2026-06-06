SUMMARY = "Smart Home GTK3 Dashboard"
PR = "r17"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

FILESEXTRAPATHS:prepend := "${THISDIR}/../../icons/png:"

SRC_URI = " \
    file://smart.py \
    file://launch-my-gtk-app.sh \
    file://my-gtk-app.service \
    file://home.png \
    file://energy.png \
    file://weather.png \
    file://alert.png \
    file://setting.png \
    "

S = "${WORKDIR}"

inherit systemd

RDEPENDS:${PN} = "python3 python3-pygobject gtk+3"

SYSTEMD_SERVICE:${PN} = "my-gtk-app.service"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"

do_install() {
    install -d ${D}/opt/my-gtk-app
    install -m 0755 ${S}/smart.py ${D}/opt/my-gtk-app/
    install -m 0755 ${S}/launch-my-gtk-app.sh ${D}/opt/my-gtk-app/

    install -d ${D}/opt/my-gtk-app/icons
    install -m 0644 ${S}/home.png    ${D}/opt/my-gtk-app/icons/
    install -m 0644 ${S}/energy.png  ${D}/opt/my-gtk-app/icons/
    install -m 0644 ${S}/weather.png ${D}/opt/my-gtk-app/icons/
    install -m 0644 ${S}/alert.png   ${D}/opt/my-gtk-app/icons/
    install -m 0644 ${S}/setting.png ${D}/opt/my-gtk-app/icons/

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${S}/my-gtk-app.service ${D}${systemd_system_unitdir}/
}

FILES:${PN} = " \
    /opt/my-gtk-app \
    ${systemd_system_unitdir}/my-gtk-app.service \
"
