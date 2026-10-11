// Owns immutable interned types until process shutdown, without leaking allocations.
#pragma once
#include <memory>
#include <set>
#include <utility>

namespace kyna::types {
// Type destructors release owned strings/vectors, never dereference other TypePtrs.
// This permits independent pools to shut down in any static destruction order.
template <class T, class Less> class TypePool {
  struct Compare {
    bool operator()(const std::unique_ptr<T> &left, const std::unique_ptr<T> &right) const {
      return Less{}(left.get(), right.get());
    }
  };
  std::set<std::unique_ptr<T>, Compare> values;
public:
  std::pair<T *, bool> insert(std::unique_ptr<T> &value) {
    if (const auto found = values.find(value); found != values.end()) return {found->get(), false};
    const auto [found, inserted] = values.insert(std::move(value));
    return {found->get(), inserted};
  }
  const T *intern(std::unique_ptr<T> value) {
    return insert(value).first;
  }
};
} // namespace kyna::types
