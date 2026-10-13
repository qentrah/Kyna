# Safety audit and release verification

Current merged checkpoint: PR #6 passed [core platform CI](https://github.com/qentrah/Kyna/actions/runs/38344931584) and [all five desktop native targets plus Android ARM64 cross-compilation](https://github.com/qentrah/Kyna/actions/runs/38344931588) at `9d33bfb`, then merged as `f21e771`. The Windows faults described below are historical and resolved in that checkpoint. Hosted physical Android application smoke remains a separate unprovisioned-runner gate.

The repository-generation/icon follow-up adds regression checks for explicit asset staging, rejected traversal/missing files, source/dependency symlink containment, preserved internal alias paths, and cleanup of rejected bundles. Its local Release suite passes all 57 tests. Exact follow-up platform results are recorded in PR #7.

The audit uses the existing C++ compiler pipeline and VM. It introduces no native
code backend. Each behavior below has executable regression coverage.

| Area | Verification and result |
| --- | --- |
| Import contracts | `verify_type_contracts.py`: checked named/namespace/aliased contracts, private dependency retention without namespace exposure, local/member alias resolution, nested object and generic-nullability compatibility, visibility, type-only erasure, generic arguments, nullability, callback incompatibility, duplicates and cold/warm on-disk dependency changes and compiler/checker build fingerprint invalidation and forged dependency-sidecar rejection |
| Type ownership | Immutable intern pools retain stable pointers and release their allocations at shutdown; duplicate and exception candidates are owned, with destructor-count regression coverage. Signature interning preserves receiver identity instead of merging distinct method signatures. Linux LeakSanitizer exposed the former raw-pointer pool leaks; the focused hosted type-family leak check now passes ([run](https://github.com/qentrah/Kyna/actions/runs/38108365096)). The full Linux suite passes 57/57 Release, Debug and ASan/UBSan tests with leak detection enabled ([run](https://github.com/qentrah/Kyna/actions/runs/38109134996)). |
| Integer boundaries | `test_numeric_parity.cpp`: checked overflow, signed minimum literal, division/remainder edge cases and unary underflow |
| Numeric comparison | Exact int/int and mixed int/float equality and ordering, including adjacent integers above 2^53 and both 2^63 boundaries; shared comparison implementation avoids rounding integer operands |
| Control flow | Duplicate/default ordering codes, constant compatible cases, adjacent large switch cases, nested labeled loops, switch break/continue targets and function boundaries |
| Evaluation | Closure side effects, argument order and short-circuit parity across supported execution paths |
| Native lifetime | Callback retain/release, nested invocation roots, GC stress, foreign/stale resource handles, child ownership, exactly-once destruction and shutdown |
| Conversion | Typed arrays, callback arity/results through `any`, dimensional/finite checks, ABI mismatch and translated C++ failures |
| Installation | SHA-256, native archive file rechecks, link/oversized-member rejection, lock rollback, removed dependencies and relocated applications |

New stable codes include `KSYN1301`, `KSYN1302`, `KSEM1308`, `KSEM1309`,
`KSEM1507`, and `KSEM1604`. See [diagnostics](diagnostics.md).

The current local Debug and Release suites each pass all 57 CTests. The relocated native package
fixture passes GUI callbacks, geometry, regression, checked imports, installation
and `ky build`. The current source also passes all 57 sanitizer tests and all 62 optional-package
tests. LeakSanitizer is unavailable in the current macOS setup.

Hosted CI at `17bee83` passed core Linux/Windows builds and Android cross-compilation.
Its macOS PTY test exposed an asynchronous exit race; the test now checks process
exit before writing EOF and validates its exit status. Earlier optional Linux/macOS
CTest runs passed; Windows exposed module-sibling DLL search, now fixed with
`LoadLibraryExW` and covered by the next hosted run. These are historical results,
not claims that the new PR head has passed CI.

The ARM64 Android APK previously passed a physical-host Android 14 emulator smoke
with lifecycle, retained callbacks, GC and shutdown. Hosted macOS cannot initialize
nested HVF; cross-compilation and the separately opt-in physical-runner application
gate are distinct. A dedicated physical CI runner has not been provisioned.

Rams `quick_review` was requested with `via: rules` for GUI edits, but the service
reported exhausted review credits. Direct application testing does not replace
that outstanding review. Bare-package extension navigation now follows native lockfiles and path dependencies,
using a TOML parser and matching the compiler's declaration suffix priority. Thirteen
focused extension tests pass. Verified source archives and extracted notices now
cover the local CLI, Qt, CGAL and mlpack dependency closures. These inventories do
not replace license clearance. Stable signing and final platform packaging gates
remain required. Real app recordings are in [videos](videos/README.md).

The final compiler source checkpoint `607fb61` passes all local 57-test Debug,
Release and ASan/UBSan suites and the 59-test optional suite. Its focused
[Linux LeakSanitizer check](https://github.com/qentrah/Kyna/actions/runs/38109135038)
passes, including receiver-sensitive signature interning. The full Linux CI job
also passes 57 Release, 57 Debug and 57 ASan/UBSan CTests with `detect_leaks=1`
([completed job](https://github.com/qentrah/Kyna/actions/runs/38109134996)). At `6971895`, native package applications
and relocation pass Linux x86_64/ARM64 and macOS ARM64; the Windows suite passes
58/59, with a GUI access violation. The native Windows platform retry at `9d870a8`
also crashes, so the backend selection did not resolve the defect. A bounded
Windows child-process probe captures exception modules and symbolized stacks;
Windows application support remains gated. Android's hosted APK at `9d870a8`
passes the refreshed local emulator lifecycle recording. Android release assets
now share one directory, avoiding nested paths in merged release artifacts.

The GUI session previously inherited QObject before owning its application.
That violated Qt's required construction/destruction order. The session now
creates a separate event bridge lazily, inside the application's lifetime,
and rejects incompatible Qt hosts and calls from a different UI thread. All
62 local optional CTests pass, including three GUI embedding contracts. Windows
verification of this fix is pending. Rams quick_review with via=rules was
requested after the edit and again reported exhausted workspace credits.
Windows app-local dependencies are inventoried without copying a file over
itself; copy failures retain both source and destination paths.

Rejected timer durations are checked before Qt starts and report `KNATIVE1003`,
even when no usable platform plugin exists. Canvas points are validated before
resource allocation, and partially constructed QML objects have scoped ownership.
The Windows diagnostic probe persists its last Kyna statement to a file, so a
crash cannot erase its checkpoint through buffered program output.

The publisher rehashes every release asset before any GitHub request, rejects
malformed/duplicate/escaping entries and requires exact manifest coverage.
All 28 release-packaging tests pass, including six checksum rejection subcases.
Windows core CI at `835ca2d` passes all 57 CTests and portable CLI/installer
verification ([run](https://github.com/qentrah/Kyna/actions/runs/38111562875)).

The bounded Windows probe now confirms completion of all Kyna statements before
a Qt6Qml shutdown fault reads unmapped memory. GUI use retains its Windows adapter
image for Qt's global meta-type registrations; metadata-only loading remains
unloadable. Session objects and callback roots still close normally, and the
Qt host regression runs two consecutive sessions. Hosted Windows verification at
`457054c` passes the complete GUI program, both host sessions and wrong-thread
checks ([run](https://github.com/qentrah/Kyna/actions/runs/38113966480)).
That run then exposed a separate ML installation fixture that supplied a raw DLL
without its BLAS closure; it did not indicate a remaining GUI crash.

The latest hosted `9b92bbc` Android APK also passes the real emulator lifecycle
recording. The Windows metadata regression checks that descriptor-only loading
unmaps its installer staging DLL. Native dependency caches use a separate
geometry/ML feature key and are saved only after successful configuration;
the former branch cache contained only core ports, repeating a 54-minute cold
native install because an immutable cache hit prevented complete cache saves.

The ML installer regression now supplies a complete relocated runtime archive on
every OS, including raw-build CTest runs. A self-contained authored binding
separately covers legacy single-file installation. Both paths pass locally.
Release relocation removes Qt/QML loader environment variables and, on Windows,
the original Qt, vcpkg and build runtime directories from PATH while retaining
compiler tools. A release regression verifies this isolation. The final platform
run at `da6d905` must pass before all desktop application targets are claimed.
Core CI at `f716aba` passes Linux, macOS and Windows, including the full Linux
Debug/ASan/UBSan suite with leak detection
([run](https://github.com/qentrah/Kyna/actions/runs/38114505914)).

The expanded Windows archive fixture exposed CRLF records from captured tar
output. Archive inspection now removes the Windows record terminator before
validating names, while rejecting embedded controls and original backslash/drive
spellings before filesystem normalization. Native installer tests additionally
reject traversal, drive paths, backslashes and carriage-return member names.
This does not relax extraction's post-validation, link rejection or size bounds.
The hosted APK at `6530819` passes another Android 14 ARM64 lifecycle recording
with startup and post-cleanup completion markers; production signing and the
physical CI runner remain external gates.

Windows at `a77f5b6` passes all 62 raw-build CTests, including complete ML
archives and malicious path rejection. SDK-isolated relocation exposed a QML
WorkerScript plugin dependency lookup failure. GUI startup now loads the packaged
root DLL closure explicitly after the Qt application exists, retaining its images
for Qt global metadata without modifying the process's search policy. The
relocated application test continues running with the original SDK directories
removed from PATH. Final hosted verification of this fix remains required.

The Windows relocation fix at `34f8fed` passes all 62 raw CTests and the SDK-free
GUI/geometry/ML application, install and build checks. The final loader audit
limits preloading to inventoried root DLLs and reuses already loaded host modules.
New Windows portable fixtures plant an unlisted invalid DLL and recover from a
malformed inventory in the same VM. QML engines commit only after configuration
succeeds. All 62 local optional CTests pass after this ownership change. Rams
quick_review was requested again with via=rules for the GUI file and returned
exhausted one-time review credits; it returned no findings.

Event release now also removes lifecycle subscription metadata, so repeated
subscribe/unsubscribe cycles do not retain stale event IDs. Timers and explicit
unsubscription share the same callback release operation. The optional package
fixture and all three GUI host lifetime tests pass after this cleanup.
