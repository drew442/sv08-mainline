# Mainsail access in Cockpit

Provide password, no-login and browser client-certificate access choices. Keep Moonraker loopback authentication and Cockpit/SSH administration independent. Issue password-protected, one-time PKCS#12 downloads against the persistent printer CA; allow certificates to be revoked. Persist policy and validate/reload the web gateway with recoverable failures. Install while preserving the current password mode and hardware gates after exact-operation assessment.

Acceptance: meaningful backend crypto/access/recovery tests, privileged Cockpit journeys, source/staging regression checks, and named diagnostic installation preserving access. No printer activation or release claim.
