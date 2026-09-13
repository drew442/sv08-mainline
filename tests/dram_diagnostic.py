#!/usr/bin/env python3
"""Execute the compiled-source diagnostic poll helper with scripted MMIO/time.

This is a native C behavior test, not simulated DRAM training or a board boot.
Pass the patched U-Boot source directory produced by the diagnostic manifest.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    source = (args.source / 'arch/arm/mach-sunxi/dram_sun50i_h616.c').read_text()
    start = source.index('static bool sv08_read_calibration_wait(')
    end = source.index('\nstatic bool mctl_phy_read_calibration(', start)
    helper = source[start:end]
    harness = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <limits.h>
#include <setjmp.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
typedef uint32_t u32;
#define SUNXI_DRAM_PHY0_BASE 0x04800000UL
static u32 sequence[16];
static unsigned int sequence_size, reads, ticks;
static unsigned long clock_start;
static jmp_buf stop;
static bool timed_out;
static unsigned long timer_get_us(void)
{
    return clock_start + (unsigned long)ticks++ * 250000UL;
}
static u32 readl(unsigned long address)
{
    assert(address == SUNXI_DRAM_PHY0_BASE + 0x184);
    assert(reads < 16); /* Fails a regression to unbounded polling. */
    unsigned int index = reads++;
    return sequence[index < sequence_size ? index : sequence_size - 1];
}
static void __attribute__((noreturn)) hang(void)
{
    timed_out = true;
    longjmp(stop, 1);
}
'''
    cases = r'''
static void check(u32 first, u32 second, u32 mask, int expected,
                  unsigned long epoch, unsigned int expected_reads)
{
    sequence[0] = first; sequence[1] = second; sequence_size = 2;
    reads = 0; ticks = 0; clock_start = epoch; timed_out = false;
    if (!setjmp(stop)) {
        bool result = sv08_read_calibration_wait(mask);
        assert(expected >= 0);
        assert(result == (bool)expected);
    } else {
        assert(expected == -1);
        assert(timed_out);
    }
    assert(reads == expected_reads);
}
int main(void)
{
    check(0xf, 0xf, 0xf, 1, 0, 1); /* full-width completion */
    check(3, 3, 3, 1, 0, 1);       /* half-width completion */
    check(0x20, 0, 0xf, 0, 0, 1);  /* explicit error remains retryable */
    check(0x2f, 0, 0xf, 1, 0, 1);  /* completion retains original priority */
    check(3, 0xf, 0xf, 1, 0, 2);   /* partial bits are not full completion */
    check(0, 0x20, 3, 0, 0, 2);    /* delayed error */
    check(0, 0, 0xf, -1, 0, 4);    /* stuck full-width fail-stop */
    check(0, 0, 3, -1, 0, 4);      /* stuck half-width fail-stop */
    check(0, 0, 3, -1, ULONG_MAX - 500000UL, 4); /* timer wrap */
    puts("9 scripted MMIO/time cases passed; physical DRAM untested");
    return 0;
}
'''
    with tempfile.TemporaryDirectory(prefix='sv08-dram-poll-') as temporary:
        root = Path(temporary)
        program = root / 'poll.c'
        program.write_text(harness + helper + cases)
        executable = root / 'poll'
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-O2',
                        str(program), '-o', str(executable)], check=True)
        subprocess.run([str(executable)], check=True, timeout=5)


if __name__ == '__main__':
    main()
