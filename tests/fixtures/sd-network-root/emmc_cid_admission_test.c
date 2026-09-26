/* SPDX-License-Identifier: MIT */
/* Synthetic sysfs and open-spy tests; no block node is ever opened. */
#define _GNU_SOURCE
#include "emmc_cid_admission.h"
#include <ftw.h>
#include <limits.h>
#include <sys/stat.h>
#include <unistd.h>

#define FAKE_CID "00000000000000000000000000000001"
#define OTHER_FAKE_CID "00000000000000000000000000000002"
#define SECTORS "61079552\n"

static char fixture_root[] = "/tmp/sv08-cid-synthetic-XXXXXX";
static int opens;
static char opened_path[64];

static int remove_entry(const char *path, const struct stat *info, int type,
                        struct FTW *walk) {
    (void)info; (void)type; (void)walk;
    return remove(path);
}

static void cleanup(void) {
    nftw(fixture_root, remove_entry, 16, FTW_DEPTH | FTW_PHYS);
}

static int put(const char *path, const char *value) {
    FILE *f = fopen(path, "w");
    if (!f) return 0;
    int ok = fputs(value, f) >= 0;
    return fclose(f) == 0 && ok;
}

static int make_card(const char *base, const char *host, const char *card,
                     const char *block, const char *type, const char *size,
                     const char *cid) {
    char path[PATH_MAX];
    const char *parts[] = {host, card, "block", block};
    if (snprintf(path, sizeof(path), "%s", base) >= (int)sizeof(path)) return 0;
    for (size_t i = 0; i < sizeof(parts) / sizeof(parts[0]); i++) {
        size_t used = strlen(path);
        if (snprintf(path + used, sizeof(path) - used, "/%s", parts[i]) >=
            (int)(sizeof(path) - used) ||
            (mkdir(path, 0700) && errno != EEXIST)) return 0;
    }
    char type_path[PATH_MAX], size_path[PATH_MAX], cid_path[PATH_MAX];
    if (snprintf(type_path, sizeof(type_path), "%s/%s/%s/type", base, host, card) >=
            (int)sizeof(type_path) ||
        snprintf(size_path, sizeof(size_path), "%s/%s/%s/block/%s/size", base,
                 host, card, block) >= (int)sizeof(size_path) ||
        snprintf(cid_path, sizeof(cid_path), "%s/%s/%s/cid", base, host, card) >=
            (int)sizeof(cid_path)) return 0;
    return (!type || put(type_path, type)) && (!size || put(size_path, size)) &&
           (!cid || put(cid_path, cid));
}

static int scenario(const char *name, char *path, size_t cap) {
    return snprintf(path, cap, "%s/%s", fixture_root, name) < (int)cap &&
           mkdir(path, 0700) == 0;
}

static int open_spy(const char *path, void *context) {
    (void)context;
    opens++;
    snprintf(opened_path, sizeof(opened_path), "%s", path);
    return 77;
}

static int admitted(const char *base, const char *expected, int success) {
    opens = 0;
    opened_path[0] = '\0';
    int result = sv08_emmc_cid_open_at(base, expected, open_spy, NULL);
    if (success)
        return result == 77 && opens == 1 &&
               !strcmp(opened_path, "/dev/mmcblk0");
    return result == -1 && opens == 0 && !opened_path[0];
}

#define REQUIRE(x) do { if (!(x)) { fprintf(stderr, "failed line %d: %s\n", __LINE__, #x); return 1; } } while (0)

int main(void) {
    char path[PATH_MAX];
    REQUIRE(mkdtemp(fixture_root));
    atexit(cleanup);

    REQUIRE(scenario("matching", path, sizeof(path)));
    REQUIRE(make_card(path, "mmc7", "mmc7:0001", "mmcblk0", "MMC\n",
                      SECTORS, FAKE_CID "\n"));
    REQUIRE(make_card(path, "mmc2", "mmc2:0001", "mmcblk2", "SD\n",
                      "3900000\n", NULL));
    REQUIRE(admitted(path, FAKE_CID, 1));
    REQUIRE(admitted(path, OTHER_FAKE_CID, 0));
    REQUIRE(admitted(path, NULL, 0));
    const char *invalid_expected[] = {"", "0", FAKE_CID "0",
                                      "0000000000000000000000000000000g",
                                      "0000000000000000000000000000000A",
                                      FAKE_CID "\n"};
    for (size_t i = 0; i < sizeof(invalid_expected) / sizeof(invalid_expected[0]); i++)
        REQUIRE(admitted(path, invalid_expected[i], 0));

    /* A mismatching value in place of the separate trusted argument is refused. */
    REQUIRE(admitted(path, OTHER_FAKE_CID, 0));

    REQUIRE(scenario("missing_cid", path, sizeof(path)));
    REQUIRE(make_card(path, "mmc0", "mmc0:0001", "mmcblk0", "MMC\n",
                      SECTORS, NULL));
    REQUIRE(admitted(path, FAKE_CID, 0));
    const char *invalid_live[] = {"", "0\n", FAKE_CID "0\n",
                                  "0000000000000000000000000000000g\n",
                                  "0000000000000000000000000000000A\n",
                                  FAKE_CID "\nextra\n"};
    for (size_t i = 0; i < sizeof(invalid_live) / sizeof(invalid_live[0]); i++) {
        char name[32];
        REQUIRE(snprintf(name, sizeof(name), "bad_live_%zu", i) < (int)sizeof(name));
        REQUIRE(scenario(name, path, sizeof(path)));
        REQUIRE(make_card(path, "mmc0", "mmc0:0001", "mmcblk0", "MMC\n",
                          SECTORS, invalid_live[i]));
        REQUIRE(admitted(path, FAKE_CID, 0));
    }

    REQUIRE(scenario("wrong_capacity", path, sizeof(path)));
    REQUIRE(make_card(path, "mmc0", "mmc0:0001", "mmcblk0", "MMC\n",
                      "61079551\n", FAKE_CID "\n"));
    REQUIRE(admitted(path, FAKE_CID, 0));
    REQUIRE(scenario("wrong_type", path, sizeof(path)));
    REQUIRE(make_card(path, "mmc0", "mmc0:0001", "mmcblk0", "SD\n",
                      SECTORS, FAKE_CID "\n"));
    REQUIRE(admitted(path, FAKE_CID, 0));
    REQUIRE(scenario("ambiguous", path, sizeof(path)));
    REQUIRE(make_card(path, "mmc0", "mmc0:0001", "mmcblk0", "MMC\n",
                      SECTORS, FAKE_CID "\n"));
    REQUIRE(make_card(path, "mmc1", "mmc1:0001", "mmcblk1", "MMC\n",
                      SECTORS, FAKE_CID "\n"));
    REQUIRE(admitted(path, FAKE_CID, 0));
    REQUIRE(scenario("absent", path, sizeof(path)));
    REQUIRE(admitted(path, FAKE_CID, 0));

    puts("synthetic CID admission and pre-open refusal checks passed");
    return 0;
}
