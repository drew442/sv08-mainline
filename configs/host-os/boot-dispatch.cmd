# Integration template: the board port must set sv08_mmcdev to its identified
# boot device. This script does not infer an eMMC device number.
if test -z "${sv08_mmcdev}"; then
    echo "SV08: boot device not identified; use recovery console"
    exit
fi
bootmeth order rauc
bootflow scan -b
# A successful Linux boot never returns. Do not reset exhausted counters.
if test "${BOOT_A_LEFT}" = "0" && test "${BOOT_B_LEFT}" = "0"; then
    if load mmc ${sv08_mmcdev}:5 ${scriptaddr} recovery.scr; then
        source ${scriptaddr}
    fi
    echo "SV08: recovery unavailable; restore using the USB eMMC reader"
    exit
fi
# An unsuccessful bounded trial consumes its saved counter before retrying.
reset
