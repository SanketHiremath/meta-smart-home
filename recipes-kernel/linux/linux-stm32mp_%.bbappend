# =========================================================================
# linux-stm32mp bbappend — adds Bluetooth config fragment
# =========================================================================
# ST's kernel recipe (linux-stm32mp.inc) does NOT use kernel-yocto.
# It applies config fragments via its own mechanism:
#   1. SRC_URI with subdir=fragments  → lands in ${WORKDIR}/fragments/
#   2. KERNEL_CONFIG_FRAGMENTS lists the full path to each fragment
#   3. do_configure:append calls merge_config.sh on all listed fragments
#
# Our fragment file lives at:
#   meta-smart-home/recipes-kernel/linux/linux-stm32mp/bluetooth.cfg
# =========================================================================

FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"

# Step 1 — fetch the file into ${WORKDIR}/fragments/bluetooth.cfg
SRC_URI:append = " file://bluetooth.cfg;subdir=fragments"

# Step 2 — tell merge_config.sh to include it
KERNEL_CONFIG_FRAGMENTS:append = " ${WORKDIR}/fragments/bluetooth.cfg"
