# H616 installed crypto offload comparison

Use the existing installed SHA-256 Crypto Engine driver through AF_ALG, with explicit
driver selection, correct digest checks and before/after hardware/fallback counters.
Bound runtime, memory and generated data; preserve boot, service masks, filesystems
and printer configuration. No kernel configuration, module reload, package install,
service restart, update or reboot. Benchmark request sizes relevant to whole-image
streaming and dm-verity; treat fallback as a result, not hardware throughput.

Trace the current update hashing consumers and construct transparent timing formulas
using current image sizes and specification/rate assumptions. Explain whether measured
offload can benefit those consumers, whether CPU timing is only assumed, and the
existing next-boot activation wait. Publish reproducible script, sanitized results
and evidence, retaining no disposable images. Self-validation applies to this bounded
measurement and documentation; two source research agents support interpretation.
