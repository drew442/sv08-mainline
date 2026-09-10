# Full Linux A/B state rollback fixture

2026-09-10. Offline QEMU only; no named physical hardware combination is validated.

The three ARM64 Linux boots A → B → A passed. Each root mounted its matching boot
partition. B copied the configuration and SQLite database changes made in A after
`expect_trial`, then changed only its own state generation. Returning to A restored
A's configuration/database, retained B's failed generation for diagnosis, cleared
the pending trial and recorded the failed trial. Shared G-code files and machine
identity survived the sequence. B's trial marker remained present; this test never
confirmed health or allowed a trial to print.

## Fixture construction

`build/host-qemu-rollback-v1/` retains the scripts, root filesystems, disk and logs.
Start with the [RAUC-integrated root](host-rauc-build.md), kernel and initramfs.
Create separate disposable root copies with release IDs `0.1.0-offline.3` (A) and
`0.1.0-offline.4` (B). Keep `deployable=false` and the six explicit fixture PARTUUIDs.
Install [the guest probe](../../tests/host_qemu_rollback.py) only in those copies
as `/usr/lib/sv08/host_qemu_rollback.py`, using this temporary enabled unit:

```ini
[Unit]
Description=Disposable QEMU rollback proof
Requires=sv08-prepare.service
After=multi-user.target sv08-prepare.service
ConditionKernelCommandLine=sv08.test=rollback
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/lib/sv08/host_qemu_rollback.py --execute
StandardOutput=journal+console
StandardError=journal+console
TimeoutStartSec=180
[Install]
WantedBy=multi-user.target
```

Populate the original relocated six-partition GPT fixture with these two roots,
two FAT boot fixtures, and a freshly formatted data filesystem. The retained
`debugfs-{A,B}.cmd` and `fix-{A,B}.cmd` show the exact offline file insertions;
both roots passed `e2fsck -fn`. The final unit must include console output: the
initial fixture omitted it, so the guest powered off without the host harness
seeing its result. Data was reset and the complete sequence rerun with logging.

The ignored `run.py` invokes `qemu-system-aarch64 -machine virt -cpu cortex-a53
-smp 2 -m 1024 -nographic -no-reboot -nic none`, with the retained kernel/initrd and
one virtio block device whose serial is `SV08-QEMU-DISPOSABLE`. Kernel arguments
include `console=ttyAMA0 rootwait ro panic=10 sv08.test=rollback`, plus these pairs:

| Boot | Root PARTUUID | Slot argument |
| --- | --- | --- |
| 1 | `26c68198-9248-47af-bbd3-643f1b604ef5` | `rauc.slot=A` |
| 2 | `d8d04a9a-f51f-41b3-a474-e079efe97186` | `rauc.slot=B` |
| 3 | `26c68198-9248-47af-bbd3-643f1b604ef5` | `rauc.slot=A` |

The probe refuses a non-QEMU machine, an unexpected disk serial, or a deployable
manifest. It checks the actual root/boot mounts and absence of failed services,
reports to serial and powers off the disposable VM. It is not installed by the
normal integration stage. Public results are in
[the evidence record](host-rollback-20260910.json); full logs are
`build/host-qemu-rollback-v1/boot-{0,1,2}.log`.

## What remains separate

The host harness explicitly chooses A/B/A; no automatic bootloader selection,
RAUC installation, health confirmation, live print admission or power interruption
occurs in this test. Those are separate integration gates. Upstream U-Boot/RAUC
selection has its own [environment fixture](host-environment-build.md), and signed
installation its own RAUC fixture. Combining them into the board-bootable release
and validating failure handling remains on the [task list](host-os-tasks.md).
