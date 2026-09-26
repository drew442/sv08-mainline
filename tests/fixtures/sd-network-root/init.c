/* SPDX-License-Identifier: MIT */
/* Disposable read-only NFS-root and eMMC environment probe. */
#define _GNU_SOURCE
#include <errno.h>
#include <dirent.h>
#include <fcntl.h>
#include <ifaddrs.h>
#include <net/if.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/types.h>
#include <unistd.h>

#define ENV_SIZE 0x10000
#define ENV_DATA_OFFSET 5
#define ENV_A_OFFSET 0x400000
#define ENV_B_OFFSET 0x800000
#define EMMC_SYSFS "/sys/bus/platform/devices/4022000.mmc/mmc_host/mmc2"

struct env_result {
    int crc_ok;
    unsigned flag;
    char order[8];
    char a_left[4];
    char b_left[4];
    char layout[16];
};

static uint32_t crc32_env(const unsigned char *p, size_t n) {
    uint32_t crc = 0xffffffffU;
    for (size_t i = 0; i < n; i++) {
        crc ^= p[i];
        for (int bit = 0; bit < 8; bit++)
            crc = (crc >> 1) ^ (0xedb88320U & (0U - (crc & 1U)));
    }
    return crc ^ 0xffffffffU;
}

static int copy_value(char *out, size_t cap, const unsigned char *env,
                      const char *key) {
    size_t keylen = strlen(key);
    const unsigned char *p = env + ENV_DATA_OFFSET;
    const unsigned char *end = env + ENV_SIZE;
    while (p < end && *p) {
        size_t len = strnlen((const char *)p, (size_t)(end - p));
        if (len == (size_t)(end - p)) return 0;
        if (len > keylen && !memcmp(p, key, keylen) && p[keylen] == '=') {
            size_t value_len = len - keylen - 1;
            if (value_len >= cap) return 0;
            memcpy(out, p + keylen + 1, value_len);
            out[value_len] = '\0';
            return 1;
        }
        p += len + 1;
    }
    return 0;
}

static int parse_env(const unsigned char *env, struct env_result *result) {
    uint32_t stored = (uint32_t)env[0] | ((uint32_t)env[1] << 8) |
                      ((uint32_t)env[2] << 16) | ((uint32_t)env[3] << 24);
    memset(result, 0, sizeof(*result));
    result->flag = env[4];
    result->crc_ok = stored == crc32_env(env + ENV_DATA_OFFSET,
                                         ENV_SIZE - ENV_DATA_OFFSET);
    if (!result->crc_ok) return 1;
    if (!copy_value(result->order, sizeof(result->order), env, "BOOT_ORDER") ||
        !copy_value(result->a_left, sizeof(result->a_left), env, "BOOT_A_LEFT") ||
        !copy_value(result->b_left, sizeof(result->b_left), env, "BOOT_B_LEFT") ||
        !copy_value(result->layout, sizeof(result->layout), env, "sv08_env_layout"))
        return 0;
    if ((strcmp(result->order, "A") && strcmp(result->order, "B") &&
         strcmp(result->order, "A B") && strcmp(result->order, "B A")) ||
        strspn(result->a_left, "0123") != strlen(result->a_left) ||
        strlen(result->a_left) != 1 ||
        strspn(result->b_left, "0123") != strlen(result->b_left) ||
        strlen(result->b_left) != 1 ||
        strcmp(result->layout, "ab-8gb-v1")) return 0;
    return 1;
}

/* Locate the card under H616 SMHC2, not by a guessed mmcblk number. */
static int emmc_device(char *device, size_t device_cap,
                       unsigned long long *target_sectors) {
    DIR *host = opendir(EMMC_SYSFS);
    struct dirent *card;
    int found = 0;
    if (!host) return 0;
    while ((card = readdir(host)) != NULL) {
        char path[512], value[128];
        FILE *f;
        if (strncmp(card->d_name, "mmc2:", 5)) continue;
        snprintf(path, sizeof(path), EMMC_SYSFS "/%s/type", card->d_name);
        f = fopen(path, "r");
        if (!f) continue;
        if (!fgets(value, sizeof(value), f)) { fclose(f); continue; }
        fclose(f);
        if (strcmp(value, "MMC\n") && strcmp(value, "MMC")) continue;
        snprintf(path, sizeof(path), EMMC_SYSFS "/%s/block", card->d_name);
        DIR *blocks = opendir(path);
        if (!blocks) continue;
        struct dirent *block;
        while ((block = readdir(blocks)) != NULL) {
            if (strncmp(block->d_name, "mmcblk", 6)) continue;
            char size_path[1024];
            unsigned long long sectors = 0;
            snprintf(size_path, sizeof(size_path), "%s/%s/size", path, block->d_name);
            f = fopen(size_path, "r");
            if (!f) continue;
            int valid = fscanf(f, "%llu", &sectors) == 1;
            fclose(f);
            /* Accept only the known nominal 32 GB module size range. */
            if (!valid || sectors < 60000000ULL || sectors > 64000000ULL)
                continue;
            if (found) { found = 2; break; }
            if (snprintf(device, device_cap, "/dev/%s", block->d_name) >=
                (int)device_cap) continue;
            *target_sectors = sectors;
            found++;
        }
        closedir(blocks);
    }
    closedir(host);
    return found == 1;
}

static int pread_exact(int fd, unsigned char *buffer, size_t size, off_t offset) {
    size_t done = 0;
    while (done < size) {
        ssize_t n = pread(fd, buffer + done, size - done, offset + (off_t)done);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return 0;
        done += (size_t)n;
    }
    return 1;
}

static int report_emmc(void) {
    char path[128];
    unsigned char env_a[ENV_SIZE], env_b[ENV_SIZE];
    struct env_result a, b;
    struct stat st;
    char a_flag[8], b_flag[8];
    unsigned long long sectors = 0;
    int fd;
    if (!emmc_device(path, sizeof(path), &sectors)) {
        puts("SV08_EMMC_ENV status=NO_CARD_OR_AMBIGUOUS_TARGET_ON_SMHC2");
        return 0;
    }
    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0 || fstat(fd, &st) || !S_ISBLK(st.st_mode) ||
        !pread_exact(fd, env_a, sizeof(env_a), ENV_A_OFFSET) ||
        !pread_exact(fd, env_b, sizeof(env_b), ENV_B_OFFSET)) {
        if (fd >= 0) close(fd);
        puts("SV08_EMMC_ENV status=READ_FAILED");
        return 0;
    }
    close(fd);
    if (!parse_env(env_a, &a) || !parse_env(env_b, &b)) {
        puts("SV08_EMMC_ENV status=ENV_FORMAT_UNRECOGNIZED");
        return 0;
    }
    if (a.crc_ok) snprintf(a_flag, sizeof(a_flag), "%u", a.flag);
    else strcpy(a_flag, "unknown");
    if (b.crc_ok) snprintf(b_flag, sizeof(b_flag), "%u", b.flag);
    else strcpy(b_flag, "unknown");
    printf("SV08_EMMC_ENV status=%s device=%s sectors=%llu copy4_crc=%s copy4_flag=%s copy4_order=%s copy4_A=%s copy4_B=%s copy8_crc=%s copy8_flag=%s copy8_order=%s copy8_A=%s copy8_B=%s\n",
           a.crc_ok && b.crc_ok ? "READ_ONLY_VALID_PAIR" : "READ_ONLY_INCOMPLETE_PAIR",
           path, sectors, a.crc_ok ? "valid" : "bad", a_flag,
           a.crc_ok ? a.order : "unknown",
           a.crc_ok ? a.a_left : "unknown", a.crc_ok ? a.b_left : "unknown",
           b.crc_ok ? "valid" : "bad", b_flag,
           b.crc_ok ? b.order : "unknown",
           b.crc_ok ? b.a_left : "unknown", b.crc_ok ? b.b_left : "unknown");
    return a.crc_ok && b.crc_ok;
}

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
    int root_ro, data_volatile, root_refuses_write, volatile_write, net_ok;
    FILE *f;
    if (!has_mount("/proc", "proc", "rw") &&
        mount("proc", "/proc", "proc", 0, NULL)) ok = 0;
    if (!has_mount("/sys", "sysfs", "rw") &&
        mount("sysfs", "/sys", "sysfs", 0, NULL)) ok = 0;
    if (!has_mount("/dev", "devtmpfs", "rw") &&
        mount("devtmpfs", "/dev", "devtmpfs", 0, "mode=0755")) ok = 0;
    if (mount("tmpfs", "/data", "tmpfs", MS_NOSUID | MS_NODEV,
              "size=32m,mode=0700")) ok = 0;
    if (mount("tmpfs", "/run", "tmpfs", MS_NOSUID | MS_NODEV,
              "size=16m,mode=0755")) ok = 0;
    if (mount("tmpfs", "/tmp", "tmpfs", MS_NOSUID | MS_NODEV,
              "size=16m,mode=1777")) ok = 0;
    root_ro = has_mount("/", "nfs", "ro") || has_mount("/", "nfs4", "ro");
    if (!root_ro) ok = 0;
    data_volatile = has_mount("/data", "tmpfs", "rw");
    if (!data_volatile) ok = 0;
    errno = 0;
    f = fopen("/immutable-refusal", "w");
    if (f) { fclose(f); root_refuses_write = 0; ok = 0; }
    else { root_refuses_write = errno == EROFS; if (!root_refuses_write) ok = 0; }
    f = fopen("/data/volatile-proof", "w");
    if (!f) { volatile_write = 0; ok = 0; }
    else { fputs("volatile\n", f); fclose(f); volatile_write = 1; }
    /* The initramfs already used DHCP; a live non-loopback address confirms it. */
    struct ifaddrs *addresses = NULL;
    int network = 0;
    if (getifaddrs(&addresses) == 0) {
        for (struct ifaddrs *p = addresses; p; p = p->ifa_next)
            if (p->ifa_addr && p->ifa_addr->sa_family == 2 &&
                !(p->ifa_flags & IFF_LOOPBACK)) network = 1;
        freeifaddrs(addresses);
    }
    net_ok = network;
    if (!net_ok) ok = 0;
    report_emmc();
    printf("SV08_SD_NFS_%s root_ro=%d data_tmpfs=%d immutable_refusal=%d volatile_write=%d dhcp_address=%d\n",
           ok ? "PASS" : "FAIL", root_ro, data_volatile, root_refuses_write,
           volatile_write, net_ok);
    fflush(stdout);
    sync();
    reboot(RB_POWER_OFF);
    for (;;) pause();
}
