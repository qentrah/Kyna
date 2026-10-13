# Optional native dependency inventory

Local validation on macOS ARM64 used Qt base/declarative 6.11.2, CGAL 6.2.1,
mlpack 4.8.0, Armadillo 15.6.1, cereal 1.3.2, ensmallen 3.11.1, and GMP 6.3.0.
Qt Android development provisioning uses Qt 6.7.3 separately from desktop Qt.
These dependencies are optional and absent from the default runtime contract.

- Qt Core/Gui/Qml/Quick: commercial or LGPL/GPL licensing depending on component.
  Distribution must include the applicable license texts and meet relinking,
  replacement, and source/notice obligations. This adapter dynamically links Qt.
  Review the exact deployed plugins too: [Qt licensing](https://doc.qt.io/qt-6/licensing.html).
- CGAL Kernel and Convex Hull packages have LGPL/commercial options. Polygon Mesh
  Processing has GPL/commercial conditions. The combined geometry adapter includes
  mesh processing; do not describe it as uniformly permissive or LGPL.
  [CGAL package licenses](https://doc.cgal.org/latest/Manual/license.html).
- mlpack and Armadillo use BSD licenses; cereal uses BSD; ensmallen uses BSD.
  Retain the installed versions' copyright notices and full license texts in
  distributed native packages. GMP uses LGPL/GPL options; retain its applicable
  notices when distributed.

Release archives must carry a `licenses/` inventory for their exact dependency
versions. Optional package licensing does not change the core project's license.
Cross-platform release bundles still require relocation/deployment validation.

Headless application verification uses Qt's [software scene-graph renderer](https://doc.qt.io/qt-6/qtquick-visualcanvas-adaptations-software.html)
with `QT_QUICK_BACKEND=software` and the offscreen platform on macOS and Linux. This checks GUI events
and lifecycle without requiring a hosted-runner GPU; it does not establish hardware
renderer coverage. Windows runners use the native Windows platform and font
database in their desktop session. The Qt 6.7.3 offscreen plugin crashed there,
including with an explicit system-font directory, so it does not establish Windows
application support. The native Windows retry also faults and requires the
exception-stack probe; changing the backend alone did not fix it. System fonts are not copied into Kyna archives. Windows Qt messages are forced to stderr, and failed child
processes report their decimal and hexadecimal exit codes. A manual optional-package
workflow can select one desktop target for diagnosis; normal PR/release runs retain
all five desktop targets and Android cross-compilation.

Windows closure scanning stops recursion at DLLs resolved from the OS root,
System32, SysWOW64 or WinSxS. MSVC redistributables remain included and audited.
This follows CMake's [post-resolution dependency filtering](https://cmake.org/cmake/help/latest/command/file.html#get-runtime-dependencies);
application DLLs, including those in temporary directories, still require resolution.
The inventory records this system-dependency policy rather than treating OS-only
service DLLs as application artifacts.

GUI session bookkeeping is plain C++ state. Its QObject event bridge and QML
engine are created after `QGuiApplication` and destroyed before it, following
Qt's [QObject lifetime rule](https://doc.qt.io/qt-6/threads-qobject.html). Type
checking native exports does not create a Qt application. An embedded Qt host
must provide a `QGuiApplication` and invoke GUI work on its UI thread; incompatible
hosts and wrong-thread calls produce structured native failures.

On Windows, the first GUI operation pins the adapter image until process exit.
Qt retains process-global meta-type data after QML engines close; the captured
Windows crash was in Qt6Qml reading unmapped memory after the Kyna program
completed. This follows Qt's [PreventUnloadHint plugin policy](https://doc.qt.io/qt-6/qpluginloader.html)
using [GetModuleHandleExW PIN](https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-getmodulehandleexw).
Sessions still release objects, resource handles and callback roots. Metadata-only
install/check sessions do not pin the module or start Qt. Replace a GUI DLL only
after its running application exits. Repeated embedded sessions have regression
coverage. Hosted Windows GUI execution, shutdown and both embedded sessions
pass at `457054c`; complete installation and relocated packaging remain gated
on the final matrix.

Packaged Windows GUI startup loads the inventoried sibling DLL closure by
absolute path after creating/validating `QGuiApplication`, before importing QML.
Nested QML plugins such as WorkerScript otherwise search their own plugin folder
and cannot find the package's root DLLs once SDK PATH entries are removed. These
DLL images follow the same process-exit residency rule as Qt plugin code; session
objects and callback roots still close normally. This uses
[LoadLibraryExW's explicit altered search path](https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-loadlibraryexw),
without changing PATH or the embedding host's global DLL search policy.

Only root DLLs named in `runtime-inventory.json` are preloaded; unlisted files
are ignored. An existing embedding host's loaded DLLs are reused and retained
rather than loading another copy of Qt's global state. A failed inventory or DLL
load does not commit a partially initialized QML engine, so startup can retry
after correction in the same session. Installed inventory/files remain covered
by the native lockfile checksums.

Linux x86_64 ML builds request OpenBLAS's `dynamic-arch` feature. The pinned
[vcpkg port](https://github.com/microsoft/vcpkg/blob/63feddf004cc39169a8b0b7f79c2eba5065d6140/ports/openblas/cmake-project-include.cmake)
otherwise optimizes for the build host, which is incompatible with reusing a
CPU-specific cache on another hosted runner. Dynamic dispatch uses the port's
baseline common code and selects optimized kernels at runtime. CI additionally
runs the C++/Kyna regression oracle with the older NEHALEM kernel selected. This
addresses a Linux x86_64 illegal-instruction failure; it is not a performance
improvement claim or a guarantee for untested CPU/OS combinations.
