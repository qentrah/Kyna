// Owns Windows code residency for Qt adapters and their packaged dependencies.
#include "gui_module_lifetime.hpp"
#if defined(_WIN32)
#define NOMINMAX
#include <windows.h>
#include <algorithm>
#include <cwctype>
#include <mutex>
#include <stdexcept>
#include <system_error>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#endif

namespace kyna::gui {
void retainGuiModule() {
#if defined(_WIN32)
  // QML can retain EventBridge's meta-type data after a session closes. Keep
  // code/static data mapped, as Qt's own PreventUnloadHint plugin policy does.
  // Pin only on first GUI use: install/check sessions remain fully unloadable.
  HMODULE module{};
  if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                         GET_MODULE_HANDLE_EX_FLAG_PIN,
                         reinterpret_cast<LPCWSTR>(&retainGuiModule), &module))
    throw std::system_error(static_cast<int>(GetLastError()), std::system_category(),
                            "cannot retain the Qt GUI adapter");
#endif
}
void retainGuiRuntimeDependencies(const std::filesystem::path &directory) {
#if defined(_WIN32)
  static std::once_flag retained;
  std::call_once(retained, [&] {
    // Nested QML/platform plugins cannot find sibling runtime DLLs using their
    // own directory. Load the verified package's flat closure by absolute path,
    // without changing PATH or the embedding process's DLL search policy.
    // Called after QGuiApplication exists, before importing QML components.
    QFile inventory(QString::fromStdWString((directory / "runtime-inventory.json").wstring()));
    if (!inventory.open(QIODevice::ReadOnly) || inventory.size() > 8 * 1024 * 1024)
      throw std::runtime_error("cannot read packaged GUI runtime inventory");
    const auto document = QJsonDocument::fromJson(inventory.readAll());
    const auto binaries = document.object().value("binaries");
    if (!document.isObject() || document.object().value("schema").toString() != "kyna.portable-runtime/v1" ||
        !binaries.isArray() || binaries.toArray().isEmpty() || binaries.toArray().size() > 10000)
      throw std::runtime_error("invalid packaged GUI runtime inventory");
    // Do not execute extra DLLs dropped into an installed package directory.
    for (const auto &record : binaries.toArray()) {
      const auto name = record.toObject().value("path").toString().toStdWString();
      const std::filesystem::path relative(name);
      if (name.empty() || name.find(L'\0') != std::wstring::npos || relative.has_root_path())
        throw std::runtime_error("invalid packaged GUI dependency path");
      for (const auto &part : relative)
        if (part == "..") throw std::runtime_error("packaged GUI dependency escapes its directory");
      if (relative.has_parent_path()) continue;
      auto extension = relative.extension().wstring();
      std::transform(extension.begin(), extension.end(), extension.begin(),
                     [](wchar_t value) { return std::towlower(value); });
      if (extension != L".dll") continue;
      // Reuse the Qt runtime already owned by an embedding host rather than
      // creating a second copy with different process-global Qt state.
      HMODULE loaded{};
      if (GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_PIN, relative.c_str(), &loaded)) continue;
      const auto path = directory / relative;
      loaded = LoadLibraryExW(path.c_str(), nullptr, LOAD_WITH_ALTERED_SEARCH_PATH);
      if (!loaded)
        throw std::system_error(static_cast<int>(GetLastError()), std::system_category(),
                                "cannot load packaged GUI dependency " + relative.string());
      HMODULE pinned{};
      const bool success = GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                                             GET_MODULE_HANDLE_EX_FLAG_PIN,
                                             reinterpret_cast<LPCWSTR>(loaded), &pinned);
      const auto error = success ? ERROR_SUCCESS : GetLastError();
      FreeLibrary(loaded);
      if (!success)
        throw std::system_error(static_cast<int>(error), std::system_category(),
                                "cannot retain packaged GUI dependency " + relative.string());
    }
  });
#else
  (void)directory;
#endif
}
}
