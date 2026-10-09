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

The default browser password prompt protects all HTTPS routes, including
static files, API and WebSocket requests. The gateway supplies a private backend
API key; it removes browser Basic credentials before proxying to Moonraker and
preserves the browser's client address. Moonraker listens only on loopback port
7125 with forced login. No LAN clients receive implicit trust.

Authentication files under `/data/sv08/mainsail-auth` and the retrieval file are
private, outside website and Moonraker file roots. The account database belongs
to the selected persistent generation. Existing credentials, configuration and
hardware selections are retained. Unknown or inconsistent authentication state
fails closed rather than resetting an existing account.

Cockpit's **Mainsail access** section manages the browser gateway independently of
Cockpit/SSH administrator access and the private Moonraker account. Choose Password
and enter a new password (at least eight characters), or explicitly choose No login.
No login allows anyone who can reach Mainsail to use its API and control the printer;
HTTPS remains enabled. Changing the browser password does not change the native
Moonraker credentials in the original retrieval file. The original file therefore
only describes the initial browser password after a later Cockpit password change.

For certificate access, generate a labelled browser client certificate and download
its password-protected `.p12` file. Import it into your browser/device's personal
certificates, then separately select Client certificate and apply. Issuance alone
does not change the login method. The certificate is signed by the persistent printer
CA, has client authentication usage, and expires after one year. Keep the download
and its password private: its private key is delivered once and is not retained by
the printer. A lost download requires a new certificate; revoke the old one.

Certificate mode requires both a valid CA chain and a listed, unrevoked certificate
fingerprint on static, API and WebSocket routes. Revoke certificates from Cockpit.
A revocation blocks new requests/connections after the gateway reload; existing
WebSocket sessions can remain until disconnected. Cockpit's own login stays available
if all client certificates are revoked, lost or expired. It can issue replacements
or restore password access. After restoring a different printer CA, Cockpit reports
that existing client certificates belong to the previous authority. Generate new
certificates to replace that trust and revoke the old clients, or select another
access mode. The running gateway keeps its last applied client trust until that
explicit change; boot provisioning refuses certificate mode with a mismatched CA.
Ordinary server certificate renewal keeps the CA and browser certificates valid. CA trust on client
devices remains a separate import from the personal client certificate.

Private root-owned policy lives in `/data/sv08/system/mainsail-access/policy.json`;
service-readable gateway hashes and public client CA are rendered under
`/data/sv08/mainsail-auth`. Updates keep a bounded durable recovery transaction,
validate nginx before reloading, and restore prior access on a rejected change.
Boot provisioning reconstructs accepted managed state without resetting passwords.
Passwords travel through Cockpit's privileged channel and are stored as salted
hashes for the gateway; exported private client keys require an HTTPS Cockpit session.
Identity backup bundles back up the CA/SSH authority, not browser access policy or
client private keys. Back up downloaded client certificates separately.

The gateway uses upstream [nginx client-certificate verification](https://nginx.org/en/docs/http/ngx_http_ssl_module.html)
and [OpenSSL PKCS#12 export](https://docs.openssl.org/3.0/man1/openssl-pkcs12/).

Generated hardware exports reference the managed gateway and identity paths;
credentials are provisioned by the host, never included in a hardware ZIP. The
web preparation service does not alter `printer.cfg`, hardware definitions,
calibration, firmware or device settings. Printing still requires appropriate
physical commissioning and calibration.

See [delivery acceptance](../features/persistent-printer-stack/evidence.md) for
source staging and named diagnostic-host installation/reboot evidence. This
software-stack acceptance does not qualify a flashable release or physical printing.
