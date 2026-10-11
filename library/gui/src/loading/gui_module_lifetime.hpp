#pragma once
#include <filesystem>
namespace kyna::gui {
void retainGuiModule();
void retainGuiRuntimeDependencies(const std::filesystem::path &directory);
}
