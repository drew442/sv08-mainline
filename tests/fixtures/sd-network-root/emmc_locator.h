/* SPDX-License-Identifier: MIT */
/* Read-only sysfs admission for the measured test-sv08-01 spare eMMC. */
#ifndef SV08_EMMC_LOCATOR_H
#define SV08_EMMC_LOCATOR_H

#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef SV08_EMMC_SECTORS
#define SV08_EMMC_SECTORS 61079552ULL
#endif
#define SV08_EMMC_HOST_SYSFS "/sys/bus/platform/devices/4022000.mmc/mmc_host"

static int sv08_named_number(const char *name, const char *prefix) {
    size_t n = strlen(prefix);
    if (strncmp(name, prefix, n) || !isdigit((unsigned char)name[n])) return 0;
    for (const char *p = name + n; *p; p++)
        if (!isdigit((unsigned char)*p)) return 0;
    return 1;
}

static int sv08_read_line(const char *path, char *value, size_t cap) {
    FILE *f = fopen(path, "r");
    if (!f) return 0;
    int ok = fgets(value, (int)cap, f) != NULL;
    if (ok) {
        size_t n = strlen(value);
        if (n && value[n - 1] == '\n') value[--n] = '\0';
        /* A truncated or multi-line sysfs value is not trusted. */
        if (!n || fgetc(f) != EOF || ferror(f)) ok = 0;
    }
    if (fclose(f)) ok = 0;
    return ok;
}

static int sv08_parse_sectors(const char *text, unsigned long long *sectors) {
    if (!isdigit((unsigned char)*text)) return 0;
    errno = 0;
    char *end;
    unsigned long long n = strtoull(text, &end, 10);
    if (errno == ERANGE || *end || n != SV08_EMMC_SECTORS) return 0;
    *sectors = n;
    return 1;
}

/* Distinguish end of a directory from a failed inventory read. */
static int sv08_next_entry(DIR *directory, struct dirent **entry) {
    errno = 0;
    *entry = readdir(directory);
    if (*entry) return 1;
    return errno ? -1 : 0;
}

/* Only sysfs metadata is read. The returned path is not a unique device ID and
 * must never, on its own, authorize opening a block node for writing. */
static int sv08_emmc_device_at(const char *base, char *device, size_t device_cap,
                               unsigned long long *target_sectors) {
    if (!base || !device || !device_cap || !target_sectors) return 0;
    device[0] = '\0';
    *target_sectors = 0;
    DIR *hosts = opendir(base);
    if (!hosts) return 0;
    int found = 0, ok = 1;
    struct dirent *host_entry;
    int next;
    while (ok && (next = sv08_next_entry(hosts, &host_entry)) > 0) {
        if (!sv08_named_number(host_entry->d_name, "mmc")) continue;
        char host_path[512];
        if (snprintf(host_path, sizeof(host_path), "%s/%s", base,
                     host_entry->d_name) >= (int)sizeof(host_path)) { ok = 0; break; }
        DIR *cards = opendir(host_path);
        if (!cards) { ok = 0; break; }
        struct dirent *card;
        int card_next;
        while (ok && (card_next = sv08_next_entry(cards, &card)) > 0) {
            size_t host_len = strlen(host_entry->d_name);
            if (strncmp(card->d_name, host_entry->d_name, host_len) ||
                card->d_name[host_len] != ':') continue;
            char card_path[768], type_path[896], type[32];
            if (snprintf(card_path, sizeof(card_path), "%s/%s", host_path,
                         card->d_name) >= (int)sizeof(card_path) ||
                snprintf(type_path, sizeof(type_path), "%s/type", card_path) >=
                    (int)sizeof(type_path) ||
                !sv08_read_line(type_path, type, sizeof(type))) { ok = 0; break; }
            if (!strcmp(type, "SD") || !strcmp(type, "SDIO")) continue;
            if (strcmp(type, "MMC") || found) { ok = 0; break; }
            found = 1;
            char block_path[896];
            if (snprintf(block_path, sizeof(block_path), "%s/block", card_path) >=
                (int)sizeof(block_path)) { ok = 0; break; }
            DIR *blocks = opendir(block_path);
            if (!blocks) { ok = 0; break; }
            int main_area = 0;
            struct dirent *block;
            int block_next;
            while (ok && (block_next = sv08_next_entry(blocks, &block)) > 0) {
                if (!sv08_named_number(block->d_name, "mmcblk")) continue;
                if (main_area++) { ok = 0; break; }
                char size_path[1024], value[32];
                unsigned long long sectors;
                if (snprintf(size_path, sizeof(size_path), "%s/%s/size", block_path,
                             block->d_name) >= (int)sizeof(size_path) ||
                    !sv08_read_line(size_path, value, sizeof(value)) ||
                    !sv08_parse_sectors(value, &sectors) ||
                    snprintf(device, device_cap, "/dev/%s", block->d_name) >=
                        (int)device_cap) { ok = 0; break; }
                *target_sectors = sectors;
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
    if (!ok || !found) {
        device[0] = '\0';
        *target_sectors = 0;
        return 0;
    }
    return 1;
}

#endif
