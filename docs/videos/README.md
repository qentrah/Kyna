# Verified application recordings

These are recordings of running applications, not animations or mockups. They have
no microphone or system audio. The desktop recording contains only the Kyna
window; the Android recording contains only the disposable ARM64 emulator display.

- [Desktop GUI + CGAL + mlpack video](kyna-native-showcase-macos.mp4)
  ([result image](kyna-native-showcase-macos.png)): edit the input, activate the
  accessible hull and regression buttons, and read the input callback. Expected
  results are four hull vertices, predictions `[9, 11]`, and the edited text.
- [Android ARM64 lifecycle video](kyna-android-arm64-smoke.mp4)
  ([application image](kyna-android-arm64-smoke.png)): the Qt application runs on
  Android 14, moves to the background and resumes, then completes its retained
  timer callback and shuts down. [Application proof markers](kyna-android-arm64-smoke.log)
  record actual startup and completion. This does not establish physical-device
  support or desktop geometry/ML support on Android.

Desktop source: [showcase.ky](../../examples/native/apps/showcase.ky).
Load all three relocated adapters with `--native-library`, then run that source.
The showcase keeps callbacks in Kyna and performs garbage collection before
entering the UI loop. Repeated clicks do not grow the result list.

macOS recording:

```bash
swiftc -parse-as-library tools/recording/record_window.swift -o record-window
./record-window 'Kyna: GUI, CGAL and mlpack' showcase.mp4 35
```

Android recording (after installing the smoke APK on a disposable emulator):

```bash
python3 tests/native/record_android_smoke.py \
  --serial emulator-5554 --output android-smoke.mp4
```

Both tools select the application explicitly. Screen recording requires the host's
normal recording permission. The Android harness fails if the application does
not produce its completion marker; unrelated emulator process failures do not
count as application failures.
