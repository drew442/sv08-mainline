# Installed initial-load navigation repair

2026-10-04. The first exact reviewed UI installation passed asset, metadata,
configuration, service-mask and read-only closure checks, before and after browser
inspection. Actual authenticated acceptance then found an initial-load race:
authorize on Overview and immediately enter Printer hardware while status is
pending. Navigation invalidated the status epoch and marked reconciliation even
though only a read had been submitted. The panel remained unloaded. Private
browser failure/diagnosis is retained in `installation-r1/` under the integration
probe directory. No configuration write, output activation or reboot occurred.

The installed task includes a bounded repair to distinguish status response
validity from navigation/review validity. Route changes may allow a current
read-only load to finish; authority, edit and load transitions still reject stale
responses. Submitted mutations are never replayed. A missing local draft can be
populated from saved state when keeping selections, since there are none to lose.
The delayed initial-load browser regression covers the observed sequence.

The original software acceptance remains historical. The repaired controller,
regression evidence, exact one-file follow-up operation and final installed
observations require independent reviews under this same approved feature.
