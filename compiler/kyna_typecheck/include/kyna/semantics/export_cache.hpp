#pragma once

#include <filesystem>
#include <vector>
#include <map>
#include <optional>
#include <kyna/semantics/type_model.hpp>

namespace kyna::export_cache {

// User-local cache bucket; dependency/source-tree sidecars are never trusted.
std::filesystem::path cachePath(const std::filesystem::path &modulePath);

// True when KYNA_DISABLE_EXPORT_CACHE is unset/empty.
bool enabled();

bool stampMatches(const std::vector<std::filesystem::path> &sources,
                  const std::filesystem::path &cacheFile);

void writeStamp(const std::vector<std::filesystem::path> &sources,
                const std::filesystem::path &cacheFile);

void invalidate(const std::filesystem::path &cacheFile);

std::optional<std::map<std::string, TypeRef>> readBindings(const std::filesystem::path &cacheFile);
void writeBindings(const std::vector<std::filesystem::path> &sources,
                   const std::filesystem::path &cacheFile,
                   const std::map<std::string, TypeRef> &bindings);

} // namespace kyna::export_cache
