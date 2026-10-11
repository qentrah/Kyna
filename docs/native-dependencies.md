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
with `QT_QUICK_BACKEND=software` and the offscreen platform. This checks GUI events
and lifecycle without requiring a hosted-runner GPU; it does not establish hardware
renderer coverage. On Windows, `QT_QPA_FONTDIR` points at the installed system
font directory: Qt 6.7.3's [offscreen integration](https://github.com/qt/qtbase/blob/v6.7.3/src/plugins/platforms/offscreen/qoffscreenintegration.cpp)
uses the FreeType font database, whose [font-directory lookup](https://github.com/qt/qtbase/blob/v6.7.3/src/gui/text/qplatformfontdatabase.cpp)
honors that variable. System fonts are not copied into Kyna archives. Windows Qt messages are forced to stderr, and failed child
processes report their decimal and hexadecimal exit codes. A manual optional-package
workflow can select one desktop target for diagnosis; normal PR/release runs retain
all five desktop targets and Android cross-compilation.
