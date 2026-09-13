#!/usr/bin/env python3
"""Exercise actual patched C statements/layouts; no radio or kernel execution."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    source = args.source
    tx = (source / 'hal/rtl8188f/sdio/rtl8189fs_xmit.c').read_text()
    statement = re.search(r'rtw_sprintf\(thread_name,.*?;', tx).group()
    headers = [('include/rtw_rf.h', 'regd_exc_ent'),
               ('include/hal_data.h', 'txpwr_lmt_ent')]
    definitions = []
    checks = []
    for path, name in headers:
        definition = re.search(r'struct ' + name + r' \{.*?\n\};',
                               (source / path).read_text(), re.S).group()
        definitions.append(definition)
        definitions.append(definition.replace('struct ' + name,
                           'struct old_' + name).replace('regd_name[]', 'regd_name[0]'))
        checks.append(f'''
        _Static_assert(sizeof(struct {name}) == sizeof(struct old_{name}), "size");
        _Static_assert(offsetof(struct {name}, regd_name) ==
                       offsetof(struct old_{name}, regd_name), "offset");
        struct {name} *p_{name} = calloc(1, sizeof(*p_{name}) + strlen(value) + 1);
        assert(p_{name});
        memcpy(p_{name}->regd_name, value, strlen(value));
        assert(strlen(p_{name}->regd_name) == strlen(value));
        assert(strcmp(p_{name}->regd_name, value) == 0);
        free(p_{name});
        ''')
    # Representative dependency shims: full module build checks real dimensions.
    prefix = '''
    #include <stdio.h>
    #include <stdlib.h>
    #include <string.h>
    #include <stddef.h>
    #include <assert.h>
    typedef unsigned char u8;
    typedef signed char s8;
    typedef struct { void *next, *prev; } _list;
    #define MAX_2_4G_BANDWIDTH_NUM 2
    #define TXPWR_LMT_RS_NUM_2G 3
    #define CENTER_CH_2G_NUM 14
    #define MAX_TX_COUNT 4
    #define rtw_sprintf snprintf
    #define ADPT_FMT "%s"
    #define ADPT_ARG(p) (p)
    '''
    body = '''
    __attribute__((noinline)) static void format(char *out, const char *padapter) {
        u8 thread_name[20] = "RTWHALXT";
        STATEMENT
        memcpy(out, thread_name, sizeof(thread_name));
    }
    int main(int argc, char **argv) {
        assert(argc == 2);
        const char *value = argv[1];
        char actual[20], expected[20];
        format(actual, value);
        snprintf(expected, sizeof(expected), "RTWHALXT-%s", value);
        assert(memchr(actual, 0, sizeof(actual)));
        assert(strcmp(actual, expected) == 0);
        CHECKS
        return 0;
    }
    '''.replace('STATEMENT', statement).replace('CHECKS', '\n'.join(checks))
    with tempfile.TemporaryDirectory(prefix='sv08-radio-compat-') as td:
        root = Path(td)
        c = root / 'check.c'
        c.write_text(prefix + '\n'.join(definitions) + body)
        command = ['gcc', '-O2', '-fstrict-flex-arrays=3', '-Wrestrict',
                   '-Werror=restrict', '-Werror=stringop-overread',
                   '-Wno-pointer-sign', '-fsanitize=undefined',
                   '-fno-sanitize-recover=all', str(c), '-o', str(root / 'check')]
        subprocess.run(command, check=True)
        for value in ('', 'wlan0', 'abcdefghijklmno', 'x' * 64):
            subprocess.run([str(root / 'check'), value], check=True)
        # Negative control must diagnose the original overlapping source.
        original = 'rtw_sprintf(thread_name, 20, "%s-"ADPT_FMT, thread_name, ADPT_ARG(padapter));'
        c.write_text(prefix + '\n'.join(definitions) + body.replace(statement, original))
        result = subprocess.run(command, capture_output=True, text=True)
        assert result.returncode and '-Werror=restrict' in result.stderr, result.stderr
    print('PASS: source-derived format, bounded strings, struct layout; original overlap rejected')


if __name__ == '__main__':
    main()
