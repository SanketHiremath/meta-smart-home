# WiFi Support — TP-Link TL-WN725N (RTL8188EUS)

**Date:** 2026-05-26  
**Board:** STM32MP157D-DK1  
**Yocto release:** Scarthgap  
**Custom layer:** `meta-smart-home`

---

## Goal

Add USB WiFi support for the TP-Link TL-WN725N dongle (hardware v2/v3, Realtek RTL8188EUS chip) using the mainline `r8188eu` kernel driver. The board connects automatically to the configured network on boot. WiFi runs alongside the existing static Ethernet (`end0`) managed by `systemd-networkd`.

---

## Approach

**wpa_supplicant + systemd-networkd** — consistent with the existing Ethernet setup. No new network management daemon; `wpa_supplicant` handles WPA2 authentication and `systemd-networkd` assigns a DHCP address to `wlan0`.

Rejected alternatives:
- *NetworkManager alongside systemd-networkd* — coexistence is stable but adds ~3 MB and a new daemon for no real gain given a fixed home network.
- *NetworkManager full takeover* — would require migrating existing static Ethernet config; too disruptive.

---

## Architecture

```
RTL8188EUS chip (USB)
        │
   r8188eu driver  (CONFIG_RTL8188EU=y, kernel config fragment)
        │
   linux-firmware   (/lib/firmware/rtlwifi/rtl8188eufw.bin)
        │
   wpa_supplicant@wlan0.service
        │  reads /etc/wpa_supplicant/wpa_supplicant-wlan0.conf
        │  authenticates to WPA2 network "Free-Wifi"
        │
   systemd-networkd
        │  reads /etc/systemd/network/20-wlan.network
        │  assigns DHCP address to wlan0
        │
   existing end0 (static IP via 10-eth-static.network) — unchanged
```

---

## Files Changed / Created

| Action   | Path in `meta-smart-home`                                              |
|----------|------------------------------------------------------------------------|
| New      | `recipes-kernel/linux/linux-stm32mp/wifi.cfg`                          |
| Modified | `recipes-kernel/linux/linux-stm32mp_%.bbappend`                        |
| New      | `recipes-connectivity/wifi-config/wifi-config.bb`                      |
| New      | `recipes-connectivity/wifi-config/files/wpa_supplicant-wlan0.conf`     |
| New      | `recipes-connectivity/wifi-config/files/20-wlan.network`               |
| Modified | `recipes-st/images/st-image-weston.bbappend`                           |

---

## Detailed Spec

### 1. Kernel Config Fragment — `wifi.cfg`

Path: `recipes-kernel/linux/linux-stm32mp/wifi.cfg`

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
CONFIG_RTL8188EU=y
```

### 2. Kernel bbappend — `linux-stm32mp_%.bbappend`

Extend the existing file with one extra entry in `SRC_URI` and `KERNEL_CONFIG_FRAGMENTS`:

```bitbake
SRC_URI:append = " file://wifi.cfg;subdir=fragments"
KERNEL_CONFIG_FRAGMENTS:append = " ${WORKDIR}/fragments/wifi.cfg"
```

### 3. New Recipe — `wifi-config.bb`

Path: `recipes-connectivity/wifi-config/wifi-config.bb`

Responsibilities:
- Install `wpa_supplicant-wlan0.conf` to `/etc/wpa_supplicant/`
- Install `20-wlan.network` to `/etc/systemd/network/`
- Enable `wpa_supplicant@wlan0.service` at image build time via `SYSTEMD_SERVICE`

The recipe inherits `systemd` to use `SYSTEMD_SERVICE` for enabling the service symlink at image population time.

### 4. WPA Supplicant Config — `wpa_supplicant-wlan0.conf`

Path: `recipes-connectivity/wifi-config/files/wpa_supplicant-wlan0.conf`

```ini
ctrl_interface=/var/run/wpa_supplicant
ctrl_interface_group=0

network={
    ssid="Free-Wifi"
    psk=a5b3f86cfd7ab4cb434a7a1fd109cb743232aa2bfe251a81ed2070e5012b6bee
    key_mgmt=WPA-PSK
}
```

Credentials: SSID `Free-Wifi`. PSK is a PBKDF2-derived 256-bit hash — plaintext password is not stored anywhere in the layer or image.

File is installed mode `0600` (owner-readable only) to prevent world-readable credentials on the target.

### 5. systemd-networkd WLAN config — `20-wlan.network`

Path: `recipes-connectivity/wifi-config/files/20-wlan.network`

```ini
[Match]
Name=wlan0

[Network]
DHCP=yes
```

Picked up automatically by the already-running `systemd-networkd`. The `10-` prefix on the Ethernet config and `20-` prefix here ensure Ethernet is processed first (lexicographic order).

### 6. Image Install additions — `st-image-weston.bbappend`

Append to `CORE_IMAGE_EXTRA_INSTALL`:

| Package                    | Reason                                              |
|----------------------------|-----------------------------------------------------|
| `wpa-supplicant`           | WPA2 authentication daemon + systemd service units  |
| `linux-firmware-rtl8188eu` | Firmware blob loaded by r8188eu driver at USB probe |
| `wifi-config`              | Our recipe (wpa conf + networkd conf + svc enable)  |

> **Risk:** `linux-firmware-rtl8188eu` is the expected OE subpackage name (derived from the firmware filename). If the build fails to find it, fall back to `linux-firmware` (full package) and then identify the correct split-package name from `bitbake-getvar -r linux-firmware PACKAGES`.

---

## Boot Sequence (WiFi path)

1. Kernel loads → USB subsystem detects TL-WN725N → r8188eu driver binds → requests `rtlwifi/rtl8188eufw.bin` via `request_firmware()`
2. `wpa_supplicant@wlan0.service` starts (after `network.target`) → reads conf → authenticates to `Free-Wifi`
3. `systemd-networkd` picks up `wlan0` becoming managed → runs DHCP → assigns IP address

---

## On-Target Verification Commands

```bash
# Confirm adapter is detected by kernel
ip link show wlan0

# Check wpa_supplicant service
systemctl status wpa_supplicant@wlan0.service

# Check DHCP address assigned
ip addr show wlan0

# Check DNS/connectivity
ping -c 3 8.8.8.8
```

---

## Build Commands

```bash
# Source environment first
. ./poky/oe-init-build-env build-stm32mp1

# Rebuild kernel with new wifi.cfg fragment
bitbake -c cleansstate linux-stm32mp && bitbake linux-stm32mp

# Build new wifi-config recipe
bitbake wifi-config

# Full image rebuild (picks up all changes)
bitbake st-image-weston
```
