// Implements nominal type identity, staged completion, and assignability.
#include "type_pool.hpp"
#include <kyna/types/named_type.hpp>
#include <kyna/types/basic_type.hpp>
#include <kyna/types/interface_type.hpp>

#include <set>
#include <stdexcept>
#include <string>

namespace kyna::types {
namespace {

struct NamedCompare {
  bool operator()(const NamedType *lhs, const NamedType *rhs) const {
    return lhs->name() < rhs->name();
  }
};

TypePool<NamedType, NamedCompare> &namedPool() {
  static TypePool<NamedType, NamedCompare> pool;
  return pool;
}

} // namespace

NamedType::NamedType(std::string name, TypePtr underlying, std::vector<NamedMethod> methods)
    : name_(std::move(name)), underlying_(underlying), methods_(std::move(methods)) {}

const NamedType *NamedType::make(std::string name, TypePtr underlying,
                                 std::vector<NamedMethod> methods) {
  auto created = std::unique_ptr<NamedType>(new NamedType(std::move(name), underlying, std::move(methods)));
  auto [existing, inserted] = namedPool().insert(created);
  if (!inserted) {
    if (existing->underlying_ && created->underlying_ &&
        !existing->underlying_->isIdenticalTo(created->underlying_)) {
      throw std::invalid_argument("named type completed with a different underlying type");
    }
    if (!existing->methods_.empty() && !created->methods_.empty()) {
      throw std::invalid_argument("named type completed with methods more than once");
    }
    if (!existing->underlying_)
      existing->underlying_ = created->underlying_;
    if (existing->methods_.empty())
      existing->methods_ = std::move(created->methods_);
  }
  return existing;
}

bool NamedType::isAssignableTo(const Type *target) const {
  if (isIdenticalTo(target))
    return true;
  if (!target)
    return false;
  if (target->kind() == TypeKind::Interface)
    return static_cast<const InterfaceType *>(target)->isSatisfiedBy(this);
  // A named type is assignable to its own underlying structural type.
  if (underlying_ && underlying_->isAssignableTo(target))
    return true;
  // Nominal types are assignable to the untyped object/any classifiers.
  if (target->kind() == TypeKind::Basic) {
    const auto kind = static_cast<const BasicType *>(target)->basicKind();
    if (kind == BasicKind::Any || kind == BasicKind::Object)
      return true;
  }
  return false;
}

bool NamedType::isIdenticalTo(const Type *other) const {
  if (this == other)
    return true;
  if (!other || other->kind() != TypeKind::Named)
    return false;
  return name_ == static_cast<const NamedType *>(other)->name_;
}

} // namespace kyna::types
