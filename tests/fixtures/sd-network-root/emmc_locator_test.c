/* SPDX-License-Identifier: MIT */
/* Synthetic sysfs tests: no device nodes are opened. */
#define _GNU_SOURCE
#include "emmc_locator.h"
#include <ftw.h>
#include <limits.h>
#include <sys/stat.h>
#include <unistd.h>

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
    return (!type || put(type_path, type)) && (!sectors || put(size_path, sectors));
}

static int admission(const char *base, int expected, const char *expected_device) {
    char device[64] = "stale";
    unsigned long long sectors = 123;
    int actual = sv08_emmc_device_at(base, device, sizeof(device), &sectors);
    if (actual != expected) return 0;
    if (expected)
        return !strcmp(device, expected_device) && sectors == SV08_EMMC_SECTORS;
    return !device[0] && sectors == 0;
}

static int scenario(const char *name, char *path, size_t cap) {
    return snprintf(path, cap, "%s/%s", fixture_root, name) < (int)cap &&
           mkdir(path, 0700) == 0;
}

#define REQUIRE(x) do { if (!(x)) { fprintf(stderr, "failed line %d: %s\n", __LINE__, #x); return 1; } } while (0)

int main(void) {
    char path[PATH_MAX], other[PATH_MAX];
    REQUIRE(mkdtemp(fixture_root));
    atexit(cleanup_fixture);
    REQUIRE(scenario("absent", path, sizeof(path)));
    REQUIRE(admission(path, 0, NULL));

    REQUIRE(scenario("numbering", path, sizeof(path)));
    REQUIRE(make_card(path, "mmc7", "mmc7:0001", "mmcblk0", "MMC\n", "61079552\n"));
    REQUIRE(make_card(path, "mmc2", "mmc2:0001", "mmcblk2", "SD\n", "3900000\n"));
    REQUIRE(admission(path, 1, "/dev/mmcblk0"));
    REQUIRE(scenario("other_controller", other, sizeof(other)));
    REQUIRE(make_card(other, "mmc0", "mmc0:0001", "mmcblk1", "MMC\n", "61079552\n"));
    REQUIRE(admission(path, 1, "/dev/mmcblk0"));
    REQUIRE(admission(other, 1, "/dev/mmcblk1"));
    REQUIRE(scenario("selected_controller_empty", path, sizeof(path)));
    REQUIRE(admission(path, 0, NULL));

    REQUIRE(scenario("sd_only", path, sizeof(path)));
    REQUIRE(make_card(path, "mmc0", "mmc0:0001", "mmcblk0", "SD\n", "61079552\n"));
    REQUIRE(admission(path, 0, NULL));

    REQUIRE(scenario("short", path, sizeof(path)));
    REQUIRE(make_card(path, "mmc0", "mmc0:0001", "mmcblk0", "MMC\n", "61079551\n"));
    REQUIRE(admission(path, 0, NULL));
    REQUIRE(scenario("large", path, sizeof(path)));
    REQUIRE(make_card(path, "mmc0", "mmc0:0001", "mmcblk0", "MMC\n", "61079553\n"));
    REQUIRE(admission(path, 0, NULL));

    const char *bad_numbers[] = {"", "abc\n", "+61079552\n", " 61079552\n",
                                 "61079552junk\n", "61079552\nother\n",
                                 "18446744073709551616\n"};
    for (size_t i = 0; i < sizeof(bad_numbers) / sizeof(bad_numbers[0]); i++) {
        char name[24];
        REQUIRE(snprintf(name, sizeof(name), "invalid%zu", i) < (int)sizeof(name));
        REQUIRE(scenario(name, path, sizeof(path)));
        REQUIRE(make_card(path, "mmc0", "mmc0:0001", "mmcblk0", "MMC\n", bad_numbers[i]));
        REQUIRE(admission(path, 0, NULL));
    }

    REQUIRE(scenario("unreadable_type", path, sizeof(path)));
    REQUIRE(make_card(path, "mmc0", "mmc0:0001", "mmcblk0", NULL, "61079552\n"));
    REQUIRE(admission(path, 0, NULL));
    REQUIRE(scenario("unreadable_size", path, sizeof(path)));
    REQUIRE(make_card(path, "mmc0", "mmc0:0001", "mmcblk0", "MMC\n", NULL));
    REQUIRE(admission(path, 0, NULL));
    REQUIRE(scenario("unknown_type", path, sizeof(path)));
    REQUIRE(make_card(path, "mmc0", "mmc0:0001", "mmcblk0", "mystery\n", "61079552\n"));
    REQUIRE(admission(path, 0, NULL));

    REQUIRE(scenario("ambiguous", path, sizeof(path)));
    REQUIRE(make_card(path, "mmc0", "mmc0:0001", "mmcblk0", "MMC\n", "61079552\n"));
    REQUIRE(make_card(path, "mmc1", "mmc1:0001", "mmcblk1", "MMC\n", "61079552\n"));
    REQUIRE(admission(path, 0, NULL));
    REQUIRE(scenario("extra_bad_size", path, sizeof(path)));
    REQUIRE(make_card(path, "mmc0", "mmc0:0001", "mmcblk0", "MMC\n", "61079552\n"));
    REQUIRE(make_card(path, "mmc1", "mmc1:0001", "mmcblk1", "MMC\n", "junk\n"));
    REQUIRE(admission(path, 0, NULL));
    REQUIRE(scenario("extra_no_type", path, sizeof(path)));
    REQUIRE(make_card(path, "mmc0", "mmc0:0001", "mmcblk0", "MMC\n", "61079552\n"));
    REQUIRE(make_card(path, "mmc1", "mmc1:0001", "mmcblk1", NULL, "61079552\n"));
    REQUIRE(admission(path, 0, NULL));
    puts("eMMC controller locator numbering/uniqueness/refusal checks passed");
    return 0;
}
