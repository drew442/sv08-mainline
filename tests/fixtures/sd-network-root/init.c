/* SPDX-License-Identifier: MIT */
/* Disposable NFS-root probe: no systemd, printer units, or block-device opens. */
#include <errno.h>
#include <ifaddrs.h>
#include <net/if.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <unistd.h>

static int has_mount(const char *where, const char *type, const char *option) {
    FILE *f = fopen("/proc/mounts", "r");
    char src[256], path[256], fs[64], opts[512];
    int ok = 0;
    if (!f) return 0;
    while (fscanf(f, "%255s %255s %63s %511s %*d %*d", src, path, fs, opts) == 4) {
        if (strcmp(path, where) == 0 && strcmp(fs, type) == 0 && strstr(opts, option)) ok = 1;
    }
    fclose(f);
    return ok;
}

int main(void) {
    int ok = 1;
    FILE *f;
    if (mount("proc", "/proc", "proc", 0, NULL)) ok = 0;
    if (mount("tmpfs", "/data", "tmpfs", MS_NOSUID | MS_NODEV,
              "size=32m,mode=0700")) ok = 0;
    if (mount("tmpfs", "/run", "tmpfs", MS_NOSUID | MS_NODEV,
              "size=16m,mode=0755")) ok = 0;
    if (mount("tmpfs", "/tmp", "tmpfs", MS_NOSUID | MS_NODEV,
              "size=16m,mode=1777")) ok = 0;
    if (!has_mount("/", "nfs", "ro") && !has_mount("/", "nfs4", "ro")) ok = 0;
    if (!has_mount("/data", "tmpfs", "rw")) ok = 0;
    errno = 0;
    f = fopen("/immutable-refusal", "w");
    if (f) { fclose(f); ok = 0; }
    else if (errno != EROFS) ok = 0;
    f = fopen("/data/volatile-proof", "w");
    if (!f) ok = 0;
    else { fputs("volatile\n", f); fclose(f); }
    /* The initramfs already used DHCP; a live non-loopback address confirms it. */
    struct ifaddrs *addresses = NULL;
    int network = 0;
    if (getifaddrs(&addresses) == 0) {
        for (struct ifaddrs *p = addresses; p; p = p->ifa_next)
            if (p->ifa_addr && p->ifa_addr->sa_family == 2 &&
                !(p->ifa_flags & IFF_LOOPBACK)) network = 1;
        freeifaddrs(addresses);
    }
    if (!network) ok = 0;
    printf("SV08_SD_NFS_%s root_ro=%d data_tmpfs=%d dhcp_address=%d\n",
           ok ? "PASS" : "FAIL", has_mount("/", "nfs", "ro") ||
           has_mount("/", "nfs4", "ro"), has_mount("/data", "tmpfs", "rw"), network);
    fflush(stdout);
    sync();
    reboot(RB_POWER_OFF);
    for (;;) pause();
}
