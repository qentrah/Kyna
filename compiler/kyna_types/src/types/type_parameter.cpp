// Implements constrained generic type-parameter identity and interning.
#include "type_pool.hpp"
#include <kyna/types/type_parameter.hpp>
#include <kyna/types/basic_type.hpp>

#include <set>

namespace kyna::types {
namespace {
struct Less {
  bool operator()(const TypeParam *left, const TypeParam *right) const {
    if (left->name() != right->name())
      return left->name() < right->name();
    return left->constraint()->str() < right->constraint()->str();
  }
};
TypePool<TypeParam, Less> &pool() {
  static TypePool<TypeParam, Less> values;
  return values;
}
} // namespace

const TypeParam *TypeParam::make(std::string name, TypePtr constraint) {
  auto created = std::unique_ptr<TypeParam>(new TypeParam(std::move(name), constraint ? constraint : Universe::Any()));
  return pool().intern(std::move(created));
}

const Type *TypeParam::underlying() const { return constraint_->underlying(); }

bool TypeParam::isAssignableTo(const Type *target) const {
  return isIdenticalTo(target) || constraint_->isAssignableTo(target);
}

bool TypeParam::isIdenticalTo(const Type *other) const {
  return this == other ||
         (other && other->kind() == TypeKind::TypeParam &&
          name_ == static_cast<const TypeParam *>(other)->name_ &&
          constraint_->isIdenticalTo(static_cast<const TypeParam *>(other)->constraint_));
}
} // namespace kyna::types
