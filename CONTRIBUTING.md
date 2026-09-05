# Contributing

Start with the [project definition](docs/project.md), [roadmap](docs/roadmap.md),
and [agent instructions](AGENTS.md); the same engineering expectations apply to
human and AI contributions.

Keep each change focused on a documented problem. Include the affected hardware
profile, source revisions, behavior before/after, checks performed, and remaining
unknowns. Mark experiments as experiments. A successful build does not establish
hardware support.

For hardware research, cite the source and its revision/page, record conflicting
evidence, and distinguish the published design from the actual installed board.
Use the [profile template](profiles/TEMPLATE.md) for new combinations.

For code, prefer a small upstreamable change over a broad fork. New patches must
name the upstream base commit, explain why configuration cannot solve the issue,
and include meaningful regression coverage. Put architecture decisions in
`docs/decisions/` using the first decision as a format example.

Follow [the upstream workflow](docs/upstreams.md) for dependencies. For docs-only
changes, check whitespace, relative links, and JSON syntax; no printer access is
needed. Firmware, device-tree, and configuration changes need the build and
hardware checks listed in the roadmap before they can be called supported.

Keep local artifacts in `artifacts/`, backups in `backups/`, and per-printer
details in `local/`; all three are ignored. Publish only intentionally redacted
evidence. Check the applicable upstream license before copying material and
retain attribution. Original project licensing is still an open decision.
