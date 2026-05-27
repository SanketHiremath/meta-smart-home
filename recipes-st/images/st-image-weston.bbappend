# Remove the entire ST demo suite (demo-gtk, installer-gtk, demo-application-*,
# demo-launcher, linux-examples-stm32mp1, etc.) from the image.
# my-gtk-app installs its own script into /usr/local/weston-start-at-startup/
# so it is autoloaded by Weston directly — no ST launcher infrastructure needed.
CORE_IMAGE_EXTRA_INSTALL:remove = "packagegroup-st-demo"

CORE_IMAGE_EXTRA_INSTALL:append = " \
    wpa-supplicant \
    linux-firmware-rtl8188 \
    wifi-config \
"
