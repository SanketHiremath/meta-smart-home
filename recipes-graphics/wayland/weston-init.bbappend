# Customise Weston for kiosk-style display:
#  - no panel (removes ST launcher buttons)
#  - solid dark background matching the GTK3 app theme (#0d1117)
do_install:append() {
    sed -i 's/^panel-position=.*/panel-position=none/' \
        ${D}${sysconfdir}/xdg/weston/weston.ini
    sed -i '/^background-image=/d' \
        ${D}${sysconfdir}/xdg/weston/weston.ini
    sed -i 's/^background-color=.*/background-color=0xff0d1117/' \
        ${D}${sysconfdir}/xdg/weston/weston.ini
}
