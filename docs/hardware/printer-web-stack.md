# Persistent printer web stack

Normal image staging enables `sv08-printer-api.service` and
`sv08-mainsail.service`. These serve Moonraker and Mainsail independently of
physical Klipper startup. Debian's default nginx stays masked. Neither web
service pulls Klipper into startup; both run as `sv08` with private devices.
Existing boot-health and hardware commissioning gates remain applicable to Klipper.

The boot sequence prepares the selected persistent configuration, validates web
settings, starts loopback Moonraker, validates or provisions authentication, then
starts the CA-signed HTTPS gateway. Mainsail is available on port 8443; port 8080
redirects to HTTPS. Cockpit remains on port 9090. Certificate authority and SSH
identity are managed by the existing persistent identity service and schedule.
Network addresses acquired during boot enter the certificate through its accepted
10–20-minute reconciliation; trust against a newly acquired address can await that
scheduled refresh. The CA remains the stable identity.

On a fresh printer, authentication provisioning creates a unique random password
and a native Moonraker account. Retrieve the credentials in Cockpit's authenticated
Terminal with:

```sh
cat /data/sv08/moonraker-login.txt
```

The native browser authentication prompt protects all HTTPS routes, including
static files, API and WebSocket requests. The gateway supplies a private backend
API key; it removes browser Basic credentials before proxying to Moonraker and
preserves the browser's client address. Moonraker listens only on loopback port
7125 with forced login. No LAN clients receive implicit trust.

Authentication files under `/data/sv08/mainsail-auth` and the retrieval file are
private, outside website and Moonraker file roots. The account database belongs
to the selected persistent generation. Existing credentials, configuration and
hardware selections are retained. Unknown or inconsistent authentication state
fails closed rather than resetting an existing account. Changing the native
Moonraker password alone does not change the gateway password; coordinated password
rotation is a separate operation.

Generated hardware exports reference the managed gateway and identity paths;
credentials are provisioned by the host, never included in a hardware ZIP. The
web preparation service does not alter `printer.cfg`, hardware definitions,
calibration, firmware or device settings. Printing still requires appropriate
physical commissioning and calibration.

See [delivery acceptance](../features/persistent-printer-stack/evidence.md) for
source staging and named diagnostic-host installation/reboot evidence. This
software-stack acceptance does not qualify a flashable release or physical printing.
