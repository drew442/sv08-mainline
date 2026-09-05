# Upstream sources

Initial intake: 2026-09-05. Five shallow direct submodules were cloned from their
upstream default branches. Gitlinks pin exact commits;
[`upstream-lock.json`](../upstream-lock.json) records the same revisions with
roles and review status. It is an intake manifest, not a complete build lock:
toolchains, OS packages, and transitive build dependencies remain to be selected.

| Submodule | Source | Role | Intake branch |
| --- | --- | --- | --- |
| `upstream/sovol-sv08` | [Sovol3d/SV08](https://github.com/Sovol3d/SV08) | Vendor reference, not the runtime update source | `main` |
| `upstream/klipper` | [Klipper3d/klipper](https://github.com/Klipper3d/klipper) | Host + MCU firmware | `master` |
| `upstream/sunxi-tools` | [linux-sunxi/sunxi-tools](https://github.com/linux-sunxi/sunxi-tools) | Host SoC diagnostic/recovery tools | `master` |
| `upstream/moonraker` | [Arksine/moonraker](https://github.com/Arksine/moonraker) | API service | `master` |
| `upstream/mainsail` | [mainsail-crew/mainsail](https://github.com/mainsail-crew/mainsail) | Web UI | `develop` |

Mainsail's default branch is development work. Its initial checkout is for
research; choose a reviewed release when assembling the first runnable stack.
No initial pin is hardware-validated. The parent has no remote configured yet.

## Initialize and inspect

```sh
git submodule update --init --depth 1
git submodule status
git ls-files --stage upstream/
```

Do not add `--remote` to normal setup/build commands: that selects new upstream
revisions instead of the parent's pins. Nested submodules are opt-in; Sovol's
snapshot includes optional services and a nested dependency declaration that
the initial intake does not need. Upstream builds may require their own nested
dependencies; inspect and initialize the specific ones required by that build.

Initial clones have shallow history to limit intake size. If research requires
older history, fetch it explicitly for the relevant submodule:

```sh
git -C upstream/klipper fetch --unshallow origin
```

## Update intentionally

1. Fetch the relevant upstream and select a specific release/commit after reading
   its changes. Record why it is needed and which profiles could be affected.
2. Check out the selected commit detached in that submodule. Keep upstream
   worktrees free of undocumented edits.
3. Review API/configuration changes and run the appropriate builds/tests.
   Update the compatibility record honestly; hardware testing is separate.
4. Update `upstream-lock.json` (commit, selection date/ref, validation status) and
   stage the submodule path. A URL change also requires `.gitmodules` changes.
5. Review and commit the gitlink, manifest, and supporting evidence together.

No automated process should promote an intake pin to supported status.

## Next candidates

Evaluate Armbian's build framework, upstream Linux, U-Boot, and TF-A when selecting
the host image pipeline. Add the actual source repositories consumed by that
pipeline, avoiding redundant full kernel trees. The linux-sunxi organization is
a useful tooling/documentation source; a repository name alone does not establish
that a kernel tree is the current Linux mainline.

Evaluate Katapult only after documenting each MCU's existing flash layout and
recovery method. Evaluate CB1 material as a related platform reference; record
SV08 differences explicitly. Optional display/camera/install tools can follow
once the core stock profile is validated.
