/* SPDX-License-Identifier: MIT */
/* Host-only checks for the same parser used by the physical probe. */
#define main sd_network_probe_main
#include "init.c"
#undef main

static void putvar(unsigned char *env, const char *key, const char *value,
                   size_t *offset) {
    size_t n = (size_t)snprintf((char *)env + *offset, ENV_SIZE - *offset,
                                "%s=%s", key, value) + 1;
    *offset += n;
}

static void finish(unsigned char *env) {
    uint32_t crc = crc32_env(env + ENV_DATA_OFFSET, ENV_SIZE - ENV_DATA_OFFSET);
    env[0] = crc & 0xff;
    env[1] = (crc >> 8) & 0xff;
    env[2] = (crc >> 16) & 0xff;
    env[3] = (crc >> 24) & 0xff;
}

int main(int argc, char **argv) {
    unsigned char env[ENV_SIZE] = {0};
    struct env_result result;
    size_t offset = ENV_DATA_OFFSET;
    if (argc == 2) {
        FILE *input = fopen(argv[1], "rb");
        if (!input) return 10;
        for (int i = 0; i < 2; i++) {
            if (fread(env, 1, sizeof(env), input) != sizeof(env) ||
                !parse_env(env, &result)) { fclose(input); return 11; }
            printf("copy%d crc=%s flag=%u order=%s A=%s B=%s\n", i + 1,
                   result.crc_ok ? "valid" : "bad", result.flag,
                   result.crc_ok ? result.order : "unknown",
                   result.crc_ok ? result.a_left : "unknown",
                   result.crc_ok ? result.b_left : "unknown");
        }
        fclose(input);
        return 0;
    }
    if (argc != 1) return 12;
    env[4] = 7;
    putvar(env, "BOOT_ORDER", "A", &offset);
    putvar(env, "BOOT_A_LEFT", "2", &offset);
    putvar(env, "BOOT_B_LEFT", "0", &offset);
    putvar(env, "sv08_env_layout", "ab-8gb-v1", &offset);
    finish(env);
    if (!parse_env(env, &result) || !result.crc_ok || result.flag != 7 ||
        strcmp(result.order, "A") || strcmp(result.a_left, "2") ||
        strcmp(result.b_left, "0")) return 1;
    env[ENV_DATA_OFFSET + 1] ^= 1;
    if (!parse_env(env, &result) || result.crc_ok) return 2;
    finish(env);
    env[ENV_DATA_OFFSET + 2] = 'X';
    finish(env);
    if (parse_env(env, &result)) return 3;
    puts("env parser valid/corrupt/policy checks passed");
    return 0;
}
