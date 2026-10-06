# Installed Connections graph

Source `113bb70`, integrated on main at `7e83b76`, installed on the spare eMMC A on 2026-10-06. Independent hash-bound installation assessment passed with the recorded closure conditions. Six existing Cockpit assets (121,742 bytes) changed; no runtime, catalogue, configuration, boot or service assets changed. Exact rollback is retained at `/data/sv08/printer-connections-graph-backup-20261006`.

The authenticated installed Cockpit browser passed: separate Connections sidebar route; temporary factory composition into an unsaved browser draft; 27 nodes covering 24 devices plus host/controllers; controller transport, internal temperature, motor and SPI inspection; filtering/table/zoom/highlighting; responsive containment at 390/1024/1440; two seconds without graph DOM mutations; reload discarding the temporary selection. Saved hardware state was identical before and after.

[Receipt](installed.json) records hashes and actual checks. Root/boot read-only, data writable, PSU off, seven service masks/inactive units, absent live configuration and unchanged unrelated assets/state were observed after installation and browser acceptance. Installer unit inactive with MainPID zero; own tunnel and offline fixture closed.

No Save, Apply, connector edit, output, firmware or printer service operation occurred. This is UI/software acceptance, not physical wiring verification or a printing release. Rendering is browser-local; idle graph work and additional printer RPC were absent in the offline sample. No ARM64 CPU benchmark is claimed.
