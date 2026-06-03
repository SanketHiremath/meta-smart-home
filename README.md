# meta-smart-home

Custom Yocto layer for the STM32MP157D-DK1 dev board, built on top of OpenSTLinux (Weston). Includes the smart home GTK3 dashboard app, WiFi driver config, and all board-specific bbappends.

## Quick start with kas

[kas](https://kas.readthedocs.io) handles cloning all layers, setting up `bblayers.conf` and `local.conf`, and dropping you into a ready-to-build environment.

### 1. Install kas

```bash
pip install kas
```

### 2. Clone this layer

```bash
git clone https://github.com/SanketHiremath/meta-smart-home.git
cd meta-smart-home
```

### 3. Build the image

```bash
kas build kas-project.yml
```

kas will automatically clone all dependency layers (poky, meta-openembedded, meta-st-stm32mp, meta-st-openstlinux), configure the build directory, and run `bitbake st-image-weston`.

### 4. Flash to SD card

Output lands in `build/tmp/deploy/images/stm32mp1/`:

```bash
sudo bmaptool copy st-image-weston-stm32mp1.wic.bz2 /dev/sdX
```

Replace `/dev/sdX` with your SD card device (check with `lsblk`).

## Manual setup (without kas)

If you prefer to manage layers manually, clone each repo listed in `kas-project.yml` under `repos:`, then source the OE environment:

```bash
. poky/oe-init-build-env build-stm32mp1
bitbake st-image-weston
```

## Layer contents

| Path | Purpose |
| ---- | ------- |
| `recipes-apps/my-gtk-app/` | Smart home GTK3 dashboard — recipe, Python source, launcher, systemd service |
| `recipes-graphics/wayland/` | `weston-init.bbappend` — removes ST panel/background, sets dark theme |
| `recipes-kernel/linux/` | WiFi kernel config fragment (RTL8188EUS via rtl8xxxu) |
| `recipes-connectivity/` | Network and BLE setup recipes |
| `conf/layer.conf` | Layer priority and compatibility declaration |

## Target: STM32MP157D-DK1

- SoC: STM32MP157D — dual Cortex-A7 @ 800 MHz + Cortex-M4
- RAM: 512 MB DDR3
- Display: requires external HDMI bridge (connect before power-on)
- Serial console: ST-LINK USB (CN11) at 115200 baud — `picocom -b 115200 /dev/ttyACM0`
