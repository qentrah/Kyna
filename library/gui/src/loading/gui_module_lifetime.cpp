// Owns Windows code residency for Qt's process-global meta-type registrations.
#include "gui_module_lifetime.hpp"
#if defined(_WIN32)
#define NOMINMAX
#include <windows.h>
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
}
