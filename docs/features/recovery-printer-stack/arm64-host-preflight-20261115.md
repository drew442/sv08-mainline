# Native ARM64 host preflight — 2026-11-15

Owner authorized SSH inspection of root@a733-host.drewnet.online to check the existing native ARM testing blocker. Existing source requirements are review-plan.md step3 and tests/recovery_restore_stack_vm.py:kvm_preflight at f79192d54e3e765095d3bd1c511e7e4d1830d70c. Current main at inspection3072fcc. Host access/capacity blocker is resolved by measured native execution capability. Full unchanged-limit validator and recovery acceptance remain to run.

## Observed host

- SSH root access succeeds with existing authentication.
- Native aarch64 Linux6.6.98-a733-diag,8logical CPUs,12153460KiB RAM total and11781968KiB available at sampling.
- QEMU7.2.22 (Debian1:7.2+dfsg-7+deb12u18+b3), Python3.11.2; /dev/kvm character device accessible to root.
- Dedicated ext4 `/run/a733-guests` has224234340352bytes free (approximately209GiB), mounted rw,nosuid,nodev,noexec. Root filesystem has3.5GiB free; /tmp is64MiB tmpfs. Assign guest images and large scratch explicitly to the dedicated filesystem. Its noexec/nodev flags constrain unpacked host executables/chroots, while VM disk files are data inputs.
- Private mount/network/PID namespaces work. A short unshare --mount --net --pid --fork --mount-proc --propagation private probe enabled loopback only inside the temporary namespace and exited cleanly. losetup -f returns /dev/loop0.
- Installed tools include qemu-img, unshare/nsenter, ip, losetup, curl, OpenSSL, SSH, tar/gzip, mount/umount, truncate, sha256sum, mkfs.ext4/e2fsck/debugfs and Python core modules.
- mksquashfs, unsquashfs, zstd, Node and Chromium are absent from PATH. Full-run preparation must arrange image building/browser execution using existing build hosts or provision the required runner tools. This check installed nothing.

## Actual native accelerator check

Launched this diskless paused process with no guest network:

```
qemu-system-aarch64 -machine virt,gic-version=host -accel kvm -cpu host -smp 2 -m 1024 -S -nodefaults -display none -nic none -qmp stdio
```

QMP greeting identified QEMU7.2.22. After qmp_capabilities, query-kvm returned `{"enabled":true,"present":true}`. query-status returned prelaunch/running:false. The two-vCPU/1024MiB profile initialized exactly as required and the active accelerator was observed through the older supported QMP query. QMP quit returned normally, process exit0 and stopped confirmed (probe PID28092). No fallback was selected.

This establishes the previously missing ARM64/KVM host prerequisite. No guest operating system or production Klipper validator ran in this preflight. Its8CPU-second/256MiB/ten-second gates remain unchanged, and their result on native KVM is still unmeasured. The existing full source/export/restore/activation/reboots/rollback/authenticated-browser/TLS checks remain the completion criteria for recovery qualification.

Only bounded capability probes were run, without image allocation or host package/configuration changes. Temporary namespace and QEMU processes exited. The native recovery goal was not resumed or replaced by this host inspection. The next useful execution is the existing isolated unchanged-limit native validator probe, followed by the full journey if it passes.
