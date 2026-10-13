// Owns explicit CMake builds of locally authored native packages.
#include "project_internals.hpp"

namespace kyna::cli {
namespace {
void requireSuccess(const ProcessResult &result, const char *phase) {
  if (!result.failedToStart && result.exitCode == 0) return;
  Diagnostic diagnostic{std::string("Native package ") + phase + " failed", {}, false,
                        result.failedToStart ? "KBUILD1004" : "KBUILD1005"};
  diagnostic.category = "build";
  diagnostic.help = result.failedToStart ? "Install CMake and make it available on PATH."
                                        : "Fix the native package CMake configuration or compiler errors, then rebuild.";
  if (!result.startError.empty()) diagnostic.notes.push_back(result.startError);
  if (!result.stdoutText.empty()) diagnostic.notes.push_back(result.stdoutText.substr(result.stdoutText.size() > 8192 ? result.stdoutText.size() - 8192 : 0));
  if (!result.stderrText.empty()) diagnostic.notes.push_back(result.stderrText.substr(result.stderrText.size() > 8192 ? result.stderrText.size() - 8192 : 0));
  throw KynaError(diagnostic);
}
}

int buildNativeProject(const Options &options, const fs::path &root,
                       const fs::path &destination, std::ostream &output) {
  const auto source = fs::absolute(options.input.empty() ? root : fs::path(options.input));
  ProcessConfig config;
  config.program = "cmake";
  config.captureOutput = true;
  config.args = {"-S", source.string(), "-B", destination.string(), "-DCMAKE_BUILD_TYPE=Release"};
  const auto host = productionRuntimeCapabilities();
  auto result = host.processes->spawn(config);
  requireSuccess(result, "configuration");
  output << result.stdoutText << result.stderrText;
  config.args = {"--build", destination.string(), "--config", "Release"};
  result = host.processes->spawn(config);
  requireSuccess(result, "compilation");
  output << result.stdoutText << result.stderrText;
  return 0;
}
}
