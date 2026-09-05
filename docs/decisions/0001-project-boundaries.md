# 0001: Stock-first profiles and pinned upstream inputs

Date: 2026-09-05

Status: accepted project direction

## Context

The repository must support conversion of stock SV08 electronics first while
allowing modified electronics later. Current upstream software evolves separately
from vendor snapshots, and published schematics do not prove installed revisions.

## Decision

Represent hardware combinations explicitly. Keep stock hardware as the first
research profile and require separate evidence for modified combinations. Keep
upstream source in Git submodules with exact pins, and keep original integration
work outside those checkouts. Track Linux/boot support and Klipper support as
separate milestones. Label initial source intake and profiles unvalidated.

Prefer upstream behavior; write custom code only for a demonstrated gap. Preserve
the ability to recover the original system as part of conversion design.

## Consequences

Updating a dependency requires a reviewed gitlink and manifest change. A new
profile needs component identities and a test record. Initial work focuses on
inventory and compatibility before build/flash automation. The OS, MCU bootloader,
and project license remain separate decisions.
