# Built with Kyna

Real applications and focused examples built with Kyna. The documentation website follows [Qentrah's current theme](https://qentrah.com/) and includes an [application gallery](https://up-to-code.github.io/kyna-docs/docs/built-with-kyna).

| Application | Type | What Kyna owns | Native libraries | Source |
| --- | --- | --- | --- | --- |
| Kyna Music | Desktop application | Navigation, search, likes, playlists, queue, shuffle, repeat and playback decisions | Typed Qt Quick + Multimedia adapter | [Application repository](https://github.com/qentrah/kyna-music) |
| Native library showcase | Interactive demo | Input callbacks, hull drawing and regression actions | `gui`, `geometry`, `ml` | [showcase.ky](../examples/native/apps/showcase.ky) |
| Convex hull viewer | GUI example | Hull calculation and drawing | `gui`, `geometry` | [gui_hull.ky](../examples/native/apps/gui_hull.ky) |
| Mesh inspection | CLI example | OFF loading, topology/measurement requests and output | `geometry` | [mesh.ky](../examples/native/apps/mesh.ky) |
| Linear regression | CLI example | Training, prediction and model disposal | `ml` | [regression.ky](../examples/native/apps/regression.ky) |

Other Qentrah products are not listed as Kyna applications unless they have Kyna source and runnable evidence.

## Kyna Music

A native desktop player for local music, with six original CC0 instrumentals and original artwork. Kyna owns application behavior; Qt Quick owns the declarative layout and Qt Multimedia supplies audio through C ABI 2.

[Actual screenshots](https://github.com/qentrah/kyna-music/tree/main/docs/screenshots) · [Working video](https://github.com/qentrah/kyna-music/blob/main/docs/videos/kyna-music-macos.mp4) · [Build tour](https://github.com/qentrah/kyna-music/blob/main/docs/build-tour.md) · [Architecture](https://github.com/qentrah/kyna-music/blob/main/docs/architecture.md)

| Part | Source |
| --- | --- |
| Entry point and application icon | [main.ky](https://github.com/qentrah/kyna-music/blob/main/main.ky) |
| Application decisions and handlers | [src/app.ky](https://github.com/qentrah/kyna-music/blob/main/src/app.ky) |
| Kyna behavior and lifetime tests | [tests](https://github.com/qentrah/kyna-music/tree/main/tests) |
| Native UI and audio adapter | [ui](https://github.com/qentrah/kyna-music/tree/main/ui) and [native/src](https://github.com/qentrah/kyna-music/tree/main/native/src) |
| Automated build/test/package actions | [tools/build.py](https://github.com/qentrah/kyna-music/blob/main/tools/build.py) |

The [desktop workflow](https://github.com/qentrah/kyna-music/actions/runs/38350021366) passes Windows x64, Linux x64 / Ubuntu 24.04 and macOS ARM64 / macOS 14 at `72a79fa`. It verifies real audio decoding and advancing playback, callbacks after GC, persistence, native launchers and SDK-free packages. Production signatures/notarization and other OS/CPU combinations remain outside that evidence.

The app's build CLI provides `build`, `check`, `test`, `run` and `package` actions. Follow its [platform requirements and commands](https://github.com/qentrah/kyna-music#run-and-build). Packaging uses `ky build main.ky`, native dependency inventories and checksums; recipients do not need a compiler or Qt SDK.

## Build the library examples

Enable only the [native libraries](libraries.md) your application needs. [Actual recordings](videos/README.md) demonstrate GUI, geometry, regression and Android lifecycle behavior. Android's cross-compilation and recorded emulator smoke do not establish physical-device support.

Start a new open-source project with `ky generate repo my-app`. Explicit `--github OWNER/REPO` also creates and pushes a public repository. See [repository generation and icons](repository-generation.md) for prerequisites and declared application assets.
