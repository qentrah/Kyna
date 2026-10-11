#include "type_pool.hpp"
// Implements pointer identity, rendering, assignability, and interning.
#include <kyna/types/pointer_type.hpp>
#include <kyna/types/basic_type.hpp>

#include <set>

namespace kyna::types {
namespace {
struct Less {
  bool operator()(const PointerType *left, const PointerType *right) const {
    return left->str() < right->str();
  }
};
TypePool<PointerType, Less> &pool() {
  static TypePool<PointerType, Less> values;
  return values;
}
} // namespace

const PointerType *PointerType::make(TypePtr base) {
  auto created = std::unique_ptr<PointerType>(new PointerType(base));
  return pool().intern(std::move(created));
}

std::string PointerType::str() const { return "ptr<" + base_->str() + ">"; }

bool PointerType::isAssignableTo(const Type *target) const {
  return isIdenticalTo(target) || isBasic(target, BasicKind::Object) ||
         isBasic(target, BasicKind::Any);
}

bool PointerType::isIdenticalTo(const Type *other) const {
  return this == other ||
         (other && other->kind() == TypeKind::Pointer &&
          base_->isIdenticalTo(static_cast<const PointerType *>(other)->base_));
}
} // namespace kyna::types
