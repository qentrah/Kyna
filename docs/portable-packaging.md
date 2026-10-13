# Portable runtime packaging

`python3 build_tools/packaging/stage_delivery.py --build build-release --output delivery`
stages the CLI, resolves its non-system shared-library closure, relocates it,
and exercises a moved copy through install, reinstall, project creation, checking,
and checksum rejection. Add `--native` for the optional GUI, geometry and ML
adapters. Use a fresh output directory. Linux requires `patchelf`; Windows requires
MSVC `dumpbin`; macOS requires `otool`, `install_name_tool`, and `codesign`.

macOS bundles use relative loader paths, preserved Qt framework resources and
ad-hoc signatures during testing. Stable distribution must sign the completed
payload and satisfy the existing notarization gate. ELF bundles use `$ORIGIN`
paths. Windows modules resolve app-local DLLs beside the module; OS API DLLs
remain system dependencies. Qt QML imports and platform plugins are staged beside
the GUI adapter and selected explicitly at runtime.

Every payload includes `runtime-inventory.json` with relocated binary hashes,
original dependency paths, and excluded system dependencies. The inventory is
build evidence; it is not a license clearance certificate. vcpkg copyright notices
and repository dependency notices are copied into `licenses/`. Before publishing,
review the exact closure, its notices, required corresponding source and relinking
materials. Locally built Homebrew payloads do not automatically inherit vcpkg
license coverage and remain release candidates until that inventory is complete.

`ky build` retains these runtime directories and licenses. Explicit native modules
are isolated in separate directories to avoid DLL basename collisions. Native
packages with dependencies must use verified archives containing their entire
closure; a raw adapter dependency describes only that single file. Archive contents
are rehashed on use, including source wrappers and runtime dependencies.

Bash, PowerShell, and npm installers retain the payload's runtime dependencies,
licenses and installed C++ ABI headers. Self-uninstall removes managed SDK headers too.
The npm adapter downloads the same archive and `SHA256SUMS` for its exact version;
publication remains an owner action. No package-provided install scripts execute.
Concurrent installers and crash recovery across the two lockfiles remain outside
the supported transaction guarantee.

`archive_delivery.py` refuses changed inventory binaries, escaping paths, links
and native payloads without application proof. Native workflow jobs use
`--native-only` so they cannot replace CLI archives from the dedicated CLI jobs.
Development-install adapter copies are excluded from the CLI payload; each adapter
ships in its own verified package. After production signing, inventories are
refreshed to describe the signed bytes.

The GUI payload includes notices extracted from vendor-checksummed Qt source
archives. Local Homebrew closures also have verified source inventories and build
recipes. CI source/version and copyright inventories follow the actual resolved
packages. CGAL GPL/commercial terms and Qt LGPL/commercial terms remain distinct;
Kyna's license does not relicense either dependency.

Portable means the verified dependency closure moves with the application. It
does not guarantee compatibility with older operating systems than the build's
system ABI. The release jobs use Ubuntu 24.04, macOS 14 ARM64/macOS 15 Intel and
Windows hosted runners; test the intended OS version before advertising support.
Local Homebrew candidates are development artifacts, not substitutes for CI builds.

Qt SDK debug bundles (`.dSYM`, `.pdb`) and development-only archives are excluded.
Universal Mach-O dependency and RPATH headers are deduplicated per architecture.
ELF dependencies are copied as regular files under their loader SONAME, preserving
versioned lookup names without archive symlinks. Regression tests cover these
hosted macOS/Linux ARM64 failures. Dependency binary caches are saved even when
subsequent packaging fails.

Windows dependency scans exclude virtual `api-ms-*` and `ext-ms-*` API-set names,
which the OS loader supplies. Missing real DLLs still fail staging. Scanner errors
preserve the underlying tool diagnostic to make CI failures actionable.
