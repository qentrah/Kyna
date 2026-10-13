# Android ARM64 application shell

`tools/android-shell` embeds Kyna in a Qt Android application. Qt supplies the
Activity and Gradle packaging; the C++ shell extracts the explicit application
file list, loads the packaged GUI adapter, and runs `main.ky`. Application logic
and event handlers stay in Kyna. Qt Network replaces host libcurl for this target.
Lifecycle callbacks use `guiOnLifecycle` on the UI/VM thread. Resource and callback
cleanup runs when the language session closes.

Install matching desktop host Qt and Android ARM64 Qt, Android SDK/NDK, and JDK.
Use Qt's `qt-cmake`, not a host-only CMake configuration:

```bash
/path/to/Qt/android_arm64_v8a/bin/qt-cmake -S . -B build-android \
  -DCMAKE_BUILD_TYPE=Release -DKYNA_BUILD_TESTS=OFF -DKYNA_BUILD_CLI=OFF \
  -DKYNA_WITH_GUI=ON -DKYNA_ANDROID_SHELL=ON \
  -DANDROID_PLATFORM=android-28 \
  -DQT_HOST_PATH=/path/to/matching/host/Qt \
  -DANDROID_SDK_ROOT=/path/to/sdk -DANDROID_NDK_ROOT=/path/to/ndk \
  -DKYNA_ANDROID_APP_SOURCE=/path/to/kyna-app \
  '-DKYNA_ANDROID_APP_FILES=main.ky;gui.ky'
cmake --build build-android --target apk --parallel
```

`main.ky` is required. Supply every imported module explicitly in
`KYNA_ANDROID_APP_FILES`. The default application is the GUI callback smoke test.
The default smoke application runs for 12 seconds and requires a background/foreground transition. After launch, run `python3 tests/native/verify_android_smoke.py`; it sends Home, relaunches the Activity, and requires the timer, lifecycle, and post-session-cleanup completion marker `KYNA_ANDROID_SMOKE_OK`. A successful cross-compilation
alone is not a supported-target claim: installation, launch, lifecycle, callback,
and shutdown smoke must pass on the target.

On 2026-10-11, the Release shell passed installation, launch, timer callback,
background/foreground lifecycle delivery, garbage collection, and session
shutdown on the Android 14 Google APIs ARM64 emulator. The rendered text, input,
and button were also inspected. This verifies that configuration; other Android
versions, physical devices, geometry/ML on Android, and production signing remain
unverified. The shell resolves the GUI adapter alongside its installed native
library rather than relative to extracted Kyna source.

The checked-in packaging uses SDK/build tools 35, NDK 26.1.10909125, matching
Qt host/Android 6.7.3, JDK 17, Android Gradle plugin 8.6.1, and Gradle 8.7.
[AGP 8.6 compatibility](https://developer.android.com/build/releases/agp-8-6-0-release-notes).
The APK produced by `apk` is unsigned. For local smoke testing only, set
`ANDROID_SDK_ROOT` and `JAVA_HOME`, then run:

```bash
python3 tests/native/sign_android_smoke.py path/to/unsigned.apk kyna-smoke.apk
adb install kyna-smoke.apk
adb logcat -c
adb shell monkey -p org.kyna.application 1
python3 tests/native/verify_android_smoke.py
```

The signing helper uses an ephemeral test certificate. Release publication needs
the application's own signing key.

Qt setup and deployment references:
[Getting started](https://doc.qt.io/qt-6/android-getting-started.html),
[androiddeployqt](https://doc.qt.io/qt-6/android-deploy-qt-tool.html).


The generated local cross-compilation SDK/NDK/Qt downloads were removed after
verification to recover disk space. Reinstall the matching versions above before
a local cross-build, or use the reproducible hosted Android build workflow. The
disposable ARM64 emulator and its verified application recordings are retained.

Hosted CI cross-compiles and uploads the ARM64 APK. GitHub's macOS VM failed
`HVF` initialization even with software emulation requested, so application
smoke is a separate manual workflow gate on a physical Apple Silicon runner
labelled `kyna-android` (with the `self-hosted`, `macOS`, and `ARM64` labels).
Provision Python, JDK 17, the Android SDK and emulator, and at least 8 GiB free;
then enable `android-emulator-smoke` when dispatching Optional native packages.
That job installs the build artifact and requires the lifecycle/callback/shutdown
marker. A hosted build passing without this gate is compilation evidence only.
Stable release tags request this same application gate when
`KYNA_ANDROID_RUNNER_ENABLED=true`. Stable publication rejects an unset/false
variable and waits for the reusable native workflow, including the application
smoke, to succeed. Enable it only after provisioning the labelled runner.

Release preparation names the signed demo `kyna-android-arm64-smoke.apk` and
uploads that single APK rather than intermediate unsigned build directories.
Its version name follows the core project version. CI collects vendor-checksummed
Qt 6.7.3 source archives and embeds their notices, source inventory and Kyna license
through `KYNA_ANDROID_NOTICES_QRC`; matching Qt source archives accompany the APK.
These resources are extracted under the application's `licenses/` directory.
Application authors can present them in their own About/licenses UI. The smoke
certificate remains explicitly temporary, and production licensing/signing review
still applies.
