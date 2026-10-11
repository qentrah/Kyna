// Owns Windows code residency for Qt adapters and their packaged dependencies.
#include "gui_module_lifetime.hpp"
#if defined(_WIN32)
#define NOMINMAX
#include <windows.h>
#include <algorithm>
#include <cwctype>
#include <mutex>
#include <system_error>
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
    for (const auto &entry : std::filesystem::directory_iterator(directory)) {
      auto extension = entry.path().extension().wstring();
      std::transform(extension.begin(), extension.end(), extension.begin(),
                     [](wchar_t value) { return std::towlower(value); });
      if (!entry.is_regular_file() || extension != L".dll") continue;
      HMODULE loaded = LoadLibraryExW(entry.path().c_str(), nullptr, LOAD_WITH_ALTERED_SEARCH_PATH);
      if (!loaded)
        throw std::system_error(static_cast<int>(GetLastError()), std::system_category(),
                                "cannot load packaged GUI dependency " + entry.path().filename().string());
      HMODULE pinned{};
      const bool success = GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                                             GET_MODULE_HANDLE_EX_FLAG_PIN,
                                             reinterpret_cast<LPCWSTR>(loaded), &pinned);
      const auto error = success ? ERROR_SUCCESS : GetLastError();
      FreeLibrary(loaded);
      if (!success)
        throw std::system_error(static_cast<int>(error), std::system_category(),
                                "cannot retain packaged GUI dependency " + entry.path().filename().string());
    }
  });
#else
  (void)directory;
#endif
}
}
