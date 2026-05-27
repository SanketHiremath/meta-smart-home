# WiFi TL-WN725N Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add TP-Link TL-WN725N (RTL8188EUS) USB WiFi support to the STM32MP157D-DK1 image, auto-connecting to "Free-Wifi" on boot via wpa_supplicant and systemd-networkd DHCP.

**Architecture:** A new kernel config fragment enables the `r8188eu` staging driver. A new `wifi-config` recipe installs the wpa_supplicant credential file (pre-hashed PSK), the systemd-networkd DHCP config for `wlan0`, and the systemd enable symlink for `wpa_supplicant@wlan0.service`. `linux-firmware-rtl8188eu` provides the firmware blob. Ethernet (`end0`) and its existing static IP config are untouched.

**Tech Stack:** Yocto/BitBake (Scarthgap), Linux kernel r8188eu driver, wpa_supplicant, systemd-networkd

---

### Task 1: Kernel WiFi config fragment

**Files:**
- Create: `meta-smart-home/recipes-kernel/linux/linux-stm32mp/wifi.cfg`
- Modify: `meta-smart-home/recipes-kernel/linux/linux-stm32mp_%.bbappend`

- [ ] **Step 1: Create `wifi.cfg`**

Create `meta-smart-home/recipes-kernel/linux/linux-stm32mp/wifi.cfg` with this exact content:

```ini
# =========================================================================
# WiFi kernel config fragment — TP-Link TL-WN725N (Realtek RTL8188EUS)
# =========================================================================

# Wireless subsystem
CONFIG_WLAN=y
CONFIG_CFG80211=y
CONFIG_MAC80211=y
CONFIG_RFKILL=y

# RTL8188EU staging driver (covers RTL8188EUS used in TL-WN725N v2/v3)
# Requires CONFIG_STAGING=y — expected to be on in ST defconfig.
# If the build warns "CONFIG_RTL8188EU depends on CONFIG_STAGING",
# add CONFIG_STAGING=y to this fragment.
CONFIG_RTL8188EU=y
```

- [ ] **Step 2: Extend the kernel bbappend**

`meta-smart-home/recipes-kernel/linux/linux-stm32mp_%.bbappend` currently reads:

```bitbake
FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"

SRC_URI:append = " file://bluetooth.cfg;subdir=fragments"

KERNEL_CONFIG_FRAGMENTS:append = " ${WORKDIR}/fragments/bluetooth.cfg"
```

Replace it with (add the two wifi lines — do not remove the bluetooth lines):

```bitbake
FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"

SRC_URI:append = " file://bluetooth.cfg;subdir=fragments"
SRC_URI:append = " file://wifi.cfg;subdir=fragments"

KERNEL_CONFIG_FRAGMENTS:append = " ${WORKDIR}/fragments/bluetooth.cfg"
KERNEL_CONFIG_FRAGMENTS:append = " ${WORKDIR}/fragments/wifi.cfg"
```

- [ ] **Step 3: Build the kernel**

```bash
cd ~/Projects/yocto_proj
. ./poky/oe-init-build-env build-stm32mp1
bitbake -c cleansstate linux-stm32mp && bitbake linux-stm32mp 2>&1 | tee /tmp/kernel-build.log
```

Expected: build completes with no ERROR lines. `merge_config.sh` warnings about options already set to a higher value are normal — they are not errors.

Watch for: `warning: override: reassigning to symbol RTL8188EU` is fine. `error: CONFIG_RTL8188EU depends on CONFIG_STAGING` means you need to add `CONFIG_STAGING=y` to `wifi.cfg` — add it under the `CONFIG_RFKILL=y` line and rerun.

- [ ] **Step 4: Confirm the driver is compiled in**

```bash
grep RTL8188EU tmp/work/stm32mp1-openstlinux_weston-linux-gnueabi/linux-stm32mp/*/build/.config
```

Expected: `CONFIG_RTL8188EU=y` or `CONFIG_RTL8188EU=m`. Either is fine — `=m` means it builds as a module which the kernel will auto-load when the USB device is plugged in.

- [ ] **Step 5: Commit**

```bash
git -C ~/Projects/yocto_proj/meta-smart-home add \
    recipes-kernel/linux/linux-stm32mp/wifi.cfg \
    recipes-kernel/linux/linux-stm32mp_%.bbappend
git -C ~/Projects/yocto_proj/meta-smart-home \
    commit -m "feat: add WiFi kernel config fragment for RTL8188EU (TL-WN725N)"
```

---

### Task 2: wifi-config recipe

**Files:**
- Create: `meta-smart-home/recipes-connectivity/wifi-config/files/wpa_supplicant-wlan0.conf`
- Create: `meta-smart-home/recipes-connectivity/wifi-config/files/20-wlan.network`
- Create: `meta-smart-home/recipes-connectivity/wifi-config/wifi-config.bb`

- [ ] **Step 1: Create the wpa_supplicant credential file**

Create `meta-smart-home/recipes-connectivity/wifi-config/files/wpa_supplicant-wlan0.conf`:

```
ctrl_interface=/var/run/wpa_supplicant
ctrl_interface_group=0

network={
    ssid="Free-Wifi"
    psk=a5b3f86cfd7ab4cb434a7a1fd109cb743232aa2bfe251a81ed2070e5012b6bee
    key_mgmt=WPA-PSK
}
```

**Important:** `psk=` without quotes means pre-hashed PSK (64 hex chars). Do not add quotes around the hash — `psk="..."` with quotes means plaintext passphrase, which is a different (insecure) format.

- [ ] **Step 2: Create the systemd-networkd WLAN interface config**

Create `meta-smart-home/recipes-connectivity/wifi-config/files/20-wlan.network`:

```ini
[Match]
Name=wlan0

[Network]
DHCP=yes
```

The `20-` prefix means systemd-networkd processes this after `10-eth-static.network` (Ethernet). Ethernet config is unchanged.

- [ ] **Step 3: Create the recipe**

Create `meta-smart-home/recipes-connectivity/wifi-config/wifi-config.bb`:

```bitbake
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
    ln -sf /lib/systemd/system/wpa_supplicant@.service \
        ${D}${sysconfdir}/systemd/system/multi-user.target.wants/wpa_supplicant@wlan0.service
}

FILES:${PN} = " \
    ${sysconfdir}/wpa_supplicant/wpa_supplicant-wlan0.conf \
    ${sysconfdir}/systemd/network/20-wlan.network \
    ${sysconfdir}/systemd/system/multi-user.target.wants/wpa_supplicant@wlan0.service \
"
```

- [ ] **Step 4: Build the recipe**

```bash
bitbake wifi-config
```

Expected: build succeeds. If it fails with "nothing provides wpa-supplicant", `wpa-supplicant` will be pulled in from `meta-openembedded/meta-networking` — check that layer is active with `bitbake-layers show-layers`.

- [ ] **Step 5: Verify installed files**

```bash
find tmp/work/stm32mp1-openstlinux_weston-linux-gnueabi/wifi-config/*/image \( -type f -o -type l \) | sort
```

Expected (three entries):
```
.../image/etc/systemd/network/20-wlan.network
.../image/etc/systemd/system/multi-user.target.wants/wpa_supplicant@wlan0.service
.../image/etc/wpa_supplicant/wpa_supplicant-wlan0.conf
```

Verify the symlink resolves correctly:
```bash
readlink tmp/work/stm32mp1-openstlinux_weston-linux-gnueabi/wifi-config/*/image/etc/systemd/system/multi-user.target.wants/wpa_supplicant@wlan0.service
```
Expected: `/lib/systemd/system/wpa_supplicant@.service`

- [ ] **Step 6: Commit**

```bash
git -C ~/Projects/yocto_proj/meta-smart-home add \
    recipes-connectivity/wifi-config/
git -C ~/Projects/yocto_proj/meta-smart-home \
    commit -m "feat: add wifi-config recipe (wpa_supplicant credentials + networkd DHCP)"
```

---

### Task 3: Add WiFi packages to the image

**Files:**
- Modify: `meta-smart-home/recipes-st/images/st-image-weston.bbappend`

- [ ] **Step 1: Add wifi packages**

`meta-smart-home/recipes-st/images/st-image-weston.bbappend` currently reads:

```bitbake
CORE_IMAGE_EXTRA_INSTALL:remove = "packagegroup-st-demo"
```

Replace it with:

```bitbake
CORE_IMAGE_EXTRA_INSTALL:remove = "packagegroup-st-demo"

CORE_IMAGE_EXTRA_INSTALL:append = " \
    wpa-supplicant \
    linux-firmware-rtl8188eu \
    wifi-config \
"
```

> **Firmware package name risk:** `linux-firmware-rtl8188eu` is the expected split-package name. If the full image build in Task 4 fails with "nothing provides linux-firmware-rtl8188eu", identify the correct name:
> ```bash
> bitbake-getvar -r linux-firmware PACKAGES | tr ' ' '\n' | grep -i rtl
> ```
> Use the package name that covers `rtlwifi/rtl8188eufw.bin`. If no matching split package exists, substitute `linux-firmware` (the full firmware package — larger image but guaranteed to work).

- [ ] **Step 2: Verify the variable resolves**

```bash
bitbake-getvar -r st-image-weston CORE_IMAGE_EXTRA_INSTALL
```

Expected: output contains `wpa-supplicant`, `linux-firmware-rtl8188eu`, and `wifi-config`.

- [ ] **Step 3: Commit**

```bash
git -C ~/Projects/yocto_proj/meta-smart-home add \
    recipes-st/images/st-image-weston.bbappend
git -C ~/Projects/yocto_proj/meta-smart-home \
    commit -m "feat: add WiFi packages to st-image-weston"
```

---

### Task 4: Full image build and on-target verification

- [ ] **Step 1: Build the full image**

```bash
bitbake st-image-weston 2>&1 | tee /tmp/image-build.log
```

Expected: build completes without ERROR lines. This takes significant time if the rootfs hasn't been built recently. Common issues:
- `linux-firmware-rtl8188eu` not found → apply the fallback from Task 3 Step 1
- `wifi-config` do_install error about the symlink → verify the `ln -sf` path in the recipe; the source must be an absolute path

- [ ] **Step 2: Flash the SD card**

```bash
cd tmp/deploy/images/stm32mp1/
# Identify your SD card device first:
lsblk
# Then flash (replace sdX with your device — e.g. sdb, NOT your system disk):
sudo bmaptool copy st-image-weston-stm32mp1.wic.bz2 /dev/sdX
```

- [ ] **Step 3: Boot the board and open serial console**

Ensure HDMI cable is connected before powering on (Weston exits immediately with no display). Insert SD card, connect USB serial (CN11 micro-USB), power on, then:

```bash
picocom -b 115200 /dev/ttyACM0
```

Wait for the login prompt (boot takes ~30 seconds).

- [ ] **Step 4: Verify WiFi on target**

Run these checks on the target over the serial console:

```bash
# 1. USB adapter detected — wlan0 interface exists
ip link show wlan0
# Expected: line starting with "2: wlan0:" with state UP or DORMANT

# 2. wpa_supplicant authenticated successfully
systemctl status wpa_supplicant@wlan0.service
# Expected: "active (running)" and the journal shows:
#   wpa_supplicant: wlan0: CTRL-EVENT-CONNECTED

# 3. DHCP address assigned by systemd-networkd
ip addr show wlan0
# Expected: line containing "inet <IP>/24 brd ... scope global dynamic wlan0"

# 4. Internet reachability
ping -c 3 8.8.8.8
# Expected: 3 packets transmitted, 3 received, 0% packet loss
```

- [ ] **Step 5: If wlan0 does not appear — v1 dongle fallback**

If `ip link show wlan0` shows nothing and `dmesg | grep -i rtl` shows an unrecognised USB ID (e.g. `0bda:8172` instead of `0bda:8179`), the dongle is hardware v1 (RTL8188SU). Add this line to `wifi.cfg`:

```ini
CONFIG_RTL8192SU=y
```

Then rebuild the kernel and image:
```bash
bitbake -c cleansstate linux-stm32mp && bitbake st-image-weston
```

Flash and re-test.

- [ ] **Step 6: If wpa_supplicant fails to authenticate**

```bash
journalctl -u wpa_supplicant@wlan0.service --no-pager | tail -30
```

Common causes:
- `nl80211: Could not set interface 'wlan0' UP` → driver not loaded yet at service start; add `After=sys-subsystem-net-devices-wlan0.device` to the unit via a drop-in
- `CTRL-EVENT-SSID-NOT-FOUND` → double-check the SSID spelling in the conf file (`wpa_supplicant-wlan0.conf` on the target at `/etc/wpa_supplicant/`)
- `WPA: 4-Way Handshake failed` → wrong PSK; regenerate with `wpa_passphrase "Free-Wifi" "<password>"` and update the conf, then restart: `systemctl restart wpa_supplicant@wlan0.service`
