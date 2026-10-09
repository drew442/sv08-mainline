# Persistent printer web stack

Replace current-boot temporary web units with image-staged normal boot services.
Preserve existing configuration, gateway credentials/account database and CA/SSH
identity. Provide fresh-image fail-closed authentication provisioning, using random
private credentials and loopback-only Moonraker; HTTPS Basic gateway covers static,
API and WebSocket routes. A root preparation/provisioning unit may configure web
files, but must not activate Klipper or other production output services.

Checks: focused source/auth/image tests; installed service and authenticated browser
acceptance before and after an actual reboot; unchanged hardware configuration,
CA and SSH identity, read-only root/boot, production masks and no MCU descriptors.
Source delivery uses self-validation. Exact installed access/boot operations require
separate independent consequential assessment before execution. No release image,
A/B update, recovery rewrite, physical commissioning or first print is claimed.
