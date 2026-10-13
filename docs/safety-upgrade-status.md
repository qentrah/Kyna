# Safety and native-library upgrade status

PR #6 is merged. Its final [core CI](https://github.com/qentrah/Kyna/actions/runs/38344931584) and [native platform matrix](https://github.com/qentrah/Kyna/actions/runs/38344931588) passed at `9d33bfb`. PR #7 completes repository generation, icons, explicit application assets, staging containment and Linux ML portability. The prepared 1.0.16 release remains a draft; npm publication belongs to the owner.

## Delivered

- Checked module/type contracts, generic/nullability compatibility, type-only declarations, transitive/versioned export caching, numeric parity and stronger switch/control-flow diagnostics.
- Focused VS Code modules with compiler diagnostic codes, unsaved dependency handling, imported-file locations, Unicode ranges and native/type navigation; consistent console stream/color behavior.
- Typed C ABI 2 packages with callback roots, resource ownership, thread validation, conversion checks and C++ exception translation. Native installation verifies artifacts; `ky build` packages applications and authored bindings.
- Optional Qt Quick GUI, CGAL geometry and mlpack regression packages, including relocated dependency closures, licenses and source inventories. Linux x86_64 BLAS uses runtime CPU dispatch.
- Five desktop release targets and Android ARM64 cross-compilation, with application smoke required for desktop target claims. Android lifecycle smoke is recorded from a local Android 14 ARM64 emulator.
- Public [Kyna Music](https://github.com/qentrah/kyna-music): Kyna application behavior, typed native presentation/audio, real playback, search, playlists, queue, persistence, platform icons, automated builds and portable Windows/Linux/macOS previews. Screenshots, a working video and a build tour are included.
- `ky generate repo NAME [--github OWNER/REPO]`, explicit `[build].assets`, runtime icon selection and containment checks that roll back rejected bundles.

## Verification

Local suites pass 57 Release CTests and 62 optional-library CTests, plus focused extension/npm and release-packaging tests. Earlier Debug and sanitizer baselines pass; the final hosted core matrix reruns Linux Debug and ASan/UBSan with leak detection. Native smoke exercises callbacks/GC, geometry, regression, installation and packaged launchers with original SDK paths removed.

See [release notes](releases/v1.0.16.md) for the exact candidate revision, platform runs and asset provenance; [the safety audit](safety-audit.md) for regression coverage; [portable packaging](portable-packaging.md) and [dependency inventory](native-dependencies.md) for distribution details; and [recordings](videos/README.md) for actual applications.

Benchmark records verify outputs before timing. Hosted performance results are informational; comparisons do not mix Debug/Release or concurrent build workloads. No new compiler backend, automatic C++ header import or arbitrary template exposure is included.

## Remaining external gates and limits

1. Production signing/notarization credentials and the stable-release approval variable must be configured before publication. No release tag or npm publication was created during preparation.
2. Final license clearance is required for the exact dependency closure and corresponding-source/relinking materials. Verified inventories and notices are evidence, not clearance.
3. A dedicated physical Android CI runner is not provisioned. Local emulator smoke does not establish physical-device or other Android-version support.
4. Rams `quick_review` with `via: rules` was attempted after UI changes and returned exhausted workspace credits with no findings. Direct app tests do not replace that review.
5. Concurrent installation and crash recovery across two lockfiles remain unsupported. Additional OS/CPU combinations require their own smoke tests.

Authorized storage cleanup removed generated builds/caches and redundant staging downloads while preserving project source, lockfiles, verification evidence and prepared release materials.
