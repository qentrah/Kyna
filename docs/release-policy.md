# Release policy

A Kyna release is built from a clean, protected tag after Debug, Release, sanitizer, cross-platform, editor, packaging, and architecture checks pass. Release jobs must use the checked-in dependency manifest and must not publish artifacts produced from a developer working tree.

Official artifacts include checksums and a dependency inventory. Production releases require provenance attestation, macOS Developer ID signing and notarization, Windows Authenticode signing, and verification on clean machines. Missing signing credentials block a production release; workflows must not silently publish unsigned installers under an official stable tag.

Marketplace and Open VSX publishing use repository secrets scoped to their respective publishers. Release logs, crash bundles, and diagnostics must redact authorization headers, credentials, and sensitive URL query values.

The CLI and optional native payloads share a signing helper and refresh binary
inventories after signing. Notarization must return `Accepted`; command success
alone is insufficient. Release assembly waits for all five desktop native package
checks and Android cross-compilation. ARM64 Android application support still
requires its physical-host emulator smoke, separately from cross-compilation.

macOS executables permit explicitly trusted third-party native plug-ins through
`disable-library-validation`, and Qt's QML runtime through `allow-jit`. These
entitlements do not sandbox packages: installing C++ adapters grants native code
execution. See [Apple hardened runtime guidance](https://developer.apple.com/documentation/xcode/configuring-the-hardened-runtime).
