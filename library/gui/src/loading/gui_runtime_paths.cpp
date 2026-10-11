// Owns adapter-relative Qt plugin and QML paths for installed native packages.
#include "gui_runtime_paths.hpp"
#include <QCoreApplication>
#include <QQmlEngine>
#include <filesystem>
#ifdef _WIN32
#include <windows.h>
#else
#include <dlfcn.h>
#endif
namespace kyna::gui {
namespace {
std::filesystem::path moduleDirectory() {
#ifdef _WIN32
  HMODULE module{};
  if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                         reinterpret_cast<LPCWSTR>(&moduleDirectory), &module)) return {};
  wchar_t buffer[32768];
  auto length = GetModuleFileNameW(module, buffer, 32768);
  if (!length || length == 32768) return {};
  return std::filesystem::path(std::wstring(buffer, length)).parent_path();
#else
  Dl_info info{};
  if (!dladdr(reinterpret_cast<void *>(&moduleDirectory), &info) || !info.dli_fname) return {};
  return std::filesystem::absolute(info.dli_fname).parent_path();
#endif
}
}
void configurePackagedRuntime(QQmlEngine *engine) {
  const auto directory = moduleDirectory();
  if (directory.empty()) return;
  const auto runtime = directory / "qt";
  if (!std::filesystem::is_directory(runtime)) return;
  const auto plugins = QString::fromStdString((runtime / "plugins").string());
  QCoreApplication::setLibraryPaths({plugins});
  if (engine) engine->setImportPathList({QString::fromStdString((runtime / "qml").string()), "qrc:/qt/qml"});
}
}
