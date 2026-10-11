# Safety audit and release verification

The audit uses the existing C++ compiler pipeline and VM. It introduces no native
code backend. Each behavior below has executable regression coverage.

| Area | Verification and result |
| --- | --- |
| Import contracts | `verify_type_contracts.py`: checked named/namespace/aliased contracts, private dependency retention without namespace exposure, local/member alias resolution, nested object and generic-nullability compatibility, visibility, type-only erasure, generic arguments, nullability, callback incompatibility, duplicates and cold/warm on-disk dependency changes and compiler/checker build fingerprint invalidation and forged dependency-sidecar rejection |
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
and `ky build`. The current source also passes all 57 sanitizer tests and all 59 optional-package
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
