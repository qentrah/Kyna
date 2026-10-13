# Safety and native-library upgrade status

Current status: [PR #6](https://github.com/qentrah/Kyna/pull/6) is merged. Its final core CI and all five desktop native package jobs passed at `9d33bfb`; Android ARM64 cross-compilation passed. Earlier failure reports below are historical checkpoints. Production signing, license clearance, physical Android CI and Rams review credits remain external release gates.


Checkpoint: 2026-10-11, PR [#6](https://github.com/qentrah/Kyna/pull/6).
Version 1.0.16 is prepared; no release tag or npm publication has been created.

## Implementation

The existing C++ compiler, HIR/MIR/bytecode pipeline and VM remain in place.
Checked module contracts preserve aliases, exported interfaces, generics, inferred
bindings and type-only declarations. On-disk export caches include source and
transitive dependency contracts plus the compiler/checker build fingerprint. Contracts live in the user-local cache;
dependency-provided sidecars are ignored.
Explicit `any` remains an escape hatch; native calls still validate conversions.

Integer arithmetic, signed boundaries, exact mixed numeric comparisons, switch
case compatibility/duplicates/default ordering, function boundaries, evaluation
order and short-circuit behavior have regression coverage. Diagnostics preserve
`kyna.diagnostic/v1` and carry stable codes and source locations.

The extension is split into execution, diagnostics, commands, views and language
features. Unsaved overlays, stale processes, imported-file diagnostics, Unicode
ranges, type imports/exports, re-exports and native/path package navigation are
covered. Console output and color tests cover redirected output and terminal use.

C ABI 2 provides typed exports, runtime conversion checks, rooted retained
callbacks, resource leases, thread affinity, stale-handle rejection, shutdown and
exception translation. Native installation verifies archive checksums and every
installed file. Reported installation failures restore source/native locks.
`ky build` compiles authored C++ bindings and packages runnable applications.

Qt Quick GUI, CGAL points/hulls/mesh inspection and mlpack linear regression are
real optional libraries. Relocated payloads include shared dependencies, Qt QML
imports/plugins/framework resources and license notices. Bash, PowerShell and npm
retain these payloads; npm consumes the same release archives and SHA256SUMS.

## Verification and evidence

- Fresh local Release: all 57 CTests passed, including release-gate rejection tests.
- Fresh optional-library configuration: all 62 CTests passed, including Qt host lifetime/thread contracts.
- Fresh Address/Undefined Behavior sanitizer configuration: all 57 CTests passed
  after the final compiler/cache changes. LeakSanitizer is unavailable on this macOS host.
- Thirteen focused extension tests, six npm installer tests, architecture and
  extension verification pass. VSIX 1.0.16 packages successfully.
- Real relocated applications exercise GUI callbacks/GC, geometry, regression,
  checked imports, verified installation and packaged `ky build` launchers.
- [App recordings](videos/README.md) show desktop GUI + geometry + regression and
  Android ARM64 lifecycle/callback/shutdown smoke on an Android 14 emulator.
- [Safety audit](safety-audit.md), [portable packaging](portable-packaging.md),
  [dependency inventory](native-dependencies.md) and
  [native workload measurements](performance/native-workloads-checkpoint.json)
  describe correctness, packaging and measurement scope.

Final compiler checkpoint `607fb61` passes full Linux Release, Debug and
ASan/UBSan CI with LeakSanitizer enabled, and macOS core portable CI. Native
application/relocation checks at `9d870a8` pass Linux x86_64/ARM64 and macOS
x86_64/ARM64. Windows core tests and portable installation now pass at `835ca2d`
([run](https://github.com/qentrah/Kyna/actions/runs/38111562875)); the scanner excludes
OS DLL recursion while retaining MSVC redistributables and avoids app-local self-copy. Windows GUI still faults under both offscreen and native
backends; exception-stack diagnosis is running. Final Windows packaging and
application retries are required. Android uploads are flat, and the hosted
`9d870a8` APK passes the refreshed local emulator lifecycle recording.

## Remaining release gates

1. The merged PR #6 platform matrix passes application/install/build smoke on all five desktop targets. Each later release revision still needs its own verified CI artifacts.
2. Production signing requires repository credentials and the enabled stable
   release gate. CLI and native libraries share signature verification and
   notarization checks; missing credentials block publication.
3. Android cross-compilation is separate from application smoke. Local physical-
   host emulator smoke passed; a dedicated physical CI runner is not provisioned.
   Physical Android devices and other Android versions remain unverified.
4. Complete license clearance for the exact CI dependency closure and any required
   corresponding-source/relinking materials. Local upstream source archives have
   verified SHA-256 and extracted notices, but inventories alone are not clearance.
5. Rams `quick_review` with `via: rules` could not run because workspace review
   credits are exhausted. Direct app and extension tests do not replace it.

Concurrent installation and crash recovery across two lockfiles remain unsupported.
Debug benchmark ratios exceeded the existing informational threshold; matching
Release checkpoints verify results and timing comparisons. No performance claim
is based on simultaneous builds or comparisons between Debug and Release.

Generated Debug/sanitizer builds, redundant Qt/NDK downloads and duplicate
staging directories were removed for recording space. Verification logs,
release candidates and their verified corresponding Qt source archives remain.
Emulator images are restored only when needed for application verification. Project source and lockfiles were
preserved during authorized cleanup.

Release publication validates every staged SHA-256 before querying or uploading
to GitHub. Modified, duplicate, unlisted, escaping and incomplete manifest entries
are rejected; all 27 release-packaging tests pass locally.
