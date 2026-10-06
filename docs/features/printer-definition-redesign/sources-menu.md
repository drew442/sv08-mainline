# Definition sources sidebar — 2026-10-06

Owner request: “move definitions sources to the left side menu so it is its own section”.
Source commit `1dd0150` makes Definition sources a separate main section under the
left navigation, with route `#definition-sources`, active sidebar state and direct
reload/Back/Forward support. The hardware-page action is removed. Source feedback
is visible in its own section; host refresh failure does not disable its controls.
Source semantics and backend remain unchanged.

Self-validation: 12 staging tests pass, Node syntax passes and the complete Chromium
Store/Budget fixture journey passes, including the new sidebar route/reload and
existing source add/disable/remove/offline-retention checks.

Installed six exact UI files (101,955 bytes) after an independent high-consequence
assessment and a passing remote dry run. Installed host-specific HTML/JS is retained
outside the marked panel, one new sidebar button and two scoped button exclusions.
The bounded systemd operation completed with hash readback, private rollback backup,
root/boot RO, dataRW, PSU OFF, unchanged saved state/unrelated assets and seven
masked inactive printer services. No live configuration or output action occurred.
Post-browser observations confirm those conditions remain true. The installation
unit is inactive with MainPID0; the temporary test tunnel is closed.

Authenticated installed Chromium acceptance passes for the separate sidebar entry,
active state, hidden hardware page, removed former action, Back/Forward, source
section reload, factory choices, single shell and saved-state retention. Desktop
and narrow layouts have no page-wide overflow. Raw screenshots/profiles and private
backup originals are excluded. The exact sanitized receipt follows.

```json
{
  "installed": true,
  "source_commit": "1dd0150cb44a3c0bd4670d8eea56c3c42771af35",
  "payload_files": 6,
  "payload_bytes": 101955,
  "after": {
    "/usr/share/cockpit/sv08-printer/app.js": {
      "sha256": "3f2b3f2008fe9ff3cff8aedc338b9ea605bdeb00c5676060696d61092d562503",
      "mode": 420,
      "uid": 0,
      "gid": 0
    },
    "/usr/share/cockpit/sv08-printer/style.css": {
      "sha256": "17b87897854c7bc893cd9c841ec8ab2e5e3db9bc01cec7811ffe88f919c45262",
      "mode": 420,
      "uid": 0,
      "gid": 0
    },
    "/usr/share/cockpit/sv08-printer/panel.html": {
      "sha256": "7edbf2f8d046b28d1cde3e36ef6c39c55c430dc9c059963830d043f15de5b810",
      "mode": 420,
      "uid": 0,
      "gid": 0
    },
    "/usr/share/cockpit/sv08-host/navigation.js": {
      "sha256": "0a3e5330e2e45695037009b60e5d73312266662f6710ee0227cd579b50ff7e08",
      "mode": 420,
      "uid": 0,
      "gid": 0
    },
    "/usr/share/cockpit/sv08-host/index.html": {
      "sha256": "38dfcd655aff9b4d19ac525054a78a2f30f99aa15f138aec307af792d3c993fa",
      "mode": 420,
      "uid": 0,
      "gid": 0
    },
    "/usr/share/cockpit/sv08-host/app.js": {
      "sha256": "70f2b7f0c4f154a8ddd25ab69f2ff8ae1663ffa2481142a88de5763d59e59bd2",
      "mode": 420,
      "uid": 0,
      "gid": 0
    }
  },
  "reviewed_inputs": {
    "deploy.py": "621ff3de39399164f1ed74a40a64c63e795e2fa405e49995ad1025e385107314",
    "packet.json": "d3866ad3283153e5480b8be4b881ddd5abee506bd9586f5234e9cf7a0bb14084",
    "target-before.json": "ac526b5ffddb6e19c2c010b31fbc32a43309a3b368b2aa8180e15ee91a396884",
    "prepare.py": "d660f9928c94334fe0db62d90840f66d7ed74322c787a642d66b1367de6af070",
    "operate.py": "26bda7d04146c43d7780142da36301f123ab4458dc076a7a95601492bf262ad7",
    "inspect-target.py": "762b230a7bf7a278f0b511319d760d6332f193007289c79ab3bbc70d648d1f5b",
    "preparation.json": "00b8e26022210aeaf1cd6ccc5434017a990f16234815312ec7549850fc4ab3fa"
  },
  "browser": {
    "passed": true,
    "authenticated": true,
    "hardware": false,
    "mutations": false,
    "checks": [
      "seven component cards, factory-only bed choices, advanced collapsed",
      "source manager and logical connections open without mutations",
      {
        "width": 1440,
        "height": 900,
        "overflow": false
      },
      {
        "width": 1024,
        "height": 600,
        "overflow": false
      },
      {
        "width": 390,
        "height": 844,
        "overflow": false
      },
      "installed ARM64 helper status, authenticated elevation, reload; saved state unchanged"
    ]
  },
  "root_boot_read_only": true,
  "data_read_write": true,
  "state_masks_and_unrelated_assets_preserved": true,
  "psu": "OFF",
  "live_configuration_present": false,
  "backup": "/data/sv08/printer-sources-menu-backup-20261006",
  "temporary_tunnel_closed": true
}
```
