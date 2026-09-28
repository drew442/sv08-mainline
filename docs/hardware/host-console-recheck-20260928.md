# Test printer 01 console recheck, 2026-09-28

After the owner restarted Beelink, SSH to Beelink worked and its ping to the
printer's reserved `192.168.1.141` succeeded. The neighbour MAC was
`02:00:b2:76:83:5a`. Printer port 22 refused a connection. These observations
do not establish the running image, selected slot or installed eMMC identity.
The applicable owner-reported host PCB remains `H616_JC_6Z_V1.2` in
[test printer 01](test-sv08-01.md); it was not physically reinspected.

The CH340 device appeared as
`/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0` on Beelink and had no other
reader. Root opened it at the documented 115200 baud, 8N1, without hardware
flow control or DTR/RTS toggling. A 12-second receive-only capture obtained
205 bytes, including garbled text and repeated `read: Connection refused`
messages. A single carriage return followed by eight seconds of capture
obtained another 112 bytes, with the same error and no identifiable login,
shell or U-Boot prompt. No command, reboot or hardware write was issued.
Receive is demonstrated; a usable interactive console is **not** established.

A read-only GLKVM snapshot showed a blank 1024×600 frame. Beelink had no
listeners on NFS/RPC ports 111, 2049 or 20048, and its former staged NFS helper
path under `/tmp` was absent. The exported files remained present. A stalled
SD/NFS boot is therefore a possible explanation, pending confirmation that
the diagnostic SD is installed and a captured boot; it is not a measured boot
diagnosis. No NFS service was started during this recheck.

Private logs are retained on Beelink and mirrored under ignored `local/` on
Codex. Receive-log SHA-256 is
`6a340d9f26dbcbc7fd7eadbbfba5454f5dcc2da3d93bc0ccdc9316da748d98d0`;
Enter-probe log SHA-256 is
`263bbeff28b5f4e129f9411f9c730c071fd4b9869662979e515cb5e85a4d96f2`.
The [H12 intake](host-network-emmc-h12-intake.md) still requires current target
identity, a working console/network path and separately reviewed physical
handoff before any installed-eMMC reimage.
