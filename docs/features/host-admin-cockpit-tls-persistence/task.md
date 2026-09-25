# Small fix: persist Cockpit's TLS material

The 2026-09-25 v5 physical boot reached the login prompt and SSH, but Cockpit
failed when its certificate helper tried to write beneath immutable `/etc`.
This task corrects the already accepted local host UI behavior under ADR 0010;
it does not add a new UI capability or authorize hardware changes.

## Bounded change

- Stage Cockpit's supported certificate directory as
  `/data/sv08/system/cockpit/ws-certs.d`.
- Initialize that real directory on `/data`, root-owned and mode 0700, during
  early boot before Cockpit can generate or read TLS files.
- Preserve generated certificate/key files on repeat initialization and across
  A/B slot changes. Never overwrite a nonempty package directory or unexpected
  symlink during staging.

## Acceptance checks

1. Staging tests accept a missing/empty package directory and the exact existing
   persistence link; reject nonempty or unexpected-link conflicts without
   changing their contents.
2. State/boot tests prove the persistent directory exists, has root:root mode
   0700, rejects a symlink, and retains a fixture certificate/key across repeat
   initialization and permission preparation.
3. Disposable ARM64 Cockpit boots with root mounted read-only and `/data`
   writable; the socket starts, HTTPS responds, and Cockpit's generated cert/key
   land only under the persistent path.
4. Physical Cockpit TLS behavior remains open until a later reviewed candidate
   boots; no reboot or write to the currently installed eMMC is part of this task.
