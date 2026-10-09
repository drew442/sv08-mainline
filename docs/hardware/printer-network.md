# Cockpit network administration

Open **Network** in the left menu and enable Cockpit administrator access. The
page shows interfaces, connection names, IPv4 addresses, gateways and DNS servers.
Choose a saved connection to edit it while keeping its password, or create a new
connection. Wi-Fi scanning supports open networks, WPA personal and WPA3 personal;
enterprise and WEP provisioning are not supported by this form. Password entry
requires HTTPS and passwords never appear in the change review or status response.

DHCP is the default. Expand **Advanced IPv4 settings** for static addresses with
prefixes, a gateway and custom DNS. IPv6 is automatic for new connections and
retained for copied existing profiles. Printer names are lower-case DNS labels;
the optional fully qualified name must begin with that label. Naming updates the
persistent hostname, local hosts aliases and running kernel hostname. It does not
create a DNS record on the router or DNS server.

Review and apply a connection or name change, then press **Keep changes** within
180 seconds. If the browser disconnects, reconnect at the new address and reopen
Network to recover the pending confirmation. The page never redirects itself.
NetworkManager checkpoints restore the previous device settings on timeout. A
root service checks the durable journal every 60 seconds, restores naming and
removes the unconfirmed candidate; failed cleanup retains the journal for retry.
At boot, a post-command of `sv08-prepare.service` restores unconfirmed persistent
profiles, hosts files and the kernel name before NetworkManager or identity starts.
Unknown/corrupt journals are refused; this is not an automatic corruption repair.
Original profiles are preserved. The form limits stored profiles to 64 and keeps
private profile/journal storage administrator-only.

User-triggered network changes issue service certificates from the existing
printer CA for intended names/static addresses, then include actual leased
addresses and publish/reload after activation. Old certificate names remain
available during the rollback window. The CA, SSH host identity and authorized
keys do not change. The accepted periodic identity reconciliation schedule remains
boot, 10–20 minutes after boot, and daily. Existing browser sessions can disconnect
when the Cockpit certificate reloads; the pending journal survives that session.

**Restart** requires a separate review and atomic Klipper idle admission. An
unmanaged active Klipper service, a transitioning service, missing idle admission,
or a pending network change refuses restart. The diagnostic exception requires
both known Klipper units to be masked and inactive. A successful reboot request
keeps the admitted printer services stopped.

Implementation: `runtime/sv08_network.py`, `ui/host/network.js`, the rollback
service/timer and host image integration. See the [delivery evidence](../features/cockpit-network-administration/evidence.md)
for actual source, ARM NetworkManager, browser and installed checks. Physical
Wi-Fi migration, destructive network faults, printing and release qualification
remain separate from this software delivery.

Upstream interfaces: [NetworkManager checkpoints](https://networkmanager.dev/docs/api/1.48.0/gdbus-org.freedesktop.NetworkManager.html)
and [nmcli reference](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/nmcli.html).
