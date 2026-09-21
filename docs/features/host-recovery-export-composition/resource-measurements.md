# Offline candidate resource measurements

These measurements are retained from the c408f3e candidate and are useful for
reproducibility. They are not evidence for the corrected source until a fresh
candidate is rebuilt.

| Item | Measurement |
| --- | ---: |
| Recovery image size | 536,870,912 bytes (512 MiB) |
| Allocated ext4 blocks | 297,635,840 bytes |
| ext4 block count | 131,072 |
| ext4 free blocks | 56,355 |
| ext4 inode count | 32,768 |
| ext4 free inodes | 31,045 |
| SquashFS `/usr` | 224,448,512 bytes |
| Peak QEMU RSS | 2,034,020,352 bytes (touch run) |

The source values are `build.json`, `filesystem.txt`, and `result.json` in the
retained local c408f3e candidate/result directories. The corrected candidate must
repeat these measurements and add final package/module/code delta, preparation and
export workspace, and factory-layout measurements before independent verification.
