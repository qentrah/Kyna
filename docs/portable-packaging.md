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

Bash, PowerShell, and npm installers retain the payload's runtime dependencies.
The npm adapter downloads the same archive and `SHA256SUMS` for its exact version;
publication remains an owner action. No package-provided install scripts execute.
Concurrent installers and crash recovery across the two lockfiles remain outside
the supported transaction guarantee.
