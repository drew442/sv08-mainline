# Called by upstream RAUC bootmeth, which supplies devtype/devnum,
# distro_bootpart/distro_rootpart and raucargs. Addresses are board-port inputs.
if part uuid ${devtype} ${devnum}:${distro_rootpart} sv08_rootuuid; then
    setenv bootargs "root=PARTUUID=${sv08_rootuuid} rootwait ro panic=10 ${raucargs} ${sv08_consoleargs}"
    if load ${devtype} ${devnum}:${distro_bootpart} ${kernel_addr_r} Image; then
        if load ${devtype} ${devnum}:${distro_bootpart} ${ramdisk_addr_r} initrd.img; then
            setenv sv08_initrd_size ${filesize}
            if load ${devtype} ${devnum}:${distro_bootpart} ${fdt_addr_r} dtb/sv08.dtb; then
                booti ${kernel_addr_r} ${ramdisk_addr_r}:${sv08_initrd_size} ${fdt_addr_r}
            fi
        fi
    fi
fi
exit
