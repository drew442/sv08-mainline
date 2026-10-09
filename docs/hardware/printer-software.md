# Cockpit additional software

Open **Software** in the left menu and enable administrator access. The initial
catalog contains Nano, htop, tmux and vnStat from the configured Debian package
sources. Select an item and review its resolved packages, download size and root
and persistent-storage headroom before applying. Preview is available in immutable
mode; actual package and service changes require writable mode already applied at
boot. Changing the mode setting alone does not remount the running system.

Package changes run in a private durable job through a fixed systemd worker, so
closing the browser does not cancel APT. Reopen Software to see the result. Atomic
Klipper idle admission prevents stopping an active print. Pending image changes,
unmanaged printer services, changed reviews, busy package locks and insufficient
space refuse execution. Dependencies may not replace existing core software or
boot/kernel/printer/access packages. Removal retains configuration and user data;
this page does not purge or automatically remove dependencies. Package services
stay stopped during installation. A fresh vnStat install stays disabled until its
reviewed service setting enables it; reinstall preserves its existing service
setting, and removal stops it first. A partial fresh install also disables any
created vnStat unit before reporting the uncertain result.

Supported operations record package versions and configured-source fingerprints,
manual package requests and service changes privately. A compatibility report can
be downloaded from Cockpit. A report is not a validated derived image: customized
slots remain protected from image replacement. Arbitrary root edits and incompatible
packages require isolated candidate reconciliation; the page states that reason
and preserves the running system. Update policy remains configured.

APT is not an atomic filesystem transaction. Interrupted package work retains an
uncertain result instead of silently repeating the operation. **Review interrupted
result** displays the package inventory and audit; reviewed acknowledgment can
restore an unchanged known service-blocking policy without retrying APT. Incomplete
package configuration or externally changed policies remain blocked with a reason.
Timeout cleanup retains printer admission until package descendants exit. The independent OS
slot and user data are preserved; physical power-loss recovery is a separate check.
See [delivery evidence](../features/cockpit-software-management/evidence.md) for the
validated source, browser, disposable Linux and installed-control boundaries.

Upstream behavior: [Debian APT reference](https://manpages.debian.org/trixie/apt/apt-get.8.en.html)
and [vnStat daemon reference](https://manpages.debian.org/trixie/vnstat/vnstatd.8.en.html).
