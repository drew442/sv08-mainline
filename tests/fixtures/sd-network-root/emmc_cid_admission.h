/* SPDX-License-Identifier: MIT */
/* Test-only eMMC identity gate. No network job field supplies expected_cid. */
#ifndef SV08_EMMC_CID_ADMISSION_H
#define SV08_EMMC_CID_ADMISSION_H

#include "emmc_locator.h"

/* Sysfs CID is canonical lowercase hexadecimal, without 0x or whitespace. */
static int sv08_canonical_cid(const char *cid) {
    if (!cid) return 0;
    for (size_t i = 0; i < 32; i++) {
        unsigned char c = (unsigned char)cid[i];
        if (!c || !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')))
            return 0;
    }
    return cid[32] == '\0';
}

/* Return one path only after the existing locator and the live sysfs CID agree.
 * The expected CID must be supplied by a separately trusted local caller.
 * This is metadata admission, not binding of a subsequently opened device. */
static int sv08_emmc_cid_device_at(const char *base, const char *expected_cid,
                                   char *device, size_t device_cap,
                                   unsigned long long *target_sectors) {
    if (!device || !device_cap || !target_sectors) return 0;
    device[0] = '\0';
    *target_sectors = 0;
    if (!base || !sv08_canonical_cid(expected_cid)) return 0;

    char candidate[64];
    unsigned long long sectors;
    if (!sv08_emmc_device_at(base, candidate, sizeof(candidate), &sectors)) return 0;

    DIR *hosts = opendir(base);
    if (!hosts) return 0;
    int ok = 1, matched = 0, next = 0;
    struct dirent *host;
    while (ok && (next = sv08_next_entry(hosts, &host)) > 0) {
        if (!sv08_named_number(host->d_name, "mmc")) continue;
        char host_path[512];
        if (snprintf(host_path, sizeof(host_path), "%s/%s", base,
                     host->d_name) >= (int)sizeof(host_path)) { ok = 0; break; }
        DIR *cards = opendir(host_path);
        if (!cards) { ok = 0; break; }
        int card_next = 0;
        struct dirent *card;
        while (ok && (card_next = sv08_next_entry(cards, &card)) > 0) {
            size_t host_len = strlen(host->d_name);
            if (strncmp(card->d_name, host->d_name, host_len) ||
                card->d_name[host_len] != ':') continue;
            char card_path[768], type_path[896], cid_path[896];
            char type[32], cid[64];
            if (snprintf(card_path, sizeof(card_path), "%s/%s", host_path,
                         card->d_name) >= (int)sizeof(card_path) ||
                snprintf(type_path, sizeof(type_path), "%s/type", card_path) >=
                    (int)sizeof(type_path) ||
                !sv08_read_line(type_path, type, sizeof(type))) { ok = 0; break; }
            if (!strcmp(type, "SD") || !strcmp(type, "SDIO")) continue;
            if (strcmp(type, "MMC") || matched++) { ok = 0; break; }
            if (snprintf(cid_path, sizeof(cid_path), "%s/cid", card_path) >=
                    (int)sizeof(cid_path) ||
                !sv08_read_line(cid_path, cid, sizeof(cid)) ||
                !sv08_canonical_cid(cid) || strcmp(cid, expected_cid)) {
                ok = 0; break;
            }
            char block_path[896];
            if (snprintf(block_path, sizeof(block_path), "%s/block", card_path) >=
                    (int)sizeof(block_path)) { ok = 0; break; }
            DIR *blocks = opendir(block_path);
            if (!blocks) { ok = 0; break; }
            int block_next = 0, main_area = 0;
            struct dirent *block;
            while (ok && (block_next = sv08_next_entry(blocks, &block)) > 0) {
                if (!sv08_named_number(block->d_name, "mmcblk")) continue;
                char block_device[64];
                if (++main_area != 1 ||
                    snprintf(block_device, sizeof(block_device), "/dev/%s",
                             block->d_name) >= (int)sizeof(block_device) ||
                    strcmp(block_device, candidate)) ok = 0;
            }
            if (ok && block_next < 0) ok = 0;
            if (closedir(blocks)) ok = 0;
            if (main_area != 1) ok = 0;
        }
        if (ok && card_next < 0) ok = 0;
        if (closedir(cards)) ok = 0;
    }
    if (ok && next < 0) ok = 0;
    if (closedir(hosts)) ok = 0;
    if (!ok || matched != 1 || strlen(candidate) + 1 > device_cap) return 0;
    strcpy(device, candidate);
    *target_sectors = sectors;
    return 1;
}

/* The callback is deliberately supplied by the caller so a synthetic test can
 * prove that no block open is requested on any failed identity check. */
#ifndef SV08_CID_NO_OPEN_WRAPPER
static int sv08_emmc_cid_open_at(const char *base, const char *expected_cid,
                                 int (*target_open)(const char *, void *), void *context) {
    char device[64];
    unsigned long long sectors;
    if (!target_open ||
        !sv08_emmc_cid_device_at(base, expected_cid, device, sizeof(device),
                                 &sectors)) return -1;
    return target_open(device, context);
}
#endif

#endif
