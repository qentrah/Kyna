# Safety audit and release verification

PR #6 merged as `f21e771` after [core platform CI](https://github.com/qentrah/Kyna/actions/runs/38344931584) and [five desktop native targets plus Android ARM64 cross-compilation](https://github.com/qentrah/Kyna/actions/runs/38344931588) passed at `9d33bfb`. PR #7 adds repository generation, application icons, explicit assets, source-path containment and portable Linux BLAS dispatch.

The existing C++ compiler, HIR/MIR/bytecode pipeline and VM remain in place. This work adds application packaging and typed native bindings; it does not add a native-code backend.

## Checked contracts and execution

| Area | Verification |
| --- | --- |
| Modules and types | `verify_type_contracts.py` covers checked named/namespace/aliased contracts, private type dependencies without private-name exposure, generics, nullability, type-only erasure, callback compatibility, duplicates, cold/warm caches, transitive invalidation and forged dependency-sidecar rejection. |
| Type ownership | Intern pools own allocations, release them at shutdown and preserve stable identity. Signature interning includes receiver identity. Destructor-count checks and Linux LeakSanitizer cover the former leaks. |
| Mathematics | Numeric parity tests cover integer overflow, signed boundaries, division/remainder, exact mixed int/float comparisons above 2^53 and around 2^63, evaluation order and short-circuit side effects. |
| Control flow | Fixtures cover constant compatible switch cases, duplicate cases/defaults, default ordering, adjacent large integer cases, nested labeled loops and function boundaries. |
| Diagnostics and tooling | Stable codes and spans preserve `kyna.diagnostic/v1`. Extension checks cover imported files, unsaved overlays, stale processes, Unicode ranges, type imports/re-exports, native/path dependency navigation and malformed/executable output. Console tests cover streams, formatting, redirected output and color. |

## Native ownership and package safety

| Area | Verification |
| --- | --- |
| ABI and conversions | Versioned C ABI 2 contracts are shared by checking and registration. Runtime tests validate arguments/results even through `any`, arrays, callback arity, finite numeric input, dimensions, ABI mismatch and translated C++ exceptions. |
| Callbacks/resources | Retain/release, nested invocation roots, GC stress, stale/foreign handles, child ownership, exactly-once destruction and shutdown have regression coverage. Unsubscription also removes lifecycle metadata. |
| Qt embedding | The Qt application outlives the lazily created QObject event bridge. Host/thread validation and two consecutive sessions are tested. UI callbacks remain synchronous on the UI thread. Windows adapter images stay loaded when required by Qt global metadata; descriptor-only installer loading remains unloadable. |
| Windows relocation | The GUI loads only inventoried root DLLs, reuses host modules, rejects unlisted DLLs and recovers from malformed inventories. QML engines commit after configuration succeeds. Application tests remove original Qt/vcpkg/build directories from PATH. |
| Installation | SHA-256 and installed-file rechecks, malicious/traversal/drive/control-character archive names, links, oversized members, lock rollback and removed dependencies have fixtures. Complete runtime archives are used for ML; authored self-contained bindings cover the legacy single-file path. |
| Application staging | Declared assets reject missing, absolute, traversing and external-symlink paths. Project/dependency source symlinks must resolve within their owner; internal aliases retain their authored paths. Rejected builds remove partial output. |
| Icons | Actual image decoding rejects missing/corrupt icons before Qt accepts a lazy icon object. KNATIVE1003 is covered by native package tests. |
| Repository generation | Names/remotes are validated, existing directories are protected, and subprocesses receive argument vectors. Public GitHub creation requires explicit `--github OWNER/REPO`. KPROJECT1001–1003 preserve structured errors and exit status 2. |
| ML portability | Linux x86_64 OpenBLAS uses baseline common code and runtime CPU dispatch. CI runs the C++/Kyna regression oracle with `OPENBLAS_CORETYPE=NEHALEM`, covering the earlier cached host-specific illegal-instruction failure. |
| Release integrity | The publisher rehashes every asset before GitHub operations, rejects duplicate/malformed/escaping/unlisted checksum entries and requires complete manifest coverage. All 28 local release-packaging tests pass. Published releases cannot be replaced. |

## Evidence

Local verification includes 57 Release CTests, the 62-test optional-library suite, focused GUI embedding tests, architecture/extension verification and SDK-isolated relocated applications. Earlier Debug and Address/Undefined Behavior sanitizer baselines also passed; macOS does not provide LeakSanitizer in this setup. The exact final hosted results are recorded in [release notes](releases/v1.0.16.md).

[Kyna Music](https://github.com/qentrah/kyna-music) separately passes [Windows x86_64, Linux x86_64 and macOS ARM64 application CI](https://github.com/qentrah/kyna-music/actions/runs/38350021366) at `72a79fa`. Tests exercise actual decoded audio, advancing playback, callbacks after GC, search, playlists, queue, persistence and packaged launchers. Its downloaded macOS CI archive also passed local playback, persistence, launcher and signature checks.

[App recordings](videos/README.md) show desktop GUI/geometry/regression and Android ARM64 lifecycle/callback/shutdown on an Android 14 emulator. Native workload measurements in [the performance record](performance/native-workloads-checkpoint.json) verify results before timing; noisy hosted results are informational.

## Remaining distribution limits

- Production signing/notarization credentials and stable-release approval are not configured. Prepared releases remain drafts; npm publication belongs to the owner.
- Android ARM64 cross-compilation passes separately from application smoke. Local physical-host emulator smoke passed; the dedicated physical CI runner is not provisioned. Physical devices and other Android versions remain unverified.
- Dependency inventories, notices and verified source materials support final license clearance; they do not replace it. Qt and CGAL have package-specific conditions.
- Rams `quick_review` with `via: rules` was requested after UI edits and returned exhausted workspace credits with no findings. Direct app/extension verification is not Rams approval.
- Concurrent installation and crash recovery across two lockfiles remain outside the current guarantee. Other OS/CPU combinations require their own application smoke tests.
