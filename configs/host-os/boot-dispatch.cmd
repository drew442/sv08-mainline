# Integration template: the board port must set sv08_mmcdev to its identified
# boot device. This script does not infer an eMMC device number.
if test -z "${sv08_mmcdev}"; then
    echo "SV08: boot device not identified; use recovery console"
    exit
fi
# This marker belongs only in the preseeded persistent environment, NEVER in
# compiled defaults. Both corrupt copies must not silently replenish trials.
setenv sv08_env_valid 1
if test "${sv08_env_layout}" != "ab-8gb-v1"; then
    setenv sv08_env_valid 0
fi
# RAUC mark-bad removes a slot from BOOT_ORDER; an empty order means recovery.
if test "${BOOT_ORDER}" != "A B" && test "${BOOT_ORDER}" != "B A" && test "${BOOT_ORDER}" != "A" && test "${BOOT_ORDER}" != "B"; then
    setenv sv08_env_valid 0
fi
if test "${BOOT_A_LEFT}" != "0" && test "${BOOT_A_LEFT}" != "1" && test "${BOOT_A_LEFT}" != "2" && test "${BOOT_A_LEFT}" != "3"; then
    setenv sv08_env_valid 0
fi
if test "${BOOT_B_LEFT}" != "0" && test "${BOOT_B_LEFT}" != "1" && test "${BOOT_B_LEFT}" != "2" && test "${BOOT_B_LEFT}" != "3"; then
    setenv sv08_env_valid 0
fi
if test "${sv08_env_valid}" = "1"; then
    bootmeth order rauc
    bootflow scan -b
    # A successful Linux boot never returns. Do not reset exhausted counters.
    if test "${BOOT_ORDER}" = "A"; then
        if test "${BOOT_A_LEFT}" != "0"; then reset; fi
    elif test "${BOOT_ORDER}" = "B"; then
        if test "${BOOT_B_LEFT}" != "0"; then reset; fi
    elif test "${BOOT_A_LEFT}" != "0" || test "${BOOT_B_LEFT}" != "0"; then
        reset
    fi
fi
if load mmc ${sv08_mmcdev}:5 ${scriptaddr} recovery.scr; then
    source ${scriptaddr}
fi
echo "SV08: recovery unavailable; restore using the USB eMMC reader"
exit
