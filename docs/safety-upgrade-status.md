# Safety and native-library upgrade status

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
- Fresh optional-library configuration: all 59 CTests passed.
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

Core Linux/macOS portable CI passed at `82c9e93`. Earlier optional Linux/macOS
CTest and Android cross-compilation passed. Windows exposed sibling DLL search,
now corrected with `LoadLibraryExW`; final five-target CLI/native release
preparation is running at `7b44cd2`. Historical passes do not establish that
all final-head targets are supported.

## Remaining release gates

1. Finish final platform CI and fix any failures. Native packages must pass actual
   application/install/build smoke before their desktop target is supported.
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

Generated Qt/NDK toolchains are preserved in verified local backups under
`build-release/verification`. Emulator images use sparse restoration. Sanitizer
logs are preserved; its previous generated archive was removed for recording
space. Project source and lockfiles were preserved during authorized cleanup.
