# Yocto Project Beginner's Guide

A practical walkthrough of this STM32MP157D-DK1 build system — from "what is Yocto?" to understanding every file in this codebase.

---

## Table of Contents

1. [What is Yocto?](#1-what-is-yocto)
2. [How This Project is Organised](#2-how-this-project-is-organised)
3. [The Build Configuration — `local.conf`](#3-the-build-configuration--localconf)
4. [The Layer List — `bblayers.conf`](#4-the-layer-list--bblayersconf)
5. [What is a Layer?](#5-what-is-a-layer)
6. [The Custom Layer — `meta-smart-home`](#6-the-custom-layer--meta-smart-home)
7. [What is a Recipe?](#7-what-is-a-recipe)
8. [The Custom App Recipe — `my-gtk-app.bb`](#8-the-custom-app-recipe--my-gtk-appbb)
9. [What is a bbappend?](#9-what-is-a-bbappend)
10. [Weston Customisation — `weston-init.bbappend`](#10-weston-customisation--weston-initbbappend)
11. [How the App Launches at Boot](#11-how-the-app-launches-at-boot)
12. [The Full Boot Sequence](#12-the-full-boot-sequence)
13. [On-Target Debugging](#13-on-target-debugging)
14. [Making a Change End-to-End](#14-making-a-change-end-to-end)
15. [Hosting on GitHub](#15-hosting-on-github)
16. [Adding Hardware Support — Kernel Config Fragments](#16-adding-hardware-support--kernel-config-fragments)
17. [Dynamic UI Scaling](#17-dynamic-ui-scaling)
18. [Shipping Static Assets — Icons and Images](#18-shipping-static-assets--icons-and-images)
19. [Build Commands Reference](#19-build-commands-reference)

---

## 1. What is Yocto?

Yocto is a build system that creates a **custom Linux operating system image** for embedded hardware. Unlike installing an OS from a pre-made ISO, Yocto compiles everything — the Linux kernel, bootloader, C library, device drivers, and every application — from source, tailored exactly to your hardware.

### Why use it?

| Approach | Use case |
|----------|----------|
| Raspberry Pi OS / Ubuntu | General-purpose, lots of built-in tools, larger footprint |
| Buildroot | Minimal, simpler, less flexible |
| **Yocto** | Production embedded Linux, full control, reproducible, scalable |

Yocto produces a binary image you flash to an SD card. The board boots it directly.

### Key vocabulary

| Term | Meaning |
|------|---------|
| **BitBake** | The task engine at the heart of Yocto — it reads recipes and runs build tasks |
| **Recipe (`.bb`)** | Instructions for building one software package |
| **Layer** | A collection of recipes, grouped by purpose |
| **Image** | The final SD card image — the sum of all selected packages |
| **bbappend** | A file that modifies an existing recipe without touching the original |
| **sstate-cache** | A shared build cache that avoids recompiling unchanged components |
| **MACHINE** | The target hardware identity |
| **DISTRO** | The OS distribution configuration (init system, feature flags, etc.) |

---

## 2. How This Project is Organised

```
yocto_proj/
├── poky/                    ← Core Yocto/OE-Core + BitBake engine
├── meta-openembedded/       ← Extended recipe collection (Python, GNOME, networking…)
├── meta-st-stm32mp/         ← STM32MP1 board support package (BSP) — do not edit
├── meta-st-openstlinux/     ← ST's OpenSTLinux distribution + Weston image — do not edit
├── meta-qt5/                ← Qt5 layer (present but not used by this image)
├── meta-smart-home/         ← OUR custom layer — all project code lives here
└── build-stm32mp1/          ← All build output lives here
    └── conf/
        ├── local.conf       ← YOUR settings (machine, distro, extra packages)
        └── bblayers.conf    ← Which layers are active
```

**The rule of thumb:** never edit files inside `poky/` or the official ST layers (`meta-st-*`). All customisation goes into either `build-stm32mp1/conf/` (settings) or your own custom layer (new/modified recipes).

**Why a separate custom layer?** All our application code and Weston tweaks live in `meta-smart-home/`. This keeps our work completely isolated from ST's official layers, making it easy to update the ST layers independently and simple to publish just our code to GitHub.

---

## 3. The Build Configuration — `local.conf`

`build-stm32mp1/conf/local.conf` is the first file BitBake reads. Think of it as the "project settings" file.

```bash
# What hardware are we targeting?
MACHINE = "stm32mp1"

# What OS distribution do we want? (defines init system, feature flags, etc.)
DISTRO = "openstlinux-weston"

# How many CPU cores and parallel jobs to use during compilation
BB_NUMBER_THREADS = "4"
PARALLEL_MAKE = "-j4"

# The image format — WIC creates a partitioned SD card image
IMAGE_FSTYPES = "wic.bz2 wic.bmap ext4"

# Accept ST's EULA automatically (required to use their BSP)
ACCEPT_EULA_stm32mp1 = "1"

# Extra packages to include in the image beyond the base image
IMAGE_INSTALL:append = " python3 my-gtk-app"

# Remove the ST splash screen to avoid a 90-second DRM wait at boot
DISTRO_FEATURES:remove = "splashscreen"
```

### Why does `DISTRO_FEATURES:remove = "splashscreen"` matter?

The ST OpenSTLinux image normally shows a splash screen (`psplash-drm`) while the system boots. That splash screen waits up to 90 seconds for the GPU (`/dev/dri/card0`) to be ready. In development this is annoying — removing it lets the system boot straight to Weston.

### The `:append` and `:remove` syntax

These are Yocto **variable operators**:

| Syntax | Meaning |
|--------|---------|
| `VAR = "value"` | Set the variable |
| `VAR:append = " extra"` | Add to the end (note the leading space) |
| `VAR:remove = "thing"` | Remove a word from the list |
| `VAR:prepend = "first "` | Add to the beginning |

---

## 4. The Layer List — `bblayers.conf`

`build-stm32mp1/conf/bblayers.conf` tells BitBake which layers to search for recipes.

```bash
BBLAYERS = " \
  /home/sanky/Projects/yocto_proj/poky/meta \
  /home/sanky/Projects/yocto_proj/poky/meta-poky \
  /home/sanky/Projects/yocto_proj/poky/meta-yocto-bsp \
  /home/sanky/Projects/yocto_proj/meta-openembedded/meta-oe \
  /home/sanky/Projects/yocto_proj/meta-openembedded/meta-python \
  /home/sanky/Projects/yocto_proj/meta-openembedded/meta-gnome \
  /home/sanky/Projects/yocto_proj/meta-openembedded/meta-networking \
  /home/sanky/Projects/yocto_proj/meta-openembedded/meta-webserver \
  /home/sanky/Projects/yocto_proj/meta-st-stm32mp \
  /home/sanky/Projects/yocto_proj/meta-st-openstlinux \
  /home/sanky/Projects/yocto_proj/meta-smart-home \
"
```

When you run `bitbake my-gtk-app`, BitBake searches every layer in this list for a recipe named `my-gtk-app`. The order matters — layers listed later can override earlier ones. `meta-smart-home` is listed last so its bbappends take priority over any matching recipe in the ST layers.

---

## 5. What is a Layer?

A layer is a directory with a specific structure:

```
meta-my-layer/
├── conf/
│   └── layer.conf          ← Declares the layer's name and priority
└── recipes-*/
    └── my-package/
        ├── my-package.bb   ← The recipe
        └── files/          ← Source files the recipe uses
```

Each layer has a **priority** (set in `layer.conf`). When two layers both provide a recipe for the same package, the higher-priority layer wins.

### Layers in this project

| Layer | What it provides |
|-------|-----------------|
| `poky/meta` | The OE-Core base: busybox, glibc, bash, the kernel framework |
| `meta-openembedded/meta-oe` | Hundreds of extra packages (databases, tools, utilities) |
| `meta-openembedded/meta-python` | Python packages and modules |
| `meta-openembedded/meta-gnome` | GTK3 and GNOME libraries |
| `meta-st-stm32mp` | STM32MP1 hardware support: kernel config, device trees, GPU drivers |
| `meta-st-openstlinux` | ST's distribution: Weston config, `weston-init`, `st-image-weston` |
| **`meta-smart-home`** | **Our code: GTK3 app recipe + Weston customisation** |

---

## 6. The Custom Layer — `meta-smart-home`

This is the only layer we own and the only one that should ever be edited.

### Directory structure

```
meta-smart-home/
├── conf/
│   └── layer.conf
├── icons/                              ← Master SVG source icons
│   ├── home.svg
│   ├── energy.svg
│   ├── weather.svg
│   ├── alert.svg
│   ├── setting.svg
│   └── png/                            ← Pre-converted PNGs (committed to git)
│       ├── home.png
│       ├── energy.png
│       ├── weather.png
│       ├── alert.png
│       └── setting.png
├── recipes-apps/
│   └── my-gtk-app/
│       ├── my-gtk-app.bb               ← App recipe
│       └── files/
│           ├── smart.py                ← GTK3 dashboard app
│           ├── launch-my-gtk-app.sh    ← Wayland environment wrapper
│           └── my-gtk-app.service      ← systemd unit
├── recipes-graphics/
│   └── wayland/
│       └── weston-init.bbappend        ← Weston kiosk tweaks
└── recipes-kernel/
    └── linux/
        ├── linux-stm32mp_%.bbappend    ← Kernel fragment wiring
        └── linux-stm32mp/
            ├── bluetooth.cfg           ← BT USB driver fragment
            └── wifi.cfg                ← WiFi rtl8xxxu driver fragment
```

### `layer.conf` explained

Every layer must have a `conf/layer.conf` that registers it with BitBake:

```bash
# Add this layer's directory to BitBake's search path
BBPATH .= ":${LAYERDIR}"

# Tell BitBake where to find recipes in this layer
BBFILES += "${LAYERDIR}/recipes-*/*/*.bb \
            ${LAYERDIR}/recipes-*/*/*.bbappend"

# Register the layer under a unique collection name
BBFILE_COLLECTIONS += "smart-home"
BBFILE_PATTERN_smart-home = "^${LAYERDIR}/"

# Priority 10 — higher than meta-st-stm32mp (typically 6), so our
# bbappends win if there is ever a conflict
BBFILE_PRIORITY_smart-home = "10"

# Declare dependencies on other layers (BitBake checks these at startup)
LAYERDEPENDS_smart-home = "core st-stm32mp st-openstlinux"

# Which Yocto release this layer is compatible with
LAYERSERIES_COMPAT_smart-home = "scarthgap"
```

Key fields:

| Field | Purpose |
|-------|---------|
| `BBFILE_COLLECTIONS` | Unique internal name for this layer |
| `BBFILE_PRIORITY` | Higher number = higher precedence when two layers have the same recipe |
| `LAYERDEPENDS` | BitBake will error at startup if these layers are missing from `bblayers.conf` |
| `LAYERSERIES_COMPAT` | Documents which Yocto release this layer supports (`scarthgap` = Yocto 5.0) |

### Why isolate your code in its own layer?

| Approach | Problem |
|----------|---------|
| Edit files inside `meta-st-stm32mp/` | When ST releases an update, your changes are overwritten by `git pull` |
| Put everything in `meta-smart-home/` | ST layers update independently; your code is untouched and lives in its own git repo |

---

## 7. What is a Recipe?

A recipe (`.bb` file) tells BitBake how to take source code and produce an installable package. Every recipe follows the same lifecycle:

```
fetch → unpack → patch → configure → compile → install → package
```

Each step is a **task** (prefixed `do_`). BitBake runs them in order, caching results in `sstate-cache` so unchanged tasks are skipped on subsequent builds.

### A minimal recipe

```bitbake
SUMMARY = "My hello-world program"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=..."

# Where to fetch the source from
SRC_URI = "https://example.com/hello-1.0.tar.gz"

# How to install the built files into the package staging area
do_install() {
    install -d ${D}${bindir}
    install -m 0755 hello ${D}${bindir}/hello
}
```

### Key variables

| Variable | Meaning |
|----------|---------|
| `${D}` | The staging directory — files go here during `do_install`, then get packaged |
| `${bindir}` | Resolves to `/usr/bin` |
| `${sysconfdir}` | Resolves to `/etc` |
| `${systemd_system_unitdir}` | Resolves to `/usr/lib/systemd/system` |
| `${WORKDIR}` | The recipe's working directory inside `tmp-glibc/work/` |
| `SRC_URI` | Where to get source files (URLs, `file://` for local files) |
| `RDEPENDS:${PN}` | Runtime dependencies — packages that must be present on the target |

---

## 8. The Custom App Recipe — `my-gtk-app.bb`

This is the recipe for our GTK3 dashboard. Let's read it section by section.

```bitbake
SUMMARY = "Smart Home GTK3 Dashboard"
PR = "r17"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
```

- `PR` is the **package revision**. Bump it (r1 → r2 → r3…) whenever you change the recipe metadata without changing the source files. This forces Yocto to re-package even when source hashes haven't changed.

### FILESEXTRAPATHS — reaching files outside `files/`

```bitbake
FILESEXTRAPATHS:prepend := "${THISDIR}/../../icons/png:"
```

By default, `file://` entries in `SRC_URI` are only searched in the recipe's own `files/` directory. `FILESEXTRAPATHS:prepend` adds extra directories to that search path.

`${THISDIR}` is the absolute path to the directory containing the recipe (`recipes-apps/my-gtk-app/`). Going up two levels (`../../`) reaches the layer root (`meta-smart-home/`), then `icons/png` points to our pre-converted PNG assets.

**The `:=` assignment** (immediate expansion) is required here because `${THISDIR}` must be evaluated right when the recipe is parsed, not deferred. Using `=` (lazy) would cause BitBake to expand `${THISDIR}` later when it might point somewhere unexpected.

### SRC_URI — what gets fetched

```bitbake
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
```

`file://` means "look in the search path for this filename". `smart.py`, `launch-my-gtk-app.sh`, and `my-gtk-app.service` are found in `files/`. The `.png` files are found in `icons/png/` (added above by `FILESEXTRAPATHS`).

### Installing everything

```bitbake
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
```

`install -d` creates a directory. `install -m 0755` copies with execute permissions (scripts/binaries). `install -m 0644` copies with read-only permissions (data files like PNGs and the service unit).

```bitbake
FILES:${PN} = " \
    /opt/my-gtk-app \
    ${systemd_system_unitdir}/my-gtk-app.service \
"
```

`/opt/my-gtk-app` covers the entire directory tree recursively, including the `icons/` subdirectory.

### The launcher script — `launch-my-gtk-app.sh`

```sh
#!/bin/sh
WESTON_UID=$(id -u weston)
export XDG_RUNTIME_DIR=/run/user/$WESTON_UID
export WAYLAND_DISPLAY=wayland-0
export GDK_BACKEND=wayland

i=0
while [ $i -lt 30 ]; do
    [ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ] && break
    sleep 1
    i=$((i + 1))
done

exec /usr/bin/python3 /opt/my-gtk-app/smart.py --kiosk
```

The `--kiosk` flag tells `smart.py` to run fullscreen with no window decorations. GTK3 apps on Wayland need three environment variables to connect to the compositor:

| Variable | Value | Meaning |
|----------|-------|---------|
| `XDG_RUNTIME_DIR` | `/run/user/1000` | Where Weston's socket lives |
| `WAYLAND_DISPLAY` | `wayland-0` | The socket filename |
| `GDK_BACKEND` | `wayland` | Forces GTK to use Wayland, not X11 |

The wait loop is essential: systemd starts our service immediately after `weston-graphical-session.service` reports success, but Weston itself may still be initialising. Without the wait, the app would fail to connect to the compositor and exit.

**A critical note about shell scripts in Yocto:** always use `#!/bin/sh` and POSIX sh syntax. `/bin/sh` on embedded Linux is usually `dash`, not `bash`. The `source` command is bash-only — use `.` instead.

### The systemd service — `my-gtk-app.service`

```ini
[Unit]
Description=Smart Home GTK3 Dashboard
After=weston-graphical-session.service
Requires=weston-graphical-session.service

[Service]
Type=simple
User=weston
Group=weston
ExecStart=/opt/my-gtk-app/launch-my-gtk-app.sh
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

- `After=` + `Requires=` together mean: "don't start until `weston-graphical-session.service` is up, and if it stops, stop us too."
- `User=weston` runs the process as the `weston` user, who owns the Wayland socket.
- `Restart=on-failure` with `RestartSec=5` means if the app crashes, systemd waits 5 seconds and tries again automatically. This also means you can edit `smart.py` directly on the target and the service will pick it up on the next restart cycle.
- `StandardOutput=journal` captures all `print()` output from the Python app — visible via `journalctl -u my-gtk-app.service`.

---

## 9. What is a bbappend?

A `.bbappend` file **extends** an existing recipe from another layer without modifying the original. This is how you customise upstream packages while keeping your changes separate and upgradeable.

The filename must match the recipe being modified:

```
weston-init.bbappend   →   modifies weston-init_%.bb  (the % is a wildcard)
```

Inside a bbappend you can:
- Add to `SRC_URI` to include extra files
- Append to `do_install` to run extra install steps
- Override any variable from the original recipe

---

## 10. Weston Customisation — `weston-init.bbappend`

```bitbake
do_install:append() {
    sed -i 's/^panel-position=.*/panel-position=none/' \
        ${D}${sysconfdir}/xdg/weston/weston.ini
    sed -i '/^background-image=/d' \
        ${D}${sysconfdir}/xdg/weston/weston.ini
    sed -i 's/^background-color=.*/background-color=0xff0d1117/' \
        ${D}${sysconfdir}/xdg/weston/weston.ini
}
```

The `:append` suffix on `do_install` means "run this code **after** the original `do_install` finishes". We use `sed` to patch `weston.ini` in the staging directory before it gets packaged.

The three changes:
1. **Remove the panel** — hides ST's launcher bar for a kiosk look
2. **Remove the background image** — no ST wallpaper
3. **Set a dark background colour** — matches the GTK3 app's `#0d1117` theme

---

## 11. How the App Launches at Boot

There are two launch mechanisms active in this image:

### Mechanism 1 — systemd service (primary)

`my-gtk-app.service` is a system service that starts after `weston-graphical-session.service`. systemd manages its lifecycle: starts it, restarts it on failure, logs its output to the journal.

### Mechanism 2 — weston-start-at-startup (fallback)

The `weston-start` script (from `meta-st-openstlinux`) scans `/usr/share/weston-start-at-startup/` at startup and runs every script it finds there with a 5-second delay.

**Important:** `/usr/local/weston-start-at-startup/` also exists but is on a **separate partition** (`/usr/local` is its own ext4 partition in the WIC image layout). Files installed there at build time are hidden at runtime by the mounted partition. Never install app files under `/usr/local/` in recipes.

---

## 12. The Full Boot Sequence

Understanding the complete startup chain helps diagnose problems:

```
Power on
  └── TF-A BL2 (Trusted Firmware-A, first stage bootloader)
        └── OP-TEE OS (Trusted Execution Environment)
              └── U-Boot (second stage bootloader)
                    └── extlinux → Linux kernel
                          └── systemd (PID 1)
                                ├── systemd-logind
                                ├── seatd-weston.service  (seat management)
                                └── weston-graphical-session.service
                                      ├── ExecStartPre: systemd-graphical-weston-session.sh
                                      │     └── Starts pipewire/pulseaudio as weston user services
                                      └── ExecStart: systemctl --user start weston.service
                                            └── weston-start (as weston user)
                                                  ├── Runs /usr/share/weston-start-at-startup/* (5s delay)
                                                  └── exec /usr/bin/weston
                                                        └── Wayland compositor ready
                                                              └── my-gtk-app.service starts
                                                                    └── launch-my-gtk-app.sh
                                                                          └── python3 smart.py --kiosk
```

### Wayland socket path explained

```
weston.socket  (systemd user socket unit)
  ListenStream = %t/wayland-0
               = /run/user/<weston-uid>/wayland-0
```

`%t` in a user socket unit expands to the user's runtime directory. The socket file is created at `/run/user/1000/wayland-0` (assuming weston's UID is 1000). This is what `launch-my-gtk-app.sh` polls for before starting the app.

### A common trap: `weston.service` sets `XDG_RUNTIME_DIR=/home/weston`

The weston compositor's own service unit sets `XDG_RUNTIME_DIR=/home/weston` for internal use. Client applications must **not** use this value — they must use `/run/user/<uid>` where the Wayland socket actually is. This is why `launch-my-gtk-app.sh` computes its own value with `id -u weston` rather than inheriting the environment.

---

## 13. On-Target Debugging

Connect via serial console (ST-LINK USB, 115200 baud):

```bash
picocom -b 115200 /dev/ttyACM0
```

### Essential diagnostic commands

```bash
# Is Weston running? (should be active/running)
systemctl status weston-graphical-session.service

# Why did the app fail? (most useful command)
journalctl -u my-gtk-app.service --no-pager

# See weather fetch errors and icon load failures printed by the app
journalctl -u my-gtk-app.service --no-pager | grep -E "weather|icons|screen"

# Does the Wayland socket exist?
ls /run/user/$(id -u weston)/wayland-0

# What did Weston log? (look for "disconnected" if screen is blank)
cat /home/weston/weston.log

# Check network reachability from the board
ping -c 3 8.8.8.8
nslookup api.open-meteo.com

# Run the app manually to see errors directly
WESTON_UID=$(id -u weston)
su weston -s /bin/sh -c \
  "XDG_RUNTIME_DIR=/run/user/$WESTON_UID WAYLAND_DISPLAY=wayland-0 \
   GDK_BACKEND=wayland python3 /opt/my-gtk-app/smart.py" 2>&1
```

### The most common causes of a blank screen

| Symptom in log | Cause | Fix |
|----------------|-------|-----|
| `connector XX is disconnected` | HDMI not plugged in | Connect HDMI **before** powering on |
| `SyntaxError` in journal | Python script has a syntax error | `python3 -m py_compile smart.py` on host first |
| `Failed to connect to bus` | Weston user manager not running | Check `weston-graphical-session.service` status |
| Service crash-loops | App exits non-zero | Check `journalctl` for the actual error |
| `[weather] fetch error: ...` | Network/DNS/SSL issue | Check `ping 8.8.8.8` and `nslookup` from board |
| `[icons] failed to load ...` | PNG missing from `/opt/my-gtk-app/icons/` | SCP the icons directory to the board |

### Quick fix without reflashing

Edit the Python script directly on the target — the `Restart=on-failure` service picks up changes on the next restart:

```bash
vi /opt/my-gtk-app/smart.py
systemctl restart my-gtk-app.service
```

---

## 14. Making a Change End-to-End

Here is the complete workflow for modifying the GTK3 app.

### Step 1 — Edit the Python script on the host

```bash
# Edit
nano meta-smart-home/recipes-apps/my-gtk-app/files/smart.py

# Syntax-check before wasting build time
python3 -m py_compile meta-smart-home/recipes-apps/my-gtk-app/files/smart.py && echo OK
```

### Step 2 — Bump PR in the recipe

Open `meta-smart-home/recipes-apps/my-gtk-app/my-gtk-app.bb` and increment `PR`:

```bitbake
PR = "r18"   # was r17
```

This forces Yocto to re-package the app even if the file hashes look the same to the sstate cache.

### Step 3 — Rebuild

```bash
# Source the build environment (required every new shell session)
. ./poky/oe-init-build-env build-stm32mp1

# Clean the package and rebuild
bitbake -c cleansstate my-gtk-app && bitbake my-gtk-app
```

`cleansstate` removes the sstate cache entry for the recipe, guaranteeing a fresh build.

### Step 4 — Rebuild the full image

```bash
bitbake st-image-weston
```

This reuses everything from cache except the changed package.

### Step 5 — Flash and test

```bash
cd build-stm32mp1/tmp/deploy/images/stm32mp1/
sudo bmaptool copy st-image-weston-stm32mp1.wic.bz2 /dev/sdX
```

`bmaptool` is much faster than `dd` — it skips empty blocks using the `.bmap` metadata file.

### Faster iteration: SCP instead of reflashing

If the board is on the same network, copy just the changed file and restart the service:

```bash
# The -O flag is required — modern OpenSSH uses SFTP by default,
# but the board runs Dropbear which doesn't have an SFTP subsystem.
# Without -O the transfer hangs silently.
scp -O meta-smart-home/recipes-apps/my-gtk-app/files/smart.py \
    root@<board-ip>:/opt/my-gtk-app/smart.py

# If you also changed icons
ssh root@<board-ip> "mkdir -p /opt/my-gtk-app/icons"
scp -O meta-smart-home/icons/png/*.png root@<board-ip>:/opt/my-gtk-app/icons/

# Restart the service to pick up changes
ssh root@<board-ip> "systemctl restart my-gtk-app.service"
```

**Why `-O`?** OpenSSH 9.x changed `scp` to use the SFTP protocol by default. Dropbear (used on embedded Linux boards) doesn't implement an SFTP subsystem, so the transfer hangs waiting for an SFTP handshake that never arrives. The `-O` flag restores the legacy SCP protocol that Dropbear understands.

---

## 15. Hosting on GitHub

You cannot and should not push the entire `yocto_proj/` directory to GitHub — most of it is third-party code that already has its own upstream repositories. The only directory you own is `meta-smart-home/`.

### What to push

| Path | Push? | Reason |
|------|-------|--------|
| `meta-smart-home/` | ✅ Yes | Entirely your code |
| `CLAUDE.md`, `YOCTO_BEGINNER_GUIDE.md` | ✅ Yes | Your documentation |
| `poky/`, `meta-openembedded/`, `meta-st-*/` | ❌ No | Already on GitHub upstream |
| `build-stm32mp1/` | ❌ No | Generated output — gigabytes of build artefacts |

### This project's repository

The custom layer is hosted at:
```
https://github.com/SanketHiremath/meta-smart-home
```

All changes go in here. The `kas-project.yml` at the root of that repo pins every external layer by exact commit hash so anyone can reproduce the build.

### Anyone can clone and build with two commands

```bash
git clone https://github.com/SanketHiremath/meta-smart-home.git
cd meta-smart-home
kas build kas-project.yml
```

`kas` clones every pinned layer, generates `bblayers.conf` and `local.conf` automatically, then runs BitBake.

### `kas-project.yml` — what it contains

```yaml
header:
  version: 14

machine: stm32mp1
distro: openstlinux-weston
target: st-image-weston

repos:
  poky:
    url: https://git.yoctoproject.org/poky
    branch: scarthgap
    commit: 7d50718f90c51fb7f650c9db59b28c6e0194e5d2
    layers:
      meta:
      meta-poky:
      meta-yocto-bsp:

  meta-openembedded:
    url: https://github.com/openembedded/meta-openembedded
    branch: scarthgap
    commit: 4d3e2639dec542b58708244662d5ce36810fc510
    layers:
      meta-oe:
      meta-python:
      meta-gnome:
      meta-multimedia:
      meta-networking:
      meta-webserver:

  meta-st-stm32mp:
    url: https://github.com/STMicroelectronics/meta-st-stm32mp.git
    branch: scarthgap
    commit: 701c0ddb5afa29842c4146773d5303a1f192ff19

  meta-st-openstlinux:
    url: https://github.com/STMicroelectronics/meta-st-openstlinux.git
    branch: scarthgap
    commit: 993e43adedbfe95dca8e93a64ec091a83a604633

  # Our custom layer — pinned to current HEAD
  meta-smart-home:
    url: https://github.com/SanketHiremath/meta-smart-home.git
    branch: main
    commit: <update this whenever you push new commits>
    layers:
      meta-smart-home:

local_conf_header:
  main: |
    ACCEPT_EULA_stm32mp1 = "1"
  parallelism: |
    BB_NUMBER_THREADS = "4"
    PARALLEL_MAKE = "-j4"
  image_install: |
    IMAGE_INSTALL:append = " kernel-image kernel-devicetree stm32mp-extlinux"
    IMAGE_INSTALL:append = " python3 my-gtk-app"
    IMAGE_INSTALL:append = " network-config time-server"
    IMAGE_INSTALL:append = " ble-tools"
  distro_features: |
    DISTRO_FEATURES:remove = "splashscreen"
  dev: |
    EXTRA_IMAGE_FEATURES ?= "debug-tweaks"
```

**Important:** The `commit:` field under `meta-smart-home` must be updated every time you push new commits, otherwise `kas build` will check out the old pinned version. Get the current HEAD with:

```bash
git -C meta-smart-home rev-parse HEAD
```

---

## 16. Adding Hardware Support — Kernel Config Fragments

Most Yocto tutorials focus on recipes and layers. But sometimes the feature you need isn't missing from the rootfs — it's missing from the **kernel** itself.

### The kernel is not "all features on"

Each driver is controlled by a **`CONFIG_` option**:

| Value | Meaning |
|-------|---------|
| `=y` | Built permanently into the kernel image |
| `=m` | Built as a separate `.ko` module file, loaded on demand |
| *(absent)* | Not compiled at all |

Rather than editing ST's full defconfig (fragile, gets overwritten on updates), Yocto lets you write a small **config fragment**: a plain text file containing only the options you want to add or change. During the kernel build, `merge_config.sh` overlays your fragment on top of ST's base config.

### How ST's kernel wires up fragments (the important gotcha)

**Standard `kernel-yocto`** (used by upstream poky kernels):
```bitbake
SRC_URI:append = " file://bluetooth.cfg"
# Just adding the file is enough — the class finds all .cfg files automatically
```

**ST's `inherit kernel`** (used by `linux-stm32mp`):
```bitbake
# Step 1: copy the file into a fragments/ subdirectory
SRC_URI:append = " file://bluetooth.cfg;subdir=fragments"

# Step 2: explicitly list it for merge_config.sh
KERNEL_CONFIG_FRAGMENTS:append = " ${WORKDIR}/fragments/bluetooth.cfg"
```

ST's recipe calls `merge_config.sh` only on files explicitly listed in `KERNEL_CONFIG_FRAGMENTS`. If you forget Step 2, the file sits unused in the build directory with no error — the kernel silently rebuilds with the old config.

### Bluetooth USB — `bluetooth.cfg`

```
CONFIG_BT=y                  # Core Bluetooth subsystem
CONFIG_BT_BREDR=y            # Classic Bluetooth (required by btusb)
CONFIG_BT_LE=y               # BLE (Low Energy)
CONFIG_BT_HCIBTUSB=y         # The btusb USB driver itself
CONFIG_BT_HCIBTUSB_RTL=y     # Realtek firmware-download logic inside btusb
CONFIG_CRYPTO_CMAC=y         # BLE security (pairing/encryption)
CONFIG_CRYPTO_AES=y
CONFIG_CRYPTO_ECB=y
CONFIG_CRYPTO_SHA256=y
CONFIG_FW_LOADER=y           # Allows btusb to load rtl8761bu_fw.bin at runtime
```

`CONFIG_BT_HCIBTUSB_RTL=y` is particularly important: without it, btusb loads for the device but fails because it doesn't know how to download Realtek firmware.

### WiFi USB — `wifi.cfg`

This project uses a **Realtek RTL8188EUS** USB WiFi adapter (USB ID `0bda:8179`). The ST 6.6 kernel tree does **not** include the staging driver `CONFIG_RTL8188EU` — that driver was removed upstream. The correct driver is `rtl8xxxu`, which covers this chip and is present in the ST kernel.

```
# wifi.cfg — RTL8188EUS via rtl8xxxu (USB ID 0x8179)
CONFIG_CFG80211=y
CONFIG_MAC80211=y
CONFIG_RFKILL=y

# rtl8xxxu covers RTL8188EUS. CONFIG_RTL8188EU does not exist in the ST 6.6 tree.
CONFIG_RTL8XXXU=m
```

**Why `=m` not `=y`?** The driver is built as a loadable module (`rtl8xxxu.ko`). It loads automatically when the kernel sees the USB device via udev, so there is no practical difference for a running system — but modules are faster to iterate on during development.

**Common mistake:** searching online for RTL8188EUS often leads to `CONFIG_RTL8188EU`. That option exists in some BSPs and staging trees but is absent from the ST 6.6 kernel. Adding it causes a build warning ("CONFIG_RTL8188EU not found") and the WiFi adapter stays unclaimed.

### The bbappend that wires both fragments in

`meta-smart-home/recipes-kernel/linux/linux-stm32mp_%.bbappend`:

```bitbake
FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"

SRC_URI:append = " \
    file://bluetooth.cfg;subdir=fragments \
    file://wifi.cfg;subdir=fragments \
"

KERNEL_CONFIG_FRAGMENTS:append = " \
    ${WORKDIR}/fragments/bluetooth.cfg \
    ${WORKDIR}/fragments/wifi.cfg \
"
```

### Rebuild order after changing a kernel fragment

```bash
. ./poky/oe-init-build-env build-stm32mp1

# cleansstate is required — plain clean does not invalidate the sstate cache
bitbake -c cleansstate linux-stm32mp
bitbake linux-stm32mp
bitbake st-image-weston
```

### Verifying it worked on the device

```bash
# WiFi driver loaded
dmesg | grep -i 'rtl8xxxu\|wlan'
# Should show: "rtl8xxxu 1-1.x: ... RTL8188EU" then "wlan0: renamed"

# WiFi interface is up
ip link show wlan0

# Bluetooth — driver bound and firmware loaded
dmesg | grep -i 'btusb\|hci\|rtl'
hciconfig hci0
```

---

## 17. Dynamic UI Scaling

The dashboard is designed at a **baseline resolution of 800×480** (the native display size of this devkit's closest equivalent). When run on a larger display (e.g. via HDMI at 1080p), all fonts and widget dimensions scale automatically.

### How it works

At startup, `smart.py` reads the actual monitor geometry from GDK before building any widgets:

```python
def _detect_screen():
    try:
        display = Gdk.Display.get_default()
        monitor = display.get_monitor(0)
        geo = monitor.get_geometry()
        return geo.width, geo.height
    except Exception:
        return 800, 480   # safe fallback

_SW, _SH = _detect_screen()
SCALE = min(_SW / 800, _SH / 480)
print("[smart_home] screen={}x{}  scale={:.2f}".format(_SW, _SH, SCALE))
```

`min()` is used so the UI always fits the smaller axis — nothing clips off screen on non-16:9 displays.

### The `_s()` helper

Every pixel value and font point size in the code goes through `_s()`:

```python
def _s(n):
    return max(1, round(n * SCALE))
```

Examples:
```python
PAD   = _s(6)          # grid padding: 6px at 800×480, 14px at 1920×1080
lbl("Smart Home", _s(23), bold=True)   # font scales with screen
self._hero.set_size_request(-1, _s(148))
```

### Scale factors for common resolutions

| Resolution | SCALE | Effect |
|-----------|-------|--------|
| 800×480 (baseline) | 1.00 | No change |
| 1024×600 | 1.25 | +25% on all dimensions |
| 1280×720 | 1.50 | +50% |
| 1920×1080 | 2.25 | Everything roughly doubles |

### What scales

Everything: `lbl()` font sizes, `Pango.FontDescription` strings, `PAD` (grid gap), all `set_margin_*` calls, all `set_size_request` min-height values, bottom nav font sizes and button height, `_SignalBars` widget size.

`_SignalBars` goes a step further — it draws its bars proportionally to its **allocated widget size** rather than at fixed pixel coordinates. This makes it fully resolution-independent even at unusual scale factors.

### Why `Gdk.Display` works at module init time

`_detect_screen()` is called at module level, before any widgets are created. This is safe because `launch-my-gtk-app.sh` waits for the Wayland socket to exist before executing `smart.py`. By the time the Python process starts, the compositor is up and `Gdk.Display.get_default()` can connect.

The detected resolution is printed to stdout on every boot — visible in the service journal:

```bash
journalctl -u my-gtk-app.service | grep "screen="
# [smart_home] screen=1920x1080  scale=2.25
```

---

## 18. Shipping Static Assets — Icons and Images

Recipes can package any file alongside the application code. This section documents the pattern used for the navigation bar icons.

### The asset pipeline

The icons are authored as SVGs (resolution-independent vector graphics) but shipped as pre-converted PNGs. This is because:

- `librsvg` (the GdkPixbuf SVG loader) is not installed in the default ST image
- Installing it requires a full image rebuild
- Pre-converting to PNG on the host produces identical visual output and avoids the dependency

**Conversion command** (run once on the dev machine after editing SVGs):

```bash
for svg in meta-smart-home/icons/*.svg; do
    name=$(basename "$svg" .svg)
    rsvg-convert -w 64 -h 64 "$svg" \
        -o "meta-smart-home/icons/png/${name}.png"
done
```

64×64 is chosen because the UI scales up to 2.25× on 1080p — 64px provides enough detail at that display size (`_s(28)` ≈ 63px on 1080p).

### Directory layout for assets

```
meta-smart-home/
└── icons/
    ├── home.svg          ← Edit these
    ├── energy.svg
    ├── weather.svg
    ├── alert.svg
    ├── setting.svg
    └── png/              ← Committed to git, generated from SVGs above
        ├── home.png
        ├── energy.png
        ├── weather.png
        ├── alert.png
        └── setting.png
```

### How FILESEXTRAPATHS reaches the icons

The recipe file sits at `recipes-apps/my-gtk-app/my-gtk-app.bb`. BitBake's default `file://` search path only covers `recipes-apps/my-gtk-app/files/`. To reach `icons/png/` at the layer root:

```bitbake
FILESEXTRAPATHS:prepend := "${THISDIR}/../../icons/png:"
```

`${THISDIR}` = `.../meta-smart-home/recipes-apps/my-gtk-app`
`${THISDIR}/../../` = `.../meta-smart-home/`
`${THISDIR}/../../icons/png` = `.../meta-smart-home/icons/png/`

### Loading PNGs at runtime

```python
def _nav_icon(filename, size, active):
    path = "/opt/my-gtk-app/icons/{}".format(filename)
    try:
        pb = GdkPixbuf.Pixbuf.new_from_file_at_size(path, size, size)
        return Gtk.Image.new_from_pixbuf(pb)
    except Exception as e:
        print("[icons] failed to load {}: {}".format(filename, e), flush=True)
        # Fall back to a text label so the nav bar doesn't break
        lb = Gtk.Label(label=filename.replace(".png", ""))
        ...
        return lb
```

`new_from_file_at_size` scales the PNG to exactly `size×size` pixels using bilinear interpolation. Combined with `_s(28)`, the icons scale cleanly to the detected screen resolution.

### When to re-convert PNGs

Re-run the conversion script and commit the new PNGs whenever the SVG sources change:

```bash
# After editing SVGs
for svg in meta-smart-home/icons/*.svg; do
    name=$(basename "$svg" .svg)
    rsvg-convert -w 64 -h 64 "$svg" -o "meta-smart-home/icons/png/${name}.png"
done

git -C meta-smart-home add icons/png/*.png
git -C meta-smart-home commit -m "chore: regenerate PNGs from updated SVGs"
git -C meta-smart-home push origin main
```

---

## 19. Build Commands Reference

A consolidated reference of every command used to build, inspect, and flash this project. Run all BitBake commands from inside `build-stm32mp1/` (sourcing the environment puts you there automatically).

### Environment Setup

```bash
# Required at the start of every new shell session — sets PATH and cd's into build-stm32mp1/
. ./poky/oe-init-build-env build-stm32mp1
```

### Building Images and Recipes

```bash
# Build the full OpenSTLinux image
bitbake st-image-weston

# Build only the custom GTK3 app package (faster during development)
bitbake my-gtk-app

# Build only the kernel
bitbake linux-stm32mp
```

### Cleaning and Rebuilding

```bash
# Remove sstate cache and local build output for a recipe, then rebuild
bitbake -c cleansstate my-gtk-app && bitbake my-gtk-app
bitbake -c cleansstate linux-stm32mp && bitbake linux-stm32mp
bitbake -c cleansstate weston-init && bitbake weston-init

# Clean local build directory only (does NOT clear sstate cache)
bitbake -c clean <recipe-name>
```

### Inspecting and Debugging Builds

```bash
# Print the resolved value of a variable for a given recipe
bitbake-getvar -r my-gtk-app RDEPENDS
bitbake-getvar -r my-gtk-app SRC_URI
bitbake-getvar -r my-gtk-app FILESEXTRAPATHS
bitbake-getvar -r linux-stm32mp KERNEL_CONFIG_FRAGMENTS

# Show all active layers and their priorities
bitbake-layers show-layers

# Search all layers for a recipe by name
bitbake-layers show-recipes my-gtk-app

# Print all tasks for a recipe
bitbake -c listtasks my-gtk-app

# Run BitBake with verbose output
bitbake -v my-gtk-app

# Open an interactive development shell inside a recipe's work directory
bitbake -c devshell my-gtk-app
```

### Syntax Checking Before Building

```bash
python3 -m py_compile meta-smart-home/recipes-apps/my-gtk-app/files/smart.py && echo OK
```

### Transferring Files to the Board (SCP)

```bash
# -O forces legacy SCP protocol — required for Dropbear (the SSH server on the board).
# Without -O, modern OpenSSH uses SFTP which Dropbake doesn't support and the transfer hangs.

# Transfer the app
scp -O meta-smart-home/recipes-apps/my-gtk-app/files/smart.py \
    root@<board-ip>:/opt/my-gtk-app/smart.py

# Transfer icons (create directory first if it doesn't exist)
ssh root@<board-ip> "mkdir -p /opt/my-gtk-app/icons"
scp -O meta-smart-home/icons/png/*.png root@<board-ip>:/opt/my-gtk-app/icons/

# Restart the service after any transfer
ssh root@<board-ip> "systemctl restart my-gtk-app.service"
```

### Flashing the SD Card

```bash
cd build-stm32mp1/tmp/deploy/images/stm32mp1/
sudo bmaptool copy st-image-weston-stm32mp1.wic.bz2 /dev/sdX
```

### kas — Reproduce the Build from Scratch

```bash
pip install kas
git clone https://github.com/SanketHiremath/meta-smart-home.git
cd meta-smart-home
kas build kas-project.yml
```

### Typical End-to-End Rebuild Sequences

```bash
# After changing smart.py
. ./poky/oe-init-build-env build-stm32mp1
bitbake -c cleansstate my-gtk-app && bitbake my-gtk-app
bitbake st-image-weston

# After changing weston-init.bbappend
. ./poky/oe-init-build-env build-stm32mp1
bitbake -c cleansstate weston-init && bitbake weston-init
bitbake st-image-weston

# After changing a kernel config fragment (bluetooth.cfg or wifi.cfg)
. ./poky/oe-init-build-env build-stm32mp1
bitbake -c cleansstate linux-stm32mp && bitbake linux-stm32mp
bitbake st-image-weston

# Full clean image build from scratch (takes several hours)
. ./poky/oe-init-build-env build-stm32mp1
bitbake st-image-weston
```

---

## Glossary

| Term | Definition |
|------|-----------|
| **BitBake** | The task scheduler/build engine used by Yocto |
| **Recipe (`.bb`)** | Build instructions for one software component |
| **bbappend** | A patch file for an existing recipe |
| **Layer** | A directory containing related recipes |
| **`layer.conf`** | Required file in every layer — registers it with BitBake and sets its priority |
| **`kas`** | Yocto-specific tool for pinning and cloning all layers from a single YAML config |
| **MACHINE** | Hardware target identifier |
| **DISTRO** | OS-level feature configuration |
| **sstate-cache** | Shared object cache that makes incremental builds fast |
| **WIC** | Wic Image Creator — produces partitioned SD card images |
| **DRM/KMS** | Linux kernel's display subsystem (`/dev/dri/card0`) |
| **Weston** | The Wayland compositor (display server) |
| **Wayland** | Modern Linux graphics protocol, replacing X11 |
| **XDG_RUNTIME_DIR** | Per-user directory for runtime sockets (e.g. Wayland socket) |
| **systemd user service** | A service that runs in a user's own systemd instance |
| `${D}` | Staging directory in BitBake — maps to target filesystem paths |
| `${PN}` | Package name — expands to the recipe's name |
| `${THISDIR}` | Absolute path to the directory containing the current recipe file |
| `PR` | Package revision — increment to force rebuild without source change |
| **`FILESEXTRAPATHS`** | Variable that extends BitBake's `file://` search path to directories outside `files/` |
| **Kernel config fragment** | A small `.cfg` file with only the `CONFIG_` options you want to add, merged on top of the base defconfig |
| **`KERNEL_CONFIG_FRAGMENTS`** | ST-specific variable listing fragment files for `merge_config.sh` to apply during `do_configure` |
| **`btusb`** | The Linux kernel USB Bluetooth driver — handles USB BT adapters including Realtek, Broadcom, Intel |
| **`rtl8xxxu`** | Linux kernel driver covering several Realtek USB WiFi chips including RTL8188EUS |
| **Firmware blob** | A binary file uploaded into hardware RAM at probe time (e.g. `rtl8761bu_fw.bin`); distinct from the kernel driver |
| **`cleansstate`** | BitBake task that removes both local build output and the sstate-cache entry, forcing a full rebuild |
| **`SCALE`** | Float computed at runtime as `min(screen_w/800, screen_h/480)` — used to resize all UI elements proportionally |
| **`_s(n)`** | Helper function in `smart.py` that returns `max(1, round(n * SCALE))` — apply to every pixel/point value |
| **SCP `-O` flag** | Forces legacy SCP protocol — required when the remote runs Dropbear, which has no SFTP subsystem |
