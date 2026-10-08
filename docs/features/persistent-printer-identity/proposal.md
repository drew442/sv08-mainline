# Persistent printer identity

Preserve the current SSH identity while introducing a persistent printer CA. Issue and renew service certificates from the same CA. Cockpit exposes CA download, authorized SSH public-key management and a reviewed private identity bundle backup/restore. Atomic generation selection preserves the previous identity across failed restore. The bundle contains CA and SSH host authority plus authorized public keys; it excludes accounts/passwords, network configuration, printer calibration and unrelated user data.

Implement boot/staging integration, simple recovery/recovery password access, focused cryptographic/restore/SSH/UI checks and isolated ARM/service acceptance. Assess exact installed identity migration independently before changing live service certificates or access. Mark only the supported identity/access requirements complete; retain unrelated onboarding/network/release and physical acceptance gaps.
