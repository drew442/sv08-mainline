# Physical update qualification preparation

This offline composer prepares a source bootstrap and two signed-update inputs for the explicitly identified test-sv08-01 printer. It performs no deployment, signing or physical writes. The physical operation belongs to H13 in [coordinated tasks](../../hardware/coordinated-human-tasks.md), with its own independent consequential review.

The healthy revision 2 and unhealthy revision 3 share the exact board kernel, DTB, regenerated persistent-data initramfs and boot filesystem. The latter changes only release identity and a PATH-scoped health observation: `systemctl is-active sv08-prepare.service` reports inactive; other calls reach the real systemctl. The production fallback and bootloader remain unchanged. Five physical-output service masks are present in every root.

All copied roots include the current hardware, connections, definitions and source pages, catalog, starter/schema downloads and pinned public Klipper dictionary. Authentication secrets are excluded. A fail-closed account binding requires a coordinator-created, server-local 0600 seed before deployment; authentication consumers depend on it. Password replacement through this bind mount is outside qualification.

The environment writer retains its existing O_NOFOLLOW guard. Its canonical Linux node is `/dev/mmcblk2`; platform by-path identity and U-Boot MMC index 1 are separate observations. The coordinator must recheck the binding immediately before physical use.

Actual composition and both regenerated root images passed filesystem checks. Ten focused tests passed, including the actual backend rejection of symlinks. Preparation found and repaired independent boot filesystem IDs, a missing printer UI payload, and the by-path symlink incompatibility before any physical writes. Earlier receipts and root images were retained for diagnosis. Exact final hashes, tools, resource charges and limits are in [preparation.json](preparation.json).

These are offline and named-artifact results, not evidence of physical update success, operator recovery or a printing release. The recipe is recorded; bit-identical rebuilds have not been established. No private signing keys, account seeds, images or printer dumps are published.
