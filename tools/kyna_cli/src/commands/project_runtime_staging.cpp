// Owns copying the verified runtime closure into an application bundle.
#include "project_internals.hpp"
namespace kyna::cli {
void stageApplicationRuntime(const fs::path &executable, const fs::path &destination) {
  const auto bin = fs::absolute(executable).parent_path();
  const auto prefix = bin.parent_path();
  if (fs::is_directory(prefix / "lib/runtime")) {
    fs::create_directories(destination / "lib/runtime");
    fs::copy(prefix / "lib/runtime", destination / "lib/runtime", fs::copy_options::recursive | fs::copy_options::overwrite_existing);
  }
  // Windows app-local DLLs and any adjacent Unix dependencies follow the CLI.
  for (const auto &entry : fs::directory_iterator(bin))
    if (entry.is_regular_file() && (entry.path().extension() == ".dll" || entry.path().extension() == ".dylib" || entry.path().extension() == ".so"))
      fs::copy_file(entry.path(), destination / "bin" / entry.path().filename(), fs::copy_options::overwrite_existing);
  if (fs::is_directory(prefix / "licenses"))
    fs::copy(prefix / "licenses", destination / "licenses", fs::copy_options::recursive);
}
void stageNativeRuntime(const fs::path &library, const fs::path &destination) {
  for (const auto &name : {"lib", "qt", "licenses"}) {
    const auto source = library.parent_path() / name;
    if (fs::is_directory(source)) fs::copy(source, destination / name, fs::copy_options::recursive);
  }
#ifdef _WIN32
  for (const auto &entry : fs::directory_iterator(library.parent_path()))
    if (entry.is_regular_file() && entry.path().extension() == ".dll" && entry.path() != library)
      fs::copy_file(entry.path(), destination / entry.path().filename(), fs::copy_options::overwrite_existing);
#endif
}
}
