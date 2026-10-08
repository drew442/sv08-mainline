# Owner request — 2026-10-08

Persist a printer CA, sign service certificates with it, and offer the CA certificate in Cockpit so users can keep trusting the printer through service certificate changes. Persist the SSH host identity. Let owners upload SSH public keys and download/upload a printer identity backup through Cockpit. Recovery needs only a simple default password. Implement and complete this goal, then mark relevant project requirements complete using actual evidence.

This replaces any conflicting requirement for secure recovery authentication. The selected recovery account/password is `recovery` / `recovery`. It does not relax normal-host authentication or authorize hardware outputs.
