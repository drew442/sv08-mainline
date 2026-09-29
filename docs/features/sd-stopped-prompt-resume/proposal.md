# Resume the identified stopped U-Boot prompt

2026-09-29. Existing writerless goal correction, not an optional feature. The one
reviewed keyboard return reached the newly written SD loader; the controller
intercepted its countdown and stopped at the actual `CB1@uboot:~$ ` prompt because
its fixture assumed `=> `. Retained effective configuration proves
CONFIG_SYS_PROMPT="CB1@uboot:~$ ". The UART capture shows the pinned loader banner,
SD/MMC enumeration and this prompt. The independent supervisor restored bounded
receive-only capture. No second HID sequence or reboot is proposed.

Correct scripts/sv08_serial_boot_route.py to recognise only the exact configured
prompt without classifying its dollar sign as a Linux shell. Retain Linux/login,
arbitrary command, MMC mapping, script count/hash, durability and UART identity
refusals. Add explicit `sd-resume` route for this reviewed stopped prompt:
exclusive UART plus fresh private capture, one empty newline to obtain a live
prompt, then the existing exact mmc0/SD/fatload/hash/source commands. Empty newline
is the only pre-prompt TX; no text/key retry, reboot or environment/media write.
Unknown redundant counters remain explicit; permit resume only with separately
reviewed stopped-U-Boot policy and the existing exact one-return exception. Do
not turn ordinary freshness true. Source only after full existing script gates.

One implementer owns scripts/sv08_serial_boot_route.py,
tests/test_sv08_serial_boot_route.py and docs/hardware/host-stopped-prompt-resume.md.
Tests use the actual configured fragmented prompt, ordinary countdown and stopped
resume success, Linux/unknown/missing prompt refusal, wrong SD/hash/count refusal,
private capture admission and changed-policy refusal. No new dependencies,
loader/writer/build changes or full-image tests. Runtime/capture limits and
independent restoration are reused. Independent delivery verification and a fresh
Sol exact-operation review precede UART operation. Record actual response/return;
then fresh environment/RTC inspection before staging or jobs. Retire diagnostic
resume when recovery has supported authenticated boot selection.
