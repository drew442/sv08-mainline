# New host: complete application payload build

Date: 2026-09-09. Scope: offline Debian trixie ARM64 userspace, test-sv08-01
candidate. PCB revisions remain unknown. No printer connection or hardware write.
Application payloads are separate from service activation and boot integration.

## Source and dependency inputs

| Application | Source | Packaging |
| --- | --- | --- |
| Klipper | `f0892d82b0f1c1228454f09eb508eddde2250f4b` | [Prior matched host/MCU package](host-apps-build.md) |
| Moonraker | `985c1d0bbeb90bc057d34a232c9dc3b05e0c6c8d` | Runtime source and 33 locked Python dependencies |
| Mainsail | `32f99e1cf97640b23a52829dfa3a0aceee11d382` | Upstream Vite build from its npm lock, static assets only |
| KlipperScreen | `3791fdf749df20c2a32fc43818749aa9f1754a9f` | Runtime source/translations and 13 locked Python dependencies, Debian PyGObject |

KlipperScreen is a new direct submodule because HDMI touch is required. Its
source pin and gitlink are recorded together in [upstream-lock.json](../../upstream-lock.json).
Downloaded source is not tested hardware compatibility. No bundled installer was
run and no upstream checkout was modified. Two documented patches are applied only
to build archives, as described below. Project packages fill the gap between
these source releases and coordinated dpkg-owned image contents; retire the
wrappers when maintained upstream/distro packages provide equivalent composition.

[Mainsail profile](../../configs/apps/mainsail.json) pins Node 22.23.2 for the
x86-64 build workstation, its archive hash and the upstream npm lock hash. The
archive came from `https://nodejs.org/dist/v22.23.2/`, checked against its official
SHASUMS256 file. Node is a build tool, not an ARM64 runtime dependency. npm ci
uses the lock and skips install scripts. The builder invokes upstream `vite build`
and consumes `dist` directly; upstream's optional ZIP step is unnecessary.
The initial `npm run build` produced assets but its ZIP step failed for missing
`zip`; the package build subsequently completed without requiring ZIP.

The [Moonraker input export](../../scripts/export_moonraker_lock.py) walks only
runtime dependencies in upstream `uv.lock`, evaluates CPython 3.13/Linux/ARM64
markers, and selects compatible locked wheels. Missing wheels are explicitly
marked as source builds. [Input records](../../configs/host/moonraker-inputs-arm64.json)
retain upstream URLs and hashes. There is no floating resolver in this path.
The only source-built runtime dependency is streaming-form-data 2.1.0, from
upstream's locked source archive. Its generated C source compiled with Debian
GCC 14.2.0-19 and Python 3.13.5 headers in a separate ARM64 QEMU build chroot.
Build backend: the previously reviewed setuptools 78.1.1 wheel. No Cython
regeneration or source patch was needed. SOURCE_DATE_EPOCH was 1787876725.

KlipperScreen uses Debian PyGObject 3.50.0-4+b1, satisfying the upstream `<3.51`
constraint, through a venv with system-site-packages. Its requested Pycairo 1.29.1
is newer than Debian's 1.27.0, so the venv includes a separately built wheel.
Source archive SHA-256:
`4fbd26b4af24c9787d84cf5448e34eb8dca064b732479aaecd03109520eebd5f`.
Build tools: meson-python 0.18.0, Meson 1.9.0, packaging 25.0,
pyproject-metadata 0.9.1, Debian ninja-build 1.12.1-1+b1, libcairo2-dev 1.18.4 and
the same compiler/Python toolchain. [Build wheel hashes](../../configs/host/cairo-build-wheels.json)
are separate from runtime inputs. SOURCE_DATE_EPOCH was 1788808152. The first
attempt lacked the venv's Meson executable on PATH; the corrected build adds
`/tmp/build-venv/bin` to PATH and uses installed Ninja. No source patch was needed.

Final runtime installation uses the complete hash-locked
[Moonraker](../../configs/host/moonraker-python313-arm64.lock) and
[KlipperScreen](../../configs/host/klipperscreen-python313-arm64.lock) requirements,
with `--no-index --require-hashes`. KlipperScreen's initial intake resolved the
requirements at the pinned revision; all subsequent builds must use this lock.
The [Moonraker](../../configs/apps/moonraker.json) and
[KlipperScreen](../../configs/apps/klipperscreen.json) profiles declare required
Debian runtime libraries. Compiler/development packages stay in the separate
build chroot. The target adds libmpv2, librsvg2-common and ustreamer from the same
pinned Debian snapshot. ustreamer 5.4 is the retained-camera candidate, not a
claim of camera operation.

## Reproduction stages

Use the [baseline instructions](host-ab-build.md) and a new isolated copy for
application assembly. Keep the existing Klipper package installed in that copy.
The paths below identify this session's ignored build artifacts; choose fresh
work paths for repeats. Linux, ARM64 binfmt/QEMU, Python packaging, dpkg-deb,
e2fsprogs and GPT fdisk are workstation prerequisites.

```sh
python3 scripts/export_moonraker_lock.py --output build/moonraker-lock-new
python3 scripts/package_mainsail.py --work build/mainsail-package-new \
  --node-archive build/app-intake/node-v22.23.2-linux-x64.tar.xz
python3 scripts/package_python_app.py --app moonraker \
  --work build/host-stack-new --wheelhouse build/moonraker-wheels
python3 scripts/package_python_app.py --app klipperscreen \
  --work build/host-stack-new --wheelhouse build/ks-wheels
```

These package commands default to validation/dry-run. Add `--execute` for
Mainsail; use `sudo` and `--execute` for the Python chroot builds. They refuse
existing source/venv/build paths and validate source/lock/wheel hashes before
assembly. Install resulting `.deb` files into the isolated rootfs separately
with chroot/dpkg for validation. No package contains maintainer scripts, printer
configuration, service activation or firmware. The existing baseline policy
continues to suppress package service starts.

To rebuild compiled wheels, copy a completed baseline into a separate compiler
work directory, mount proc there, and install build-essential, python3-dev,
pkg-config, libsystemd-dev, libcairo2-dev and ninja-build using its pinned APT
sources. Create `/tmp/build-venv`, install only the recorded build wheels, then:

```sh
# Inside the compiler chroot; sources and build wheels must be hash-checked first.
PATH=/tmp/build-venv/bin:/usr/bin:/bin SOURCE_DATE_EPOCH=1787876725 \
  /tmp/build-venv/bin/pip wheel --no-index --no-build-isolation --no-deps \
  --wheel-dir /tmp/built-wheels /tmp/moonraker-inputs/streaming_form_data-2.1.0.tar.gz
PATH=/tmp/build-venv/bin:/usr/bin:/bin SOURCE_DATE_EPOCH=1788808152 \
  /tmp/build-venv/bin/pip wheel --no-index --no-build-isolation --no-deps \
  --wheel-dir /tmp/built-wheels /tmp/pycairo-1.29.1.tar.gz
```

Unmount proc after building. Compare generated wheel hashes to the runtime locks;
if they differ, investigate before changing a lock. The subsequent [independent rebuilds](host-compiled-wheels.md) establish
Pycairo reproducibility and a canonical-debug-path recipe for streaming-form-data.
Use that recipe for the updated Moonraker lock; the original direct archive
command above explains the older artifact but embeds random debug paths.
Installed venvs keep absolute final paths and use the slot's system Python.
The [KlipperScreen patch](../../patches/klipperscreen/README.md) reads the packaged
`.version` before falling back to Git, avoiding errors in archive installations.
Its patched installed runtime reports the selected commit. The
[Mainsail patch](../../patches/mainsail/README.md) makes precache ordering stable;
repeat-build results and asset-preservation checks are recorded in the result.

## Validation and release limits

The [build result](host-stack-20260909.json) records package hashes, validation
scope and capacity measurements. Moonraker ran on workstation loopback under
ARM64 QEMU with `provider: none` and an absent Klipper socket. `/server/info`
reported the expected version, no failed components and no warnings after
creating its temporary log directory. Disconnected Klipper is expected; no
printer, machine reboot, systemd service control or G-code operation was used.
Temporary test state is excluded from the capacity fixture.

Mainsail compiled with warnings about chunk sizes. npm audit of the unchanged
upstream lock reported 17 findings: 8 low, 6 moderate and 3 high. This is a release
review gate, not a reason to silently rewrite upstream dependencies. High findings
include js-yaml, nanoid and Vuetify; the suggested Vuetify replacement is a major
version change. Assess actual shipped reachability and upstream fixes, then pin
and test the resulting release. This build is not a security-approved release.
Audit output remains in ignored build evidence; it is not evidence that all 17
issues are exploitable in the deployed UI.

The subsequent [dependency review](host-mainsail-audit.md) pins two compatible
fixes and records new reproducible package evidence; the original fixture above
retains its original package versions.

Remaining system work is tracked in the [completion checklist](host-os-tasks.md).

## Completed capacity and GUI result

The final installed stack has **501 packages**, **1,397,470,284 apparent root
bytes (1,332.73 MiB)** and **74,531,314 boot bytes (71.08 MiB)**. Both content
budgets pass. Populating a **2 GiB ext4** regular-file fixture and running
`e2fsck -f -n` succeeded, with **562,692,096 free bytes** (including 21,471,232
reserved bytes). This fixture conservatively includes the boot directory in the
root filesystem too; the final paired boot mount remains to be assembled.

The [capacity tool](../../scripts/measure_host_slot.py) refuses mounted source
subtrees and existing outputs, writes only new regular files below build/, and
defaults to dry-run. It is a filesystem-capacity test, not image finalization:

```sh
sudo python3 scripts/measure_host_slot.py --work build/host-stack-v1 \
  --output build/host-stack-capacity-new/root.ext4 --execute
```

KlipperScreen's installed ARM64 runtime loaded GTK 3.24, PyGObject 3.50.0,
Pycairo 1.29.1 and python-mpv 1.0.8. Under native workstation Xvfb it opened a
1024×600 window and connected to the local test Moonraker with Klipper absent.
The first chroot GUI attempt lacked `/sys/class/power_supply`; adding an empty
test directory enabled the expected no-battery path. No host sysfs or hardware
devices were bound into the test. System/session D-Bus hardware services were
absent; this does not validate network provisioning. The archive-version patch
was then tested in the installed package and reports `3791fdf` without Git.
All temporary servers, mounts and test configuration/state were removed.

Two fresh Mainsail builds with the final patch produced identical `.deb` hashes.
The same 188 unique precache URL/revision pairs were retained; 28 duplicate
entries from the original 216-entry list were removed. The first sorting-only
attempt still had unstable appended entries; the final patch prevents duplicate
asset/icon collection in addition to sorting the glob results.
