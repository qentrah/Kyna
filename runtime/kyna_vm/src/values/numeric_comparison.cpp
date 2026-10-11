// Owns portable numeric ordering without widening signed integers to double.
#include <kyna/execution/numeric_comparison.hpp>
#include <kyna/execution/runtime_object_model.hpp>
#include <cmath>
namespace kyna {
namespace {
std::optional<int> compareIntegerFloat(std::int64_t integer, double real) {
  if (std::isnan(real)) return {};
  constexpr double boundary = 9223372036854775808.0;
  if (real < -boundary) return 1;
  if (real >= boundary) return -1;
  const auto truncated = static_cast<std::int64_t>(real);
  if (integer < truncated) return -1;
  if (integer > truncated) return 1;
  const auto integral = static_cast<double>(truncated);
  return real > integral ? -1 : real < integral ? 1 : 0;
}
}
std::optional<int> compareNumbers(const Value &left, const Value &right) {
  const auto a = std::get_if<std::int64_t>(&left.data);
  const auto b = std::get_if<std::int64_t>(&right.data);
  const auto x = std::get_if<double>(&left.data);
  const auto y = std::get_if<double>(&right.data);
  if (a && b) return *a < *b ? -1 : *a > *b ? 1 : 0;
  if (a && y) return compareIntegerFloat(*a, *y);
  if (x && b) { const auto result = compareIntegerFloat(*b, *x); return result ? std::optional<int>(-*result) : std::nullopt; }
  if (x && y && !std::isnan(*x) && !std::isnan(*y)) return *x < *y ? -1 : *x > *y ? 1 : 0;
  return {};
}
}
