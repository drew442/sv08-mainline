# Current selected package reproducibility qualification

## Outcome

Two fresh builds of every selected package produced identical complete artifact bytes. Two fresh Klipper helper and MarkupSafe native source builds also match each other and their selected hashes. No package or runtime recipe required a change. This qualifies the recorded selected-package recipes and toolchain; it does not qualify a complete boot image or arbitrary build environments.

Build source: `ef565eb5e4293abd42a351a8fd1548cda9542f4f`. [Machine-readable results](results.json) record exact source/configuration/patch hashes, clean pinned upstream revisions, source archive and wheel hashes, toolchain versions/binary hashes, commands, elapsed times, log hashes, distinct artifact paths and package metadata. The later documentation candidate preserves those build inputs; it is not substituted for the build-source identity. Historical evidence is unchanged.

| Artifact | Bytes per build | SHA256 of both outputs |
| --- | ---: | --- |
| admission | 16,644 | `5310237a0d1b18f550ec9f3b7856436b9b99adeed37dfd2deec19860eea6af60` |
| klipper | 5,701,648 | `e8c07d7b85403f3f55944c75e4664c95df005ecdb8f32acc84d97f1b1cbd4806` |
| moonraker | 11,799,396 | `5bbc65c0441391837859c9131829b241f2a91a3f7e028221d1a5e8bd08f226e1` |
| klipperscreen | 2,850,722 | `a35f4e732da35bacce52ed858ded703129e6d28fb1d006e1a5c252edbbf4a1c6` |
| mainsail | 2,493,762 | `67d0f64595d6f8c8570d8152ebdf8b0e21cdb16965db2e8bb5ceaecf80d75c50` |
| rauc | 191,768 | `fc1d757cbe91b39d59f1e4f6634d77016748929ac17849f2047935a4f620f0ec` |
| helper | 327,352 | `d8cad1e9601bfca7a0c50dd3783d99809284eadc6561d80072f84e7694742835` |
| markupsafe | 30,165 | `f7d4bb143ff52a492af33af7e89051c480c8424f3083fb5b98f52729b140c8fa` |

## Method and coverage

The selected versions are admission0.1.0-3, Klipper0.0+gitf0892d82-2, Moonraker0.11.0+git985c1d0b-2, KlipperScreen0.0+git3791fdf7-2, Mainsail2.19.0+git32f99e1c-10 and RAUC1.15.2-0sv08.2. Both package metadata and complete bytes were compared; paths and inodes are distinct. Qualification did not compare only extracted payloads or omit archive metadata. Source/configuration, original archives/wheelhouses and clean upstream pins were rechecked after the builds.

RAUC compiles the exact patched C source twice with Meson/Ninja, and Mainsail performs two fresh offline npm installations and Vite source builds. Klipper source packages incorporate independently compiled helper bytes; Python applications archive their pinned source and assemble new virtualenvs from exact locked wheels. These application assemblies do not rebuild supplier wheels. Klipper helper uses the pinned cross GCC13.3.0 toolchain; MarkupSafe uses the pinned ARM64 Python3.13.5/GCC14.2.0/setuptools78.1.1 environment, with actual backend contents verified by the recipe. Actual complete ARM64 package lists and seven compiler/interpreter/build-tool binary hashes match between the two roots. ARM64 compilation and package commands run through installed userspace emulation, not an ARM64/KVM boot fixture.

Two private namespaces use separate new writable layers over read-only bind mounts of the retained Debian baseline and compiler layer. Existing layers and source inputs are preserved. Each package uses a distinct new workspace; the second root does not reuse the first root's compiler products, virtualenvs or package output. The two ARM64 jobs share only read-only source/toolchain inputs. Network is disabled in those namespaces. Mainsail uses an assigned copy of the previously populated public npm cache with offline mode and empty explicit npm configuration files; each npm install/build is fresh. No dependency tools were installed on the host.

The A harness copied the byte-identical selected MarkupSafe wheel because of a filename-case mismatch; the corrected B harness explicitly uses its newly compiled wheel. Both fresh source-built wheels and both actual packaging input wheels have the exact selected hash. This is recorded rather than claiming A consumed a different input.

## Reproduction

Use the [existing reproducible-build recipes](../../development/reproducible-builds.md), exact inputs/toolchains in results.json, fresh assigned baseline/compiler layers and fresh `a`/`b` workspace names. Do not point a compiler root at a running printer. `$CANDIDATE` means this source checkout, `$CHECKOUT` the retained public build-input checkout, `$SCRATCH` a new coordinator-owned artifact directory, and `$PRIOR_INPUTS` the recorded immutable source/wheel inputs. These markers describe the measured resources and may be relocated after verifying their hashes.

For each side, execute the following supported entrypoints with its own fresh work paths:

```sh
python3 scripts/package_update_admission.py --work build/admission-a --execute
python3 scripts/build_klipper_inputs.py --kind helper --source upstream/klipper --work "$SCRATCH/helper-a" --execute
python3 scripts/build_klipper_inputs.py --kind markupsafe --source "$MARKUPSAFE_SDIST" --compiler-root "$COMPILER_ROOT" --work "$COMPILER_ROOT/tmp/repro-markup-a" --build-venv /tmp/closure-backend --backend-wheelhouse "$BACKEND_WHEELS" --execute
python3 scripts/package_rauc.py --archive "$RAUC_ARCHIVE" --builder build/compiler-a --work build/rauc-a --execute
python3 scripts/package_klipper.py --work build/klipper-a --wheelhouse "$SELECTED_WHEELS_A" --helper "$SCRATCH/helper-a/c_helper-aarch64.so" --execute
python3 scripts/package_python_app.py --app moonraker --work build/moonraker-a --wheelhouse "$MOONRAKER_WHEELS" --execute
python3 scripts/package_python_app.py --app klipperscreen --work build/klipperscreen-a --wheelhouse "$KLIPPERSCREEN_WHEELS" --execute
NPM_CONFIG_OFFLINE=true python3 scripts/package_mainsail.py --work build/mainsail-a --node-archive "$NODE_ARCHIVE" --execute
```

Compiler/chroot commands require the assigned disposable root and coordinator privilege. Packaging baseline workspaces require `rootfs` and `refresh-complete`, with fresh app paths as enforced by their builders. Create the Klipper wheelhouse with exactly its locked wheels, explicitly using the rebuilt lowercase `markupsafe-...whl`. Set the Mainsail copied-cache and empty configuration paths explicitly as recorded in the results environment overrides. Repeat with fresh B paths, then use whole-file `cmp` and SHA256 for each of the eight pairs; require matching selected package metadata and native-input hashes. Retained namespace/record/comparison harness hashes identify the actual measured invocations in results.json.

## Regression checks, retained attempts and resources

29 checks pass across test_klipper_build_inputs, test_package_klipper, test_package_rauc, test_python_app_package, test_package_update_admission_license and test_package_policy, including input identity/hash and operation refusal tests. The combined run exited0 in0.084seconds. Every accepted build exited0, including each offline pip dependency check and RAUC version check. Complete candidate diff and machine-readable results were inspected; `git diff --check` passes.

Initial ordinary-user admission attempts failed on the newly root-owned build parent before generating artifacts. Corrected scoped sudo invocations passed; failed logs/receipts remain. A read-only compiler hash query assumed the wrong cc1 location; querying GCC's actual program path corrected it. Neither correction changed a production recipe or protection. Retained sanitized command logs, input manifests, source/output pairs and harnesses live in the assigned scratch/build directories; no binary artifacts are committed.

Accepted primary build/preflight invocations measured 1215.087 cumulative process-seconds; failed admission attempts add 0.147seconds. Add a conservative600-second charge for research, checks, workflow and other unmetered commands. Primary allowance7200seconds/12GiB remains unexhausted; conservatively charge4GiB generated including temporary/deleted data, cache copies and source clones. Observed retained build1.9GiB and scratch127MiB; free space49GiB before and46GiB after. No image copies/builds or remote mutations. Both build jobs terminated successfully and their assigned mounts were cleaned up.

One fresh named project_researcher child (`/root/repro_intake`) performed source/resource tracing at the repository default requested Sol/low route. Effective runtime settings and native thread ID were not exposed; no model-savings or independent-review claim. Coordinator executed all builds, checks, diff/evidence inspection and publication under self-validation.

## Limits

This is same-host, fixed-toolchain selected-package reproducibility, with distinct fresh build paths/roots and canonical source epochs. It is not cross-toolchain/platform reproducibility, a fully hermetic compiler bootstrap, full-image reproducibility, supplier/distro source-rebuild qualification or license compliance. Unchanged prior streaming-form-data/Pycairo proof remains separately scoped. No printer access, service activation, hardware/printing/recovery-execution qualification, merge or deployment occurred. Full recovery-stack qualification remains deferred for the separate ARM64/KVM host.
