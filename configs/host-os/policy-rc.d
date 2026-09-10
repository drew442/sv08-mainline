#!/bin/sh
# Keep daemon activation blocked in the image builder, but allow the supported
# writable-mode package workflow on a booted system. Printer units separately
# enforce their admission lock; this does not bypass that check.
if [ ! -d /run/systemd/system ]; then
    exit 101
fi
exit 0
