/* SPDX-License-Identifier: MIT */
/* Host-only tests for exact-controller eMMC discovery. */
#define main sd_network_probe_main
#include "init.c"
#undef main

#include <limits.h>
#include <ftw.h>

static char fixture_root[] = "/tmp/sv08-mmc-host-XXXXXX";

static int remove_fixture_entry(const char *path, const struct stat *info,
                                int type, struct FTW *walk) {
    (void)info; (void)type; (void)walk;
    return remove(path);
}

static void cleanup_fixture(void) {
    nftw(fixture_root, remove_fixture_entry, 16, FTW_DEPTH | FTW_PHYS);
}

static int put(const char *path, const char *value) {
    FILE *f = fopen(path, "w");
    if (!f) return 0;
    int ok = fputs(value, f) >= 0;
    return fclose(f) == 0 && ok;
}

static int make_card(const char *base, const char *host, const char *card,
                     const char *block, const char *type, const char *sectors) {
    char path[PATH_MAX];
    const char *parts[] = {host, card, "block", block};
    if (snprintf(path, sizeof(path), "%s", base) >= (int)sizeof(path)) return 0;
    for (size_t i = 0; i < sizeof(parts) / sizeof(parts[0]); i++) {
        size_t used = strlen(path);
        if (snprintf(path + used, sizeof(path) - used, "/%s", parts[i]) >=
            (int)(sizeof(path) - used)) return 0;
        if (mkdir(path, 0700) && errno != EEXIST) return 0;
    }
    char type_path[PATH_MAX], size_path[PATH_MAX];
    if (snprintf(type_path, sizeof(type_path), "%s/%s/%s/type", base, host, card) >=
            (int)sizeof(type_path) ||
        snprintf(size_path, sizeof(size_path), "%s/%s/%s/block/%s/size", base,
                 host, card, block) >= (int)sizeof(size_path)) return 0;
    return put(type_path, type) && put(size_path, sectors);
}

int main(void) {
    char *temp = fixture_root;
    char device[64] = {0};
    unsigned long long sectors = 0;
    if (!mkdtemp(temp)) return 1;
    atexit(cleanup_fixture);
    /* Linux numbering is intentionally unlike the guessed mmc2 mapping:
     * the target MMC is mmc0, while mmc2 carries a small SD card. */
    if (!make_card(temp, "mmc0", "mmc0:0001", "mmcblk0", "MMC\n", "61000000\n") ||
        !make_card(temp, "mmc2", "mmc2:0001", "mmcblk2", "SD\n", "3900000\n"))
        return 2;
    if (!emmc_device_at(temp, device, sizeof(device), &sectors) ||
        strcmp(device, "/dev/mmcblk0") || sectors != 61000000ULL) return 3;
    /* A second matching MMC on the same controller is ambiguous and rejected. */
    if (!make_card(temp, "mmc1", "mmc1:0001", "mmcblk1", "MMC\n", "62000000\n"))
        return 4;
    if (emmc_device_at(temp, device, sizeof(device), &sectors)) return 5;
    puts("eMMC controller locator numbering/uniqueness checks passed");
    return 0;
}
